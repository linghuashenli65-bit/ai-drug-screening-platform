"""
E2E 端到端测试 Fixture 配置 (Playwright)
测试完整用户流程

Usage:
    pytest e2e/ -v --browser chromium --headed
    playwright test
"""

import pytest
from typing import Generator


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """配置浏览器上下文参数"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }


@pytest.fixture(scope="session")
def base_url() -> str:
    """测试环境 base URL"""
    return "http://localhost:5173"  # Vite dev server


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """API base URL"""
    return "http://localhost:8000/api/v1"


@pytest.fixture
def test_user() -> dict:
    """标准测试用户"""
    return {
        "username": "test_researcher",
        "password": "SecurePass123!",
        "role": "researcher",
    }


@pytest.fixture
def admin_user() -> dict:
    """管理员测试用户"""
    return {
        "username": "test_admin",
        "password": "SecurePass123!",
        "role": "administrator",
    }


# ============================================================
# Playwright 页面 Fixtures (预期使用 sync Playwright)
# 注意: 实际运行时需要 playwright 库
# pip install playwright pytest-playwright
# playwright install chromium
# ============================================================


@pytest.fixture
def auth_page(page):
    """返回已登录的页面 (Researcher 角色)"""
    page.goto("http://localhost:5173/login")

    # 填写登录表单
    page.fill('input[name="username"]', "test_researcher")
    page.fill('input[name="password"]', "SecurePass123!")
    page.click('button[type="submit"]')

    # 等待跳转到 Dashboard
    page.wait_for_url("http://localhost:5173/dashboard")
    return page


@pytest.fixture
def admin_auth_page(page):
    """返回已登录的管理员页面"""
    page.goto("http://localhost:5173/login")

    page.fill('input[name="username"]', "test_admin")
    page.fill('input[name="password"]', "SecurePass123!")
    page.click('button[type="submit"]')

    page.wait_for_url("http://localhost:5173/dashboard")
    return page
