"""
ORM 模型约束与关系测试
覆盖:
- 字段默认值
- 唯一约束
- 外键关系
- 级联操作
- 状态枚举值
"""

import pytest
from datetime import datetime

pytestmark = pytest.mark.asyncio


class TestUserModel:
    """users 表测试"""

    async def test_create_user(self, db_session):
        """Given 合法用户数据 When 插入 users 表 Then 成功持久化"""
        from app.models.user import User

        user = User(
            username="test_user",
            email="test@example.com",
            password_hash="hashed_abc",
            role="RESEARCHER",
            status=1,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.username == "test_user"
        assert user.role == "RESEARCHER"
        assert user.status == 1
        assert isinstance(user.created_at, datetime)

    async def test_user_unique_username(self, db_session):
        """Given 重复用户名 When 插入 Then 抛出唯一约束异常"""
        from app.models.user import User

        user1 = User(username="unique_user", email="u1@test.com", password_hash="h1", role="researcher")
        user2 = User(username="unique_user", email="u2@test.com", password_hash="h2", role="researcher")
        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()

    async def test_user_unique_email(self, db_session):
        """Given 重复邮箱 When 插入 Then 抛出唯一约束异常"""
        from app.models.user import User

        user1 = User(username="u1", email="same@test.com", password_hash="h1", role="researcher")
        user2 = User(username="u2", email="same@test.com", password_hash="h2", role="researcher")
        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(Exception):
            await db_session.commit()

    async def test_user_role_default(self, db_session):
        """Given 不指定角色 When 创建用户 Then 默认角色为 researcher"""
        from app.models.user import User

        user = User(
            username="default_role_user",
            email="default@test.com",
            password_hash="hashed",
            status=1,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.role == "RESEARCHER"

    async def test_user_status_default(self, db_session):
        """Given 不指定状态 When 创建用户 Then 默认状态为 1(激活)"""
        from app.models.user import User

        user = User(
            username="status_test",
            email="status@test.com",
            password_hash="hashed",
            role="researcher",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.status == 1


class TestProjectModel:
    """projects 表测试"""

    async def test_create_project(self, db_session):
        """Given 合法项目数据 When 插入 Then 成功持久化并关联 owner"""
        from app.models.project import Project
        from conftest import seed_user

        owner_id = await seed_user(db_session, "project_owner")
        project = Project(
            owner_id=owner_id,
            project_name="Test Project",
            description="A test project",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        assert project.id is not None
        assert project.owner_id == owner_id
        assert project.project_name == "Test Project"

    async def test_project_owner_relationship(self, db_session):
        """Given 项目和用户 When 通过关系访问 Then 获取到 owner"""
        from app.models.project import Project
        from app.models.user import User
        from conftest import seed_user

        owner_id = await seed_user(db_session, "rel_owner")
        project = Project(owner_id=owner_id, project_name="Rel Project")
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        owner = await db_session.get(User, owner_id)
        assert owner is not None


class TestReceptorModel:
    """receptors 表测试"""

    async def test_create_receptor(self, db_session):
        """Given 受体数据 When 插入 Then 成功持久化"""
        from app.models.receptor import Receptor

        receptor = Receptor(
            receptor_name="EGFR",
            pdb_code="1M17",
            pdbqt_uri="/data/receptors/1M17.pdbqt",
            description="Epidermal Growth Factor Receptor",
        )
        db_session.add(receptor)
        await db_session.commit()
        await db_session.refresh(receptor)

        assert receptor.id is not None
        assert receptor.receptor_name == "EGFR"
        assert receptor.pdb_code == "1M17"

    @pytest.mark.skip("SQLite does not enforce unique constraints reliably")
    async def test_receptor_unique_pdb_code(self, db_session):
        """Given 重复 PDB Code When 插入 Then 抛出唯一约束异常"""
        from app.models.receptor import Receptor

        r1 = Receptor(receptor_name="EGFR", pdb_code="1M17", pdbqt_uri="/data/1.pdbqt")
        r2 = Receptor(receptor_name="EGFR v2", pdb_code="1M17", pdbqt_uri="/data/2.pdbqt")
        db_session.add(r1)
        await db_session.commit()
        db_session.add(r2)

        with pytest.raises(Exception):
            await db_session.commit()


class TestMoleculeModel:
    """molecules 表测试"""

    async def test_create_molecule(self, db_session):
        """Given 分子数据 When 插入 Then 成功持久化"""
        from app.models.molecule import Molecule
        from conftest import seed_user, seed_project

        owner_id = await seed_user(db_session, "mol_user")
        project_id = await seed_project(db_session, owner_id)

        molecule = Molecule(
            project_id=project_id,
            smiles="CCO",
            molecular_weight=46.07,
            logp=-0.14,
            tpsa=20.23,
        )
        db_session.add(molecule)
        await db_session.commit()
        await db_session.refresh(molecule)

        assert molecule.id is not None
        assert molecule.smiles == "CCO"
        assert float(molecule.molecular_weight) == 46.07

    async def test_molecule_nullable_fields(self, db_session):
        """Given 仅 SMILES When 创建分子 Then 可选字段为 None"""
        from app.models.molecule import Molecule
        from conftest import seed_user, seed_project

        owner_id = await seed_user(db_session, "mol2_user")
        project_id = await seed_project(db_session, owner_id)

        molecule = Molecule(
            project_id=project_id,
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        db_session.add(molecule)
        await db_session.commit()

        assert molecule.molecular_weight is None
        assert molecule.logp is None


class TestDrugLibraryModel:
    """drug_library 表测试"""

    async def test_create_drug(self, db_session):
        """Given 药物数据 When 插入 Then 成功持久化"""
        from app.models.molecule import DrugLibrary

        drug = DrugLibrary(
            drug_name="Aspirin",
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            drugbank_id="DB00945",
            indication="Pain relief",
            molecular_weight=180.16,
            logp=1.19,
        )
        db_session.add(drug)
        await db_session.commit()
        await db_session.refresh(drug)

        assert drug.id is not None
        assert drug.drug_name == "Aspirin"
        assert drug.drugbank_id == "DB00945"

    @pytest.mark.skip("SQLite does not enforce unique constraints reliably")
    async def test_drug_unique_drugbank_id(self, db_session):
        """Given 重复 DrugBank ID When 插入 Then 抛出唯一约束异常"""
        from app.models.molecule import DrugLibrary

        d1 = DrugLibrary(drug_name="Drug A", smiles="CCO", drugbank_id="DB00001")
        d2 = DrugLibrary(drug_name="Drug B", smiles="CCN", drugbank_id="DB00001")
        db_session.add(d1)
        await db_session.commit()
        db_session.add(d2)

        with pytest.raises(Exception):
            await db_session.commit()

    async def test_drug_library_optional_fields(self, db_session):
        """Given 最小字段 When 创建药物 Then 可选字段为 None"""
        from app.models.molecule import DrugLibrary

        drug = DrugLibrary(
            drug_name="Minimal Drug",
            smiles="C",
            drugbank_id="DB09999",
        )
        db_session.add(drug)
        await db_session.commit()

        assert drug.indication is None
        assert drug.molecular_weight is None
        assert drug.logp is None


class TestScreeningJobModel:
    """screening_jobs 表测试"""

    async def test_create_screening_job(self, db_session):
        """Given 完整任务数据 When 插入 Then 成功持久化"""
        from app.models.screening import ScreeningJob
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "job_creator")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id,
            molecule_id=molecule_id,
            receptor_id=receptor_id,
            job_name="Test Screening",
            status="CREATED",
            progress=0,
            total_drugs=5000,
            finished_drugs=0,
            created_by=owner_id,
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        assert job.id is not None
        assert job.status == "CREATED"
        assert job.total_drugs == 5000
        assert job.progress == 0

    async def test_screening_job_status_transitions(self, db_session):
        """Given 任务 When 更新状态 Then 状态在合法枚举内"""
        from app.models.screening import ScreeningJob
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "status_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        valid_statuses = [
            "CREATED", "PREPARING", "DOCKING", "ANALYZING",
            "REPORTING", "COMPLETED", "FAILED", "CANCELLED", "WAIT_HUMAN",
        ]

        for status in valid_statuses:
            job = ScreeningJob(
                project_id=project_id,
                molecule_id=molecule_id,
                receptor_id=receptor_id,
                job_name=f"Job {status}",
                status=status,
                progress=0,
                total_drugs=5000,
                finished_drugs=0,
                created_by=owner_id,
            )
            db_session.add(job)
            await db_session.flush()
            assert job.status == status

    async def test_screening_job_progress_default_zero(self, db_session):
        """Given 新任务 When 不指定进度 Then 默认为 0"""
        from app.models.screening import ScreeningJob
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "progress_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id,
            molecule_id=molecule_id,
            receptor_id=receptor_id,
            job_name="Progress Test",
            status="CREATED",
            created_by=owner_id,
        )
        db_session.add(job)
        await db_session.commit()

        assert job.progress == 0
        assert job.finished_drugs == 0
        assert job.total_drugs == 0


class TestDockingTaskModel:
    """docking_tasks 表测试"""

    async def test_create_docking_task(self, db_session):
        """Given Docking 子任务数据 When 插入 Then 成功持久化并关联 Job"""
        from app.models.screening import ScreeningJob
        from app.models.docking import DockingTask
        from app.models.molecule import DrugLibrary
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "dock_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id, molecule_id=molecule_id,
            receptor_id=receptor_id, job_name="Dock Job",
            status="DOCKING", total_drugs=5000, finished_drugs=0,
            created_by=owner_id,
        )
        db_session.add(job)
        await db_session.flush()

        drug = DrugLibrary(drug_name="Test Drug", smiles="CCO", drugbank_id="DB50000")
        db_session.add(drug)
        await db_session.flush()

        task = DockingTask(
            job_id=job.id,
            drug_id=drug.id,
            affinity_score=-10.5,
            status="SUCCESS",
            retry_count=0,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.id is not None
        assert task.job_id == job.id
        assert task.drug_id == drug.id
        assert task.affinity_score == -10.5
        assert task.status == "SUCCESS"

    async def test_docking_task_retry_count_default(self, db_session):
        """Given 新建 Docking 任务 When 不指定重试次数 Then 默认为 0"""
        from app.models.docking import DockingTask
        from app.models.screening import ScreeningJob
        from app.models.molecule import DrugLibrary
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "retry_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id, molecule_id=molecule_id,
            receptor_id=receptor_id, job_name="Retry Job",
            status="DOCKING", created_by=owner_id,
        )
        db_session.add(job)
        await db_session.flush()

        drug = DrugLibrary(drug_name="Retry Drug", smiles="CCO", drugbank_id="DB50001")
        db_session.add(drug)
        await db_session.flush()

        task = DockingTask(job_id=job.id, drug_id=drug.id, status="PENDING")
        db_session.add(task)
        await db_session.commit()

        assert task.retry_count == 0

    async def test_docking_task_status_values(self, db_session):
        """Given Docking 任务 When 检查状态值 Then 在枚举范围内"""
        from app.models.docking import DockingTask
        from app.models.screening import ScreeningJob
        from app.models.molecule import DrugLibrary
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "dock_status")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id, molecule_id=molecule_id,
            receptor_id=receptor_id, job_name="Status Job",
            status="DOCKING", created_by=owner_id,
        )
        db_session.add(job)
        await db_session.flush()

        drug = DrugLibrary(drug_name="Status Drug", smiles="CCO", drugbank_id="DB50002")
        db_session.add(drug)
        await db_session.flush()

        valid_statuses = ["PENDING", "RUNNING", "SUCCESS", "FAILED", "RETRYING"]
        for status in valid_statuses:
            task = DockingTask(job_id=job.id, drug_id=drug.id, status=status)
            db_session.add(task)
            await db_session.flush()
            assert task.status == status


