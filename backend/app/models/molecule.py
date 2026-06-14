"""
分子与药物库模型 (molecules, molecule_files, drug_library)

molecules: 用户上传/标准化后的分子主表
molecule_files: 分子关联文件（SDF/PDBQT 等），支持一个分子多个文件
drug_library: 已上市药物库元数据（DrugBank 来源）
"""

from datetime import datetime

from decimal import Decimal
from sqlalchemy import Integer, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Molecule(Base):
    """分子主表

    存储用户上传的候选小分子结构及其理化性质。
    """

    __tablename__ = "molecules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    smiles: Mapped[str] = mapped_column(Text, nullable=False)
    molecular_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True)
    logp: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    tpsa: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    source_file_uri: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="molecules", lazy="selectin")
    files: Mapped[list["MoleculeFile"]] = relationship("MoleculeFile", back_populates="molecule", lazy="selectin")
    screening_jobs: Mapped[list["ScreeningJob"]] = relationship("ScreeningJob", back_populates="molecule", lazy="selectin")


class MoleculeFile(Base):
    """分子关联文件

    支持一个分子拥有多个文件（SDF, PDBQT 等格式）。
    文件实际存储在 MinIO，此处只存 URI。
    """

    __tablename__ = "molecule_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    molecule_id: Mapped[int] = mapped_column(Integer, ForeignKey("molecules.id"), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关系
    molecule: Mapped["Molecule"] = relationship("Molecule", back_populates="files", lazy="selectin")


class DrugLibrary(Base):
    """已上市药物库

    存储 DrugBank 等来源的上市药物信息，含预计算的 PDBQT 和 Milvus 向量引用。
    """

    __tablename__ = "drug_library"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    smiles: Mapped[str] = mapped_column(Text, nullable=False)
    drugbank_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    cas: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    indication: Mapped[str] = mapped_column(Text, nullable=True)
    molecular_weight: Mapped[float] = mapped_column(Numeric(10, 3), nullable=True)
    logp: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    milvus_vector_id: Mapped[int] = mapped_column(Integer, nullable=True)
    pdbqt_uri: Mapped[str] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="正常")

    # 关系
    docking_tasks: Mapped[list["DockingTask"]] = relationship("DockingTask", back_populates="drug", lazy="selectin")
