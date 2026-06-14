"""
通用 Pydantic 模型
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    """分页响应（通用）"""
    total: int
    page: int
    page_size: int
    items: list[Any]


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: Optional[Any] = None


class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None


class ProjectCreateRequest(BaseModel):
    """创建项目请求"""
    project_name: str
    description: str = ""


class ProjectResponse(BaseModel):
    """项目响应"""
    id: int
    project_name: str
    description: Optional[str] = None
    owner_id: int
    created_at: Optional[str] = None


class ProjectUpdateRequest(BaseModel):
    """更新项目请求"""
    project_name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectMemberRequest(BaseModel):
    """添加项目成员请求"""
    user_id: int = Field(..., gt=0, description="用户 ID")
    role: str = Field("RESEARCHER", description="角色: RESEARCHER, VIEWER, ADMIN")
