"""
系统常量定义

包含：
- 任务状态枚举
- Agent 状态枚举
- 错误码定义
- 角色定义
- 文件类型定义
"""

from enum import Enum


# ──────────────────────────────────────────────
# 筛选任务状态（一级状态机）
# ──────────────────────────────────────────────


class JobStatus(str, Enum):
    """筛选任务业务状态

    状态流转:
        CREATED → PREPARING → DOCKING → ANALYZING → REPORTING → COMPLETED
        任意状态 → FAILED | CANCELLED | WAIT_HUMAN
        FAILED → RETRYING → (回到前一状态)
    """

    CREATED = "CREATED"          # 已创建，等待开始
    PREPARING = "PREPARING"      # 准备中：分子处理、药库加载
    DOCKING = "DOCKING"          # 对接中
    ANALYZING = "ANALYZING"      # 分析中
    REPORTING = "REPORTING"      # 报告生成中
    COMPLETED = "COMPLETED"      # 已完成
    FAILED = "FAILED"            # 失败
    RETRYING = "RETRYING"        # 重试中
    WAIT_HUMAN = "WAIT_HUMAN"    # 等待人工介入
    CANCELLED = "CANCELLED"      # 已取消


# 合法的状态转移
VALID_JOB_TRANSITIONS: dict[JobStatus, list[JobStatus]] = {
    JobStatus.CREATED: [JobStatus.PREPARING, JobStatus.CANCELLED, JobStatus.FAILED],
    JobStatus.PREPARING: [JobStatus.DOCKING, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.WAIT_HUMAN],
    JobStatus.DOCKING: [JobStatus.ANALYZING, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.WAIT_HUMAN],
    JobStatus.ANALYZING: [JobStatus.REPORTING, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.WAIT_HUMAN],
    JobStatus.REPORTING: [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
    JobStatus.COMPLETED: [],  # 终态
    JobStatus.FAILED: [JobStatus.RETRYING, JobStatus.CANCELLED, JobStatus.WAIT_HUMAN],
    JobStatus.RETRYING: [JobStatus.PREPARING, JobStatus.DOCKING, JobStatus.ANALYZING, JobStatus.FAILED],
    JobStatus.WAIT_HUMAN: [JobStatus.RETRYING, JobStatus.CANCELLED, JobStatus.FAILED],
    JobStatus.CANCELLED: [],  # 终态
}


def can_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    """检查状态转移是否合法"""
    allowed = VALID_JOB_TRANSITIONS.get(from_status, [])
    return to_status in allowed


# ──────────────────────────────────────────────
# Agent 状态
# ──────────────────────────────────────────────


class AgentStatus(str, Enum):
    """Agent 执行状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


# ──────────────────────────────────────────────
# Tool 调用状态
# ──────────────────────────────────────────────


class ToolCallStatus(str, Enum):
    """Tool 调用状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


# ──────────────────────────────────────────────
# Docking 子任务状态
# ──────────────────────────────────────────────


class DockingTaskStatus(str, Enum):
    """Docking 子任务状态"""
    PENDING = "PENDING"
    QUEUED = "QUEUED"        # 已入队
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


# ──────────────────────────────────────────────
# 用户角色
# ──────────────────────────────────────────────


class UserRole(str, Enum):
    """系统用户角色"""
    ADMIN = "ADMIN"              # 管理员：全部权限
    PI = "PI"                    # 项目负责人：管理项目
    RESEARCHER = "RESEARCHER"    # 科研人员：创建/查看任务
    VIEWER = "VIEWER"            # 访客：只读


class ProjectMemberRole(str, Enum):
    """项目成员角色"""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    VIEWER = "VIEWER"


# ──────────────────────────────────────────────
# 用户状态
# ──────────────────────────────────────────────


class UserStatus(int, Enum):
    """用户账户状态"""
    ACTIVE = 1
    DISABLED = 0
    DELETED = -1


# ──────────────────────────────────────────────
# 报告类型
# ──────────────────────────────────────────────


class ReportType(str, Enum):
    """报告输出格式"""
    PDF = "PDF"
    HTML = "HTML"
    MARKDOWN = "Markdown"


# ──────────────────────────────────────────────
# 文件类型
# ──────────────────────────────────────────────


class FileType(str, Enum):
    """分子关联文件类型"""
    SDF = "SDF"
    PDBQT = "PDBQT"
    PDB = "PDB"
    MOL2 = "MOL2"
    SMI = "SMI"


# ──────────────────────────────────────────────
# Agent 名称
# ──────────────────────────────────────────────


class AgentName(str, Enum):
    """Agent 名称标识"""
    PLANNER = "PlannerAgent"
    MOLECULE = "MoleculeAgent"
    DATABASE = "DatabaseAgent"
    DOCKING = "DockingAgent"
    RANKING = "RankingAgent"
    ANALYSIS = "AnalysisAgent"
    REPORT = "ReportAgent"


# ──────────────────────────────────────────────
# Tool 名称
# ──────────────────────────────────────────────


class ToolName(str, Enum):
    """Tool 名称标识"""
    RDKit_PARSER = "RdkitParser"
    RDkit_DESCRIPTORS = "RdkitDescriptors"
    RDKit_CONFORMER = "RdkitConformer"
    RDKit_PDBQT = "RdkitPdbqtConverter"
    AUTODOCK_RUNNER = "AutoDockRunner"
    AUTODOCK_BUILDER = "AutoDockTaskBuilder"
    AUTODOCK_PARSER = "AutoDockResultParser"
    AUTODOCK_SCORE = "AutoDockScoreExtractor"
    PLIP_INTERACTION = "PlipInteraction"
    PLIP_PARSER = "PlipParser"
    DRUGBANK_QUERY = "DrugbankQuery"
    PUBMED_SEARCH = "PubmedSearch"
    LLM_CLIENT = "LLMClient"
    LLM_CHAIN = "LLMChain"
    REPORT_PDF = "ReportPdfGenerator"
    REPORT_MD = "ReportMarkdownGenerator"
    REPORT_HTML = "ReportHtmlGenerator"


# ──────────────────────────────────────────────
# Redis Key 前缀
# ──────────────────────────────────────────────


class RedisKeyPrefix(str, Enum):
    """Redis Key 命名规范"""
    JOB_PROGRESS = "job:{job_id}:progress"
    JOB_TOP_HITS = "job:{job_id}:top_hits"
    LOCK_PREFIX = "lock:"
    IDEMPOTENT_PREFIX = "idempotent:"


# ──────────────────────────────────────────────
# 错误码汇总
# ──────────────────────────────────────────────

ERROR_CODES = {
    # 通用错误 1000 系列
    1000: "参数错误",
    1001: "文件格式错误",
    1002: "权限不足",
    1003: "资源不存在",
    1004: "资源冲突",
    1005: "认证失败",
    1006: "请求频率限制",
    1007: "文件过大",

    # Docking 错误 2000 系列
    2000: "Docking 基础错误",
    2001: "AutoDock Vina 启动失败",
    2002: "Docking 计算超时",
    2003: "Docking 结果为空",
    2004: "Vina 执行错误",
    2005: "Docking 文件错误",

    # AI 分析错误 3000 系列
    3000: "AI 分析基础错误",
    3001: "LLM 调用超时",
    3002: "Prompt 执行失败",
    3003: "LLM 模型调用错误",
    3004: "Prompt 注入攻击",

    # Agent 错误 4000 系列
    4000: "Agent 执行错误",
    4001: "Agent 执行超时",
    4002: "Agent 状态错误",

    # 工作流错误 5000 系列
    5000: "工作流执行错误",
    5001: "工作流状态错误",
    5002: "工作流恢复失败",

    # 存储错误 6000 系列
    6000: "存储服务错误",
    6001: "文件上传失败",
    6002: "文件下载失败",
}
