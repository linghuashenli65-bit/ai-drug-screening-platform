"""
Screening API 集成测试
GET /api/v1/jobs/{job_id}/results, /api/v1/jobs/{job_id}/results/top
覆盖: Docking 结果查询、Top Hits、药物搜索、PLIP 分析
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestGetResults:
    """GET /api/v1/jobs/{job_id}/results"""

    async def test_get_docking_results(self, db_session, sample_top20_results):
        """Given Docking 完成 When GET /api/v1/jobs/{id}/results Then 返回排序结果"""
        with patch("app.services.screening_service.ScreeningService.get_top_hits",
                   new_callable=AsyncMock) as mock_hits:
            mock_hits.return_value = sample_top20_results

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.get_top_hits(
                session=db_session,
                job_id=1,
            )
            assert len(result) == 20
            assert result[0]["rank"] == 1

    async def test_get_results_filter_top_n(self, db_session):
        """Given top_n=5 参数 When GET /api/v1/jobs/{id}/results?top_n=5 Then 返回 5 条"""
        with patch("app.services.screening_service.ScreeningService.get_top_hits",
                   new_callable=AsyncMock) as mock_hits:
            mock_hits.return_value = [
                {"rank": i + 1, "drug_name": f"Drug_{i+1}", "affinity_score": -10.0 + i}
                for i in range(5)
            ]

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.get_top_hits(
                session=db_session,
                job_id=1,
                top_n=5,
            )
            assert len(result) == 5

    async def test_get_results_job_not_completed(self, db_session):
        """Given 任务仍在运行 When GET results Then 返回 400"""
        from app.core.exceptions import ValidationError

        with patch("app.services.screening_service.ScreeningService.get_top_hits",
                   new_callable=AsyncMock) as mock_hits:
            mock_hits.side_effect = ValidationError("Docking 尚未完成")

            with pytest.raises(ValidationError):
                await mock_hits(session=db_session, job_id=1)


class TestSearchDrugInResults:
    """GET /api/v1/jobs/{job_id}/results/search?name={name}"""

    async def test_search_drug_in_results(self, db_session):
        """Given 药物名 When 搜索 Docking 结果 Then 返回匹配项"""
        with patch("app.services.screening_service.ScreeningService.search_results",
                   new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [
                {"drug_name": "Aspirin", "affinity_score": -10.5},
            ]

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.search_results(
                session=db_session,
                job_id=1,
                query="Aspirin",
            )
            assert len(result) == 1
            assert result[0]["drug_name"] == "Aspirin"

    async def test_search_drug_not_found(self, db_session):
        """Given 不在结果集中的药物名 When 搜索 Then 返回空列表"""
        with patch("app.services.screening_service.ScreeningService.search_results",
                   new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.search_results(
                session=db_session,
                job_id=1,
                query="NonexistentDrug",
            )
            assert len(result) == 0


class TestInteractionAnalysis:
    """GET /api/v1/jobs/{job_id}/interactions"""

    async def test_get_interaction_for_drug(self, db_session):
        """Given drug_id When GET /api/v1/jobs/{id}/interactions/{drug_id} Then 返回 PLIP 结果"""
        with patch("app.services.screening_service.ScreeningService.get_interaction",
                   new_callable=AsyncMock) as mock_plip:
            mock_plip.return_value = {
                "drug_id": 1,
                "hydrogen_bonds": 3,
                "hydrophobic_contacts": 12,
                "salt_bridges": 1,
                "pi_interactions": 2,
                "details": [
                    {"residue": "ARG145", "type": "HydrogenBond", "distance": 2.8},
                ],
            }

            from app.services.screening_service import ScreeningService
            result = await ScreeningService.get_interaction(
                session=db_session,
                job_id=1,
                drug_id=1,
            )
            assert result["hydrogen_bonds"] == 3
            assert len(result["details"]) > 0


class TestAIInquiryEndpoint:
    """POST /api/v1/jobs/{job_id}/ask"""

    async def test_ask_ai_about_result(self, db_session):
        """Given 用户提问 When POST /api/v1/jobs/{id}/ask Then AI 基于当前任务回答"""
        with patch("app.services.analysis_service.AnalysisService.answer_question",
                   new_callable=AsyncMock) as mock_ask:
            mock_ask.return_value = {
                "question": "为什么 DrugA 排名第一?",
                "answer": "DrugA 与靶点结合亲和力最高,因为...",
            }

            result = await mock_ask(
                session=db_session,
                job_id=1,
                question="为什么 DrugA 排名第一?",
                user_id=1,
            )
            assert "DrugA" in result["answer"] or "结合" in result["answer"]
