"""
Milvus 向量数据库连接管理

Milvus 职责：
- 分子指纹/嵌入向量存储与检索
- 相似药物检索（similarity search）
- 候选库预筛选（先取最相似的 K 个药物，再做 Docking）
- 交互式探索（"与当前命中最相似的已上市药物有哪些？"）

Milvus 不存 Docking 结果，不用于事务性业务记录。
"""

from typing import Optional

from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()

# MilvusClient 实例（用于高级操作）
_milvus_client: Optional[object] = None


def _import_pymilvus():
    """Lazy import pymilvus to avoid startup dependency."""
    from pymilvus import (  # noqa: E402
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        MilvusClient,
        connections,
        utility,
    )
    return Collection, CollectionSchema, DataType, FieldSchema, MilvusClient, connections, utility


def init_milvus():
    """初始化 Milvus 连接

    连接到 Milvus 服务并验证连接状态。
    返回 MilvusClient 实例。

    Returns:
        MilvusClient: 已连接的 Milvus 客户端
    """
    global _milvus_client

    _, _, _, _, MilvusClient, connections, _ = _import_pymilvus()

    # 使用 PyMilvus ORM 风格连接
    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
    )

    # 同时创建 MilvusClient（用于更简单的操作）
    _milvus_client = MilvusClient(
        uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
    )

    logger.info(f"Milvus 已连接: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    return _milvus_client


def get_milvus():
    """获取 MilvusClient 实例

    Returns:
        MilvusClient: Milvus 客户端

    Raises:
        RuntimeError: Milvus 未初始化
    """
    if _milvus_client is None:
        raise RuntimeError("Milvus 未初始化，请先调用 init_milvus()")
    return _milvus_client


def close_milvus() -> None:
    """关闭 Milvus 连接"""
    _, _, _, _, _, connections, _ = _import_pymilvus()
    connections.disconnect("default")


def get_or_create_drug_collection():
    """获取或创建药物嵌入向量 Collection

    Collection 设计:
    - drug_id: Int64 主键（对应 MySQL drug_library.id）
    - drug_name: 药物名称
    - fingerprint_vector: BinaryVector(2048) Morgan 指纹

    索引类型: IVF_FLAT
    度量类型: JACCARD / HAMMING (适用于二元指纹)

    Returns:
        Collection: drug_embeddings 集合
    """
    Collection, CollectionSchema, DataType, FieldSchema, _, _, utility = _import_pymilvus()

    collection_name = settings.MILVUS_COLLECTION

    if utility.has_collection(collection_name):
        return Collection(collection_name)

    # 定义 schema
    fields = [
        FieldSchema(name="drug_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="drug_name", dtype=DataType.VARCHAR, max_length=255),
        FieldSchema(name="fingerprint_vector", dtype=DataType.BINARY_VECTOR, dim=settings.MILVUS_VECTOR_DIM),
    ]
    schema = CollectionSchema(fields, description="药物 Morgan 指纹向量库")

    collection = Collection(collection_name, schema)

    # 创建索引
    index_params = {
        "metric_type": "HAMMING",
        "index_type": "BIN_IVF_FLAT",
        "params": {"nlist": settings.MILVUS_NLIST},
    }
    collection.create_index("fingerprint_vector", index_params)

    logger.info(f"Milvus Collection '{collection_name}' 已创建，索引类型: BIN_IVF_FLAT")
    return collection


async def insert_drug_vector(drug_id: int, drug_name: str, fingerprint: list[int]) -> None:
    """向 Milvus 插入药物向量

    Args:
        drug_id: 药物 ID (对应 MySQL drug_library.id)
        drug_name: 药物名称
        fingerprint: Morgan 指纹 (2048 位列表)
    """
    get_milvus()
    collection = get_or_create_drug_collection()
    collection.load()
    collection.insert([[drug_id], [drug_name], [fingerprint]])
    collection.flush()


async def search_similar_drugs(
    fingerprint: list[int], top_k: int = 100
) -> list[dict]:
    """相似药物检索

    使用 Hamming 距离查找最相似的 K 个药物。
    用于候选库预筛选：将 5000~50000 个药物缩到 200~1000 个候选，
    显著降低 Docking 计算量。

    Args:
        fingerprint: 查询分子 Morgan 指纹 (2048 位)
        top_k: 返回最相似的 K 个药物

    Returns:
        相似药物列表，每项包含 drug_id, drug_name, distance
    """
    collection = get_or_create_drug_collection()
    collection.load()

    search_params = {"metric_type": "HAMMING", "params": {"nprobe": 16}}
    results = collection.search(
        data=[fingerprint],
        anns_field="fingerprint_vector",
        param=search_params,
        limit=top_k,
        output_fields=["drug_id", "drug_name"],
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "drug_id": hit.entity.drug_id,
            "drug_name": hit.entity.drug_name,
            "distance": hit.distance,
        })
    return hits


async def delete_drug_vector(drug_id: int) -> None:
    """从 Milvus 删除药物向量

    Args:
        drug_id: 要删除的药物 ID
    """
    collection = get_or_create_drug_collection()
    collection.delete(f'drug_id == {drug_id}')
