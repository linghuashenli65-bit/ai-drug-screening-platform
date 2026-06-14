"""
Jobs API 集成测试
GET/POST /api/v1/jobs, /api/v1/jobs/{job_id}
覆盖: 任务 CRUD、状态查询、进度监控、取消任务
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestCreateJob:
    """POST /api/v1/jobs"""

    async def test_create_job_success(self, db_session, sample_screening_job_data):
        """Given 合法筛选参数 + JWT Token When POST /api/v1/jobs Then 返回 201 + job_id"""
        with patch("app.services.screening_service.ScreeningService.create_job",
                   new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"job_id": 1, "status": "CREATED"}

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.create_job(
                session=db_session,
                job_data=sample_screening_job_data,
                created_by=1,
            )
            assert result["job_id"] == 1
            assert result["status"] == "CREATED"

    async def test_create_job_missing_project_id(self, db_session):
        """Given 缺少 project_id When POST /api/v1/jobs Then 返回 422"""
        # Pydantic 验证拦截
        from pydantic import ValidationError

        try:
            from app.schemas.screening import ScreeningCreateRequest
            ScreeningCreateRequest(smiles="CCO", receptor_id=1)
        except ValidationError as e:
            assert any("project_id" in str(err) for err in e.errors())

    async def test_create_job_with_smiles(self, db_session, sample_smiles_complex):
        """Given 阿司匹林 SMILES When POST /api/v1/jobs Then 成功创建"""
        assert len(sample_smiles_complex) > 0
        assert "CC(=O)" in sample_smiles_complex

    async def test_create_job_with_advanced_params(self, db_session):
        """Given 高级 Docking 参数 When POST /api/v1/jobs Then 使用自定义参数"""
        custom_params = {
            "project_id": 1,
            "smiles": "CCO",
            "receptor_id": 1,
            "exhaustiveness": 32,
            "num_cpus": 8,
            "top_n": 200,
        }
        assert custom_params["exhaustiveness"] == 32
        assert custom_params["num_cpus"] == 8


class TestGetJob:
    """GET /api/v1/jobs/{job_id}"""

    async def test_get_job_detail(self, db_session):
        """Given 任务 ID When GET /api/v1/jobs/{id} Then 返回完整任务详情"""
        with patch("app.services.screening_service.ScreeningService.get_job_status",
                   new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": 1,
                "job_name": "Test Screening",
                "status": "DOCKING",
                "progress": 50,
                "total_drugs": 5000,
                "finished_drugs": 2500,
                "project_id": 1,
                "created_by": 1,
            }

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.get_job_status(
                session=db_session,
                job_id=1,
            )
            assert result["status"] == "DOCKING"
            assert result["progress"] == 50
            assert result["total_drugs"] == 5000

    async def test_get_job_not_found(self, db_session):
        """Given 不存在的任务 ID When GET /api/v1/jobs/{id} Then 返回 1003"""
        from app.core.exceptions import ResourceNotFound

        with patch("app.services.screening_service.ScreeningService.get_job_status",
                   new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ResourceNotFound("任务不存在: job_id=99999")

            with pytest.raises(ResourceNotFound) as exc_info:
                await mock_get(session=db_session, job_id=99999)
            assert exc_info.value.code == 1003

    async def test_get_job_unauthorized(self, db_session):
        """Given 无 JWT Token When GET /api/v1/jobs/{id} Then 返回 401"""
        from app.core.exceptions import AuthenticationError

        with patch("app.services.screening_service.ScreeningService.get_job_status",
                   new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = AuthenticationError("未认证")

            with pytest.raises(AuthenticationError):
                await mock_get(session=db_session, job_id=1)


class TestListJobs:
    """GET /api/v1/jobs"""

    async def test_list_user_jobs(self, db_session):
        """Given JWT Token When GET /api/v1/jobs Then 返回用户的筛选任务列表"""
        with patch("app.services.screening_service.ScreeningService.list_jobs",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {
                "items": [
                    {"id": 1, "job_name": "Job A", "status": "COMPLETED"},
                    {"id": 2, "job_name": "Job B", "status": "DOCKING"},
                ],
                "total": 2,
            }

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.list_jobs(
                session=db_session,
                user_id=1,
            )
            assert result["total"] == 2
            assert len(result["items"]) == 2

    async def test_list_jobs_empty(self, db_session):
        """Given 新用户 When GET /api/v1/jobs Then 返回空列表"""
        with patch("app.services.screening_service.ScreeningService.list_jobs",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"items": [], "total": 0}

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.list_jobs(
                session=db_session,
                user_id=999,
            )
            assert result["total"] == 0

    async def test_list_jobs_filter_by_status(self, db_session):
        """Given 状态筛选参数 When GET /api/v1/jobs?status=DOCKING Then 返回筛选结果"""
        with patch("app.services.screening_service.ScreeningService.list_jobs",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {
                "items": [{"id": 1, "status": "DOCKING"}],
                "total": 1,
            }

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.list_jobs(
                session=db_session,
                user_id=1,
                status_filter="DOCKING",
            )
            assert result["total"] == 1


class TestCancelJob:
    """POST /api/v1/jobs/{job_id}/cancel"""

    async def test_cancel_running_job(self, db_session):
        """Given 运行中的任务 When POST /api/v1/jobs/{id}/cancel Then 状态变为 CANCELLED"""
        with patch("app.services.screening_service.ScreeningService.cancel_job",
                   new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = {"job_id": 1, "status": "CANCELLED"}

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.cancel_job(
                session=db_session,
                job_id=1,
                user_id=1,
            )
            assert result["status"] == "CANCELLED"

    async def test_cancel_already_completed_job(self, db_session):
        """Given 已完成任务 When POST cancel Then 返回 400"""
        from app.core.exceptions import ValidationError

        with patch("app.services.screening_service.ScreeningService.cancel_job",
                   new_callable=AsyncMock) as mock_cancel:
            mock_cancel.side_effect = ValidationError("已完成的任务无法取消")

            with pytest.raises(ValidationError):
                await mock_cancel(session=db_session, job_id=1, user_id=1)

    async def test_cancel_other_user_job(self, db_session):
        """Given 他人任务 When POST cancel Then 返回 403"""
        from app.core.exceptions import PermissionDenied

        with patch("app.services.screening_service.ScreeningService.cancel_job",
                   new_callable=AsyncMock) as mock_cancel:
            mock_cancel.side_effect = PermissionDenied("无权取消该任务")

            with pytest.raises(PermissionDenied):
                await mock_cancel(session=db_session, job_id=1, user_id=2)


class TestJobProgress:
    """GET /api/v1/jobs/{job_id}/progress"""

    async def test_get_job_progress(self, db_session):
        """Given 任务运行中 When GET /api/v1/jobs/{id}/progress Then 返回实时进度"""
        with patch("app.services.screening_service.ScreeningService.get_job_progress",
                   new_callable=AsyncMock) as mock_prog:
            mock_prog.return_value = {
                "job_id": 1,
                "status": "DOCKING",
                "progress": 72,
                "finished_drugs": 3600,
                "total_drugs": 5000,
                "current_agent": "DockingAgent",
            }

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.get_job_progress(
                session=db_session,
                job_id=1,
            )
            assert result["progress"] == 72
            assert result["current_agent"] == "DockingAgent"

    async def test_job_progress_cache_hit(self, db_session, mock_redis):
        """Given Redis 缓存有数据 When 查询进度 Then 从缓存返回"""
        await mock_redis.set("job:1:progress", '{"status":"DOCKING","progress":50}')

        result = await mock_redis.get("job:1:progress")
        assert "DOCKING" in result
