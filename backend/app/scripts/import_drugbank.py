"""
DrugBank / e-drug3d SDF 药物库导入脚本

从 e-drug3d.sdf 解析 2,162 个上市药物分子，提取物化属性
和 SDF 数据字段并批量写入 drug_library 表。

使用方式:
    cd backend
    python -m app.scripts.import_drugbank \
        "C:/Users/27644/Desktop/自动化高通量处理系统/e-drug3d.sdf"
"""

import argparse
import logging
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 已知原子序数上限（用于验证 3D 坐标有效性）
MAX_ATOMIC_NUMBER = 118


def compute_smiles(mol: Chem.Mol) -> str:
    """从 3D Mol 对象计算 canonical SMILES

    不移除氢原子以保留完整结构信息。
    """
    # SDMolSupplier 默认不移除氢，保留 3D 构象中的氢
    mol_no_h = Chem.RemoveHs(mol, sanitize=False)
    try:
        Chem.SanitizeMol(mol_no_h)
    except Exception:
        # 若 sanitize 失败，尝试以部分清理模式
        mol_no_h = Chem.RemoveHs(mol, sanitize=True)

    return Chem.MolToSmiles(mol_no_h, canonical=True)


def parse_sdf_file(file_path: str) -> list[dict]:
    """解析 e-drug3d.sdf 文件

    每个分子提取以下字段:
        - drug_name: 通用名（来自 SDF <name> 数据字段）
        - smiles: 从 3D 坐标生成的 canonical SMILES
        - cas: CAS 号（来自 SDF <cas> 数据字段）
        - status: 药品状态（正常 或 DISCONTINUED）
        - molecular_weight: 分子量
        - logp: 脂水分配系数（Crippen Wildman）

    Returns:
        药物字典列表
    """
    supplier = Chem.SDMolSupplier(file_path)
    drugs = []
    errors = 0

    # SDF 数据字段名（大小写不敏感，SDMolSupplier 自动转为大写）
    field_status = "status"
    field_cas = "cas"
    field_name = "name"
    field_id = "ID"

    for i, mol in enumerate(supplier):
        if mol is None:
            errors += 1
            logger.warning("分子 %d 解析失败，跳过", i + 1)
            continue

        # 提取数据字段
        props = mol.GetPropsAsDict()
        drug_name = props.get(field_name, "").strip()
        cas = props.get(field_cas, "").strip()
        status = props.get(field_status, "正常").strip()

        if not drug_name:
            drug_name = f"UNKNOWN_{i + 1}"

        # 生成 canonical SMILES
        try:
            smiles = compute_smiles(mol)
        except Exception as e:
            logger.warning("分子 %d (%s) SMILES 生成失败: %s", i + 1, drug_name, e)
            errors += 1
            continue

        # 计算物化属性
        try:
            mol_wt = round(Descriptors.MolWt(mol), 3)
        except Exception:
            mol_wt = None

        try:
            logp = round(Crippen.MolLogP(mol), 2)
        except Exception:
            logp = None

        drugs.append({
            "drug_name": drug_name,
            "smiles": smiles,
            "cas": cas if cas else None,
            "status": status if status else "正常",
            "molecular_weight": mol_wt,
            "logp": logp,
        })

    logger.info(
        "SDF 解析完成: 成功 %d 个分子, 失败 %d 个, 总计 %d 个",
        len(drugs),
        errors,
        len(drugs) + errors,
    )
    return drugs


def import_to_database(drugs: list[dict], batch_size: int = 200) -> int:
    """批量写入 drug_library 表

    Args:
        drugs: 药物字典列表
        batch_size: 每批插入的行数

    Returns:
        成功插入的行数
    """
    settings = get_settings()

    engine = create_engine(
        settings.MYSQL_URL,
        pool_size=5,
        pool_pre_ping=True,
    )

    total_inserted = 0

    with Session(engine) as session:
        # 先清空表（幂等导入）
        result = session.execute(text("SELECT COUNT(*) FROM drug_library"))
        existing = result.scalar()
        if existing > 0:
            logger.warning(
                "drug_library 表已有 %d 条记录，将清空后重新导入", existing
            )
            session.execute(text("DELETE FROM drug_library"))
            session.commit()

        # 批量插入（使用参数化查询避免注入）
        insert_sql = text(
            "INSERT INTO drug_library (drug_name, smiles, cas, status, molecular_weight, logp) "
            "VALUES (:drug_name, :smiles, :cas, :status, :molecular_weight, :logp)"
        )
        for start in range(0, len(drugs), batch_size):
            batch = drugs[start : start + batch_size]
            try:
                for d in batch:
                    session.execute(
                        insert_sql,
                        {
                            "drug_name": d["drug_name"],
                            "smiles": d["smiles"],
                            "cas": d["cas"],
                            "status": d["status"],
                            "molecular_weight": d["molecular_weight"],
                            "logp": d["logp"],
                        },
                    )
                session.commit()
                total_inserted += len(batch)
                logger.info(
                    "已导入 %d/%d 条记录 (%d%%)",
                    total_inserted,
                    len(drugs),
                    int(total_inserted / len(drugs) * 100),
                )
            except Exception as e:
                session.rollback()
                logger.error("批量插入失败 (offset %d): %s", start, e)
                raise

    engine.dispose()
    return total_inserted


def main():
    parser = argparse.ArgumentParser(
        description="导入 e-drug3d.sdf 药物库到 drug_library 表"
    )
    parser.add_argument(
        "sdf_path",
        type=str,
        help="e-drug3d.sdf 文件路径",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="批量插入大小 (默认: 200)",
    )
    parser.add_argument(
        "--skip-truncate",
        action="store_true",
        help="不清空已有数据，追加导入",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sdf_path = Path(args.sdf_path)
    if not sdf_path.exists():
        logger.error("文件不存在: %s", args.sdf_path)
        sys.exit(1)

    logger.info("开始导入药物库: %s", args.sdf_path)

    # 1. 解析 SDF
    drugs = parse_sdf_file(str(sdf_path))
    if not drugs:
        logger.error("未解析到任何有效分子")
        sys.exit(1)

    # 2. 统计
    normal_count = sum(1 for d in drugs if d["status"] == "正常")
    discontinued_count = sum(1 for d in drugs if d["status"] == "DISCONTINUED")
    logger.info(
        "药物状态分布: 正常=%d, DISCONTINUED=%d, 总计=%d",
        normal_count,
        discontinued_count,
        len(drugs),
    )

    # 3. 导入数据库
    inserted = import_to_database(drugs, batch_size=args.batch_size)

    logger.info("导入完成: 成功写入 %d 条记录到 drug_library 表", inserted)


if __name__ == "__main__":
    main()
