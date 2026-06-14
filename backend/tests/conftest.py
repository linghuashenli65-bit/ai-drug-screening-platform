"""
全平台测试 Fixture 配置
提供: 异步测试客户端、SQLite 内存库、Redis Mock、认证 Token、测试数据工厂

Usage:
    pytest backend/tests/ -v --cov=backend --cov-report=html
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================
# 测试数据库配置 (SQLite 内存库)
# ============================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///test_db.sqlite"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """创建异步 SQLite 文件引擎，每个测试函数独立"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    from app.core.database import Base

    # 导入所有模型以注册到 Base.metadata
    import app.models.user  # noqa
    import app.models.project  # noqa
    import app.models.receptor  # noqa
    import app.models.molecule  # noqa
    import app.models.screening  # noqa
    import app.models.docking  # noqa
    import app.models.report  # noqa
    import app.models.agent  # noqa
    import app.models.audit  # noqa
    import app.models.analysis  # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """提供每个测试独立的数据库会话"""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


# ============================================================
# Redis Mock
# ============================================================

class MockRedis:
    """Redis Mock 实现,模拟键值存储和 Stream 操作"""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._streams: Dict[str, list] = {}
        self._expiry: Dict[str, datetime] = {}
        self._locks: Dict[str, str] = {}
        self._sets: Dict[str, set] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        self._store[key] = value
        if ex:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        return sum(1 for k in keys if k in self._store)

    async def hset(self, name: str, mapping: dict) -> int:
        if name not in self._store:
            self._store[name] = {}
        self._store[name].update(mapping)
        return len(mapping)

    async def hget(self, name: str, key: str) -> Optional[str]:
        if name in self._store:
            return self._store[name].get(key)
        return None

    async def hgetall(self, name: str) -> dict:
        return self._store.get(name, {})

    async def xadd(self, stream: str, fields: dict, maxlen: int = None) -> str:
        if stream not in self._streams:
            self._streams[stream] = []
        msg_id = f"{int(datetime.utcnow().timestamp() * 1000)}-0"
        self._streams[stream].append({"id": msg_id, "fields": fields})
        if maxlen and len(self._streams[stream]) > maxlen:
            self._streams[stream] = self._streams[stream][-maxlen:]
        return msg_id

    async def xread(self, streams: dict, count: int = None, block: int = None) -> list:
        """返回格式: [[stream_name, [(msg_id, fields_dict)]]]"""
        result = []
        for stream_name, last_id in streams.items():
            msgs = self._streams.get(stream_name, [])
            # 简单实现: 返回所有消息
            parsed = [(m["id"], m["fields"]) for m in msgs]
            if parsed:
                result.append([stream_name, parsed])
        return result

    async def xlen(self, stream: str) -> int:
        return len(self._streams.get(stream, []))

    async def xpending(self, stream: str, group: str) -> dict:
        return {"pending": len([m for m in self._streams.get(stream, []) if m.get("pending")])}

    async def setnx(self, key: str, value: str) -> bool:
        if key not in self._store:
            self._store[key] = value
            return True
        return False

    async def expire(self, key: str, seconds: int) -> bool:
        self._expiry[key] = datetime.utcnow() + timedelta(seconds=seconds)
        return True

    async def sadd(self, key: str, *values: str) -> int:
        if key not in self._sets:
            self._sets[key] = set()
        before = len(self._sets[key])
        self._sets[key].update(values)
        return len(self._sets[key]) - before

    async def smembers(self, key: str) -> set:
        return self._sets.get(key, set())

    async def publish(self, channel: str, message: str) -> int:
        return 1

    async def ping(self) -> bool:
        return True

    async def close(self):
        pass

    def __await__(self):
        """使 MockRedis 可 awaitable,兼容 async Redis client 初始化"""
        async def _await():
            return self
        return _await().__await__()


@pytest_asyncio.fixture(scope="function")
async def mock_redis() -> MockRedis:
    """提供 Mock Redis 实例"""
    return MockRedis()


# ============================================================
# HTTP 异步测试客户端
# ============================================================

@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession,
    mock_redis: MockRedis,
) -> AsyncGenerator[AsyncClient, None]:
    """提供集成测试的 AsyncClient"""
    from app.main import app
    from app.core.database import get_db
    from app.core.redis import get_redis

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    base_url = "http://testserver"

    async with AsyncClient(transport=transport, base_url=base_url) as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================
# 认证 Token Fixtures
# ============================================================

@pytest.fixture(scope="module")
def researcher_token_headers() -> Dict[str, str]:
    """生成 Researcher 角色的 JWT 认证头"""
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=1,
        username="researcher_test",
        role="RESEARCHER",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token_headers() -> Dict[str, str]:
    """生成 Admin 角色的 JWT 认证头"""
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=2,
        username="admin_test",
        role="ADMIN",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def pi_token_headers() -> Dict[str, str]:
    """生成 PI (Principal Investigator) 角色的 JWT 认证头"""
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=3,
        username="pi_test",
        role="PI",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def expired_token_headers() -> Dict[str, str]:
    """生成过期的 JWT Token (手动构造过期 token 供中间件测试使用)"""
    # 注意: 实际 create_access_token 不接受 expires_delta,
    # 过期 token 测试通过手动拼接无效 JWT 完成
    return {"Authorization": "Bearer expired.invalid.token"}


# ============================================================
# 测试数据工厂 (Factory Boy 风格简化版)
# ============================================================

@pytest.fixture
def fake() -> Faker:
    return Faker()


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """有效的用户创建数据"""
    return {
        "username": "test_researcher",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "role": "RESEARCHER",
    }


