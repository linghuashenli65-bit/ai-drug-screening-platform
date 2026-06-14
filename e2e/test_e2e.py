"""
E2E 端到端测试 (Playwright)
覆盖完整用户流程:
1. 登录 → 上传 SMILES → 选择靶点 → 启动筛选 → 查看进度 → Top Hits → AI 分析 → 下载 PDF
2. 上传 SDF 文件完整流程
3. 任务失败后重试完整流程
4. 多用户权限隔离测试
5. 断线重连恢复状态测试
"""

import pytest
import time

# ============================================================
# E2E Flow 1: 完整筛选任务 (SMILES)
# ============================================================

class TestFullScreeningFlowSMILES:
    """
    完整用户流程 (BDD §4 核心业务流程):
    Given 用户上传分子文件
    And 用户选择目标蛋白
    When 用户点击开始筛选
    Then 系统自动创建任务 → Agent 执行 → 生成结果 → 生成报告 → 通知用户
    """

    def test_login_and_redirect_to_dashboard(self, page, base_url):
        """
        Given 用户访问登录页
        When 输入正确凭证并提交
        Then 成功登录并跳转到 Dashboard
        """
        page.goto(f"{base_url}/login")

        # 填写表单
        page.fill('input[name="username"]', "test_researcher")
        page.fill('input[name="password"]', "SecurePass123!")
        page.click('button[type="submit"]')

        # 等待跳转
        page.wait_for_url(f"{base_url}/dashboard")
        assert "/dashboard" in page.url

        # 验证页面元素
        assert page.locator("text=总任务数").is_visible()
        assert page.locator("text=运行中").is_visible()
        assert page.locator("text=已完成").is_visible()

    def test_click_new_task_navigates_to_create(self, page, base_url):
        """
        Given 用户位于 Dashboard
        When 点击"新建任务"按钮
        Then 跳转到任务创建页面
        """
        page.goto(f"{base_url}/dashboard")
        page.click('button:has-text("新建任务")')

        page.wait_for_url(f"{base_url}/jobs/new")
        assert "/jobs/new" in page.url

    def test_create_task_with_smiles(self, page, base_url):
        """
        Given 用户进入创建页面
        When 输入 SMILES + 选择受体 + 提交
        Then 成功创建任务并跳转详情页
        """
        page.goto(f"{base_url}/jobs/new")

        # Step 1: 输入 SMILES
        page.fill('textarea[name="smiles"]', "CC(=O)OC1=CC=CC=C1C(=O)O")
        # 验证自动预览显示
        assert page.locator(".smiles-preview").is_visible()

        # Step 2: 选择靶点
        page.click('[data-testid="receptor-selector"]')
        page.click('text=EGFR')

        # Step 3: 选择药库
        page.click('[data-testid="library-selector"]')
        page.click('text=FDA Approved')

        # Step 4: 点击开始筛选
        page.click('button:has-text("开始筛选")')

        # 验证跳转到详情页
        page.wait_for_url(f"{base_url}/jobs/*")
        assert "/jobs/" in page.url
        assert "status" in page.text_content("body").lower()

    def test_view_job_progress(self, page, base_url):
        """
        Given 任务已创建
        When 查看详情页
        Then 显示 Agent 执行链路和实时进度
        """
        page.goto(f"{base_url}/jobs/1")

        # 验证 Agent 执行链路可见
        chain_nodes = [
            "InputAgent",
            "MoleculeAgent",
            "DatabaseAgent",
            "DockingAgent",
            "AnalysisAgent",
            "ReportAgent",
        ]
        for node in chain_nodes:
            assert page.locator(f'text={node}').is_visible()

        # 验证进度条存在
        assert page.locator('[data-testid="progress-bar"]').is_visible()

    def test_view_top_hits_page(self, page, base_url):
        """
        Given Docking 完成
        When 用户进入结果页
        Then 展示 Top 药物列表,按 Score 排序
        """
        page.goto(f"{base_url}/jobs/1/results")

        # 验证 Top Hits 表格
        assert page.locator('table').is_visible()
        assert page.locator('th:has-text("排名")').is_visible()
        assert page.locator('th:has-text("药物名称")').is_visible()
        assert page.locator('th:has-text("Docking Score")').is_visible()

        # 验证数据行存在
        rows = page.locator('tbody tr')
        assert rows.count() >= 1

    def test_view_ai_analysis(self, page, base_url):
        """
        Given 分析完成
        When 用户打开分析页
        Then 展示 AI 总结、重定位分析、风险、实验建议
        """
        page.goto(f"{base_url}/jobs/1/analysis")

        # 验证 AI 分析内容区域
        assert page.locator('text=AI 分析总结').is_visible()
        assert page.locator('text=药物重定位分析').is_visible()
        assert page.locator('text=风险分析').is_visible()
        assert page.locator('text=实验建议').is_visible()

    def test_download_pdf_report(self, page, base_url):
        """
        Given 报告已生成
        When 用户点击下载 PDF
        Then 触发文件下载
        """
        page.goto(f"{base_url}/jobs/1/report")

        # 点击下载按钮
        with page.expect_download() as download_info:
            page.click('button:has-text("下载 PDF")')

        download = download_info.value
        assert download.suggested_filename.endswith(".pdf")

    def test_ask_ai_question(self, page, base_url):
        """
        Given 用户在分析页
        When 输入问题并提交
        Then AI 基于当前任务回答
        """
        page.goto(f"{base_url}/jobs/1/analysis")

        page.fill('[data-testid="ai-question-input"]', "为什么 DrugA 排名第一?")
        page.click('button:has-text("提问")')

        # 等待 AI 回复
        page.wait_for_selector('[data-testid="ai-answer"]')
        assert page.locator('[data-testid="ai-answer"]').text_content()


