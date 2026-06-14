"""
项目管理 API

POST   /api/v1/projects         — 创建项目
GET    /api/v1/projects/{id}    — 获取项目详情
PUT    /api/v1/projects/{id}    — 更新项目
DELETE /api/v1/projects/{id}    — 删除项目
GET    /api/v1/projects         — 查询项目列表
POST   /api/v1/projects/{id}/members — 添加项目成员
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictError, PermissionDenied, ResourceNotFound
from app.core.security import get_current_user
from app.models.project import Project, ProjectMember
from app.schemas.common import (
    ProjectCreateRequest,
    ProjectMemberRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    req: ProjectCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新项目"""
    project = Project(
        owner_id=current_user["user_id"],
        project_name=req.project_name,
        description=req.description,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    # 创建者自动成为 OWNER 成员
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user["user_id"],
        role="OWNER",
    )
    db.add(member)

    return ProjectResponse(
        id=project.id,
        project_name=project.project_name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=str(project.created_at) if project.created_at else None,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取项目详情"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFound(message=f"项目 ID={project_id} 不存在")

    # 权限检查：OWNER/ADMIN/PI 可访问，或项目成员可访问
    role = current_user["role"]
    if role not in ("ADMIN", "PI") and project.owner_id != current_user["user_id"]:
        member_result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user["user_id"],
            )
        )
        if not member_result.scalar_one_or_none():
            raise PermissionDenied(message="无权访问此项目")

    return ProjectResponse(
        id=project.id,
        project_name=project.project_name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=str(project.created_at) if project.created_at else None,
    )


def _check_project_owner(project: Project, current_user: dict) -> None:
    """检查用户是否为项目 Owner 或 ADMIN"""
    if current_user["role"] == "ADMIN":
        return
    if project.owner_id != current_user["user_id"]:
        raise PermissionDenied(message="只有项目 Owner 或 ADMIN 可以执行此操作")


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户参与的所有项目"""
    # 查询用户是 owner 或 member 的项目
    owned = select(Project).where(Project.owner_id == current_user["user_id"])
    member_of = select(Project).join(ProjectMember).where(ProjectMember.user_id == current_user["user_id"])

    from sqlalchemy import union

    combined = union(owned, member_of).alias()
    result = await db.execute(select(combined))
    projects = result.all()

    return [
        ProjectResponse(
            id=p.id,
            project_name=p.project_name,
            description=p.description,
            owner_id=p.owner_id,
            created_at=str(p.created_at) if p.created_at else None,
        )
        for p in projects
    ]


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    req: ProjectUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新项目信息（仅 Owner 或 ADMIN 可操作）"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFound(message=f"项目 ID={project_id} 不存在")

    _check_project_owner(project, current_user)

    if req.project_name is not None:
        project.project_name = req.project_name
    if req.description is not None:
        project.description = req.description

    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        project_name=project.project_name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=str(project.created_at) if project.created_at else None,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除项目（仅 Owner 或 ADMIN 可操作）

    级联删除：先清理关联的 screening_jobs、molecules、project_members，再删除项目本身。
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFound(message=f"项目 ID={project_id} 不存在")

    _check_project_owner(project, current_user)

    # 手动级联清理子表，避免 SQLAlchemy 默认的 SET NULL 行为与 NOT NULL 列冲突
    from app.models.molecule import Molecule
    from app.models.screening import ScreeningJob

    # 1. 删除项目下的所有 screening_jobs
    jobs_result = await db.execute(select(ScreeningJob).where(ScreeningJob.project_id == project_id))
    for job in jobs_result.scalars().all():
        await db.delete(job)

    # 2. 删除项目下的所有 molecules
    mols_result = await db.execute(select(Molecule).where(Molecule.project_id == project_id))
    for mol in mols_result.scalars().all():
        await db.delete(mol)

    # 3. 删除所有 project_members
    members_result = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
    for member in members_result.scalars().all():
        await db.delete(member)

    # 4. 最后删除项目本身
    await db.delete(project)
    await db.flush()

    return {"project_id": project_id, "message": "项目已删除"}


@router.post("/{project_id}/members")
async def add_project_member(
    project_id: int,
    req: ProjectMemberRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加项目成员（仅 Owner 或 ADMIN 可操作）"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFound(message=f"项目 ID={project_id} 不存在")

    _check_project_owner(project, current_user)

    # 检查是否已是成员
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == req.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(message=f"用户 ID={req.user_id} 已是项目成员")

    member = ProjectMember(
        project_id=project_id,
        user_id=req.user_id,
        role=req.role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    return {
        "id": member.id,
        "project_id": member.project_id,
        "user_id": member.user_id,
        "role": member.role,
        "message": "成员添加成功",
    }
