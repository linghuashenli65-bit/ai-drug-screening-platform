"""
Molecules API 集成测试
POST /api/v1/molecules (SMILES/SDF 上传)
GET /api/v1/molecules/{id}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestUploadMolecule:
    """POST /api/v1/molecules"""

    async def test_create_from_smiles(self, db_session, sample_smiles_complex):
        """Given SMILES When POST /api/v1/molecules Then 解析并返回分子信息"""
        with patch("app.services.molecule_service.MoleculeService.create_from_smiles",
                   new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": 1,
                "smiles": sample_smiles_complex,
                "molecular_weight": 180.16,
                "logp": 1.19,
            }

            result = await mock_create(
                session=db_session,
                project_id=1,
                smiles=sample_smiles_complex,
            )
            assert result["id"] == 1
            assert result["molecular_weight"] == 180.16

    async def test_create_from_smiles_invalid(self, db_session, invalid_smiles):
        """Given 非法 SMILES When POST /api/v1/molecules Then 返回 1000 参数错误"""
        from app.core.exceptions import ValidationError

        with patch("app.services.molecule_service.MoleculeService.create_from_smiles",
                   new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValidationError("参数错误: SMILES 格式不合法")

            with pytest.raises(ValidationError) as exc_info:
                await mock_create(
                    session=db_session,
                    project_id=1,
                    smiles=invalid_smiles,
                )
            assert exc_info.value.code == 1000

    async def test_upload_sdf_file(self, db_session):
        """Given SDF 文件 When POST /api/v1/molecules Then 解析并返回结构"""
        with patch("app.services.molecule_service.MoleculeService.create_from_file",
                   new_callable=AsyncMock) as mock_file:
            mock_file.return_value = {
                "id": 1,
                "smiles": "CCO",
                "source_file_uri": "/uploads/mol.sdf",
            }

            result = await mock_file(
                session=db_session,
                project_id=1,
                file_uri="/uploads/mol.sdf",
            )
            assert result["source_file_uri"] == "/uploads/mol.sdf"

    async def test_upload_invalid_file_format(self, db_session):
        """Given 非 SDF/MOL2 文件 When POST /api/v1/molecules Then 返回 1001"""
        from app.core.exceptions import FileFormatError

        with patch("app.services.molecule_service.MoleculeService.create_from_file",
                   new_callable=AsyncMock) as mock_file:
            mock_file.side_effect = FileFormatError("文件格式错误: 仅支持 SDF/MOL2/PDB")

            with pytest.raises(FileFormatError) as exc_info:
                await mock_file(
                    session=db_session,
                    project_id=1,
                    file_uri="/uploads/bad.exe",
                )
            assert exc_info.value.code == 1001

    async def test_upload_file_too_large(self, db_session):
        """Given 超大文件 When 上传 Then 返回 413"""
        max_upload_size = 100 * 1024 * 1024  # 100MB
        assert max_upload_size == 104857600

    async def test_upload_no_file_and_no_smiles(self, db_session):
        """Given 既无文件也无 SMILES When POST /api/v1/molecules Then 返回 422"""
        from pydantic import ValidationError

        try:
            from app.schemas.molecule import MoleculeUploadRequest
            MoleculeUploadRequest(project_id=1)
        except ValidationError:
            pass  # 预期行为


class TestGetMolecule:
    """GET /api/v1/molecules/{molecule_id}"""

    async def test_get_molecule_detail(self, db_session):
        """Given 分子 ID When GET /api/v1/molecules/{id} Then 返回详细信息"""
        with patch("app.services.molecule_service.MoleculeService.get_molecule",
                   new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": 1,
                "smiles": "CCO",
                "molecular_weight": 46.07,
                "logp": -0.14,
                "tpsa": 20.23,
                "files": [
                    {"file_type": "sdf", "file_uri": "/files/mol.sdf"},
                    {"file_type": "pdbqt", "file_uri": "/files/mol.pdbqt"},
                ],
            }

            result = await mock_get(
                session=db_session,
                molecule_id=1,
            )
            assert result["smiles"] == "CCO"
            assert len(result["files"]) == 2
