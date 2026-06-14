"""
MinIO 对象存储客户端管理

MinIO 职责：
- 存储大文件：SDF、PDBQT、Docking 输出、PDF 报告
- MySQL 只存 URI（minio://bucket/path），不存二进制
- 统一 URI 规范：minio://{bucket}/{path}

这样设计的好处：
- 避免 MySQL BLOB 存储引起的备份、迁移、I/O 问题
- 文件上传/下载支持断点续传
"""

from typing import Optional

from minio import Minio

from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()

_minio_client: Optional[Minio] = None


def init_minio() -> Minio:
    """初始化 MinIO 客户端并确保必要 bucket 存在

    Returns:
        Minio: 已连接的 MinIO 客户端
    """
    global _minio_client

    _minio_client = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    # 确保必要 bucket 存在
    buckets = [settings.MINIO_BUCKET_MOLECULES, settings.MINIO_BUCKET_DOCKING, settings.MINIO_BUCKET_REPORTS]
    for bucket in buckets:
        if not _minio_client.bucket_exists(bucket):
            _minio_client.make_bucket(bucket)
            logger.info(f"MinIO bucket '{bucket}' 已创建")

    logger.info(f"MinIO 已连接: {settings.MINIO_ENDPOINT}")
    return _minio_client


def get_minio() -> Minio:
    """获取 MinIO 客户端实例

    Returns:
        Minio: MinIO 客户端

    Raises:
        RuntimeError: MinIO 未初始化
    """
    if _minio_client is None:
        raise RuntimeError("MinIO 未初始化，请先调用 init_minio()")
    return _minio_client


def close_minio() -> None:
    """关闭 MinIO 连接（MinIO SDK 无持久连接，仅为接口统一保留）"""
    global _minio_client
    _minio_client = None


async def upload_file(
    bucket: str,
    object_name: str,
    file_path: str,
    content_type: str = "application/octet-stream",
) -> str:
    """上传文件到 MinIO

    Args:
        bucket: Bucket 名称
        object_name: 对象名称（路径）
        file_path: 本地文件路径
        content_type: 文件 MIME 类型

    Returns:
        URI 字符串: minio://{bucket}/{object_name}
    """
    client = get_minio()
    client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=file_path,
        content_type=content_type,
    )
    uri = f"minio://{bucket}/{object_name}"
    return uri


async def upload_bytes(
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """上传字节数据到 MinIO

    Args:
        bucket: Bucket 名称
        object_name: 对象名称（路径）
        data: 文件字节数据
        content_type: 文件 MIME 类型

    Returns:
        URI 字符串: minio://{bucket}/{object_name}
    """
    import io
    client = get_minio()
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    uri = f"minio://{bucket}/{object_name}"
    return uri


async def download_file(bucket: str, object_name: str, output_path: str) -> None:
    """从 MinIO 下载文件到本地

    Args:
        bucket: Bucket 名称
        object_name: 对象名称（路径）
        output_path: 本地输出路径
    """
    client = get_minio()
    client.fget_object(bucket, object_name, output_path)


async def get_file_bytes(bucket: str, object_name: str) -> bytes:
    """从 MinIO 读取文件字节

    Args:
        bucket: Bucket 名称
        object_name: 对象名称（路径）

    Returns:
        文件字节数据
    """
    client = get_minio()
    response = client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def delete_file(bucket: str, object_name: str) -> None:
    """从 MinIO 删除文件

    Args:
        bucket: Bucket 名称
        object_name: 对象名称（路径）
    """
    client = get_minio()
    client.remove_object(bucket, object_name)


def parse_minio_uri(uri: str) -> tuple[str, str]:
    """解析 MinIO URI

    Args:
        uri: minio://{bucket}/{object_name}

    Returns:
        (bucket, object_name) 元组
    """
    uri = uri.replace("minio://", "")
    parts = uri.split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""
