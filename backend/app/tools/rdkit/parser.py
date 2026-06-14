"""
RDKit 分子解析器

职责：
- 解析 SMILES 字符串为 RDKit 分子对象
- 解析 SDF/MOL2 文件
- 标准化分子结构（去盐、中和、Kekulize）
- 验证分子合法性
"""

from typing import Optional

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, MolStandardize, SaltRemover

from app.core.exceptions import FileFormatError
from app.tools.base import BaseTool, ToolResult


class RdkitParser(BaseTool):
    """SMILES / SDF 分子解析工具

    将输入字符串或文件解析为标准化的 RDKit 分子对象。
    """

    name = "rdkit_parser"
    description = "解析 SMILES 或 SDF 文件为标准化分子结构"

    def parse_smiles(self, smiles: str) -> ToolResult:
        """解析 SMILES 字符串

        Args:
            smiles: SMILES 字符串

        Returns:
            ToolResult 包含标准化后的 Mol 对象和 canonical SMILES
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError("无法解析 SMILES")

            # 标准化流程：去盐 → 中和 → 重新 Kekulize
            mol = self._standardize(mol)
            canonical_smiles = Chem.MolToSmiles(mol, canonical=True)

            return ToolResult.success(
                data={
                    "mol": mol,
                    "canonical_smiles": canonical_smiles,
                    "num_atoms": mol.GetNumAtoms(),
                    "num_heavy_atoms": mol.GetNumHeavyAtoms(),
                }
            )
        except Exception as e:
            raise FileFormatError(message="SMILES 解析失败", detail={"error": str(e), "smiles": smiles})

    def parse_sdf(self, file_path: str) -> ToolResult:
        """解析 SDF 文件

        Args:
            file_path: SDF 文件路径

        Returns:
            ToolResult 包含分子列表
        """
        try:
            supplier = Chem.SDMolSupplier(file_path)
            mols = [mol for mol in supplier if mol is not None]

            if not mols:
                raise ValueError("SDF 文件中未找到有效分子")

            standardized = [self._standardize(mol) for mol in mols]

            return ToolResult.success(
                data={
                    "mol": standardized[0],  # 主分子
                    "mols": standardized,
                    "num_molecules": len(standardized),
                    "canonical_smiles": Chem.MolToSmiles(standardized[0], canonical=True),
                }
            )
        except Exception as e:
            raise FileFormatError(message="SDF 文件解析失败", detail={"error": str(e), "file": file_path})

    def _standardize(self, mol: Chem.Mol) -> Chem.Mol:
        """分子标准化：去盐 → 保留最大片段 → 中和 → 标准化官能团 → 再Kekulize

        Args:
            mol: RDKit Mol 对象

        Returns:
            标准化后的 Mol 对象
        """
        # 去除盐和溶剂
        remover = SaltRemover.SaltRemover()
        mol = remover.StripMol(mol, dontRemoveEverything=True)

        # 保留最大片段
        mol = MolStandardize.rdMolStandardize.FragmentParent(mol)

        # 中和电荷
        uncharger = MolStandardize.rdMolStandardize.Uncharger()
        mol = uncharger.uncharge(mol)

        # 标准化官能团
        normalizer = MolStandardize.rdMolStandardize.Normalizer()
        mol = normalizer.normalize(mol)

        # 重新 Kekulize 确保芳香性正确
        try:
            Chem.Kekulize(mol, clearAromaticFlags=True)
        except Exception:
            pass  # 部分分子无法 Kekulize，忽略

        Chem.SanitizeMol(mol)
        return mol
