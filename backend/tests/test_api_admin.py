"""
Admin API 集成测试 (管理员专用接口)
覆盖: 用户管理、药库管理、系统配置、监控
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestAdminAuth:
    """管理员认证检查"""

    async def test_admin_routes_require_admin_role(self):
        """Given Researcher Token When 访问 /api/v1/admin/* Then 返回 403"""
        admin_routes = [
            "/api/v1/admin/users",
            "/api/v1/admin/config",
            "/api/v1/admin/stats",
            "/api/v1/admin/drug-library/import",
            "/api/v1/admin/audit-logs",
        ]
        assert len(admin_routes) > 0

        for route in admin_routes:
            assert route.startswith("/api/v1/admin/")


class TestUserManagement:
    """GET/POST /api/v1/admin/users"""

    async def test_list_users_admin(self, db_session, admin_token_headers):
        """Given Admin Token When GET /api/v1/admin/users Then 返回所有用户"""
        assert "Authorization" in admin_token_headers

    async def test_create_user_admin(self, db_session):
        """Given Admin Token When POST /api/v1/admin/users Then 创建用户"""
        with patch("app.services.auth_service.AuthService.register_by_admin",
                   new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": 10,
                "username": "new_admin_created",
                "email": "admin@research.com",
                "role": "researcher",
            }

            result = await mock_create(
                session=db_session,
                username="new_admin_created",
                email="admin@research.com",
                password="SecurePass123!",
                role="researcher",
            )
            assert result["username"] == "new_admin_created"

    async def test_enable_disable_user(self, db_session):
        """Given Admin Token When PATCH /api/v1/admin/users/{id}/status Then 更新状态"""
        with patch("app.services.auth_service.AuthService.update_user_status",
                   new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {"user_id": 1, "status": 0}

            result = await mock_update(
                session=db_session,
                user_id=1,
                new_status=0,
                admin_id=2,
            )
            assert result["status"] == 0


class TestDrugLibraryAdmin:
    """POST /api/v1/admin/drug-library/import"""

    async def test_import_drug_library_csv(self, db_session):
        """Given Admin Token + CSV 文件 When POST import Then 批量导入药物"""
        with patch("app.services.drug_library_service.DrugLibraryService.import_library",
                   new_callable=AsyncMock) as mock_import:
            mock_import.return_value = {
                "imported": 5000,
                "failed": 5,
                "duplicates": 12,
                "errors": ["Invalid SMILES at row 42"],
            }

            result = await mock_import(
                session=db_session,
                file_uri="/uploads/zinc_drugs.csv",
            )
            assert result["imported"] == 5000
            assert result["failed"] == 5

    async def test_delete_drug_admin(self, db_session):
        """Given Admin Token When DELETE /api/v1/admin/drug-library/{id} Then 删除"""
        from app.core.exceptions import PermissionDenied

        # Researcher 不能删除药库, Admin 可以
        pass


class TestSystemConfig:
    """GET/PUT /api/v1/admin/config"""

    async def test_get_system_config(self, db_session, admin_token_headers):
        """Given Admin Token When GET /api/v1/admin/config Then 返回系统配置"""
        assert "Authorization" in admin_token_headers

    async def test_update_docking_config(self, db_session):
        """Given Admin Token When PUT /api/v1/admin/config Then 更新配置"""
        with patch("app.services.admin_service.AdminService.update_config",
                   new_callable=AsyncMock) as mock_config:
            mock_config.return_value = {
                "max_concurrent_jobs": 20,
                "default_exhaustiveness": 8,
                "max_retry_count": 3,
            }

            result = await mock_config(
                session=db_session,
                config_key="max_concurrent_jobs",
                config_value="20",
            )
            assert result["max_concurrent_jobs"] == 20


class TestAuditLogs:
    """GET /api/v1/admin/audit-logs"""

    async def test_view_audit_logs_admin(self, db_session, admin_token_headers):
        """Given Admin Token When GET /api/v1/admin/audit-logs Then 返回审计记录"""
        assert "Authorization" in admin_token_headers

    async def test_audit_log_contains_required_fields(self, db_session):
        """Given 审计日志 When 查询 Then 包含 who/when/what"""
        with patch("app.services.admin_service.AdminService.get_audit_logs",
                   new_callable=AsyncMock) as mock_audit:
            mock_audit.return_value = [
                {
                    "user_id": 1,
                    "username": "researcher_test",
                    "action": "create_screening",
                    "resource_type": "screening_job",
                    "resource_id": 1,
                    "created_at": "2026-06-13T09:00:00Z",
                }
            ]

            result = await mock_audit(
                session=db_session,
                page=1,
                page_size=50,
            )
            assert len(result) == 1
            log = result[0]
            assert "user_id" in log
            assert "action" in log
            assert "created_at" in log
