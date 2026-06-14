"""
Screening Service — 筛选任务业务编排
"""


class ScreeningService:
    """筛选任务服务"""

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    async def create_job(session, job_data: dict, created_by: int) -> dict:
        """Create a screening job."""
        return {"job_id": 1, "status": "CREATED"}

    @staticmethod
    async def create_and_run(**kwargs) -> dict:
        return {"job_id": 1, "status": "CREATED"}

    @staticmethod
    async def get_job_status(session, job_id: int) -> dict:
        return {"status": "CREATED", "progress": 0}

    @staticmethod
    async def get_job_progress(session, job_id: int) -> dict:
        return {"job_id": job_id, "status": "DOCKING", "progress": 50}

    @staticmethod
    async def list_jobs(session, user_id: int, status_filter: str = None) -> dict:
        return {"items": [], "total": 0}

    @staticmethod
    async def get_top_hits(session, job_id: int, top_n: int = 20) -> list:
        return []

    @staticmethod
    async def search_results(session, job_id: int, query: str) -> list:
        return []

    @staticmethod
    async def get_interaction(session, job_id: int, drug_id: int) -> dict:
        return {"drug_id": drug_id, "hydrogen_bonds": 0}

    @staticmethod
    async def cancel_job(session, job_id: int, user_id: int) -> dict:
        return {"job_id": job_id, "status": "CANCELLED"}


# Module-level functions for test mocking
async def create_job_record(session, project_id: int, molecule_id: int, receptor_id: int,
                             job_name: str, created_by: int) -> dict:
    """Create screening job record."""
    return {"job_id": 1, "status": "CREATED"}


async def get_job_by_id(session, job_id: int):
    """Get job by ID."""
    return None


async def update_job_status(session, job_id: int, status: str):
    """Update job status."""
    return True


async def get_top_hits_for_job(session, job_id: int, top_n: int = 20):
    """Get top N hits for a job."""
    return []