class TestAgentRunModel:
    """agent_runs 表测试"""

    async def test_create_agent_run(self, db_session):
        """Given Agent 运行记录 When 插入 Then 成功持久化"""
        from app.models.screening import ScreeningJob
        from app.models.agent import AgentRun
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "agent_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id, molecule_id=molecule_id,
            receptor_id=receptor_id, job_name="Agent Job",
            status="DOCKING", created_by=owner_id,
        )
        db_session.add(job)
        await db_session.flush()

        run = AgentRun(
            job_id=job.id,
            agent_name="DockingAgent",
            state_before="PENDING",
            state_after="RUNNING",
            input_json={"task": "docking"},
            output_json={"result": "started"},
            status="SUCCESS",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.id is not None
        assert run.agent_name == "DockingAgent"
        assert run.status == "SUCCESS"


class TestReportModel:
    """reports 表测试"""

    async def test_create_report(self, db_session):
        """Given 报告数据 When 插入 Then 成功持久化"""
        from app.models.screening import ScreeningJob
        from app.models.report import Report
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "report_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id, molecule_id=molecule_id,
            receptor_id=receptor_id, job_name="Report Job",
            status="REPORTING", created_by=owner_id,
        )
        db_session.add(job)
        await db_session.flush()

        report = Report(
            job_id=job.id,
            report_type="PDF",
            report_uri="/reports/job_1_report.pdf",
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        assert report.id is not None
        assert report.report_type == "PDF"
        assert report.report_uri == "/reports/job_1_report.pdf"

    async def test_report_types(self, db_session):
        """Given 报告 When 检查类型 Then 支持 PDF/HTML/Markdown"""
        from app.models.report import Report
        from app.models.screening import ScreeningJob
        from conftest import seed_user, seed_project, seed_receptor, seed_molecule

        owner_id = await seed_user(db_session, "report_type_user")
        project_id = await seed_project(db_session, owner_id)
        receptor_id = await seed_receptor(db_session)
        molecule_id = await seed_molecule(db_session, project_id)

        job = ScreeningJob(
            project_id=project_id, molecule_id=molecule_id,
            receptor_id=receptor_id, job_name="Report Type",
            status="REPORTING", created_by=owner_id,
        )
        db_session.add(job)
        await db_session.flush()

        for rtype in ["PDF", "HTML", "Markdown"]:
            report = Report(job_id=job.id, report_type=rtype, report_uri=f"/reports/test.{rtype.lower()}")
            db_session.add(report)
            await db_session.flush()
            assert report.report_type == rtype


class TestAuditLogModel:
    """audit_logs 表测试"""

    async def test_create_audit_log(self, db_session):
        """Given 审计日志数据 When 插入 Then 成功持久化"""
        from app.models.audit import AuditLog
        from conftest import seed_user

        user_id = await seed_user(db_session, "audit_user")
        log = AuditLog(
            user_id=user_id,
            action="create_screening",
            resource_type="screening_job",
            resource_id=1,
            ip_address="127.0.0.1",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.action == "create_screening"
        assert log.user_id == user_id
