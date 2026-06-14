"""
Pydantic Schema validation tests
Covers all API request/response models for:
- Valid input
- Invalid input
- Boundary values
- Type errors

All imports use actual schema classes from app.schemas.*
"""

import pytest
from pydantic import ValidationError


class TestAuthSchemas:
    """Auth-related schema tests (RegisterRequest, LoginRequest, UserResponse)"""

    # ── RegisterRequest ──

    def test_register_request_valid(self):
        """Given valid username, email, password When creating RegisterRequest Then validation passes"""
        from app.schemas.auth import RegisterRequest

        data = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
        )
        assert data.username == "testuser"
        assert data.email == "test@example.com"

    def test_register_request_username_too_short(self):
        """Given username < 2 chars When creating RegisterRequest Then raises ValidationError"""
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(
                username="a",
                email="test@example.com",
                password="SecurePass123!",
            )

    def test_register_request_password_too_short(self):
        """Given password < 6 chars When creating RegisterRequest Then raises ValidationError"""
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="12345",
            )

    def test_register_request_no_role_field(self):
        """RegisterRequest has no role field — role is server-assigned during registration"""
        from app.schemas.auth import RegisterRequest

        data = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!",
        )
        assert not hasattr(data, "role")

    # ── LoginRequest ──

    def test_login_request_valid(self):
        """Given valid username and password When creating LoginRequest Then validation passes"""
        from app.schemas.auth import LoginRequest

        data = LoginRequest(username="testuser", password="SecurePass123!")
        assert data.username == "testuser"

    def test_login_request_empty_username(self):
        """Given empty username When creating LoginRequest Then raises ValidationError"""
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(username="", password="SecurePass123!")

    def test_login_request_short_password(self):
        """Given password < 6 chars When creating LoginRequest Then raises ValidationError"""
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="12345")

    # ── UserResponse ──

    def test_user_response_fields(self):
        """Given full user data When serializing UserResponse Then excludes password hash"""
        from app.schemas.auth import UserResponse

        data = UserResponse(
            id=1,
            username="testuser",
            email="test@example.com",
            role="RESEARCHER",
            status=1,
            created_at="2025-01-01T00:00:00",
        )
        result = data.model_dump()
        assert "password_hash" not in result
        assert "password" not in result
        assert result["id"] == 1
        assert result["username"] == "testuser"

    # ── TokenResponse ──

    def test_token_response(self):
        """Given token data When creating TokenResponse Then includes token_type=bearer"""
        from app.schemas.auth import TokenResponse

        data = TokenResponse(access_token="abc123", refresh_token="ref456")
        assert data.token_type == "bearer"
        assert data.access_token == "abc123"

    # ── RefreshTokenRequest ──

    def test_refresh_token_request(self):
        """Given refresh token When creating RefreshTokenRequest Then validation passes"""
        from app.schemas.auth import RefreshTokenRequest

        data = RefreshTokenRequest(refresh_token="some-refresh-token")
        assert data.refresh_token == "some-refresh-token"


class TestProjectSchemas:
    """Project-related schema tests"""

    def test_project_response_valid(self):
        """Given valid project data When creating ProjectResponse Then validation passes"""
        from app.schemas.common import ProjectResponse

        data = ProjectResponse(
            id=1,
            project_name="COVID-19 Mpro Screening",
            description="Virtual screening against main protease",
            owner_id=1,
            created_at="2025-01-01T00:00:00",
        )
        assert data.project_name == "COVID-19 Mpro Screening"
        assert data.owner_id == 1

    def test_project_response_minimal(self):
        """Given minimal project data When creating ProjectResponse Then validation passes"""
        from app.schemas.common import ProjectResponse

        data = ProjectResponse(
            id=1,
            project_name="Test",
            owner_id=1,
        )
        assert data.description is None
        assert data.created_at is None


