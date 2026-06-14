"""
PubMed 文献检索工具

通过 NCBI Entrez API 检索 PubMed 文献：
- 按药物名称/靶点搜索相关文献
- 获取文献摘要和元数据
- 为 AI 分析提供科学文献支撑
"""

import time
from typing import Any, Optional
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

from app.tools.base import BaseTool, ToolResult


class PubmedSearch(BaseTool):
    """PubMed 文献检索工具

    使用 NCBI E-utilities API 检索 PubMed 数据库。
    注意：E-utilities 有速率限制（3 req/s 无 API key, 10 req/s 有 API key）。
    """

    name = "pubmed_search"
    description = "检索 PubMed 生物医学文献数据库"
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key: Optional[str] = None, tool_email: str = "ai-screening@example.com"):
        self.api_key = api_key
        self.tool_email = tool_email

    async def search(
        self,
        query: str,
        max_results: int = 10,
        retstart: int = 0,
    ) -> ToolResult:
        """搜索 PubMed 文献

        Args:
            query: 搜索查询（支持 PubMed 查询语法）
            max_results: 最大结果数
            retstart: 结果偏移量

        Returns:
            ToolResult 包含文献列表
        """
        try:
            # Step 1: ESearch - 获取 PMID 列表
            pmids = await self._search_pmids(query, max_results, retstart)
            if not pmids:
                return ToolResult.success(data={"articles": [], "total_count": 0, "query": query})

            # Step 2: EFetch - 获取文献详情
            articles = await self._fetch_articles(pmids)

            return ToolResult.success(
                data={
                    "articles": articles,
                    "total_count": len(articles),
                    "query": query,
                    "pmids": pmids,
                }
            )

        except Exception as e:
            return ToolResult.failure(error=f"PubMed 检索失败: {str(e)}")

    async def search_by_drug_and_target(
        self,
        drug_name: str,
        target_name: str,
        max_results: int = 5,
    ) -> ToolResult:
        """搜索药物+靶点联合文献

        Args:
            drug_name: 药物名称
            target_name: 靶点名称
            max_results: 最大结果数

        Returns:
            ToolResult 包含相关文献列表
        """
        query = f'("{drug_name}"[Title/Abstract]) AND ("{target_name}"[Title/Abstract])'
        return await self.search(query, max_results)

    async def _search_pmids(self, query: str, max_results: int, retstart: int) -> list[str]:
        """ESearch: 获取 PMID 列表"""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retstart": retstart,
            "sort": "relevance",
            "retmode": "xml",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.tool_email:
            params["email"] = self.tool_email

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
            resp.raise_for_status()
            time.sleep(0.34)  # 速率限制

        root = ElementTree.fromstring(resp.text)
        id_list = root.findall(".//Id")
        return [elem.text for elem in id_list]

    async def _fetch_articles(self, pmids: list[str]) -> list[dict[str, Any]]:
        """EFetch: 获取文献摘要"""
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.tool_email:
            params["email"] = self.tool_email

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
            resp.raise_for_status()

        root = ElementTree.fromstring(resp.text)
        articles = []

        for article_elem in root.findall(".//PubmedArticle"):
            medline = article_elem.find(".//MedlineCitation")
            if medline is None:
                continue

            pmid = medline.findtext(".//PMID", "")
            title = medline.findtext(".//ArticleTitle", "")
            abstract = medline.findtext(".//AbstractText", "")

            # 提取期刊信息
            journal = medline.findtext(".//Journal/Title", "")
            pub_date = medline.findtext(".//PubDate/Year", "")

            # 提取作者（最多5个）
            authors = []
            for author_elem in medline.findall(".//Author")[:5]:
                last = author_elem.findtext("LastName", "")
                fore = author_elem.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {fore}".strip())

            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract[:1000] if abstract else "",  # 截断长摘要
                "journal": journal,
                "pub_date": pub_date,
                "authors": authors,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        return articles
