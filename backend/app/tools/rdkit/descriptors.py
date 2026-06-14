"""
RDKit 分子描述符计算器

计算化学相关的分子性质：
- 分子量 (MW)
- LogP (亲脂性)
- TPSA (拓扑极性表面积)
- 氢键供体/受体数
- 可旋转键数
- Lipinski 五规则
- Morgan 指纹 (用于 Milvus 向量检索)
"""

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Crippen, Lipinski, rdMolDescriptors

from app.tools.base import BaseTool, ToolResult


class RdkitDescriptors(BaseTool):
    """分子描述符计算工具

    计算分子量、LogP、TPSA、氢键供受体等常见药物化学描述符，
    以及 Morgan 指纹用于相似性搜索。
    """

    name = "rdkit_descriptors"
    description = "计算分子理化性质描述符和分子指纹"

    def compute(self, mol: Chem.Mol) -> ToolResult:
        """计算分子所有描述符

        Args:
            mol: RDKit Mol 对象

        Returns:
            ToolResult 包含所有计算得到的描述符
        """
        mw = Descriptors.ExactMolWt(mol)
        logp = Crippen.MolLogP(mol)
        tpsa = Descriptors.TPSA(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        rotatable_bonds = Lipinski.NumRotatableBonds(mol)
        ring_count = rdMolDescriptors.CalcNumRings(mol)
        aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)

        # Lipinski 五规则检查
        lipinski_violations = 0
        if mw > 500:
            lipinski_violations += 1
        if logp > 5:
            lipinski_violations += 1
        if hbd > 5:
            lipinski_violations += 1
        if hba > 10:
            lipinski_violations += 1

        return ToolResult.success(
            data={
                "molecular_weight": round(mw, 3),
                "logp": round(logp, 2),
                "tpsa": round(tpsa, 2),
                "h_bond_donors": hbd,
                "h_bond_acceptors": hba,
                "rotatable_bonds": rotatable_bonds,
                "ring_count": ring_count,
                "aromatic_rings": aromatic_rings,
                "lipinski_violations": lipinski_violations,
                "lipinski_pass": lipinski_violations <= 1,
            }
        )

    def compute_fingerprint(self, mol: Chem.Mol, radius: int = 2, n_bits: int = 2048) -> ToolResult:
        """计算 Morgan (ECFP) 指纹（用于 Milvus 向量检索）

        Args:
            mol: RDKit Mol 对象
            radius: 指纹半径 (默认 2 = ECFP4)
            n_bits: 指纹位长度 (默认 2048)

        Returns:
            ToolResult 包含指纹向量 (list[int])
        """
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        # 转为整数列表
        fp_list = list(fp)

        return ToolResult.success(
            data={
                "fingerprint": fp_list,
                "fingerprint_bits": n_bits,
                "radius": radius,
                "on_bits": sum(fp_list),
            }
        )
