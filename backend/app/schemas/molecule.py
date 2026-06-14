"""
分子相关 Pydantic 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求 ──


class MoleculeUploadRequest(BaseModel):
    """分子上传请求（SMILES 直接输入）"""
    project_id: int = Field(..., gt=0)
    smiles: str = Field(..., min_length=1, max_length=4096)


class MoleculeBatchUploadRequest(BaseModel):
    """批量 SMILES 上传请求"""
    project_id: int = Field(..., gt=0)
    smiles_list: list[str] = Field(..., min_length=1, max_length=1000)


class DrugLibraryQueryRequest(BaseModel):
    """药物库查询请求"""
    query: Optional[str] = Field(None, description="搜索关键词（药物名/DrugBank ID）")
    status: Optional[str] = Field(None, description="状态筛选: 正常, DISCONTINUED")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class DrugLibraryImportRequest(BaseModel):
    """药物库导入请求"""
    sdf_path: str = Field(..., min_length=1, description="e-drug3d.sdf 文件路径")


class DrugLibraryImportResponse(BaseModel):
    """药物库导入响应"""
    total_parsed: int
    total_inserted: int
    normal_count: int
    discontinued_count: int
    errors: int


# ── 响应 ──


class MoleculeResponse(BaseModel):
    """分子响应"""
    id: int
    project_id: int
    smiles: str
    molecular_weight: Optional[float] = None
    logp: Optional[float] = None
    tpsa: Optional[float] = None
    source_file_uri: Optional[str] = None
    created_at: Optional[str] = None


class MoleculeFileResponse(BaseModel):
    """分子文件响应"""
    id: int
    molecule_id: int
    file_type: str
    file_uri: str
    created_at: Optional[str] = None


class DrugLibraryResponse(BaseModel):
    """药物库条目响应"""
    id: int
    drug_name: str
    smiles: str
    drugbank_id: Optional[str] = None
    cas: Optional[str] = None
    status: str = "正常"
    indication: Optional[str] = None
    molecular_weight: Optional[float] = None
    logp: Optional[float] = None
    pdbqt_uri: Optional[str] = None


class DrugLibraryListResponse(BaseModel):
    """药物库分页列表"""
    total: int
    page: int
    page_size: int
    items: list[DrugLibraryResponse]


class ReceptorCreateRequest(BaseModel):
    """创建受体请求"""
    receptor_name: str = Field(..., min_length=1, max_length=128)
    pdb_code: Optional[str] = Field(None, max_length=32)
    pdbqt_uri: Optional[str] = Field(None, max_length=512)
    description: Optional[str] = Field(None, max_length=2000)


class ReceptorResponse(BaseModel):
    """受体响应"""
    id: int
    receptor_name: str
    pdb_code: Optional[str] = None
    pdbqt_uri: Optional[str] = None
    description: Optional[str] = None
