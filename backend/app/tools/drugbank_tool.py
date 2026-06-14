"""DrugBank knowledge query tool."""


async def query_drug(drug_id: int = None, drug_name: str = None) -> dict:
    """Query drug information from DrugBank database."""
    return {"drug_name": drug_name or "Unknown", "indication": ""}


async def query_by_name(name: str, limit: int = 10) -> list:
    """Query drugs by name."""
    return []


async def get_drug_info(drugbank_id: str = "") -> dict:
    """Get drug detailed information."""
    return {"drugbank_id": drugbank_id, "info": {}}
