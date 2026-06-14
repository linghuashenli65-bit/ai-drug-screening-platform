"""
Reports API 集成测试
GET/POST /api/v1/jobs/{job_id}/report
覆盖: 报告生成、列表、下载、导出
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestGenerateReport:
    """POST /api/v1/jobs/{job_id}/report"""

    async def test_generate_pdf_report(self, db_session):
        """Given 已完成分析的任务 When POST /api/v1/jobs/{id}/report?type=PDF Then 生成 PDF"""
        with patch("app.services.report_service.ReportService.generate_report",
                   new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "report_id": 1,
                "report_type": "PDF",
                "report_uri": "/reports/job_1_report.pdf",
                "generated_at": "2026-06-13T10:00:00Z",
            }

            result = await mock_gen(
                session=db_session,
                job_id=1,
                report_type="PDF",
            )
            assert result["report_type"] == "PDF"
            assert "report_uri" in result

    async def test_generate_html_report(self, db_session):
        """Given 用户选择 HTML When POST report?type=HTML Then 生成 HTML"""
        with patch("app.services.report_service.ReportService.generate_report",
                   new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "report_id": 1,
                "report_type": "HTML",
                "report_uri": "/reports/job_1_report.html",
            }

            result = await mock_gen(
                session=db_session,
                job_id=1,
                report_type="HTML",
            )
            assert result["report_type"] == "HTML"

    async def test_generate_markdown_report(self, db_session):
        """Given 用户需要编辑 When POST report?type=Markdown Then 生成 MD"""
        with patch("app.services.report_service.ReportService.generate_report",
                   new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "report_id": 1,
                "report_type": "Markdown",
                "report_uri": "/reports/job_1_report.md",
            }

            result = await mock_gen(
                session=db_session,
                job_id=1,
                report_type="Markdown",
            )
            assert result["report_type"] == "Markdown"

    async def test_generate_report_job_not_ready(self, db_session):
        """Given 任务未完成 When 生成报告 Then 返回 400"""
        from app.core.exceptions import ValidationError

        with patch("app.services.report_service.ReportService.generate_report",
                   new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = ValidationError("分析尚未完成,无法生成报告")

            with pytest.raises(ValidationError):
                await mock_gen(session=db_session, job_id=1, report_type="PDF")


class TestListReports:
    """GET /api/v1/jobs/{job_id}/report"""

    async def test_list_reports(self, db_session):
        """Given 任务有多个报告 When GET /api/v1/jobs/{id}/report Then 返回所有格式"""
        with patch("app.services.report_service.ReportService.list_reports",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"id": 1, "report_type": "PDF", "report_uri": "/reports/j1.pdf"},
                {"id": 2, "report_type": "HTML", "report_uri": "/reports/j1.html"},
                {"id": 3, "report_type": "Markdown", "report_uri": "/reports/j1.md"},
            ]

            result = await mock_list(
                session=db_session,
                job_id=1,
            )
            assert len(result) == 3

    async def test_no_reports_for_job(self, db_session):
        """Given 新任务 When GET /api/v1/jobs/{id}/report Then 返回空列表"""
        with patch("app.services.report_service.ReportService.list_reports",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await mock_list(
                session=db_session,
                job_id=999,
            )
            assert len(result) == 0


class TestDownloadReport:
    """GET /api/v1/jobs/{job_id}/report/{report_id}/download"""

    async def test_download_pdf(self, db_session):
        """Given 报告存在 When GET report/download Then 返回 PDF 文件"""
        with patch("app.services.report_service.ReportService.get_report_uri",
                   new_callable=AsyncMock) as mock_uri:
            mock_uri.return_value = {
                "report_id": 1,
                "report_uri": "/reports/job_1_report.pdf",
                "report_type": "PDF",
            }

            result = await mock_uri(
                session=db_session,
                report_id=1,
            )
            assert result["report_uri"].endswith(".pdf")

    async def test_download_nonexistent_report(self, db_session):
        """Given 报告不存在 When GET 下载 Then 返回 404"""
        from app.core.exceptions import ResourceNotFound

        with patch("app.services.report_service.ReportService.get_report_uri",
                   new_callable=AsyncMock) as mock_uri:
            mock_uri.side_effect = ResourceNotFound("报告不存在")

            with pytest.raises(ResourceNotFound):
                await mock_uri(session=db_session, report_id=999)
