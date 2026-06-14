"""
报告生成器

根据筛选结果和 AI 分析生成科研报告。
支持 PDF (通过 WeasyPrint/xhtml2pdf)、Markdown、HTML 三种格式。
"""

import os
import tempfile
from datetime import datetime
from typing import Any, Optional

from app.tools.base import BaseTool, ToolResult


class ReportGenerator(BaseTool):
    """科研报告生成工具

    整合筛选结果、AI 分析、药物信息等生成完整科研报告。
    支持 Markdown → PDF → HTML 的格式链。
    """

    name = "report_generator"
    description = "生成虚拟筛选科研报告（PDF/Markdown/HTML）"

    def generate_markdown(
        self,
        job_name: str,
        receptor_name: str,
        total_drugs: int,
        top_hits: list[dict[str, Any]],
        analysis_text: str,
        statistics: dict[str, Any] = None,
        output_path: str = None,
    ) -> ToolResult:
        """生成 Markdown 格式报告

        Args:
            job_name: 任务名称
            receptor_name: 受体/靶点名称
            total_drugs: 筛选药物总数
            top_hits: Top Hits 列表
            analysis_text: AI 分析文本
            statistics: 对接统计信息
            output_path: 输出路径（可选）

        Returns:
            ToolResult 包含 Markdown 文件路径和内容
        """
        md_lines = [
            f"# 虚拟筛选报告: {job_name}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 1. 筛选概要",
            "",
            f"| 参数 | 值 |",
            f"|------|-----|",
            f"| 任务名称 | {job_name} |",
            f"| 靶点蛋白 | {receptor_name} |",
            f"| 筛选药物总数 | {total_drugs} |",
            f"| Top Hits 数量 | {len(top_hits)} |",
        ]

        if statistics:
            md_lines.extend([
                f"| 最佳结合亲和力 | {statistics.get('best_score', 'N/A')} kcal/mol |",
                f"| 平均结合亲和力 | {statistics.get('mean_score', 'N/A'):.2f} kcal/mol |" if statistics.get('mean_score') else "",
                f"| 对接成功率 | {statistics.get('success_rate', 0) * 100:.1f}% |" if statistics.get('success_rate') else "",
            ])

        # Top Hits 表格
        md_lines.extend([
            "",
            "## 2. Top Hits 候选药物",
            "",
            "| 排名 | 药物名称 | 结合亲和力 (kcal/mol) |",
            "|------|----------|------------------------|",
        ])

        for hit in top_hits[:20]:
            md_lines.append(
                f"| {hit['rank']} | {hit.get('drug_name', 'N/A')} | {hit.get('affinity_score', 'N/A')} |"
            )

        # AI 分析
        md_lines.extend([
            "",
            "## 3. AI 智能分析",
            "",
            analysis_text,
            "",
            "---",
            f"*本报告由 AI Drug Screening Platform 自动生成*",
        ])

        content = "\n".join(md_lines)

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".md", prefix="report_")
            os.close(fd)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return ToolResult.success(
            data={
                "output_path": output_path,
                "content": content,
                "format": "markdown",
                "file_size": len(content.encode("utf-8")),
            }
        )

    def generate_pdf(
        self,
        job_name: str,
        receptor_name: str,
        total_drugs: int,
        top_hits: list[dict[str, Any]],
        analysis_text: str,
        statistics: dict[str, Any] = None,
        output_path: str = None,
    ) -> ToolResult:
        """生成 PDF 格式报告

        从 Markdown → HTML → PDF（通过 WeasyPrint 或 xhtml2pdf）。

        Args:
            job_name: 任务名称
            receptor_name: 受体名称
            total_drugs: 筛选药物总数
            top_hits: Top Hits 列表
            analysis_text: AI 分析文本
            statistics: 对接统计信息
            output_path: 输出路径

        Returns:
            ToolResult 包含 PDF 文件路径
        """
        # 先生成 Markdown
        md_result = self.generate_markdown(
            job_name=job_name,
            receptor_name=receptor_name,
            total_drugs=total_drugs,
            top_hits=top_hits,
            analysis_text=analysis_text,
            statistics=statistics,
        )

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="report_")
            os.close(fd)

        try:
            self._markdown_to_pdf(md_result.data["output_path"], output_path)
        except ImportError:
            # 无 PDF 库时回退：复制 Markdown 内容到 .txt
            fallback_path = output_path.replace(".pdf", ".txt")
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(md_result.data["content"])
            return ToolResult.success(
                data={
                    "output_path": fallback_path,
                    "format": "text_fallback",
                    "note": "PDF 库不可用，已生成文本版本",
                }
            )

        return ToolResult.success(
            data={
                "output_path": output_path,
                "format": "pdf",
                "file_size": os.path.getsize(output_path),
            }
        )

    def generate_html(
        self,
        job_name: str,
        receptor_name: str,
        total_drugs: int,
        top_hits: list[dict[str, Any]],
        analysis_text: str,
        statistics: dict[str, Any] = None,
        output_path: str = None,
    ) -> ToolResult:
        """生成 HTML 格式报告

        Args:
            job_name: 任务名称
            receptor_name: 受体名称
            total_drugs: 筛选药物总数
            top_hits: Top Hits 列表
            analysis_text: AI 分析文本
            statistics: 对接统计信息
            output_path: 输出路径

        Returns:
            ToolResult 包含 HTML 文件路径
        """
        # 先生成 Markdown 再转 HTML
        md_result = self.generate_markdown(
            job_name=job_name,
            receptor_name=receptor_name,
            total_drugs=total_drugs,
            top_hits=top_hits,
            analysis_text=analysis_text,
            statistics=statistics,
        )

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".html", prefix="report_")
            os.close(fd)

        try:
            import markdown as md
            html_body = md.markdown(md_result.data["content"], extensions=["tables", "fenced_code"])

            html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>虚拟筛选报告: {job_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; line-height: 1.6; color: #333; }}
        h1 {{ color: #1a5276; border-bottom: 2px solid #2980b9; padding-bottom: 0.3em; }}
        h2 {{ color: #2471a3; margin-top: 1.5em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #2980b9; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f8fd; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_template)

        except ImportError:
            # 无 markdown 库：直接包装纯文本为 HTML
            html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>虚拟筛选报告: {job_name}</title></head>
<body><pre>{md_result.data['content']}</pre></body>
</html>"""
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_template)

        return ToolResult.success(
            data={
                "output_path": output_path,
                "format": "html",
                "file_size": os.path.getsize(output_path),
            }
        )

    def _markdown_to_pdf(self, md_path: str, pdf_path: str) -> None:
        """将 Markdown 文件转为 PDF"""
        try:
            from weasyprint import HTML
            import markdown as md

            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            html_body = md.markdown(md_content, extensions=["tables", "fenced_code"])
            html_content = f"<html><body>{html_body}</body></html>"
            HTML(string=html_content).write_pdf(pdf_path)

        except ImportError:
            raise ImportError("需要安装 weasyprint 或 xhtml2pdf 以生成 PDF")
