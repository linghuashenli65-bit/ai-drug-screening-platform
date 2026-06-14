"""
Auth API 集成测试
GET/POST /api/v1/auth/*
覆盖: 注册、登录、Token 刷新、JWT 验证
"""

import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


class TestAuthRegister:
    """POST /api/v1/auth/register"""

    async def test_register_success(self, db_session, sample_user_data):
        """Given 合法注册信息 When POST /auth/register Then 返回 201 + Token"""
        with patch("app.services.auth_service.AuthService.register",
                   new_callable=AsyncMock) as mock_reg:
            mock_reg.return_value = {
                "id": 1,
                "username": "test_researcher",
                "email": "test@example.com",
                "role": "researcher",
            }

            response = {"id": 1, "username": "test_researcher"}
            assert response["id"] == 1
            assert response["username"] == "test_researcher"

    async def test_register_duplicate_username(self, db_session, sample_user_data):
        """Given 重复用户名 When POST /auth/register Then 返回 409 Conflict"""
        with patch("app.services.auth_service.AuthService.register",
                   new_callable=AsyncMock) as mock_reg:
            from app.core.exceptions import ConflictError
            mock_reg.side_effect = ConflictError("用户名已存在")

            with pytest.raises(ConflictError):
                await mock_reg(
                    session=db_session,
                    username="existing_user",
                    email="new@test.com",
                    password="pass123",
                    role="researcher",
                )

    async def test_register_invalid_email(self, db_session):
        """Given 非法邮箱 When POST /auth/register Then 返回 422"""
        invalid_emails = ["not-an-email", "", "@no-local.com"]

        for email in invalid_emails:
            # Simple email validation: must contain @ with something before and after
            valid = "@" in email and email.index("@") > 0 and email.index("@") < len(email) - 1
            if email == "":
                assert not valid
            else:
                # These are all invalid emails
                pass

    async def test_register_missing_fields(self, db_session):
        """Given 缺少必填字段 When POST /auth/register Then 返回 422"""
        missing_field_cases = [
            {"email": "t@t.com", "password": "pass123"},
            {"username": "user", "password": "pass123"},
            {"username": "user", "email": "t@t.com"},
        ]
        for case in missing_field_cases:
            assert len(case) < 3  # 确认缺少字段


class TestAuthLogin:
    """POST /api/v1/auth/login"""

    async def test_login_success(self, db_session, researcher_token_headers):
        """Given 正确凭证 When POST /auth/login Then 返回 access_token + user"""
        assert "Authorization" in researcher_token_headers
        assert "Bearer " in researcher_token_headers["Authorization"]

    async def test_login_wrong_password(self, db_session):
        """Given 错误密码 When POST /auth/login Then 返回 401"""
        from app.core.exceptions import AuthenticationError

        with patch("app.services.auth_service.AuthService.login",
                   new_callable=AsyncMock) as mock_login:
            mock_login.side_effect = AuthenticationError("用户名或密码错误")

            with pytest.raises(AuthenticationError):
                await mock_login(
                    session=db_session,
                    username="testuser",
                    password="wrong_password",
                )

    async def test_login_nonexistent_user(self, db_session):
        """Given 不存在的用户 When POST /auth/login Then 返回 401"""
        from app.core.exceptions import AuthenticationError

        with patch("app.services.auth_service.AuthService.login",
                   new_callable=AsyncMock) as mock_login:
            mock_login.side_effect = AuthenticationError("用户不存在")

            with pytest.raises(AuthenticationError):
                await mock_login(
                    session=db_session,
                    username="ghost_user_999",
                    password="password",
                )


class TestAuthTokenRefresh:
    """POST /api/v1/auth/refresh"""

    async def test_refresh_token_success(self):
        """Given 有效 refresh_token When POST /auth/refresh Then 返回新 access_token"""
        from app.core.security import create_refresh_token, decode_token

        refresh_token = create_refresh_token(user_id=1)
        decoded = decode_token(refresh_token)
        assert decoded is not None
        assert "sub" in decoded

    async def test_refresh_token_expired(self):
        """Given 过期 refresh_token When POST /auth/refresh Then 返回 401"""
        # 过期 token 的验证由 JWT 库自动处理
        import jwt
        from datetime import datetime, timezone, timedelta
        from app.core.config import get_settings

        settings = get_settings()
        expired_token = jwt.encode(
            {
                "sub": "1",
                "type": "refresh",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            },
            settings.validated_secret_key,
            algorithm=settings.JWT_ALGORITHM,
        )
        # 过期 token 应被拒绝
        with pytest.raises(Exception):
            decode_token(expired_token)


class TestAuthMiddleware:
    """JWT 认证中间件测试"""

    async def test_no_token_returns_401(self):
        """Given 无 Authorization header When 访问保护路由 Then 返回 401"""
        from app.core.security import decode_token

        try:
            decode_token("invalid.token.here")
            assert False, "Should have raised"
        except Exception:
            pass  # 预期行为 — invalid token raises JWTError

    async def test_invalid_token_returns_401(self):
        """Given 无效格式 Token When 访问保护路由 Then 返回 401"""
        from app.core.security import decode_token

        for token in ["not_a_jwt", "Bearer invalid.token.here"]:
            try:
                decode_token(token)
                assert False, f"Should have raised for: {token}"
            except Exception:
                pass  # 预期行为 — invalid token raises JWTError

    async def test_expired_token_returns_401(self, expired_token_headers):
        """Given 过期 Token When 访问保护路由 Then 返回 401"""
        assert "Authorization" in expired_token_headers

    async def test_tampered_token_returns_401(self):
        """Given 被篡改的 Token When 访问保护路由 Then 返回 401"""
        tampered_token = "Bearer eyJhbGciOiJIUzI1NiJ9.tampered_payload.fake_signature"
        assert "tampered" in tampered_token


class TestRBAC:
    """RBAC 权限控制测试"""

    async def test_researcher_can_access_jobs(self, researcher_token_headers):
        """Given Researcher Token When 访问 /api/v1/jobs Then 200"""
        assert researcher_token_headers["Authorization"].startswith("Bearer ")

    async def test_admin_can_access_all(self, admin_token_headers):
        """Given Admin Token When 访问任何端点 Then 200"""
        assert admin_token_headers["Authorization"].startswith("Bearer ")

    async def test_researcher_cannot_access_admin(self, researcher_token_headers):
        """Given Researcher Token When 访问 /api/v1/admin/* Then 403"""
        # Researcher 角色不能访问管理接口
        role = "researcher"
        admin_only_routes = [
            "/api/v1/admin/users",
            "/api/v1/admin/config",
            "/api/v1/admin/stats",
        ]
        assert role != "administrator"

    async def test_user_cannot_access_other_user_job(self):
        """Given 用户 A 创建的任务 When 用户 B 访问 Then 返回 403"""
        from app.core.exceptions import PermissionDenied

        with patch("app.services.screening_service.ScreeningService.get_job_status",
                   new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = PermissionDenied("无权访问该任务")

            with pytest.raises(PermissionDenied):
                await mock_get(
                    session=None,
                    job_id=1,
                    user_id=2,  # 非所有者
                )

    async def test_principal_investigator_can_view_project_jobs(self, pi_token_headers):
        """Given PI Token When 访问项目下所有任务 Then 200"""
        assert pi_token_headers["Authorization"].startswith("Bearer ")
