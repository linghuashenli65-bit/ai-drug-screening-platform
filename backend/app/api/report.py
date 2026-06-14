"""
报告 API

GET /api/v1/reports                  — 查询报告列表
GET /api/v1/reports/{job_id}         — 获取报告信息
GET /api/v1/reports/{job_id}/preview — 在线预览（HTML）
GET /api/v1/reports/{job_id}/download — 下载报告文件
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import PermissionDenied, ResourceNotFound
from app.core.security import get_current_user
from app.models.docking import DockingTask
from app.models.report import Report
from app.models.screening import ScreeningJob

import os
import tempfile
from pathlib import Path

router = APIRouter()


async def _get_job_with_permission(job_id: int, current_user: dict, db: AsyncSession) -> "ScreeningJob":
    """获取任务并检查权限"""
    job_result = await db.execute(select(ScreeningJob).where(ScreeningJob.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise ResourceNotFound(message=f"任务 ID={job_id} 不存在")
    if current_user["role"] not in ("ADMIN", "PI") and job.created_by != current_user["user_id"]:
        raise PermissionDenied(message="无权访问此任务")
    return job


async def _get_top_hits(job_id: int, db: AsyncSession, limit: int = 20) -> list[dict]:
    """获取任务的 Top Hits"""
    result = await db.execute(
        select(DockingTask)
        .where(DockingTask.job_id == job_id, DockingTask.status == "SUCCESS")
        .order_by(DockingTask.affinity_score.asc())
        .limit(limit)
    )
    tasks = result.scalars().all()
    hits = []
    for rank, t in enumerate(tasks, 1):
        drug_name = t.drug.drug_name if t.drug else f"Drug-{t.drug_id}"
        hits.append({
            "rank": rank,
            "drug_name": drug_name,
            "affinity_score": float(t.affinity_score) if t.affinity_score else None,
        })
    return hits


def _generate_html_report(job: "ScreeningJob", top_hits: list[dict], analysis_text: str = "") -> str:
    """生成 HTML 格式报告内容"""
    from datetime import datetime

    hits_rows = ""
    for hit in top_hits:
        score = f"{hit['affinity_score']:.2f}" if hit['affinity_score'] else "N/A"
        hits_rows += f"<tr><td>{hit['rank']}</td><td>{hit['drug_name']}</td><td>{score}</td></tr>\n"

    analysis_html = ""
    if analysis_text:
        paragraphs = analysis_text.replace("**", "").split("\n")
        for p in paragraphs:
            p = p.strip()
            if p:
                analysis_html += f"<p>{p}</p>\n"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>筛选报告: {job.job_name}</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 2em; line-height: 1.7; color: #333; background: #fff; }}
  h1 {{ color: #1a365d; border-bottom: 3px solid #3182ce; padding-bottom: 0.4em; }}
  h2 {{ color: #2c5282; margin-top: 2em; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 10px 14px; text-align: left; }}
  th {{ background: #3182ce; color: #fff; font-weight: 500; }}
  tr:nth-child(even) {{ background: #f7fafc; }}
  .meta {{ color: #718096; font-size: 0.9em; margin-bottom: 2em; }}
  .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 1em 0; }}
  .summary-item {{ background: #f7fafc; border-radius: 8px; padding: 12px 16px; }}
  .summary-item .label {{ color: #718096; font-size: 0.85em; }}
  .summary-item .value {{ font-size: 1.1em; font-weight: 600; color: #2d3748; }}
  .analysis {{ background: #f0fff4; border-left: 4px solid #38a169; padding: 1em 1.5em; margin: 1em 0; border-radius: 0 8px 8px 0; }}
  .footer {{ margin-top: 3em; padding-top: 1em; border-top: 1px solid #e2e8f0; color: #a0aec0; font-size: 0.85em; text-align: center; }}
</style>
</head>
<body>
<h1>{job.job_name}</h1>
<div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

<h2>筛选概要</h2>
<div class="summary-grid">
  <div class="summary-item"><div class="label">任务名称</div><div class="value">{job.job_name}</div></div>
  <div class="summary-item"><div class="label">筛选药物总数</div><div class="value">{job.total_drugs or 0}</div></div>
  <div class="summary-item"><div class="label">完成对接数</div><div class="value">{job.finished_drugs or 0}</div></div>
  <div class="summary-item"><div class="label">Top Hits</div><div class="value">{len(top_hits)} 个</div></div>
</div>

<h2>Top Hits 候选药物</h2>
<table>
<thead><tr><th>排名</th><th>药物名称</th><th>结合亲和力 (kcal/mol)</th></tr></thead>
<tbody>
{hits_rows if hits_rows else "<tr><td colspan='3' style='text-align:center;color:#a0aec0'>暂无对接数据</td></tr>"}
</tbody>
</table>

{"<h2>AI 智能分析</h2><div class='analysis'>" + analysis_html + "</div>" if analysis_html else ""}

<div class="footer">本报告由 AI Drug Screening Platform 自动生成</div>
</body>
</html>"""


