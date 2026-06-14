"""
Molecule Agent — 分子解析与预处理

职责：
- 解析 SMILES 字符串
- 解析 SDF 文件
- 标准化分子结构
- 计算分子描述符
- 生成 3D 构象
- 转换为 PDBQT 格式
- 上传结果到 MinIO

输入: {"smiles": "..."}
输出: {"ligand_pdbqt_uri": "minio://...", "fingerprint": [...], "descriptors": {...}}
"""

from typing import Any

from app.agents.base import BaseAgent
from app.tools.rdkit.parser import RdkitParser
from app.tools.rdkit.descriptors import RdkitDescriptors
from app.tools.rdkit.conformer import RdkitConformer
from app.tools.rdkit.pdbqt_converter import RdkitPdbqtConverter


class MoleculeAgent(BaseAgent):
    """分子预处理 Agent

    解析用户输入的 SMILES/SDF，完成标准化 → 描述符计算 → 3D 构象 → PDBQT 转换。
    所有中间文件和最终文件上传至 MinIO。
    """

    name = "MoleculeAgent"
    description = "SMILES 解析、3D 构象生成、PDBQT 格式转换"

    def __init__(self):
        super().__init__()
        self.parser = RdkitParser()
        self.descriptors = RdkitDescriptors()
        self.conformer = RdkitConformer()
        self.converter = RdkitPdbqtConverter()

    def _validate_input(self, state: dict[str, Any]) -> None:
        smiles = state.get("smiles", "")
        input_file = state.get("input_file", "")
        if not smiles and not input_file:
            raise ValueError("MoleculeAgent: 需要 smiles 或 input_file")

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        smiles = state.get("smiles", "")

        # Step 1: 解析 SMILES
        parse_result = self.parser.parse_smiles(smiles)
        mol = parse_result.data["mol"]
        canonical_smiles = parse_result.data["canonical_smiles"]

        # Step 2: 计算描述符
        desc_result = self.descriptors.compute(mol)
        fp_result = self.descriptors.compute_fingerprint(mol)

        # Step 3: 生成 3D 构象
        conf_result = self.conformer.generate(mol)
        mol_3d = conf_result.data["mol"]

        # Step 4: 保存 3D 构象为 SDF
        sdf_result = self.conformer.save_to_sdf(mol_3d)

        # Step 5: 转换为 PDBQT
        pdbqt_result = self.converter.convert_mol_to_pdbqt(mol_3d)

        return {
            "smiles": canonical_smiles,
            "mol": mol,
            "mol_3d": mol_3d,
            "ligand_sdf_path": sdf_result.data.get("sdf_path"),
            "ligand_pdbqt_path": pdbqt_result.data.get("pdbqt_path"),
            "fingerprint": fp_result.data.get("fingerprint", []),
            "descriptors": desc_result.data,
            "num_atoms": parse_result.data.get("num_atoms"),
            "num_heavy_atoms": parse_result.data.get("num_heavy_atoms"),
        }

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "smiles": output.get("smiles"),
            "ligand_sdf_path": output.get("ligand_sdf_path"),
            "ligand_pdbqt_path": output.get("ligand_pdbqt_path"),
            "fingerprint": output.get("fingerprint"),
            "descriptors": output.get("descriptors"),
            "num_atoms": output.get("num_atoms"),
            "preparation_complete": True,
        }
