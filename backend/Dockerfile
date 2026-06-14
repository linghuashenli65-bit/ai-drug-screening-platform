# =============================================================================
# AI Drug Screening Platform — Backend Dockerfile
# =============================================================================
# 基于 Python 3.12，安装 RDKit + 所有 Python 依赖
# =============================================================================

FROM python:3.12-slim

LABEL app="ai-drug-screening-backend"

WORKDIR /app

# ── 系统依赖 ──
# RDKit 需要 libxrender, libxext6 等运行时库
# weasyprint 需要 libpango, libcairo 等 PDF 渲染库
# meeko 需要 openbabel
RUN apt-get update && apt-get install -y --no-install-recommends \
    # RDKit 运行时
    libxrender1 \
    libxext6 \
    libsm6 \
    libglib2.0-0 \
    # weasyprint (PDF 报告生成)
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libpango1.0-dev \
    libcairo2-dev \
    # OpenBabel (meeko 依赖)
    openbabel \
    libopenbabel-dev \
    swig \
    # Milvus 客户端需要
    libopenblas0 \
    # 基础工具
    curl \
    # C 编译器 (部分 Python 包需要从源码编译)
    gcc \
    g++ \
    # AutoDock Vina — 分子对接引擎
    autodock-vina \
    && rm -rf /var/lib/apt/lists/*

# ── Python 依赖 ──
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 安装除 RDKit/meeko/plip 之外的纯 Python 依赖
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    "sqlalchemy[asyncio]>=2.0" \
    aiomysql \
    pymysql \
    alembic \
    "redis[hiredis]" \
    pymilvus \
    minio \
    "python-jose[cryptography]" \
    bcrypt \
    passlib \
    pydantic \
    pydantic-settings \
    langgraph \
    langchain \
    langchain-openai \
    openai \
    httpx \
    structlog \
    markdown \
    weasyprint \
    xhtml2pdf \
    python-dotenv

# RDKit (pip 安装较慢，先装再装其他)
RUN pip install --no-cache-dir rdkit

# meeko — 分子预处理 (SMILES→PDBQT)
RUN pip install --no-cache-dir meeko

# PLIP — 蛋白-配体相互作用分析
RUN pip install --no-cache-dir plip

# ── 应用代码 ──
COPY . .

# ── 健康检查 ──
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