class TestScreeningSchemas:
    """Screening task schema tests"""

    # ── ScreeningCreateRequest ──

    def test_screening_create_valid(self):
        """Given valid SMILES and receptor When creating ScreeningCreateRequest Then validation passes"""
        from app.schemas.screening import ScreeningCreateRequest

        data = ScreeningCreateRequest(
            project_id=1,
            smiles="CCO",
            receptor_id=1,
            job_name="Test Screening",
        )
        assert data.smiles == "CCO"
        assert data.job_name == "Test Screening"

    def test_screening_create_empty_smiles(self):
        """Given empty SMILES When creating ScreeningCreateRequest Then raises ValidationError"""
        from app.schemas.screening import ScreeningCreateRequest

        with pytest.raises(ValidationError):
            ScreeningCreateRequest(
                project_id=1,
                smiles="",
                receptor_id=1,
                job_name="Test",
            )

    def test_screening_create_smiles_too_long(self):
        """Given SMILES > 4096 chars When creating ScreeningCreateRequest Then raises ValidationError"""
        from app.schemas.screening import ScreeningCreateRequest

        with pytest.raises(ValidationError):
            ScreeningCreateRequest(
                project_id=1,
                smiles="C" * 4097,
                receptor_id=1,
                job_name="Test",
            )

    def test_screening_create_invalid_project_id(self):
        """Given project_id <= 0 When creating ScreeningCreateRequest Then raises ValidationError"""
        from app.schemas.screening import ScreeningCreateRequest

        with pytest.raises(ValidationError):
            ScreeningCreateRequest(
                project_id=0,
                smiles="CCO",
                receptor_id=1,
                job_name="Test",
            )

    def test_screening_create_invalid_receptor_id(self):
        """Given receptor_id <= 0 When creating ScreeningCreateRequest Then raises ValidationError"""
        from app.schemas.screening import ScreeningCreateRequest

        with pytest.raises(ValidationError):
            ScreeningCreateRequest(
                project_id=1,
                smiles="CCO",
                receptor_id=0,
                job_name="Test",
            )

    def test_screening_create_empty_job_name(self):
        """Given empty job_name When creating ScreeningCreateRequest Then raises ValidationError"""
        from app.schemas.screening import ScreeningCreateRequest

        with pytest.raises(ValidationError):
            ScreeningCreateRequest(
                project_id=1,
                smiles="CCO",
                receptor_id=1,
                job_name="",
            )

    # ── ScreeningResponse ──

    def test_screening_response_status_values(self):
        """Given all valid status values When creating ScreeningResponse Then validation passes"""
        valid_statuses = [
            "CREATED", "PREPARING", "DOCKING", "ANALYZING",
            "REPORTING", "COMPLETED", "FAILED", "CANCELLED", "WAIT_HUMAN",
        ]
        from app.schemas.screening import ScreeningResponse

        for status in valid_statuses:
            data = ScreeningResponse(
                id=1,
                project_id=1,
                molecule_id=1,
                receptor_id=1,
                job_name="Test",
                status=status,
                progress=50,
                total_drugs=5000,
                finished_drugs=2500,
                created_by=1,
            )
            assert data.status == status

    # ── ScreeningListRequest ──

    def test_screening_list_request_defaults(self):
        """Given no optional params When creating ScreeningListRequest Then uses defaults"""
        from app.schemas.screening import ScreeningListRequest

        data = ScreeningListRequest()
        assert data.page == 1
        assert data.page_size == 20
        assert data.project_id is None
        assert data.status is None

    def test_screening_list_request_page_out_of_range(self):
        """Given page < 1 When creating ScreeningListRequest Then raises ValidationError"""
        from app.schemas.screening import ScreeningListRequest

        with pytest.raises(ValidationError):
            ScreeningListRequest(page=0)

    # ── TopHitItem / TopHitsResponse ──

    def test_top_hit_item_valid(self):
        """Given valid docking result data When creating TopHitItem Then validation passes"""
        from app.schemas.screening import TopHitItem

        data = TopHitItem(
            rank=1,
            drug_id=10,
            drug_name="Aspirin",
            affinity_score=-10.5,
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            drugbank_id="DB00945",
        )
        assert data.affinity_score == -10.5
        assert data.drug_name == "Aspirin"

    def test_top_hits_response(self):
        """Given multiple hits When creating TopHitsResponse Then validation passes"""
        from app.schemas.screening import TopHitItem, TopHitsResponse

        hits = [
            TopHitItem(rank=1, drug_id=10, drug_name="Drug_A", affinity_score=-10.5),
            TopHitItem(rank=2, drug_id=20, drug_name="Drug_B", affinity_score=-9.8),
        ]
        data = TopHitsResponse(job_id=1, total_hits=2, top_hits=hits)
        assert data.total_hits == 2
        assert len(data.top_hits) == 2

    # ── DockingTaskResponse ──

    def test_docking_task_response_status(self):
        """Given Docking task statuses When checking valid statuses Then all accepted"""
        valid_statuses = ["PENDING", "RUNNING", "SUCCESS", "FAILED", "RETRYING"]
        from app.schemas.screening import DockingTaskResponse

        for status in valid_statuses:
            data = DockingTaskResponse(
                id=1,
                job_id=1,
                drug_id=1,
                status=status,
                retry_count=0,
            )
            assert data.status == status

    def test_docking_task_optional_fields(self):
        """Given minimal fields When creating DockingTaskResponse Then optional fields are None"""
        from app.schemas.screening import DockingTaskResponse

        data = DockingTaskResponse(
            id=1,
            job_id=1,
            drug_id=1,
            status="PENDING",
            retry_count=0,
        )
        assert data.drug_name is None
        assert data.affinity_score is None


