"""
AI 分析 Prompt 模板

用于 Drug Screening 结果分析的标准 Prompt 模板集合。
所有模板遵循结构化输出要求，防止 Prompt 注入。
"""

# ──────────────────────────────────────────────
# Docking 结果分析 Prompt
# ──────────────────────────────────────────────

DOCKING_ANALYSIS_PROMPT = """你是一位计算药物化学专家。请分析以下虚拟筛选结果。

## 靶点蛋白
{receptor_name} ({pdb_code})

## Top 候选药物对接结果
{docking_results}

## 任务要求
1. 分析每个候选药物的结合能力（按亲和力分数评价）
2. 识别关键的结合模式（氢键、疏水作用等）
3. 评估药物重定位（drug repurposing）潜力
4. 标记潜在风险（毒性、代谢问题等）
5. 给出优先级排序和实验验证建议

## 输出格式
请以中文回答，结构化输出：
### 结合能力总体评价
### Top 3 候选药物详细分析
### 药物重定位分析
### 风险评估
### 实验建议
"""

DRUG_DETAIL_ANALYSIS_PROMPT = """你是一位药物化学家。请对以下候选药物进行详细分析。

## 药物信息
- 名称: {drug_name}
- DrugBank ID: {drugbank_id}
- 适应症: {indication}
- SMILES: {smiles}
- 分子量: {molecular_weight}
- LogP: {logp}

## 对接结果
- 结合亲和力: {affinity_score} kcal/mol
- 相互作用:
{interactions}

## PubMed 相关文献
{pubmed_articles}

## 任务
1. 评价该药物的结合能力
2. 分析与靶点的关键相互作用
3. 评估药物重定位到当前靶点的可行性
4. 基于文献给出支持或反对的证据
5. 给出下一步实验建议

请用中文回答，条理清晰。
"""

ATPOCKET_ANALYSIS_PROMPT = """你是一位结构生物学家。请分析以下对接结果中药物与靶点结合口袋的匹配度。

## 受体
{receptor_name} ({pdb_code})

## 候选药物结合数据
{drug_binding_data}

## 任务
1. 分析药物是否占据了关键结合口袋
2. 识别口袋中的关键残基相互作用
3. 评价药物-口袋的形状互补性
4. 给出结构优化的建议

请用中文回答。
"""
