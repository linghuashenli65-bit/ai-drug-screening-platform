"""
项目服务

项目的增删改查与成员管理。
"""


class ProjectService:
    """项目服务"""

    @staticmethod
    async def create_project(session, owner_id: int, project_name: str, description: str = ""):
        """创建项目"""
        from app.models.project import Project

        project = Project(
            owner_id=owner_id,
            project_name=project_name,
            description=description,
        )
        session.add(project)
        await session.flush()
        return project

    @staticmethod
    async def list_projects(session, owner_id: int = None, skip: int = 0, limit: int = 50):
        """列出项目"""
        from app.models.project import Project
        from sqlalchemy import select

        stmt = select(Project)
        if owner_id:
            stmt = stmt.where(Project.owner_id == owner_id)
        result = await session.execute(stmt.offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def get_project(session, project_id: int):
        """获取项目详情"""
        from app.models.project import Project
        from sqlalchemy import select

        result = await session.execute(select(Project).where(Project.id == project_id))
        proj = result.scalar_one_or_none()
        if not proj:
            raise ValueError("Project not found")
        return proj

    @staticmethod
    async def add_member(session, project_id: int, user_id: int, role: str = "RESEARCHER"):
        """添加项目成员"""
        from app.models.project import ProjectMember

        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        session.add(member)
        await session.flush()
        return member

    @staticmethod
    async def remove_member(session, project_id: int, user_id: int):
        """移除项目成员"""
        from app.models.project import ProjectMember
        from sqlalchemy import delete

        await session.execute(
            delete(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        await session.flush()
        return True


async def create_project_record(session, owner_id: int, project_name: str, description: str = ""):
    """创建项目记录（独立函数）"""
    return await ProjectService.create_project(session, owner_id, project_name, description)


async def get_projects_by_owner(session, owner_id: int):
    """按所有者获取项目（独立函数）"""
    return await ProjectService.list_projects(session, owner_id=owner_id)


async def get_project_member_role(session, project_id: int, user_id: int) -> str:
    """获取项目成员角色（独立函数）"""
    from app.models.project import ProjectMember
    from sqlalchemy import select

    result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    return member.role if member else None