def _generate_markdown_report(job: "ScreeningJob", top_hits: list[dict], analysis_text: str = "") -> str:
    """生成 Markdown 格式报告"""
    from datetime import datetime

    lines = [
        f"# 虚拟筛选报告: {job.job_name}",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 1. 筛选概要",
        "",
        "| 参数 | 值 |",
        "|------|-----|",
        f"| 任务名称 | {job.job_name} |",
        f"| 筛选药物总数 | {job.total_drugs or 0} |",
        f"| 完成对接数 | {job.finished_drugs or 0} |",
        f"| Top Hits 数量 | {len(top_hits)} |",
        "",
        "## 2. Top Hits 候选药物",
        "",
        "| 排名 | 药物名称 | 结合亲和力 (kcal/mol) |",
        "|------|----------|------------------------|",
    ]

    for hit in top_hits:
        score = f"{hit['affinity_score']:.2f}" if hit['affinity_score'] else "N/A"
        lines.append(f"| {hit['rank']} | {hit['drug_name']} | {score} |")

    if analysis_text:
        lines.extend(["", "## 3. AI 智能分析", "", analysis_text])

    lines.extend(["", "---", "*本报告由 AI Drug Screening Platform 自动生成*"])
    return "\n".join(lines)


@router.get("/")
async def list_reports(
    job_id: Optional[int] = Query(None, description="按任务 ID 筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询报告列表"""
    base_query = select(Report)
    if job_id:
        base_query = base_query.where(Report.job_id == job_id)

    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    base_query = base_query.order_by(Report.generated_at.desc())
    base_query = base_query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(base_query)
    reports = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reports": [
            {
                "id": r.id,
                "job_id": r.job_id,
                "report_type": r.report_type,
                "report_uri": r.report_uri,
                "generated_at": str(r.generated_at) if r.generated_at else None,
            }
            for r in reports
        ],
    }


@router.get("/{job_id}")
async def get_report(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定任务的报告信息"""
    result = await db.execute(
        select(Report).where(Report.job_id == job_id).order_by(Report.generated_at.desc())
    )
    reports = result.scalars().all()

    return {
        "job_id": job_id,
        "reports": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "report_uri": r.report_uri,
                "generated_at": str(r.generated_at) if r.generated_at else None,
            }
            for r in reports
        ],
    }


@router.get("/{job_id}/preview")
async def preview_report(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在线预览报告（返回 HTML）"""
    job = await _get_job_with_permission(job_id, current_user, db)
    top_hits = await _get_top_hits(job_id, db)

    # 尝试获取 AI 分析文本
    analysis_text = ""
    try:
        from app.models.analysis import AIAnalysisResult
        ar = await db.execute(
            select(AIAnalysisResult).where(AIAnalysisResult.job_id == job_id).limit(1)
        )
        analysis_record = ar.scalar_one_or_none()
        if analysis_record:
            parts = []
            if analysis_record.summary:
                parts.append(analysis_record.summary)
            if analysis_record.recommendation:
                parts.append(analysis_record.recommendation)
            if analysis_record.risk_analysis:
                parts.append(analysis_record.risk_analysis)
            analysis_text = "\n\n".join(parts)
    except Exception:
        pass

    html = _generate_html_report(job, top_hits, analysis_text)
    return HTMLResponse(content=html)


@router.get("/{job_id}/download")
async def download_report(
    job_id: int,
    report_type: str = Query("pdf", description="报告格式: pdf, markdown"),
    format: str = Query(None, description="兼容前端参数名"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下载报告文件（支持按需生成）"""
    # 兼容前端传 format 参数
    actual_type = format or report_type

    job = await _get_job_with_permission(job_id, current_user, db)

    # 先查 DB 中是否有已生成的报告
    result = await db.execute(
        select(Report)
        .where(Report.job_id == job_id, Report.report_type.ilike(f"%{actual_type}%"))
        .order_by(Report.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if report and report.report_uri:
        # 尝试从存储中返回已有报告
        uri = report.report_uri
        if uri.startswith("minio://"):
            try:
                from app.core.minio import download_file, parse_minio_uri
                bucket, obj_name = parse_minio_uri(uri)
                tmp_path = os.path.join(tempfile.gettempdir(), f"report_{job_id}.{actual_type}")
                await download_file(bucket, obj_name, tmp_path)
                mime_map = {"pdf": "application/pdf", "markdown": "text/markdown", "html": "text/html"}
                return FileResponse(tmp_path, media_type=mime_map.get(actual_type, "application/octet-stream"),
                                    filename=f"screening_report_{job_id}.{actual_type}")
            except Exception:
                pass

    # 按需生成报告
    top_hits = await _get_top_hits(job_id, db)
    analysis_text = ""
    try:
        from app.models.analysis import AIAnalysisResult
        ar = await db.execute(
            select(AIAnalysisResult).where(AIAnalysisResult.job_id == job_id).limit(1)
        )
        analysis_record = ar.scalar_one_or_none()
        if analysis_record:
            parts = []
            if analysis_record.summary:
                parts.append(analysis_record.summary)
            if analysis_record.recommendation:
                parts.append(analysis_record.recommendation)
            if analysis_record.risk_analysis:
                parts.append(analysis_record.risk_analysis)
            analysis_text = "\n\n".join(parts)
    except Exception:
        pass

    if actual_type == "markdown":
        content = _generate_markdown_report(job, top_hits, analysis_text)
        return PlainTextResponse(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="report_{job_id}.md"'},
        )
    else:
        # PDF 不可用时返回 HTML 作为替代
        html = _generate_html_report(job, top_hits, analysis_text)
        tmp_path = os.path.join(tempfile.gettempdir(), f"report_{job_id}.html")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(html)
        return FileResponse(
            tmp_path,
            media_type="text/html; charset=utf-8",
            filename=f"screening_report_{job_id}.html",
        )