@pytest.fixture
def sample_smiles() -> str:
    """有效的 SMILES 字符串 (乙醇)"""
    return "CCO"


@pytest.fixture
def sample_smiles_complex() -> str:
    """复杂的有效 SMILES (阿司匹林)"""
    return "CC(=O)OC1=CC=CC=C1C(=O)O"


@pytest.fixture
def invalid_smiles() -> str:
    """无效的 SMILES 字符串"""
    return "INVALID_SMILES!!!"


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """有效的项目数据"""
    return {
        "project_name": "COVID-19 主蛋白酶筛选",
        "description": "针对 SARS-CoV-2 Mpro 靶点的虚拟筛选项目",
    }


@pytest.fixture
def sample_receptor_data() -> Dict[str, Any]:
    """有效的受体数据"""
    return {
        "receptor_name": "EGFR",
        "pdb_code": "1M17",
        "description": "Epidermal Growth Factor Receptor",
    }


@pytest.fixture
def sample_screening_job_data() -> Dict[str, Any]:
    """有效的筛选任务数据"""
    return {
        "project_id": "1",
        "smiles": "CCO",
        "receptor_id": "1",
        "job_name": "Test Screening",
        "exhaustiveness": 8,
        "num_cpus": 4,
        "top_n": 100,
    }


@pytest.fixture
def sample_drug_library_entry() -> Dict[str, Any]:
    """有效的药物库条目"""
    return {
        "drug_name": "Aspirin",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "drugbank_id": "DB00945",
        "indication": "Pain relief, anti-inflammatory",
        "molecular_weight": 180.16,
        "logp": 1.19,
    }


@pytest.fixture
def sample_top20_results() -> List[Dict[str, Any]]:
    """模拟 Docking Top 20 结果"""
    results = []
    for i in range(20):
        results.append({
            "rank": i + 1,
            "drug_name": f"Drug_{i+1}",
            "drugbank_id": f"DB{10000 + i}",
            "affinity_score": round(-12.5 + i * 0.3, 3),
            "molecular_weight": 180.0 + i * 50,
        })
    return results


@pytest.fixture
def sample_ai_analysis_result() -> Dict[str, Any]:
    """模拟 AI 分析结果"""
    return {
        "summary": "Top 20 候选药物中,3个表现出优异结合能力",
        "top_candidates": [
            {
                "drug_name": "Drug_1",
                "affinity_score": -12.5,
                "analysis": "具有最高结合亲和力,建议优先验证",
            }
        ],
        "repurposing_analysis": "Drug_3 可能具有抗病毒重定位潜力",
        "risk_analysis": "Drug_7 存在潜在肝毒性风险",
        "experimental_suggestions": [
            "对 Top 5 药物进行分子动力学模拟验证",
            "进行细胞层面的活性验证实验",
        ],
    }


# ============================================================
# 数据库种子数据帮助函数
# ============================================================

async def seed_user(
    session: AsyncSession,
    username: str = "test_user",
    role: str = "RESEARCHER",
) -> int:
    """向数据库插入测试用户"""
    from app.models.user import User

    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash="hashed_password_placeholder",
        role=role,
        status=1,
    )
    session.add(user)
    await session.flush()
    return user.id


async def seed_project(
    session: AsyncSession,
    owner_id: int,
    project_name: str = "Test Project",
) -> int:
    """向数据库插入测试项目"""
    from app.models.project import Project

    project = Project(
        owner_id=owner_id,
        project_name=project_name,
        description=f"Description for {project_name}",
    )
    session.add(project)
    await session.flush()
    return project.id


async def seed_receptor(
    session: AsyncSession,
    receptor_name: str = "EGFR",
    pdb_code: str = "1M17",
) -> int:
    """向数据库插入测试受体"""
    from app.models.receptor import Receptor

    receptor = Receptor(
        receptor_name=receptor_name,
        pdb_code=pdb_code,
        pdbqt_uri=f"/data/receptors/{pdb_code}.pdbqt",
        description=f"Test receptor {receptor_name}",
    )
    session.add(receptor)
    await session.flush()
    return receptor.id


async def seed_molecule(
    session: AsyncSession,
    project_id: int,
    smiles: str = "CCO",
) -> int:
    """向数据库插入测试分子"""
    from app.models.molecule import Molecule

    molecule = Molecule(
        project_id=project_id,
        smiles=smiles,
        molecular_weight=46.07,
        logp=-0.14,
    )
    session.add(molecule)
    await session.flush()
    return molecule.id


async def seed_screening_job(
    session: AsyncSession,
    project_id: int,
    molecule_id: int,
    receptor_id: int,
    created_by: int,
    status: str = "CREATED",
) -> int:
    """向数据库插入测试筛选任务"""
    from app.models.screening import ScreeningJob

    job = ScreeningJob(
        project_id=project_id,
        molecule_id=molecule_id,
        receptor_id=receptor_id,
        job_name="Test Screening Job",
        status=status,
        progress=0,
        total_drugs=5000,
        finished_drugs=0,
        created_by=created_by,
    )
    session.add(job)
    await session.flush()
    return job.id


async def seed_drug_library(
    session: AsyncSession,
    count: int = 10,
) -> List[int]:
    """向数据库批量插入测试药物"""
    from app.models.molecule import DrugLibrary

    drug_ids = []
    for i in range(count):
        drug = DrugLibrary(
            drug_name=f"Test_Drug_{i+1}",
            smiles=f"C{i+1}CC",
            drugbank_id=f"DB{20000 + i}",
            indication=f"Test indication {i+1}",
            molecular_weight=180.0 + i * 30,
            logp=1.0 + i * 0.2,
        )
        session.add(drug)
        await session.flush()
        drug_ids.append(drug.id)
    return drug_ids
