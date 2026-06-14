"""
Docking Worker — 消费 Redis Stream 执行 AutoDock Vina 对接

职责：
- 从 stream:docking 消费 Docking 子任务
- 调用 AutoDock Vina 执行对接计算
- 解析结果，提取 affinity score
- 将结果写回 MySQL (docking_tasks 表) 并更新 Redis 进度

消费者组模式：支持多 Worker 并发消费，Worker 崩溃后任务可被其他 Worker 认领。
"""

import asyncio
import json
import logging
import os
import signal
import sys
import tempfile
import uuid

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.logger import get_logger, setup_logger
from app.core.minio import download_file, get_file_bytes, parse_minio_uri
from app.core.redis import (
    init_redis,
    get_redis,
    stream_ack,
    stream_claim_pending,
    stream_create_consumer_group,
    stream_read_group,
)
from app.models.docking import DockingTask
from app.tools.autodock.vina_runner import AutoDockRunner
from app.tools.autodock.result_parser import AutoDockResultParser

settings = get_settings()
logger = get_logger("worker.docking")


class DockingWorker:
    """AutoDock Vina 对接 Worker

    消费 Redis Stream 中的 Docking 任务，执行对接计算并回写结果。
    """

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"docking-worker-{uuid.uuid4().hex[:8]}"
        self.runner = AutoDockRunner()
        self.parser = AutoDockResultParser()
        self.running = True

    async def start(self):
        """启动 Worker 主循环"""
        logger.info(f"DockingWorker [{self.worker_id}] 启动中...")

        await init_redis()
        await init_db()

        # 创建消费者组
        await stream_create_consumer_group(
            settings.REDIS_STREAM_DOCKING,
            settings.REDIS_CONSUMER_GROUP,
        )

        # 恢复超时任务
        await self._recover_pending_tasks()

        logger.info(f"DockingWorker [{self.worker_id}] 开始消费任务")

        while self.running:
            try:
                messages = await stream_read_group(
                    stream=settings.REDIS_STREAM_DOCKING,
                    group=settings.REDIS_CONSUMER_GROUP,
                    consumer=self.worker_id,
                    count=1,
                    block=5000,
                )

                for msg in messages:
                    await self._process_task(msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker 循环异常: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info(f"DockingWorker [{self.worker_id}] 已停止")

    async def _process_task(self, msg: dict):
        """处理单个 Docking 任务

        Args:
            msg: {"id": msg_id, "data": {...}}
        """
        msg_id = msg["id"]
        task_data = msg["data"]

        job_id = int(task_data.get("job_id", 0))
        drug_id = int(task_data.get("drug_id", 0))
        drug_name = task_data.get("drug_name", "")

        logger.info(f"处理 Docking 任务: job={job_id}, drug={drug_id} ({drug_name})")
        await self._push_log(job_id, f"开始对接: {drug_name} (ID={drug_id})")

        try:
            # 解析完整任务数据
            task_json = task_data.get("task_data", "{}")
            task = json.loads(task_json)

            # ── 模拟模式：生成随机对接分数 ──
            if settings.DOCKING_SIMULATION_MODE:
                affinity = await self._simulate_docking(drug_id, task.get("smiles", ""))
                await self._save_result(job_id, drug_id, affinity, "SUCCESS")
                await self._update_progress(job_id)
                await self._push_log(job_id, f"完成对接: {drug_name}, Score={affinity} kcal/mol")
                return

            # ── 真实对接模式 ──
            with tempfile.TemporaryDirectory(prefix="docking_") as work_dir:
                # 获取或生成配体 PDBQT
                ligand_pdbqt = task.get("ligand_pdbqt") or ""
                smiles = task.get("smiles") or ""
                ligand_local = os.path.join(work_dir, "ligand.pdbqt")

                if ligand_pdbqt.startswith("minio://"):
                    bucket, obj_name = parse_minio_uri(ligand_pdbqt)
                    await download_file(bucket, obj_name, ligand_local)
                elif ligand_pdbqt and os.path.exists(ligand_pdbqt):
                    import shutil
                    shutil.copy(ligand_pdbqt, ligand_local)
                elif smiles:
                    ligand_local = await self._smiles_to_pdbqt(smiles, work_dir)
                    if not ligand_local:
                        raise FileNotFoundError(f"无法从 SMILES 生成 PDBQT: {smiles}")
                else:
                    raise FileNotFoundError(f"配体文件不可用: {ligand_pdbqt}")

                # 获取或生成受体 PDBQT
                receptor_pdbqt = task.get("receptor_pdbqt") or ""
                receptor_local = os.path.join(work_dir, "receptor.pdbqt")
                if receptor_pdbqt.startswith("minio://"):
                    bucket, obj_name = parse_minio_uri(receptor_pdbqt)
                    await download_file(bucket, obj_name, receptor_local)
                elif receptor_pdbqt and os.path.exists(receptor_pdbqt):
                    import shutil
                    shutil.copy(receptor_pdbqt, receptor_local)
                else:
                    raise FileNotFoundError(f"受体 PDBQT 不可用: {receptor_pdbqt}")

                # 执行 Docking
                output_path = os.path.join(work_dir, "output.pdbqt")
                result = self.runner.run(
                    receptor_pdbqt=receptor_local,
                    ligand_pdbqt=ligand_local,
                    output_path=output_path,
                )

                if result.success:
                    parse_result = self.parser.parse(output_path)
                    affinity = parse_result.data.get("best_affinity") if parse_result.success else None
                    await self._save_result(job_id, drug_id, affinity, "SUCCESS", output_path)
                    await self._update_progress(job_id)
                    await self._push_log(job_id, f"完成对接: {drug_name}, Score={affinity} kcal/mol")
                else:
                    logger.warning(f"Docking 失败: {result.error}")
                    await self._save_result(job_id, drug_id, None, "FAILED")
                    await self._push_log(job_id, f"对接失败: {drug_name}, 错误: {result.error}")

        except Exception as e:
            logger.error(f"处理任务异常: {e}", exc_info=True)
            await self._save_result(int(task_data.get("job_id", 0)), int(task_data.get("drug_id", 0)), None, "FAILED")
            await self._push_log(job_id, f"任务异常: {drug_name}, {str(e)[:100]}")

        finally:
            # ACK 消息
            await stream_ack(settings.REDIS_STREAM_DOCKING, settings.REDIS_CONSUMER_GROUP, msg_id)

    async def _simulate_docking(self, drug_id: int, smiles: str) -> float:
        """模拟对接计算，生成基于分子特征的合理 affinity score

        真实 Vina affinity 范围通常在 -12 ~ -3 kcal/mol。
        模拟模式使用 drug_id 和 smiles 的哈希生成可复现的伪随机分数。
        """
        import hashlib
        seed_str = f"{drug_id}:{smiles}"
        hash_val = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        score = -3.0 - (hash_val % 9000) / 1000.0  # 范围: -3.0 ~ -12.0
        return round(score, 2)

    async def _save_result(self, job_id: int, drug_id: int, affinity: float | None, status: str, result_path: str = ""):
        """将结果保存到 MySQL"""
        from datetime import datetime

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(DockingTask).where(
                    DockingTask.job_id == job_id,
                    DockingTask.drug_id == drug_id,
                ).limit(1)
            )
            task = result.scalar_one_or_none()

            if task:
                task.affinity_score = affinity
                task.status = status
                task.finished_at = datetime.utcnow()
                if result_path:
                    task.docking_result_uri = f"file://{result_path}"

            await session.commit()

    async def _update_progress(self, job_id: int):
        """更新 Redis 进度缓存"""
        from app.core.redis import get_job_progress, cache_job_progress
        from app.models.docking import DockingTask
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            finished = await session.execute(
                select(func.count(DockingTask.id)).where(
                    DockingTask.job_id == job_id,
                    DockingTask.status.in_(["SUCCESS", "FAILED"]),
                )
            )
            total = await session.execute(
                select(func.count(DockingTask.id)).where(DockingTask.job_id == job_id)
            )

            finished_count = finished.scalar() or 0
            total_count = total.scalar() or 0
            progress = int(finished_count / total_count * 100) if total_count > 0 else 0

            await cache_job_progress(job_id, {
                "status": "DOCKING",
                "progress": progress,
                "finished_drugs": finished_count,
                "total_drugs": total_count,
            })

    async def _push_log(self, job_id: int, message: str):
        """将日志条目推送到 Redis 列表"""
        from datetime import datetime
        try:
            r = get_redis()
            log_key = f"job:{job_id}:node:docking:logs"
            timestamp = datetime.now().strftime("%H:%M:%S")
            await r.rpush(log_key, f"[{timestamp}] {message}")
            await r.expire(log_key, 86400)
        except Exception:
            pass

    async def _smiles_to_pdbqt(self, smiles: str, work_dir: str) -> str | None:
        """从 SMILES 在线生成配体 PDBQT 文件

        使用 Meeko 进行分子准备 (SMILES → 3D → PDBQT)。
        """
        try:
            from meeko import MoleculePreparation, PDBQTWriterLegacy
            from rdkit import Chem
            from rdkit.Chem import AllChem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.error(f"SMILES 解析失败: {smiles}")
                return None

            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)

            preparator = MoleculePreparation()
            mol_setup = preparator.prepare(mol)
            pdbqt_string, is_ok = PDBQTWriterLegacy.write_string(mol_setup)

            if not is_ok:
                logger.error(f"PDBQT 写入失败: {smiles}")
                return None

            output_path = os.path.join(work_dir, "ligand.pdbqt")
            with open(output_path, "w") as f:
                f.write(pdbqt_string)

            return output_path

        except Exception as e:
            logger.error(f"SMILES→PDBQT 转换失败: {e}")
            return None

    async def _recover_pending_tasks(self):
        """恢复超时未处理的任务（Worker 崩溃恢复）"""
        claimed = await stream_claim_pending(
            settings.REDIS_STREAM_DOCKING,
            settings.REDIS_CONSUMER_GROUP,
            self.worker_id,
            min_idle_ms=60000,  # 1 分钟
        )
        if claimed:
            logger.info(f"恢复 {len(claimed)} 个超时任务")
            for msg in claimed:
                await self._process_task(msg)

    def stop(self):
        """停止 Worker"""
        self.running = False


async def main():
    """Worker 入口函数"""
    setup_logger()
    worker = DockingWorker()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
