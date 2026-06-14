"""
自定义异常体系

统一异常处理，所有业务异常继承 AppException。
FastAPI 全局异常处理器自动将异常转换为标准 JSON 响应。
"""

from typing import Any, Optional


class AppException(Exception):
    """应用基础异常

    所有业务异常继承此类，全局异常处理器统一捕获。

    Attributes:
        code: 错误码
        message: 错误消息
        status_code: HTTP 状态码
        detail: 额外详情
    """

    def __init__(
        self,
        code: int = 1000,
        message: str = "内部错误",
        status_code: int = 500,
        detail: Any = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


# ──────────────────────────────────────────────
# 通用错误 (1000 系列)
# ──────────────────────────────────────────────


class ValidationError(AppException):
    """参数校验错误 (1000)"""
    def __init__(self, message: str = "参数错误", detail: Any = None):
        super().__init__(code=1000, message=message, status_code=400, detail=detail)


class FileFormatError(AppException):
    """文件格式错误 (1001)"""
    def __init__(self, message: str = "文件格式错误", detail: Any = None):
        super().__init__(code=1001, message=message, status_code=400, detail=detail)


class PermissionDenied(AppException):
    """权限不足 (1002)"""
    def __init__(self, message: str = "权限不足", detail: Any = None):
        super().__init__(code=1002, message=message, status_code=403, detail=detail)


class ResourceNotFound(AppException):
    """资源不存在 (1003)"""
    def __init__(self, message: str = "资源不存在", detail: Any = None):
        super().__init__(code=1003, message=message, status_code=404, detail=detail)


class ConflictError(AppException):
    """资源冲突 (1004) — 重复创建等"""
    def __init__(self, message: str = "资源冲突", detail: Any = None):
        super().__init__(code=1004, message=message, status_code=409, detail=detail)


class AuthenticationError(AppException):
    """认证失败 (1005)"""
    def __init__(self, message: str = "认证失败", detail: Any = None):
        super().__init__(code=1005, message=message, status_code=401, detail=detail)


class RateLimited(AppException):
    """请求频率限制 (1006)"""
    def __init__(self, message: str = "请求过于频繁", detail: Any = None):
        super().__init__(code=1006, message=message, status_code=429, detail=detail)


class FileTooLarge(AppException):
    """文件过大 (1007)"""
    def __init__(self, message: str = "文件过大", detail: Any = None):
        super().__init__(code=1007, message=message, status_code=413, detail=detail)


# ──────────────────────────────────────────────
# Docking 错误 (2000 系列)
# ──────────────────────────────────────────────


class DockingError(AppException):
    """Docking 相关错误基类"""
    def __init__(self, code: int = 2000, message: str = "Docking 错误", detail: Any = None):
        super().__init__(code=code, message=message, status_code=500, detail=detail)


class AutoDockStartError(DockingError):
    """AutoDock Vina 启动失败 (2001)"""
    def __init__(self, message: str = "AutoDock Vina 启动失败", detail: Any = None):
        super().__init__(code=2001, message=message, detail=detail)


class DockingTimeoutError(DockingError):
    """Docking 超时 (2002)"""
    def __init__(self, message: str = "Docking 计算超时", detail: Any = None):
        super().__init__(code=2002, message=message, detail=detail)


class DockingEmptyResultError(DockingError):
    """Docking 结果为空 (2003)"""
    def __init__(self, message: str = "Docking 结果为空", detail: Any = None):
        super().__init__(code=2003, message=message, detail=detail)


class DockingVinaError(DockingError):
    """Vina 执行错误 (2004)"""
    def __init__(self, message: str = "Vina 执行错误", detail: Any = None):
        super().__init__(code=2004, message=message, detail=detail)


class DockingFileError(DockingError):
    """Docking 输入/输出文件错误 (2005)"""
    def __init__(self, message: str = "Docking 文件错误", detail: Any = None):
        super().__init__(code=2005, message=message, detail=detail)


# ──────────────────────────────────────────────
# AI 分析错误 (3000 系列)
# ──────────────────────────────────────────────


class AIAnalysisError(AppException):
    """AI 分析相关错误基类"""
    def __init__(self, code: int = 3000, message: str = "AI 分析错误", detail: Any = None):
        super().__init__(code=code, message=message, status_code=500, detail=detail)


class LLMTimeoutError(AIAnalysisError):
    """LLM 调用超时 (3001)"""
    def __init__(self, message: str = "LLM 调用超时", detail: Any = None):
        super().__init__(code=3001, message=message, detail=detail)


class LLMPromptError(AIAnalysisError):
    """Prompt 执行失败 (3002)"""
    def __init__(self, message: str = "Prompt 执行失败", detail: Any = None):
        super().__init__(code=3002, message=message, detail=detail)


class LLMModelError(AIAnalysisError):
    """LLM 模型错误 (3003)"""
    def __init__(self, message: str = "LLM 模型调用错误", detail: Any = None):
        super().__init__(code=3003, message=message, detail=detail)


class PromptInjectionError(AIAnalysisError):
    """Prompt 注入检测 (3004)"""
    def __init__(self, message: str = "检测到 Prompt 注入攻击", detail: Any = None):
        super().__init__(code=3004, message=message, detail=detail)


# ──────────────────────────────────────────────
# Agent 错误 (4000 系列)
# ──────────────────────────────────────────────


class AgentError(AppException):
    """Agent 执行错误"""
    def __init__(self, code: int = 4000, message: str = "Agent 执行错误", detail: Any = None):
        super().__init__(code=code, message=message, status_code=500, detail=detail)


class AgentTimeoutError(AgentError):
    """Agent 执行超时 (4001)"""
    def __init__(self, message: str = "Agent 执行超时", detail: Any = None):
        super().__init__(code=4001, message=message, detail=detail)


class AgentStateError(AgentError):
    """Agent 状态错误 (4002) — 状态机不合法转移"""
    def __init__(self, message: str = "Agent 状态错误", detail: Any = None):
        super().__init__(code=4002, message=message, detail=detail)


# ──────────────────────────────────────────────
# 工作流错误 (5000 系列)
# ──────────────────────────────────────────────


class WorkflowError(AppException):
    """工作流执行错误"""
    def __init__(self, code: int = 5000, message: str = "工作流执行错误", detail: Any = None):
        super().__init__(code=code, message=message, status_code=500, detail=detail)


class WorkflowStateError(WorkflowError):
    """工作流状态错误 (5001)"""
    def __init__(self, message: str = "工作流状态错误", detail: Any = None):
        super().__init__(code=5001, message=message, detail=detail)


class WorkflowRecoveryError(WorkflowError):
    """工作流恢复失败 (5002)"""
    def __init__(self, message: str = "工作流恢复失败", detail: Any = None):
        super().__init__(code=5002, message=message, detail=detail)


# ──────────────────────────────────────────────
# 存储错误 (6000 系列)
# ──────────────────────────────────────────────


class StorageError(AppException):
    """存储服务错误"""
    def __init__(self, code: int = 6000, message: str = "存储服务错误", detail: Any = None):
        super().__init__(code=code, message=message, status_code=500, detail=detail)


class MinIOUploadError(StorageError):
    """MinIO 上传失败 (6001)"""
    def __init__(self, message: str = "文件上传失败", detail: Any = None):
        super().__init__(code=6001, message=message, detail=detail)


class MinIODownloadError(StorageError):
    """MinIO 下载失败 (6002)"""
    def __init__(self, message: str = "文件下载失败", detail: Any = None):
        super().__init__(code=6002, message=message, detail=detail)