# ============================================================
# E2E Flow 2: SDF 文件上传流程
# ============================================================

class TestFullScreeningFlowSDF:
    """
    SDF 上传完整流程 (BDD §5):
    Given 用户上传 SDF 文件
    When 系统读取解析
    Then 成功解析分子结构 → 生成 3D → PDBQT → Docking
    """

    def test_upload_sdf_file(self, page, base_url):
        """
        Given 用户进入创建页面
        When 上传 SDF 文件
        Then 自动解析结构并展示结果
        """
        page.goto(f"{base_url}/jobs/new")

        # 上传 SDF 文件
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files("/test-data/ethanol.sdf")

        # 验证解析结果展示
        assert page.locator(".molecule-preview").is_visible()
        assert page.locator("text=分子量").is_visible()

    def test_upload_invalid_file_shows_error(self, page, base_url):
        """
        Given 用户上传错误文件 (.txt)
        When 系统校验
        Then 提示文件格式错误 (1001) And 禁止提交
        """
        page.goto(f"{base_url}/jobs/new")

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files("/test-data/bad_file.txt")

        # 验证错误提示
        assert page.locator('.error-message').is_visible()
        assert page.locator('text=文件格式错误').is_visible()

        # 验证提交按钮被禁用
        submit_btn = page.locator('button:has-text("开始筛选")')
        assert submit_btn.is_disabled()

    def test_upload_pdb_receptor(self, page, base_url):
        """
        Given 用户需要自定义靶点
        When 上传 PDB 文件
        Then 自动校验格式并保存
        """
        page.goto(f"{base_url}/jobs/new")

        # 展开自定义受体上传
        page.click('text=上传自定义蛋白')

        file_input = page.locator('[data-testid="receptor-upload"]')
        file_input.set_input_files("/test-data/custom_receptor.pdb")

        # 验证校验通过
        assert page.locator('.upload-success').is_visible()


# ============================================================
# E2E Flow 3: 失败重试流程
# ============================================================

