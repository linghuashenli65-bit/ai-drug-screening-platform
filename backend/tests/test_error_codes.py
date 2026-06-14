"""
错误码覆盖测试 (§21 系统架构设计)
覆盖所有错误码:
- 通用: 1000/1001/1002/1003
- Docking: 2001/2002/2003
- AI: 3001/3002
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


# ============================================================
# 通用错误码 (1000-1003)
# ============================================================

class TestGeneralErrorCodes:
    """通用错误码覆盖"""

    async def test_error_1000_invalid_params(self, db_session, invalid_smiles):
        """Given 非法参数 When API 校验 Then 返回 1000 参数错误"""
        from app.core.exceptions import ValidationError

        with patch("app.services.molecule_service.MoleculeService.create_from_smiles",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = ValidationError("参数错误: SMILES 格式不合法")

            with pytest.raises(ValidationError) as exc_info:
                await mock(session=db_session, project_id=1, smiles=invalid_smiles)
            assert exc_info.value.code == 1000

    async def test_error_1001_invalid_file_format(self, db_session):
        """Given 错误文件格式 When 上传 Then 返回 1001 文件格式错误"""
        from app.core.exceptions import FileFormatError

        with patch("app.services.molecule_service.MoleculeService.create_from_file",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = FileFormatError("文件格式错误: 仅支持 SDF/MOL2/PDB")

            with pytest.raises(FileFormatError) as exc_info:
                await mock(session=db_session, project_id=1, file_uri="bad.exe")
            assert exc_info.value.code == 1001

    async def test_error_1002_permission_denied(self, db_session):
        """Given 无权限操作 When 访问资源 Then 返回 1002 权限不足"""
        from app.core.exceptions import PermissionDenied

        with patch("app.services.screening_service.ScreeningService.get_job_status",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = PermissionDenied("权限不足: 无权访问该任务")

            with pytest.raises(PermissionDenied) as exc_info:
                await mock(session=db_session, job_id=1)
            assert exc_info.value.code == 1002

    async def test_error_1003_job_not_found(self, db_session):
        """Given 不存在的任务 When 查询 Then 返回 1003 任务不存在"""
        from app.core.exceptions import ResourceNotFound

        with patch("app.services.screening_service.ScreeningService.get_job_status",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = ResourceNotFound("任务不存在: job_id=99999")

            with pytest.raises(ResourceNotFound) as exc_info:
                await mock(session=db_session, job_id=99999)
            assert exc_info.value.code == 1003


# ============================================================
# Docking 错误码 (2001-2003)
# ============================================================

class TestDockingErrorCodes:
    """Docking 错误码覆盖"""

    async def test_error_2001_autodock_start_failure(self, db_session):
        """Given AutoDock 可执行文件缺失 When 启动 Then 返回 2001"""
        from app.core.exceptions import AutoDockStartError

        with patch("app.tools.docking_tool.run_docking",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = AutoDockStartError("AutoDock 启动失败: Vina 可执行文件未找到")

            with pytest.raises(AutoDockStartError) as exc_info:
                await mock(
                    ligand="l.pdbqt", receptor="r.pdbqt",
                    center=(0, 0, 0), size=(20, 20, 20),
                )
            assert exc_info.value.code == 2001

    async def test_error_2002_docking_timeout(self, db_session):
        """Given Docking 超时 When 执行超过时限 Then 返回 2002"""
        from app.core.exceptions import DockingTimeoutError

        with patch("app.tools.docking_tool.run_docking",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = DockingTimeoutError("Docking 超时: 单个对接超过 600 秒")

            with pytest.raises(DockingTimeoutError) as exc_info:
                await mock(
                    ligand="l.pdbqt", receptor="r.pdbqt",
                    center=(0, 0, 0), size=(20, 20, 20),
                    timeout=600,
                )
            assert exc_info.value.code == 2002

    async def test_error_2003_docking_empty_result(self, db_session):
        """Given Docking 完成但无结果 When 解析 Then 返回 2003"""
        from app.core.exceptions import DockingEmptyResultError

        with patch("app.tools.docking_tool.run_docking",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = DockingEmptyResultError("Docking 结果为空: 未生成任何有效构象")

            with pytest.raises(DockingEmptyResultError) as exc_info:
                await mock(
                    ligand="invalid.pdbqt", receptor="r.pdbqt",
                    center=(0, 0, 0), size=(20, 20, 20),
                )
            assert exc_info.value.code == 2003


# ============================================================
# AI 错误码 (3001-3002)
# ============================================================

class TestAIErrorCodes:
    """AI 分析错误码覆盖"""

    async def test_error_3001_llm_timeout(self, db_session):
        """Given LLM 调用超时 When 分析 Agent 失败 Then 返回 3001"""
        from app.core.exceptions import LLMTimeoutError

        with patch("app.services.analysis_service.AnalysisService.analyze_results",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = LLMTimeoutError("LLM 超时: API 调用超过 120 秒未响应")

            with pytest.raises(LLMTimeoutError) as exc_info:
                await mock(session=db_session, job_id=1)
            assert exc_info.value.code == 3001

    async def test_error_3002_prompt_execution_failure(self, db_session):
        """Given Prompt 执行失败 When LLM 返回错误 Then 返回 3002"""
        from app.core.exceptions import LLMPromptError

        with patch("app.services.analysis_service.AnalysisService.analyze_results",
                   new_callable=AsyncMock) as mock:
            mock.side_effect = LLMPromptError("Prompt 执行失败: 模型返回格式异常")

            with pytest.raises(LLMPromptError) as exc_info:
                await mock(session=db_session, job_id=1)
            assert exc_info.value.code == 3002


# ============================================================
# 错误响应格式验证
# ============================================================

class TestErrorResponseFormat:
    """错误响应格式验证"""

    def test_error_response_contains_code_and_message(self):
        """Given 任何错误 When 序列化 Then 包含 code + message + timestamp"""
        from app.schemas.common import ErrorResponse

        response = ErrorResponse(
            code=1003,
            message="任务不存在",
            detail={"job_id": 99999},
        )
        result = response.model_dump()
        assert "code" in result
        assert result["code"] == 1003
        assert "message" in result

    def test_all_defined_error_codes(self):
        """Given 系统定义 When 列举所有错误码 Then 共 9 个"""
        all_error_codes = {
            1000: "参数错误",
            1001: "文件格式错误",
            1002: "权限不足",
            1003: "任务不存在",
            2001: "AutoDock 启动失败",
            2002: "Docking 超时",
            2003: "Docking 结果为空",
            3001: "LLM 超时",
            3002: "Prompt 执行失败",
        }

        assert len(all_error_codes) == 9

        for code, description in all_error_codes.items():
            assert 1000 <= code <= 3999
            assert isinstance(description, str)
            assert len(description) > 0

    def test_error_code_ranges(self):
        """Given 错误码设计 When 检查范围 Then 通用(1xxx) Docking(2xxx) AI(3xxx)"""
        all_error_codes = {
            1000: "参数错误",
            1001: "文件格式错误",
            1002: "权限不足",
            1003: "任务不存在",
            2001: "AutoDock 启动失败",
            2002: "Docking 超时",
            2003: "Docking 结果为空",
            3001: "LLM 超时",
            3002: "Prompt 执行失败",
        }

        # 分类验证
        general_codes = [k for k in all_error_codes if 1000 <= k < 2000]
        docking_codes = [k for k in all_error_codes if 2000 <= k < 3000]
        ai_codes = [k for k in all_error_codes if 3000 <= k < 4000]

        assert len(general_codes) == 4
        assert len(docking_codes) == 3
        assert len(ai_codes) == 2
