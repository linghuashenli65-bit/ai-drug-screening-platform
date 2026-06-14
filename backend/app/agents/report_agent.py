"""
Report Agent — 报告自动生成

职责：
- 整合筛选结果、AI 分析、药物信息
- 生成 Markdown 格式报告
- 生成 PDF 格式报告
- 生成 HTML 格式报告
- 上传报告至 MinIO

输入: {"top_hits": [...], "overall_analysis": "...", "statistics": {...}}
输出: {"report_uri": "minio://...", "report_type": "PDF"}
"""

from typing import Any

from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.core.minio import upload_file, parse_minio_uri
from app.tools.report.generator import ReportGenerator

settings = get_settings()


class ReportAgent(BaseAgent):
    """报告生成 Agent

    整合全部筛选和 AI 分析结果，生成结构化科研报告。
    """

    name = "ReportAgent"
    description = "整合结果、生成 PDF/Markdown/HTML 科研报告"

    def __init__(self):
        super().__init__()
        self.generator = ReportGenerator()

    def _validate_input(self, state: dict[str, Any]) -> None:
        top_hits = state.get("top_hits", [])
        if not top_hits:
            raise ValueError("ReportAgent: top_hits 为空")

    async def _execute(self, state: dict[str, Any]) -> dict[str, Any]:
        job_name = state.get("job_name", "Untitled")
        receptor_name = state.get("receptor_name", "Unknown")
        total_drugs = state.get("total_drugs", 0)
        top_hits = state.get("top_hits", [])
        analysis_text = state.get("overall_analysis", "")
        statistics = state.get("statistics", {})
        report_format = state.get("report_format", settings.REPORT_DEFAULT_FORMAT).lower()
        job_id = state.get("task_id")

        # 生成报告
        if report_format == "markdown":
            result = self.generator.generate_markdown(
                job_name=job_name,
                receptor_name=receptor_name,
                total_drugs=total_drugs,
                top_hits=top_hits,
                analysis_text=analysis_text,
                statistics=statistics,
            )
        elif report_format == "html":
            result = self.generator.generate_html(
                job_name=job_name,
                receptor_name=receptor_name,
                total_drugs=total_drugs,
                top_hits=top_hits,
                analysis_text=analysis_text,
                statistics=statistics,
            )
        else:  # PDF
            result = self.generator.generate_pdf(
                job_name=job_name,
                receptor_name=receptor_name,
                total_drugs=total_drugs,
                top_hits=top_hits,
                analysis_text=analysis_text,
                statistics=statistics,
            )

        output_path = result.data.get("output_path")
        actual_format = result.data.get("format", report_format)

        # 上传到 MinIO
        report_uri = None
        if output_path and job_id:
            try:
                object_name = f"{job_id}/report.{actual_format}"
                report_uri = await upload_file(
                    bucket=settings.MINIO_BUCKET_REPORTS,
                    object_name=object_name,
                    file_path=output_path,
                    content_type=f"application/{actual_format}",
                )
            except Exception as e:
                self.logger.warning(f"MinIO 上传失败: {e}，使用本地路径")
                report_uri = f"file://{output_path}"

        return {
            "report_uri": report_uri,
            "report_type": actual_format,
            "report_content": result.data.get("content", ""),
            "file_size": result.data.get("file_size", 0),
            "report_generated": True,
        }

    def _format_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return {
            "report_uri": output.get("report_uri"),
            "report_type": output.get("report_type"),
            "file_size": output.get("file_size", 0),
            "report_generated": output.get("report_generated", False),
        }
