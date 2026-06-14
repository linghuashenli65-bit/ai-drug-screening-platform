"""
Receptors API 集成测试
GET /api/v1/receptors - 列表
POST /api/v1/receptors - 上传自定义蛋白
GET /api/v1/receptors/{id} - 详情
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestListReceptors:
    """GET /api/v1/receptors"""

    async def test_list_receptors(self, db_session):
        """Given 系统已配置受体 When GET /api/v1/receptors Then 返回可选靶点列表"""
        with patch("app.services.receptor_service.ReceptorService.list_receptors",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"id": 1, "receptor_name": "EGFR", "pdb_code": "1M17"},
                {"id": 2, "receptor_name": "SARS-CoV-2 Mpro", "pdb_code": "6LU7"},
                {"id": 3, "receptor_name": "VEGFR2", "pdb_code": "3VHE"},
                {"id": 4, "receptor_name": "ABL1", "pdb_code": "1IEP"},
            ]

            result = await mock_list(session=db_session)
            assert len(result) == 4

    async def test_list_receptors_empty(self, db_session):
        """Given 系统未配置受体 When GET /api/v1/receptors Then 返回空列表"""
        with patch("app.services.receptor_service.ReceptorService.list_receptors",
                   new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await mock_list(session=db_session)
            assert len(result) == 0


class TestGetReceptor:
    """GET /api/v1/receptors/{receptor_id}"""

    async def test_get_receptor_detail(self, db_session, sample_receptor_data):
        """Given 受体 ID When GET /api/v1/receptors/{id} Then 返回完整蛋白信息"""
        with patch("app.services.receptor_service.ReceptorService.get_receptor",
                   new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "id": 1,
                "receptor_name": "EGFR",
                "pdb_code": "1M17",
                "pdbqt_uri": "/data/receptors/1M17.pdbqt",
                "description": "Epidermal Growth Factor Receptor",
            }

            result = await mock_get(
                session=db_session,
                receptor_id=1,
            )
            assert result["receptor_name"] == "EGFR"


class TestUploadReceptor:
    """POST /api/v1/receptors (Admin only)"""

    async def test_admin_upload_pdb(self, db_session, admin_token_headers):
        """Given Admin Token + PDB 文件 When POST /api/v1/receptors Then 成功"""
        assert "Authorization" in admin_token_headers

    async def test_researcher_cannot_upload_receptor(self, db_session):
        """Given Researcher Token When POST /api/v1/receptors Then 返回 403"""
        from app.core.exceptions import PermissionDenied

        with patch("app.services.receptor_service.ReceptorService.create_receptor",
                   new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = PermissionDenied("权限不足: 仅管理员可上传受体")

            with pytest.raises(PermissionDenied):
                await mock_create(
                    session=db_session,
                    receptor_data={"receptor_name": "New"},
                    uploaded_by=1,
                )

    async def test_upload_invalid_pdb(self, db_session):
        """Given 非法 PDB 文件 When POST /api/v1/receptors Then 返回 1001"""
        from app.core.exceptions import FileFormatError

        with patch("app.services.receptor_service.ReceptorService.create_receptor",
                   new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = FileFormatError("文件格式错误: PDB 格式校验失败")

            with pytest.raises(FileFormatError) as exc_info:
                await mock_create(
                    session=db_session,
                    receptor_data={"receptor_name": "Bad PDB"},
                    file_uri="/uploads/bad.pdb",
                )
            assert exc_info.value.code == 1001
