"""
Redis 客户端管理

Redis 职责（不做持久化）：
- Redis Streams: 任务队列（消费者组模式）
- Redis Hash: 运行态缓存（任务进度、状态，TTL 24h）
- Redis String: 分布式锁
- Redis String: 幂等键、限流

注意：Redis 不是真相来源（source of truth），任务最终状态以 MySQL 为准。
"""

import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

# 全局 Redis 连接池
_redis_pool: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    """初始化 Redis 连接池

    在应用启动时调用。
    """
    global _redis_pool
    _redis_pool = aioredis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        decode_responses=True,
    )
    await _redis_pool.ping()


async def close_redis() -> None:
    """关闭 Redis 连接池

    在应用关闭时调用。
    """
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端实例

    Returns:
        aioredis.Redis: 异步 Redis 客户端

    Raises:
        RuntimeError: Redis 未初始化
    """
    if _redis_pool is None:
        raise RuntimeError("Redis 未初始化，请先调用 init_redis()")
    return _redis_pool


# ──────────────────────────────────────────────
# Streams 队列操作
# ──────────────────────────────────────────────


async def stream_add(stream: str, data: dict, max_len: int = 10000) -> str:
    """向 Redis Stream 添加任务（自动生成任务 ID）

    Args:
        stream: Stream 名称 (e.g. "stream:docking")
        data: 任务数据字典
        max_len: Stream 最大长度限制

    Returns:
        生成的消息 ID
    """
    r = get_redis()
    msg_id = await r.xadd(stream, data, maxlen=max_len, id="*")
    return msg_id


async def stream_create_consumer_group(stream: str, group: str) -> None:
    """创建消费者组（如果不存在则创建）

    Args:
        stream: Stream 名称
        group: 消费者组名称
    """
    r = get_redis()
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def stream_read_group(
    stream: str, group: str, consumer: str, count: int = 1, block: int = 5000
) -> list[dict]:
    """以消费者组模式读取 Stream 消息

    Args:
        stream: Stream 名称
        group: 消费者组名称
        consumer: 消费者名称
        count: 每次读取消息数
        block: 阻塞等待时间 (ms)

    Returns:
        消息列表，每条包含 id 和 data
    """
    r = get_redis()
    results = await r.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block)
    messages = []
    for _stream, entries in results:
        for msg_id, fields in entries:
            messages.append({"id": msg_id, "data": fields})
    return messages


async def stream_ack(stream: str, group: str, msg_id: str) -> None:
    """确认消息已处理

    Args:
        stream: Stream 名称
        group: 消费者组名称
        msg_id: 消息 ID
    """
    r = get_redis()
    await r.xack(stream, group, msg_id)


async def stream_pending(stream: str, group: str, count: int = 100) -> list[dict]:
    """获取待处理消息列表（用于故障恢复）

    Args:
        stream: Stream 名称
        group: 消费者组名称
        count: 获取数量

    Returns:
        待处理消息列表
    """
    r = get_redis()
    results = await r.xpending_range(stream, group, "-", "+", count=count)
    return [{"id": r["message_id"], "consumer": r["consumer"], "idle_ms": r["time_since_delivered"]} for r in results]


async def stream_claim_pending(stream: str, group: str, consumer: str, min_idle_ms: int = 60000) -> list[dict]:
    """认领超时的待处理消息（Worker 崩溃恢复）

    Args:
        stream: Stream 名称
        group: 消费者组名称
        consumer: 新消费者名称
        min_idle_ms: 最小空闲时间 (ms)

    Returns:
        认领的消息列表
    """
    r = get_redis()
    pending = await r.xpending_range(stream, group, "-", "+", count=100)
    to_claim = [p["message_id"] for p in pending if p["time_since_delivered"] >= min_idle_ms]
    if not to_claim:
        return []
    claimed = await r.xclaim(stream, group, consumer, min_idle_ms, to_claim)
    return [{"id": c["message_id"], "data": c["fields"]} for c in claimed]


# ──────────────────────────────────────────────
# 运行态缓存（Hash，TTL 24h）
# ──────────────────────────────────────────────


async def cache_job_progress(job_id: int, data: dict) -> None:
    """缓存任务进度到 Redis Hash

    Args:
        job_id: 任务 ID
        data: 进度数据 (status, progress, finished_drugs, total_drugs 等)
    """
    r = get_redis()
    key = f"job:{job_id}:progress"
    await r.hset(key, mapping=data)
    await r.expire(key, settings.REDIS_PROGRESS_TTL)


async def get_job_progress(job_id: int) -> dict:
    """从 Redis 读取任务进度

    Args:
        job_id: 任务 ID

    Returns:
        进度数据字典，不存在则返回空 dict
    """
    r = get_redis()
    key = f"job:{job_id}:progress"
    data = await r.hgetall(key)
    return data


async def cache_top_hits(job_id: int, hits: list[dict], ttl: int = 3600) -> None:
    """缓存 Top Hits 结果

    Args:
        job_id: 任务 ID
        hits: Top Hits 列表
        ttl: 过期时间 (秒)
    """
    r = get_redis()
    key = f"job:{job_id}:top_hits"
    await r.set(key, json.dumps(hits, ensure_ascii=False), ex=ttl)


async def get_top_hits(job_id: int) -> Optional[list[dict]]:
    """读取缓存的 Top Hits

    Args:
        job_id: 任务 ID

    Returns:
        Top Hits 列表，不存在返回 None
    """
    r = get_redis()
    key = f"job:{job_id}:top_hits"
    data = await r.get(key)
    return json.loads(data) if data else None


# ──────────────────────────────────────────────
# 分布式锁
# ──────────────────────────────────────────────


@asynccontextmanager
async def distributed_lock(lock_name: str, ttl: int = None):
    """基于 Redis 的分布式锁上下文管理器

    用于避免多个 Agent 重复准备同一受体或药库。

    用法:
        async with distributed_lock("prepare_receptor:EGFR") as acquired:
            if acquired:
                # 执行需要互斥的操作
                pass

    Args:
        lock_name: 锁名称
        ttl: 锁过期时间 (秒)，默认使用配置值
    """
    ttl = ttl or settings.REDIS_LOCK_TTL
    r = get_redis()
    lock_key = f"lock:{lock_name}"
    lock_value = str(uuid.uuid4())

    acquired = await r.set(lock_key, lock_value, nx=True, ex=ttl)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            # 使用 Lua 脚本保证释放的原子性
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await r.eval(lua_script, 1, lock_key, lock_value)


# ──────────────────────────────────────────────
# 幂等键
# ──────────────────────────────────────────────


async def check_idempotent(key: str, ttl: int = 86400) -> bool:
    """检查操作是否已执行（幂等去重）

    Args:
        key: 幂等键
        ttl: 过期时间 (秒)

    Returns:
        True 表示首次执行，False 表示已执行
    """
    r = get_redis()
    idem_key = f"idempotent:{key}"
    return bool(await r.set(idem_key, "1", nx=True, ex=ttl))
