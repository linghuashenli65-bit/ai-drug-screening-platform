"""
RDKit 3D 构象生成器

通过 ETKDG (Experimental Torsion Knowledge Distance Geometry) 方法
生成高质量三维构象，并进行 UFF 力场优化。
"""

import os
import tempfile

from rdkit import Chem
from rdkit.Chem import AllChem

from app.tools.base import BaseTool, ToolResult


class RdkitConformer(BaseTool):
    """3D 构象生成工具

    使用 ETKDG + UFF 优化生成分子的三维构象。
    输出可用于 AutoDock Vina 对接的 SDF 文件。
    """

    name = "rdkit_conformer"
    description = "生成高质量 3D 分子构象并输出 SDF"

    def generate(
        self,
        mol: Chem.Mol,
        num_confs: int = 1,
        optimize: bool = True,
        random_seed: int = 42,
    ) -> ToolResult:
        """生成 3D 构象

        Args:
            mol: 2D/3D RDKit Mol 对象
            num_confs: 生成构象数 (默认 1)
            optimize: 是否进行 UFF 力场优化
            random_seed: 随机种子

        Returns:
            ToolResult 包含 3D 构象 Mol 对象
        """
        mol = Chem.AddHs(mol)

        # ETKDG 构象生成
        params = AllChem.ETKDGv3()
        params.randomSeed = random_seed
        params.numThreads = 0  # 使用全部 CPU

        status = AllChem.EmbedMultipleConfs(mol, numConfs=num_confs, params=params)

        if all(s != 0 for s in status):
            # 所有构象生成失败，回退到基础 DG
            AllChem.EmbedMolecule(mol, randomSeed=random_seed)

        if optimize and mol.GetNumConformers() > 0:
            AllChem.MMFFOptimizeMoleculeConfs(mol)

        # 移除氢（对接不需要氢）
        mol = Chem.RemoveHs(mol)

        energies = []
        if mol.GetNumConformers() > 0:
            mp = AllChem.MMFFGetMoleculeProperties(mol)
            ff = AllChem.MMFFGetMoleculeForceField(mol, mp)
            if ff:
                energies = [ff.CalcEnergy()]

        return ToolResult.success(
            data={
                "mol": mol,
                "num_conformers": mol.GetNumConformers(),
                "energies": energies,
                "optimized": optimize,
            }
        )

    def save_to_sdf(self, mol: Chem.Mol, output_path: str = None) -> ToolResult:
        """将 3D 构象保存为 SDF 文件

        Args:
            mol: 3D 构象 Mol 对象
            output_path: 输出路径，不指定则使用临时文件

        Returns:
            ToolResult 包含 SDF 文件路径
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".sdf", prefix="ligand_")
            os.close(fd)

        writer = Chem.SDWriter(output_path)
        writer.write(mol)
        writer.close()

        return ToolResult.success(
            data={
                "sdf_path": output_path,
                "file_size": os.path.getsize(output_path),
            }
        )
