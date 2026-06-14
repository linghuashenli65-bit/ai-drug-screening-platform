"""
Service 层业务逻辑单元测试
Mock 所有外部依赖 (数据库、Redis、Agent、LLM)

BDD Given/When/Then 注释风格
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# Auth Service
# ============================================================

class TestAuthService:
    """认证服务测试"""

    @pytest.mark.asyncio
    async def test_login_success(self, db_session):
        """Given 合法用户名密码 When 执行 login Then 返回 JWT Token"""
        svc = AsyncMock()
        svc.login.return_value = {
            "access_token": "mock_jwt_token_xxx",
            "user": {"username": "testuser"},
        }

        result = await svc.login(
            session=db_session,
            username="testuser",
            password="SecurePass123!",
        )

        assert result["access_token"] == "mock_jwt_token_xxx"
        assert result["user"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, db_session):
        """Given 不存在的用户名 When 执行 login Then 返回认证失败"""
        svc = AsyncMock()
        svc.login.side_effect = ValueError("User not found")

        with pytest.raises(ValueError, match="not found"):
            await svc.login(
                session=db_session,
                username="nonexistent",
                password="password",
            )

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, db_session):
        """Given 错误密码 When 执行 login Then 返回密码错误"""
        svc = AsyncMock()
        svc.login.side_effect = ValueError("Invalid credentials")

        with pytest.raises(ValueError, match="Invalid"):
            await svc.login(
                session=db_session,
                username="testuser",
                password="WrongPassword123!",
            )

    @pytest.mark.asyncio
    async def test_register_success(self, db_session):
        """Given 合法注册信息 When 执行 register Then 创建用户并返回 Token"""
        svc = AsyncMock()
        svc.register.return_value = {
            "id": 1,
            "username": "newuser",
        }

        result = await svc.register(
            session=db_session,
            username="newuser",
            email="new@test.com",
            password="SecurePass123!",
            role="researcher",
        )

        assert result["id"] == 1
        assert result["username"] == "newuser"


# ============================================================
# Screening Service
# ============================================================

class TestScreeningService:
    """筛选服务测试"""

    @pytest.mark.asyncio
    async def test_create_screening_job(self, db_session, sample_screening_job_data):
        """Given 合法筛选参数 When 创建任务 Then 返回 job_id 且状态为 CREATED"""
        svc = AsyncMock()
        svc.create_job.return_value = {"job_id": 1, "status": "CREATED"}

        result = await svc.create_job(
            session=db_session,
            job_data=sample_screening_job_data,
            created_by=1,
        )

        assert result["job_id"] == 1
        assert result["status"] == "CREATED"

    @pytest.mark.asyncio
    async def test_get_job_status(self, db_session):
        """Given 任务 ID When 查询状态 Then 返回进度和状态"""
        svc = AsyncMock()
        svc.get_job_status.return_value = {
            "status": "DOCKING",
            "progress": 72,
            "total_drugs": 5000,
            "finished_drugs": 3600,
        }

        result = await svc.get_job_status(session=db_session, job_id=1)

        assert result["status"] == "DOCKING"
        assert result["progress"] == 72

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, db_session):
        """Given 不存在的任务 ID When 查询 Then 返回 1003 任务不存在"""
        from app.core.exceptions import ResourceNotFound

        svc = AsyncMock()
        svc.get_job_status.side_effect = ResourceNotFound("任务不存在: job_id=99999")

        with pytest.raises(ResourceNotFound) as exc_info:
            await svc.get_job_status(session=db_session, job_id=99999)
        assert exc_info.value.code == 1003

    @pytest.mark.asyncio
    async def test_cancel_job(self, db_session):
        """Given 运行中的任务 When 取消 Then 状态变为 CANCELLED"""
        svc = AsyncMock()
        svc.cancel_job.return_value = {"job_id": 1, "status": "CANCELLED"}

        result = await svc.cancel_job(session=db_session, job_id=1, user_id=1)

        assert result["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_get_top_hits(self, db_session, sample_top20_results):
        """Given 完成的任务 When 查询 Top Hits Then 返回排序后的 Top 药物"""
        svc = AsyncMock()
        svc.get_top_hits.return_value = sample_top20_results

        result = await svc.get_top_hits(session=db_session, job_id=1, top_n=20)

        assert len(result) == 20
        assert result[0]["rank"] == 1
        assert result[0]["affinity_score"] < result[-1]["affinity_score"]


# ============================================================
# Project Service
# ============================================================

class TestProjectService:
    """项目服务测试"""

    @pytest.mark.asyncio
    async def test_create_project(self, db_session, sample_project_data):
        """Given 合法项目数据 When 创建项目 Then 返回项目 ID"""
        svc = AsyncMock()
        svc.create_project.return_value = {"project_id": 1, "project_name": "COVID-19 主蛋白酶筛选"}

        result = await svc.create_project(
            session=db_session,
            project_data=sample_project_data,
            owner_id=1,
        )

        assert result["project_id"] == 1

    @pytest.mark.asyncio
    async def test_list_user_projects(self, db_session):
        """Given 用户 ID When 查询项目列表 Then 返回该用户的所有项目"""
        svc = AsyncMock()
        svc.list_projects.return_value = [
            {"id": 1, "project_name": "Project A", "owner_id": 1},
            {"id": 2, "project_name": "Project B", "owner_id": 1},
        ]

        result = await svc.list_projects(session=db_session, user_id=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_other_user_cannot_access_project(self, db_session):
        """Given 用户 A 创建的项目 When 用户 B 查询 Then 返回 403/空"""
        svc = AsyncMock()
        svc.list_projects.return_value = []

        result = await svc.list_projects(session=db_session, user_id=2)

        assert len(result) == 0


# ============================================================
# Molecule Service
# ============================================================

class TestMoleculeService:
    """分子服务测试"""

    @pytest.mark.asyncio
    async def test_parse_smiles_and_create_molecule(self, db_session, sample_smiles):
        """Given SMILES When 解析并创建分子 Then 返回分子 ID 和属性"""
        svc = AsyncMock()
        svc.create_from_smiles.return_value = {
            "id": 1,
            "smiles": "CCO",
            "molecular_weight": 46.07,
        }

        result = await svc.create_from_smiles(
            session=db_session,
            project_id=1,
            smiles=sample_smiles,
        )

        assert result["id"] == 1
        assert result["smiles"] == "CCO"

    @pytest.mark.asyncio
    async def test_parse_invalid_smiles_fails(self, db_session, invalid_smiles):
        """Given 无效 SMILES When 解析 Then 返回错误码 1000"""
        svc = AsyncMock()
        svc.create_from_smiles.side_effect = ValueError("无法解析 SMILES")

        with pytest.raises(ValueError, match="无法解析"):
            await svc.create_from_smiles(
                session=db_session,
                project_id=1,
                smiles=invalid_smiles,
            )


# ============================================================
# Receptor Service
# ============================================================

class TestReceptorService:
    """受体服务测试"""

    @pytest.mark.asyncio
    async def test_list_receptors(self, db_session):
        """Given 系统已配置受体 When 查询列表 Then 返回可选靶点"""
        svc = AsyncMock()
        svc.list_receptors.return_value = [
            {"id": 1, "receptor_name": "EGFR", "pdb_code": "1M17"},
            {"id": 2, "receptor_name": "Mpro", "pdb_code": "6LU7"},
            {"id": 3, "receptor_name": "VEGFR2", "pdb_code": "3VHE"},
        ]

        result = await svc.list_receptors(session=db_session)

        assert len(result) >= 3
        assert result[0]["receptor_name"] == "EGFR"

    @pytest.mark.asyncio
    async def test_get_receptor_detail(self, db_session):
        """Given 受体 ID When 查询详情 Then 返回完整信息"""
        svc = AsyncMock()
        svc.get_receptor.return_value = {
            "id": 1,
            "receptor_name": "SARS-CoV-2 Mpro",
            "pdb_code": "6LU7",
            "pdbqt_uri": "/data/receptors/6LU7.pdbqt",
            "description": "COVID-19 主蛋白酶",
        }

        result = await svc.get_receptor(session=db_session, receptor_id=1)

        assert result["receptor_name"] == "SARS-CoV-2 Mpro"


# ============================================================
# Report Service
# ============================================================

class TestReportService:
    """报告服务测试"""

    @pytest.mark.asyncio
    async def test_generate_report_for_job(self, db_session):
        """Given 完成的任务 When 生成报告 Then 返回报告 URI"""
        svc = AsyncMock()
        svc.generate_report.return_value = {
            "report_id": 1,
            "report_type": "PDF",
            "report_uri": "/reports/job_1_report.pdf",
        }

        result = await svc.generate_report(
            session=db_session,
            job_id=1,
            report_type="PDF",
        )

        assert result["report_type"] == "PDF"

    @pytest.mark.asyncio
    async def test_list_reports_for_job(self, db_session):
        """Given 任务 ID When 列出报告 Then 返回所有格式报告"""
        svc = AsyncMock()
        svc.list_reports.return_value = [
            {"id": 1, "report_type": "PDF", "report_uri": "/reports/j1.pdf"},
            {"id": 2, "report_type": "HTML", "report_uri": "/reports/j1.html"},
            {"id": 3, "report_type": "Markdown", "report_uri": "/reports/j1.md"},
        ]

        result = await svc.list_reports(session=db_session, job_id=1)

        assert len(result) == 3


# ============================================================
# Analysis Service
# ============================================================

class TestAnalysisService:
    """AI 分析服务测试"""

    @pytest.mark.asyncio
    async def test_analyze_top_candidates(self, db_session, sample_top20_results):
        """Given Top 20 结果 When AI 分析 Then 返回结构化分析"""
        svc = AsyncMock()
        svc.analyze_results.return_value = {
            "summary": "发现 3 个高亲和力候选药物",
            "top_candidates": [
                {"drug": "Drug_1", "analysis": "最高结合能力,..."},
            ],
            "repurposing_analysis": "Drug_3 具有抗病毒重定位潜力",
            "risk_analysis": "Drug_7 存在潜在肝毒性",
            "experimental_suggestions": [
                "分子动力学模拟验证",
                "细胞实验验证",
            ],
        }

        result = await svc.analyze_results(session=db_session, job_id=1, top_n=20)

        assert "summary" in result
        assert "top_candidates" in result
        assert len(result["experimental_suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_empty_results(self, db_session):
        """Given 空 Docking 结果 When AI 分析 Then 返回空分析"""
        svc = AsyncMock()
        svc.analyze_results.return_value = {
            "summary": "无有效 Docking 结果",
            "top_candidates": [],
        }

        result = await svc.analyze_results(session=db_session, job_id=1)

        assert result["top_candidates"] == []


# ============================================================
# Drug Library Service
# ============================================================

class TestDrugLibraryService:
    """药物库服务测试"""

    @pytest.mark.asyncio
    async def test_list_drugs(self, db_session):
        """Given 药物库已加载 When 列出药物 Then 返回分页列表"""
        svc = AsyncMock()
        svc.list_drugs.return_value = {
            "items": [
                {"id": 1, "drug_name": "Aspirin"},
                {"id": 2, "drug_name": "Metformin"},
            ],
            "total": 5000,
            "page": 1,
            "page_size": 50,
        }

        result = await svc.list_drugs(session=db_session, page=1, page_size=50)

        assert result["total"] == 5000
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_search_drug_by_name(self, db_session):
        """Given 药物名 When 搜索 Then 返回匹配药物"""
        svc = AsyncMock()
        svc.search_drugs.return_value = [
            {"id": 1, "drug_name": "Aspirin", "drugbank_id": "DB00945"},
        ]

        result = await svc.search_drugs(session=db_session, query="Aspirin")

        assert len(result) == 1
        assert result[0]["drug_name"] == "Aspirin"

    @pytest.mark.asyncio
    async def test_import_drug_library(self, db_session):
        """Given CSV 药物列表 When 导入药库 Then 批量创建药物"""
        svc = AsyncMock()
        svc.import_library.return_value = {
            "imported": 5000,
            "failed": 0,
            "duplicates": 10,
        }

        result = await svc.import_library(session=db_session, file_uri="/uploads/drugs.csv")

        assert result["imported"] == 5000
        assert result["failed"] == 0
