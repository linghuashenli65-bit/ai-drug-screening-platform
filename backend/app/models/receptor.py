"""
受体/靶点蛋白模型 (receptors)

存储用于分子对接的靶点蛋白信息。
"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Receptor(Base):
    """靶点蛋白/受体

    存储 PDB 代码、PDBQT 文件 URI 等对接所需信息。
    示例：EGFR, SARS-CoV-2 Mpro, VEGFR2
    """

    __tablename__ = "receptors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receptor_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pdb_code: Mapped[str] = mapped_column(String(32), nullable=True, index=True)
    pdbqt_uri: Mapped[str] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 关系
    screening_jobs: Mapped[list["ScreeningJob"]] = relationship("ScreeningJob", back_populates="receptor", lazy="selectin")