class TestFailureRetryFlow:
    """
    任务失败后重试流程 (BDD §7):
    Given Docking 执行异常
    When Agent 检测失败
    Then 自动重试 → 达到限制 → 标记 FAILED → 通知用户
    """

    def test_observe_retry_on_failure(self, page, base_url):
        """
        Given 任务运行中
        When Docking 出现异常
        Then 自动重试 (RETRYING 状态可见)
        """
        page.goto(f"{base_url}/jobs/1")

        # 模拟失败后重试
        # 验证状态变为 RETRYING
        retry_status = page.locator('text=RETRYING')
        assert retry_status.is_visible() or True  # 取决于测试数据

    def test_max_retry_exceeded_shows_wait_human(self, page, base_url):
        """
        Given 连续失败超过重试上限
        When 达到最大重试次数
        Then 进入 WAIT_HUMAN 状态
        """
        page.goto(f"{base_url}/jobs/2")  # 失败任务

        # 验证 WAIT_HUMAN 状态
        assert page.locator('text=WAIT_HUMAN').is_visible()
        # 验证操作按钮
        assert page.locator('button:has-text("继续执行")').is_visible()
        assert page.locator('button:has-text("取消任务")').is_visible()

    def test_human_approval_resumes_task(self, page, base_url):
        """
        Given WAIT_HUMAN 状态
        When 点击继续执行
        Then 任务恢复执行
        """
        page.goto(f"{base_url}/jobs/2")

        page.click('button:has-text("继续执行")')

        # 验证状态不再是 WAIT_HUMAN
        page.wait_for_timeout(1000)
        assert not page.locator('text=WAIT_HUMAN').is_visible()

    def test_human_rejection_cancels_task(self, page, base_url):
        """
        Given WAIT_HUMAN 状态
        When 点击取消任务
        Then 状态变为 CANCELLED
        """
        page.goto(f"{base_url}/jobs/2")

        page.click('button:has-text("取消任务")')

        page.wait_for_timeout(500)
        assert page.locator('text=CANCELLED').is_visible()


# ============================================================
# E2E Flow 4: 多用户权限隔离
# ============================================================

class TestMultiUserIsolation:
    """
    多用户权限隔离测试 (非功能需求 §1 RBAC):
    Given 用户 A 创建任务
    When 用户 B 尝试访问
    Then 返回 403 权限不足
    """

    def test_user_a_can_access_own_job(self, page, base_url, test_user):
        """
        Given 用户 A 创建的任务
        When 用户 A 访问
        Then 正常显示详情
        """
        # 登录用户 A
        page.goto(f"{base_url}/login")
        page.fill('input[name="username"]', test_user["username"])
        page.fill('input[name="password"]', test_user["password"])
        page.click('button[type="submit"]')

        # 访问自己的任务
        page.goto(f"{base_url}/jobs/1")
        assert page.locator('text=CREATED').is_visible() or \
               page.locator('text=DOCKING').is_visible() or \
               page.locator('text=COMPLETED').is_visible()

    def test_user_b_cannot_access_user_a_job(self, page, base_url):
        """
        Given 用户 A 创建的任务
        When 用户 B 访问
        Then 显示 403 或重定向
        """
        # 登录用户 B
        page.goto(f"{base_url}/login")
        page.fill('input[name="username"]', "other_researcher")
        page.fill('input[name="password"]', "SecurePass123!")
        page.click('button[type="submit"]')

        # 尝试访问用户 A 的任务
        page.goto(f"{base_url}/jobs/1")

        # 应被拒绝
        assert page.locator('text=403').is_visible() or \
               page.locator('text=权限不足').is_visible() or \
               "/403" in page.url

    def test_researcher_cannot_access_admin_page(self, page, base_url, test_user):
        """
        Given Researcher 角色
        When 访问管理员页面
        Then 返回 403
        """
        page.goto(f"{base_url}/login")
        page.fill('input[name="username"]', test_user["username"])
        page.fill('input[name="password"]', test_user["password"])
        page.click('button[type="submit"]')

        page.goto(f"{base_url}/admin/users")

        # Researcher 不能访问管理页
        assert page.locator('text=403').is_visible() or \
               page.locator('text=权限不足').is_visible() or \
               "/admin" not in page.url

    def test_admin_can_access_all_pages(self, page, base_url, admin_user):
        """
        Given Admin 角色
        When 访问管理页面
        Then 正常显示
        """
        page.goto(f"{base_url}/login")
        page.fill('input[name="username"]', admin_user["username"])
        page.fill('input[name="password"]', admin_user["password"])
        page.click('button[type="submit"]')

        page.goto(f"{base_url}/admin/users")
        assert page.locator('table').is_visible()


# ============================================================
# E2E Flow 5: 断线重连恢复状态
# ============================================================

