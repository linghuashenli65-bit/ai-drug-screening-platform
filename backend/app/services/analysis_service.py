"""
AI 分析服务

LLM 驱动的药物筛选结果分析和推荐。
"""


class AnalysisService:
    """AI 分析服务"""

    @staticmethod
    async def analyze_results(session, job_id: int):
        """分析筛选结果"""
        from app.models.analysis import AIAnalysisResult

        result = AIAnalysisResult(
            job_id=job_id,
            drug_id=0,
            llm_model="gpt-4",
            summary="Analysis complete",
        )
        session.add(result)
        await session.flush()
        return result

    @staticmethod
    async def answer_question(session, job_id: int, question: str):
        """对筛选结果进行问答"""
        return {"answer": f"Q: {question} - Analysis pending"}

    @staticmethod
    async def analyze_candidates(session, job_id: int, top_n: int = 20):
        """分析候选药物"""
        return {
            "summary": f"Analyzed top {top_n} candidates",
            "candidates": [],
        }


async def analyze_candidates(session, job_id: int, top_n: int = 20):
    """分析候选药物（独立函数）"""
    return await AnalysisService.analyze_candidates(session, job_id, top_n)