class TestMoleculeSchemas:
    """Molecule schema tests"""

    # ── MoleculeUploadRequest ──

    def test_molecule_upload_valid(self):
        """Given valid SMILES When creating MoleculeUploadRequest Then validation passes"""
        from app.schemas.molecule import MoleculeUploadRequest

        data = MoleculeUploadRequest(
            project_id=1,
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        assert "CC(=O)" in data.smiles

    def test_molecule_upload_empty_smiles(self):
        """Given empty SMILES When creating MoleculeUploadRequest Then raises ValidationError"""
        from app.schemas.molecule import MoleculeUploadRequest

        with pytest.raises(ValidationError):
            MoleculeUploadRequest(project_id=1, smiles="")

    def test_molecule_upload_smiles_too_long(self):
        """Given SMILES > 4096 chars When creating MoleculeUploadRequest Then raises ValidationError"""
        from app.schemas.molecule import MoleculeUploadRequest

        with pytest.raises(ValidationError):
            MoleculeUploadRequest(project_id=1, smiles="C" * 4097)

    # ── MoleculeResponse ──

    def test_molecule_response_includes_properties(self):
        """Given molecule data When serializing MoleculeResponse Then includes computed properties"""
        from app.schemas.molecule import MoleculeResponse

        data = MoleculeResponse(
            id=1,
            project_id=1,
            smiles="CCO",
            molecular_weight=46.07,
            logp=-0.14,
            tpsa=20.23,
        )
        result = data.model_dump()
        assert result["molecular_weight"] == 46.07
        assert result["logp"] == -0.14

    # ── MoleculeBatchUploadRequest ──

    def test_molecule_batch_upload_valid(self):
        """Given valid SMILES list When creating MoleculeBatchUploadRequest Then validation passes"""
        from app.schemas.molecule import MoleculeBatchUploadRequest

        data = MoleculeBatchUploadRequest(
            project_id=1,
            smiles_list=["CCO", "CCN", "CCOC"],
        )
        assert len(data.smiles_list) == 3

    def test_molecule_batch_upload_empty_list(self):
        """Given empty SMILES list When creating MoleculeBatchUploadRequest Then raises ValidationError"""
        from app.schemas.molecule import MoleculeBatchUploadRequest

        with pytest.raises(ValidationError):
            MoleculeBatchUploadRequest(project_id=1, smiles_list=[])

    # ── DrugLibraryResponse ──

    def test_drug_library_response(self):
        """Given drug data When creating DrugLibraryResponse Then default status is '正常'"""
        from app.schemas.molecule import DrugLibraryResponse

        data = DrugLibraryResponse(
            id=1,
            drug_name="Aspirin",
            smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        assert data.status == "正常"
        assert data.drug_name == "Aspirin"


class TestReportSchemas:
    """Report schema tests"""

    def test_report_response_valid(self):
        """Given report data When creating ReportResponse Then validation passes"""
        from app.schemas.report import ReportResponse

        data = ReportResponse(
            id=1,
            job_id=1,
            report_type="PDF",
            report_uri="/reports/report.pdf",
        )
        assert data.report_type == "PDF"

    # ── AnalysisResultResponse ──

    def test_analysis_result_response(self):
        """Given AI analysis data When creating AnalysisResultResponse Then validation passes"""
        from app.schemas.report import AnalysisResultResponse

        data = AnalysisResultResponse(
            id=1,
            job_id=1,
            drug_id=10,
            llm_model="gpt-4",
            summary="Strong binding affinity observed",
            recommendation="Prioritize for experimental validation",
            risk_analysis="No significant toxicity predicted",
        )
        assert data.llm_model == "gpt-4"
        assert data.drug_name is None

    # ── InteractionResponse ──

    def test_interaction_response(self):
        """Given PLIP interaction data When creating InteractionResponse Then defaults are 0"""
        from app.schemas.report import InteractionResponse

        data = InteractionResponse(id=1, job_id=1, drug_id=10)
        assert data.hydrogen_bonds == 0
        assert data.hydrophobic_contacts == 0
        assert data.salt_bridges == 0
        assert data.pi_interactions == 0


class TestErrorResponseSchemas:
    """Error response schema tests"""

    def test_error_response_format(self):
        """Given error info When serializing ErrorResponse Then includes code and message"""
        from app.schemas.common import ErrorResponse

        data = ErrorResponse(
            code=1000,
            message="Parameter error: invalid SMILES format",
            detail={"field": "smiles", "value": "INVALID"},
        )
        result = data.model_dump()
        assert result["code"] == 1000
        assert "SMILES" in result["message"]
        assert "detail" in result

    def test_error_response_all_codes(self):
        """Given all system error codes When creating ErrorResponse Then validation passes"""
        from app.schemas.common import ErrorResponse

        error_codes = {
            1000: "Parameter error",
            1001: "File format error",
            1002: "Insufficient permissions",
            1003: "Task not found",
            2001: "AutoDock launch failed",
            2002: "Docking timeout",
            2003: "Docking result empty",
            3001: "LLM timeout",
            3002: "Prompt execution failed",
        }

        for code, msg in error_codes.items():
            data = ErrorResponse(code=code, message=msg)
            assert data.code == code


class TestCommonSchemas:
    """Common/generic schema tests"""

    def test_paginated_response(self):
        """Given paginated data When creating PaginatedResponse Then includes metadata"""
        from app.schemas.common import PaginatedResponse

        data = PaginatedResponse(
            total=100,
            page=1,
            page_size=20,
            items=[{"id": 1}, {"id": 2}],
        )
        assert data.total == 100
        assert data.page == 1
        assert data.page_size == 20
        assert len(data.items) == 2

    def test_success_response(self):
        """Given success data When creating SuccessResponse Then defaults are applied"""
        from app.schemas.common import SuccessResponse

        data = SuccessResponse()
        assert data.success is True
        assert data.message == "操作成功"
        assert data.data is None
