"""
分子服务

SMILES 解析、分子创建、文件导入。
"""


class MoleculeService:
    """分子服务"""

    @staticmethod
    async def create_from_smiles(session, project_id: int, smiles: str):
        """从 SMILES 创建分子"""
        from rdkit import Chem
        from rdkit.Chem import Descriptors

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError("Invalid SMILES")

        from app.models.molecule import Molecule

        mw = round(Descriptors.MolWt(mol), 2)
        logp = round(Descriptors.MolLogP(mol), 2)

        molecule = Molecule(
            project_id=project_id,
            smiles=smiles,
            molecular_weight=mw,
            logp=logp,
        )
        session.add(molecule)
        await session.flush()
        return {"id": molecule.id, "smiles": smiles}

    @staticmethod
    async def create_from_file(session, project_id: int, file_path: str):
        """从文件导入分子"""
        # Stub implementation
        return {"message": "File import triggered", "file_path": file_path}

    @staticmethod
    async def get_molecule(session, molecule_id: int):
        """获取分子详情"""
        from app.models.molecule import Molecule
        from sqlalchemy import select

        result = await session.execute(select(Molecule).where(Molecule.id == molecule_id))
        mol = result.scalar_one_or_none()
        if not mol:
            raise ValueError("Molecule not found")
        return mol


def parse_smiles(smiles: str) -> dict:
    """解析 SMILES 字符串"""
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Invalid SMILES")
    return {
        "smiles": smiles,
        "molecular_weight": round(Descriptors.MolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 2),
    }


async def create_molecule_record(session, project_id: int, smiles: str):
    """创建分子记录（独立函数）"""
    return await MoleculeService.create_from_smiles(session, project_id, smiles)
