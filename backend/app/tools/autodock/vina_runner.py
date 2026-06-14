"""
AutoDock Vina 运行器

执行单个分子对接计算。
调用外部 vina 可执行文件，配置盒子参数、exhaustiveness 等。
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.logger import get_logger
from app.tools.base import BaseTool, ToolResult

settings = get_settings()
logger = get_logger("tool.vina_runner")


class AutoDockRunner(BaseTool):
    """AutoDock Vina 对接执行器

    调用系统安装的 vina 可执行文件执行分子对接。
    输入：受体 PDBQT + 配体 PDBQT + 对接盒子参数
    输出：对接结果 PDBQT（含多个 binding mode + affinity）
    """

    name = "autodock_runner"
    description = "执行单个 AutoDock Vina 分子对接计算"

    def run(
        self,
        receptor_pdbqt: str,
        ligand_pdbqt: str,
        output_path: Optional[str] = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        center_z: float = 0.0,
        size_x: float = 20.0,
        size_y: float = 20.0,
        size_z: float = 20.0,
        exhaustiveness: int = None,
        num_modes: int = None,
        energy_range: int = None,
        timeout: int = None,
    ) -> ToolResult:
        """执行 AutoDock Vina 对接

        Args:
            receptor_pdbqt: 受体 PDBQT 文件路径
            ligand_pdbqt: 配体 PDBQT 文件路径
            output_path: 输出 PDBQT 文件路径（不指定则用临时文件）
            center_x/y/z: 对接盒子中心坐标
            size_x/y/z: 对接盒子尺寸 (A)
            exhaustiveness: 搜索详尽度（默认从配置读取）
            num_modes: 输出模式数
            energy_range: 能量范围 (kcal/mol)
            timeout: 超时时间 (秒)

        Returns:
            ToolResult 包含输出 PDBQT 路径和对接日志
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".pdbqt", prefix="docking_out_")
            os.close(fd)

        exhaustiveness = exhaustiveness or settings.VINA_EXHAUSTIVENESS
        num_modes = num_modes or settings.VINA_NUM_MODES
        energy_range = energy_range or settings.VINA_ENERGY_RANGE
        timeout = timeout or settings.VINA_TIMEOUT

        # 验证输入文件存在
        for path, label in [(receptor_pdbqt, "受体"), (ligand_pdbqt, "配体")]:
            if not os.path.exists(path):
                return ToolResult.failure(error=f"{label} PDBQT 文件不存在: {path}")

        cmd = [
            settings.VINA_EXECUTABLE,
            "--receptor", receptor_pdbqt,
            "--ligand", ligand_pdbqt,
            "--out", output_path,
            "--center_x", str(center_x),
            "--center_y", str(center_y),
            "--center_z", str(center_z),
            "--size_x", str(size_x),
            "--size_y", str(size_y),
            "--size_z", str(size_z),
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
            "--energy_range", str(energy_range),
        ]

        logger.info(f"启动 AutoDock Vina: receptor={os.path.basename(receptor_pdbqt)}, ligand={os.path.basename(ligand_pdbqt)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.error(f"Vina 执行失败: {result.stderr}")
                return ToolResult.failure(
                    error=f"Vina 执行失败 (exit code {result.returncode})",
                    data={"stderr": result.stderr, "stdout": result.stdout},
                )

            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return ToolResult.failure(error="Docking 输出文件为空")

            return ToolResult.success(
                data={
                    "output_pdbqt": output_path,
                    "output_size": os.path.getsize(output_path),
                    "stdout": result.stdout,
                    "exhaustiveness": exhaustiveness,
                    "num_modes": num_modes,
                }
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Vina 对接超时 ({timeout}s): ligand={os.path.basename(ligand_pdbqt)}")
            return ToolResult.failure(
                error=f"Vina 对接超时（{timeout}s）",
                data={"ligand": ligand_pdbqt, "receptor": receptor_pdbqt, "timeout": timeout},
            )
        except FileNotFoundError:
            return ToolResult.failure(
                error=f"Vina 可执行文件未找到: {settings.VINA_EXECUTABLE}",
                data={"vina_path": settings.VINA_EXECUTABLE},
            )