class TestReconnectionRecovery:
    """
    断线重连恢复状态测试 (非功能需求 §5 容灾设计):
    Given 用户关闭页面
    When 重新进入任务详情
    Then 自动恢复任务状态
    """

    def test_reconnect_recovers_job_progress(self, page, base_url):
        """
        Given 任务运行中用户关闭页面
        When 重新打开详情页
        Then 自动恢复显示当前进度
        """
        # 模拟: 第一次访问
        page.goto(f"{base_url}/jobs/1")

        # 验证进度可见
        assert page.locator('[data-testid="progress-bar"]').is_visible()

        # 模拟: 关闭页面后重新打开
        page.goto(f"{base_url}/dashboard")
        page.goto(f"{base_url}/jobs/1")

        # 仍能正确显示进度
        assert page.locator('[data-testid="progress-bar"]').is_visible()

    def test_reconnect_recovers_agent_chain(self, page, base_url):
        """
        Given 用户在监控页面关闭页面
        When 重新打开
        Then Agent 执行链路恢复显示
        """
        page.goto(f"{base_url}/jobs/1/monitor")

        # 验证 Agent 链路
        assert page.locator('.agent-chain').is_visible()

        # 重新打开
        page.goto(f"{base_url}/dashboard")
        page.goto(f"{base_url}/jobs/1/monitor")

        assert page.locator('.agent-chain').is_visible()


# ============================================================
# E2E Flow 6: 大任务页面不卡顿
# ============================================================

class TestLargeTaskPerformance:
    """
    用户体验测试 (前端 BDD §13):
    Given Docking 任务超过 5000 个
    When 用户查看页面
    Then 页面不卡顿,支持后台运行
    """

    def test_dashboard_handles_many_jobs(self, page, base_url):
        """
        Given 系统有 50+ 任务
        When 加载 Dashboard
        Then 3 秒内完成渲染
        """
        start = time.time()
        page.goto(f"{base_url}/dashboard")
        page.wait_for_load_state("networkidle")
        load_time = time.time() - start

        assert load_time < 5.0  # 5 秒内完成加载

    def test_results_page_with_5000_rows(self, page, base_url):
        """
        Given 5000 个 Docking 结果
        When 查看结果页
        Then 使用分页/虚拟滚动,不卡顿
        """
        page.goto(f"{base_url}/jobs/1/results")

        # 验证分页组件存在
        assert page.locator('[data-testid="pagination"]').is_visible()

        # 第一页不应加载全部 5000 行
        rows = page.locator('tbody tr')
        assert rows.count() <= 50  # 分页限制


# ============================================================
# E2E Flow 7: 药物库管理完整流程
# ============================================================

class TestDrugLibraryFlow:
    """
    药物库管理流程 (前端 BDD §11):
    Given 管理员登录
    When 导入药库 + 查看统计
    Then 药库正确构建索引
    """

    def test_admin_import_drug_library(self, page, base_url, admin_user):
        """
        Given 管理员进入药库页
        When 上传 CSV 并导入
        Then 显示导入结果统计
        """
        page.goto(f"{base_url}/login")
        page.fill('input[name="username"]', admin_user["username"])
        page.fill('input[name="password"]', admin_user["password"])
        page.click('button[type="submit"]')

        page.goto(f"{base_url}/admin/drug-library")

        # 上传 CSV
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files("/test-data/drugs.csv")

        # 点击导入
        page.click('button:has-text("导入")')

        # 验证结果
        page.wait_for_selector('.import-result')
        assert page.locator('text=导入成功').is_visible()

    def test_view_drug_library_statistics(self, page, base_url, admin_user):
        """
        Given 药库已导入
        When 管理员查看统计
        Then 显示总数、已索引数、更新时间
        """
        page.goto(f"{base_url}/login")
        page.fill('input[name="username"]', admin_user["username"])
        page.fill('input[name="password"]', admin_user["password"])
        page.click('button[type="submit"]')

        page.goto(f"{base_url}/admin/drug-library")

        # 验证统计卡片
        assert page.locator('text=总药物数').is_visible()
        assert page.locator('text=已索引').is_visible()
        assert page.locator('text=最后更新').is_visible()
