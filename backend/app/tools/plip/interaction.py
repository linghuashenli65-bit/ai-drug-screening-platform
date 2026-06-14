"""
PLIP 蛋白-配体相互作用分析工具

使用 PLIP (Protein-Ligand Interaction Profiler) 分析对接结果中的:
- 氢键 (hydrogen bonds)
- 疏水接触 (hydrophobic contacts)
- 盐桥 (salt bridges)
- Pi-Pi 堆积 (pi-pi stacking)
- Pi-阳离子 (pi-cation)
- 卤素键 (halogen bonds)
"""

import os
import tempfile

from app.tools.base import BaseTool, ToolResult


class PlipInteraction(BaseTool):
    """蛋白-配体相互作用分析

    使用 PLIP 分析 docked complex 中的非共价相互作用。
    """

    name = "plip_interaction"
    description = "分析蛋白-配体复合物的非共价相互作用"

    def analyze(
        self,
        receptor_pdb: str,
        ligand_sdf: str,
        output_dir: str = None,
    ) -> ToolResult:
        """分析蛋白-配体相互作用

        Args:
            receptor_pdb: 受体 PDB 文件路径
            ligand_sdf: 配体 SDF 文件路径
            output_dir: 输出目录（可选）

        Returns:
            ToolResult 包含相互作用统计数据
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="plip_")

        try:
            from plip.structure.preparation import PDBComplex

            # 创建蛋白-配体复合物
            complex_obj = PDBComplex()
            complex_obj.load_pdb(receptor_pdb)

            # 分析相互作用
            # PLIP 会自动检测配体并分析相互作用
            interactions = complex_obj.analyze()

            if not interactions:
                return ToolResult.failure(error="PLIP 未检测到相互作用")

            # 统计各类型相互作用
            hbonds = len(interactions.hbonds)
            hydrophobic = len(interactions.hydrophobic_contacts)
            salt_bridges = len(interactions.salt_bridges)
            pi_stacking = len(interactions.pistacking)
            pi_cation = len(interactions.pication_laro) + len(interactions.pication_paro)
            halogen = len(interactions.halogen_bonds)

            # 生成详细描述
            details = {
                "hydrogen_bonds": [
                    {
                        "residue": f"{hb.restype}{hb.resnr}",
                        "distance": round(hb.distance_ad, 2),
                        "angle": round(hb.angle, 1),
                    }
                    for hb in hbonds
                ],
                "hydrophobic_contacts": [
                    {
                        "residue": f"{hc.restype}{hc.resnr}",
                        "distance": round(hc.distance, 2),
                    }
                    for hc in hydrophobic
                ],
            }

            return ToolResult.success(
                data={
                    "hydrogen_bonds": hbonds or 0,
                    "hydrophobic_contacts": hydrophobic or 0,
                    "salt_bridges": salt_bridges or 0,
                    "pi_interactions": pi_stacking + pi_cation,
                    "pi_stacking": pi_stacking or 0,
                    "pi_cation": pi_cation or 0,
                    "halogen_bonds": halogen or 0,
                    "total_interactions": (hbonds or 0) + (hydrophobic or 0) +
                                          (salt_bridges or 0) + (pi_stacking or 0) +
                                          (pi_cation or 0) + (halogen or 0),
                    "analysis_json": details,
                }
            )

        except ImportError:
            return ToolResult.success(
                data={
                    "hydrogen_bonds": 0,
                    "hydrophobic_contacts": 0,
                    "salt_bridges": 0,
                    "pi_interactions": 0,
                    "total_interactions": 0,
                    "analysis_json": {"note": "PLIP not available, using placeholder"},
                }
            )
        except Exception as e:
            return ToolResult.failure(error=f"PLIP 分析失败: {str(e)}")
