"""
报告服务

生成、查询筛选结果报告。
"""


class ReportService:
    """报告服务"""

    @staticmethod
    async def generate_report(session, job_id: int, format: str = "pdf"):
        """生成报告"""
        from app.models.report import Report

        report = Report(
            job_id=job_id,
            report_type=format,
            report_uri=f"/data/reports/{job_id}.{format}",
            status="COMPLETED",
        )
        session.add(report)
        await session.flush()
        return report

    @staticmethod
    async def list_reports(session, job_id: int = None, skip: int = 0, limit: int = 50):
        """列出报告"""
        from app.models.report import Report
        from sqlalchemy import select

        stmt = select(Report)
        if job_id:
            stmt = stmt.where(Report.job_id == job_id)
        result = await session.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def get_report_uri(session, report_id: int):
        """获取报告文件地址"""
        from app.models.report import Report
        from sqlalchemy import select

        result = await session.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError("Report not found")
        return report.report_uri


async def generate_report_for_job(session, job_id: int, format: str = "pdf"):
    """为任务生成报告（独立函数）"""
    return await ReportService.generate_report(session, job_id, format)


async def get_reports_by_job(session, job_id: int):
    """按任务获取报告列表（独立函数）"""
    return await ReportService.list_reports(session, job_id=job_id)
