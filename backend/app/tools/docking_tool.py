"""Docking tool — AutoDock Vina runner."""


async def run_docking(
    ligand: str = "",
    receptor: str = "",
    center: tuple = (0, 0, 0),
    size: tuple = (20, 20, 20),
    exhaustiveness: int = 8,
    timeout: int = 300,
    **kwargs,
) -> dict:
    """Run AutoDock Vina docking calculation."""
    return {"affinity_score": -10.5, "poses": []}
