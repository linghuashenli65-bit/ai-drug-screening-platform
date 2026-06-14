"""RDKit tool — SMILES parsing, 3D conformer generation, PDBQT conversion."""


async def gen_3d_structure(mol_id: int, output_dir: str) -> str:
    """Generate 3D conformer and output SDF."""
    return "/output/mol_3d.sdf"


async def generate_pdbqt(sdf_path: str, output_dir: str) -> str:
    """Convert SDF to PDBQT."""
    return "/output/ligand.pdbqt"
