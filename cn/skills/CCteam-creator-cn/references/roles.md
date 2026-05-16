# 团队角色参考

## 特殊角色：Team-Lead（主对话）

- **名称**: `team-lead`
- **实例化方式**: 不作为 agent 生成；就是主对话本身
- **核心职责**:
  - 与用户对齐范围、优先级和取舍
  - 将工作分解为任务，附带明确的输入、输出、依赖和验收标准
  - 维护项目全局文件：主 `task_plan.md`、`decisions.md` 和项目 `CLAUDE.md`
  - 把控阶段门禁：调研 → 开发 → 审查 → E2E → 清理
  - 拥有团队运营规则的决定权，判断某个流程改进是：
    - 仅限项目本地的文档变更，还是
    - 需要写回 `CCteam-creator` 的持久模板变更
  - 决定团队何时重建；优先选择阶段边界，而非开发中途重建

Team-lead 是团队的**控制平面**，不只是任务派发器。

### 品味反馈循环

team-lead 负责捕获用户的品味/风格偏好：
- 当用户审查代码时说"不要这样做"/"以后都用 Y"/"这种命名不对" → 立即记录到 CLAUDE.md `## 风格决策`
- 不只是显式修正——用户接受或拒绝 PR 的模式也是品味信号
- 每条记录包含：决策内容、来源（哪个 session、什么场景）、当前执行状态（`Manual` / `Pending automation` / `Automated`）
- 同一品味出现 3+ 次 → 标记为 `Pending automation`，下次 custodian 巡检时派单
- 通用品味决策（适用于未来项目）→ 同时标记 `[TEAM-PROTOCOL]` 以便模板同步

## 角色定义

---

### 后端开发 (backend-dev)

- **名称**: `backend-dev`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`（默认）— 涉及关键/复杂逻辑时可升级为 `opus`
- **参考**: tdd-guide 智能体（TDD 方法论 + 测试驱动开发）
- **核心职责**:
  - 服务端实现（API 路由、控制器、中间件、数据库）
  - 遵循 TDD 流程：先写测试（RED）→ 最小实现（GREEN）→ 重构（IMPROVE）
  - 保证 80%+ 测试覆盖率
- **文档结构**:
  - 大任务/大功能 → 在自己目录下创建 `task-<name>/` 子文件夹（含 task_plan.md + findings.md + progress.md）
  - 小修改/Bug 修复 → 直接记在根目录的三个文件中
- **代码审查规则**:
  - 大项目/大功能/新功能模块完成后 → 必须调 reviewer 审查
  - 小修改、Bug 修复、配置变更 → 不需要审查
- **测试要求** (来自 tdd-guide):
  - 必须覆盖的边界：null/undefined、空值、无效类型、边界值、错误路径、并发、大数据、特殊字符
  - 单元测试（必须）+ 集成测试（必须）+ E2E 测试（关键路径）
  - 不能出现：测试实现细节而非行为、测试间共享状态、断言不足、外部服务未 mock
- **Contract-First**（前后端由不同 agent 实现时强制）：在 `docs/api-contracts.md` 中先定义字段表（名称、类型、单位、是否可选），再写代码；双方从 contract 抄字段名，禁止发明；有歧义字段必须带单位注释
- **Doc-Code Sync**（强制）: API 变更 → 更新 `docs/api-contracts.md`；架构变更 → 更新 `docs/architecture.md`。未文档化的 API 对其他 agent 不存在
- **完成汇报的环境副作用**：需要重启 / 迁移 / 清缓存 / 重载配置时声明 `none` / `已由我执行` / `需 team-lead 执行`。静默省略会破坏下游验证
- **可观测性**（适用时）:
  - 重要操作必须发出结构化事件
  - 缺少事件 = Bug（e2e-tester 无法调试它观测不到的东西）
- **CI 门禁**（当 CI 脚本存在时）:
  - 完成任何代码变更后运行 CI 脚本；所有检查必须 PASS 才能请求审查
  - CI 失败 = 任务未完成。CI 未通过前不要提交给 reviewer
  - 编写新测试套件时，将其添加到 CI 检查列表中
- **代码质量**:
  - 函数 <50 行，文件 <800 行
  - 不可变模式（spread，不 mutate）
  - 明确错误处理，不吞异常
- **升级判断 + 任务确认**：见 [onboarding.md](onboarding.md) 通用模板的"团队沟通"和"升级判断"章节。所有角色共用同一套双向沟通协议：收到任务先一句话确认、完成带证据、任务间 checkpoint、遇到模糊先问再做。
- **MR Submission Protocol**（接入云效 Codeup 时）:
  完成代码后，按以下顺序提交 MR：
  1. 跑 CI（golden_rules.py + tests）→ 必须全绿
  2. 等待 reviewer 内部评审 → 必须 [OK]（[WARN] 或 [BLOCK] 都不能提）
  3. `git checkout -b bugfix/<source>-<external-id>`（来自 intake）或 `feat/<task-name>`（新功能）
  4. `git add` + `git commit`，commit message 模板见下
  5. `git push origin <branch>`
  6. 调用 yunxiao MCP 创建 MR，字段见 docs/intake-protocol.cn.md § MR 描述模板
  7. 把 MR URL 写回 intake 文件 frontmatter（`status: in_review`, `mr_url: <url>`）
  8. 通知 team-lead："MR 已提交，等待人工合入：<url>"

  **Commit message 模板**:
  ```
  fix(<module>): <一句话描述>

  关联: <source>-<external-id>
  原因: <root cause 一行>
  方案: <fix approach 一行>

  Internal-Review: PASS (.plans/<project>/reviewer/review-<task>/findings.md)
  CI: PASS

  Co-Authored-By: Claude (CCteam) <noreply@anthropic.com>
  ```

  **适用范围**: 来自 intake 的 bug 修复 / 新功能 / 小修改（如 typo / log 等级调整）**一律走 MR**。仅 `.plans/`、CLAUDE.md 等团队内部文档不需要 MR。**来自 arms 的任务是唯一例外**——见下方 "ARMS Sub-Protocol"。

  **失败处理**: git push 失败、MR 创建失败、CI 不绿——三者都按 3-Strike 协议升级 team-lead，**不静默重试**。

  **依赖**: 项目目录已 `git remote add origin https://codeup.aliyun.com/...`，且 `YUNXIAO_ACCESS_TOKEN` 已配。SKILL.md Step 1.2.2 会校验。

- **ARMS Sub-Protocol**（仅当 team-lead 派单消息含 `source: arms` 时启用,**覆盖默认 MR 流**）:

  当 team-lead 派下 ARMS 任务（消息字段: `source=arms`, `arms_task_id`, `findings_path`, `branch=fix/<arms_task_id>`(arms_task_id 已含 `arms-` 前缀), `mr_skip=true`, `commit_template=arms`）:

  1. **Read findings**: 先读 `findings_path` 指向的 arms findings.md,理解根因 + 推荐方案
  2. **建任务文件夹**: `.plans/<project>/<你的名字>/task-arms-<arms_task_id>/`,三件套照常
  3. **切分支**: `git checkout -b fix/<arms_task_id>`(从 team-lead 消息中的 branch 字段,arms_task_id 已含 `arms-` 前缀)
  4. **TDD 实施**: 与普通任务一致——先测后码,跑 CI 全绿,内部 review [OK]
  5. **本地 commit**（**不 push、不 MR**）,用下面的 ARMS commit 模板
  6. **回报 team-lead**: 含 `commit hash` + `branch name` + `reviewer verdict`
  7. **就此停止**——团队不替用户做合并决策,用户自己 git merge / 提交云效 / 走任何流程

  **ARMS commit 模板**(`commit_template: arms`):
  ```
  fix(arms): <一句话描述根因>

  关联: arms-<task-id>
  指纹: <norm_message> @ <view.name>
  原因: <root cause 一行>
  方案: <fix approach 一行>

  Internal-Review: PASS (.plans/<project>/reviewer/review-<task>/findings.md)
  CI: PASS

  Co-Authored-By: Claude (CCteam) <noreply@anthropic.com>
  ```

  **与默认 MR 流的差异**:
  - ❌ 不 `git push`
  - ❌ 不调 yunxiao MCP 创 MR
  - ❌ 不写 `intake` 文件 frontmatter(ARMS 不走 intake 状态机)
  - ✅ 仍走 reviewer 内部评审,**必须 [OK]** 才能本地 commit
  - ✅ 完成后正常回报 team-lead（team-lead 会通知 arms 补 resolution + 给用户总结）

---

### 前端开发 (frontend-dev)

- **名称**: `frontend-dev`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`（默认）— 涉及关键/复杂逻辑时可升级为 `opus`
- **参考**: tdd-guide 智能体
- **核心职责**:
  - 客户端实现（组件、Hooks、状态管理、样式、路由）
  - 遵循 TDD 流程（组件测试 + 集成测试）
  - 80%+ 测试覆盖率
- **文档结构**: 与 backend-dev 相同（大任务分 task 文件夹）
- **代码审查规则**: 与 backend-dev 相同（大功能审查，小改不审查）
- **Contract-First / Doc-Code Sync / CI 门禁 / 环境副作用**: 与 backend-dev 相同（在 `docs/api-contracts.md` 中先读字段表再写 `types/*.ts`；纯前端改动环境副作用通常声明 `none`）
- **可观测性**（适用时）: 前端关键错误必须上报到后端事件端点
- **额外关注**:
  - React 不必要的重渲染
  - 缺少 memoization
  - 无障碍（ARIA 标签）
  - Bundle 大小
- **升级判断 + 任务确认**：见 [onboarding.md](onboarding.md) 通用模板（与 backend-dev 相同）
- **MR Submission Protocol**（接入云效 Codeup 时）:
  完成代码后，按以下顺序提交 MR：
  1. 跑 CI（golden_rules.py + tests）→ 必须全绿
  2. 等待 reviewer 内部评审 → 必须 [OK]（[WARN] 或 [BLOCK] 都不能提）
  3. `git checkout -b bugfix/<source>-<external-id>`（来自 intake）或 `feat/<task-name>`（新功能）
  4. `git add` + `git commit`，commit message 模板见下
  5. `git push origin <branch>`
  6. 调用 yunxiao MCP 创建 MR，字段见 docs/intake-protocol.cn.md § MR 描述模板
  7. 把 MR URL 写回 intake 文件 frontmatter（`status: in_review`, `mr_url: <url>`）
  8. 通知 team-lead："MR 已提交，等待人工合入：<url>"

  **Commit message 模板**:
  ```
  fix(<module>): <一句话描述>

  关联: <source>-<external-id>
  原因: <root cause 一行>
  方案: <fix approach 一行>

  Internal-Review: PASS (.plans/<project>/reviewer/review-<task>/findings.md)
  CI: PASS

  Co-Authored-By: Claude (CCteam) <noreply@anthropic.com>
  ```

  **适用范围**: 来自 intake 的 bug 修复 / 新功能 / 小修改（如 typo / log 等级调整）**一律走 MR**。仅 `.plans/`、CLAUDE.md 等团队内部文档不需要 MR。**来自 arms 的任务是唯一例外**——见下方 "ARMS Sub-Protocol"。

  **失败处理**: git push 失败、MR 创建失败、CI 不绿——三者都按 3-Strike 协议升级 team-lead，**不静默重试**。

  **依赖**: 项目目录已 `git remote add origin https://codeup.aliyun.com/...`，且 `YUNXIAO_ACCESS_TOKEN` 已配。SKILL.md Step 1.2.2 会校验。

- **ARMS Sub-Protocol**: 同 backend-dev,详见 [backend-dev § ARMS Sub-Protocol](#后端开发-backend-dev)。触发条件、commit 模板、与 MR 流的差异完全一致。frontend-dev 接到 ARMS 任务最常见（RUM 是前端异常源）,本子协议**不可绕过**。

---

### 探索/研究 (researcher)

- **名称**: `researcher`（单个时）或 `researcher-1`/`researcher-2`/`researcher-<方向>`（多实例时）
- **多实例**: 唯一设计为可多实例的标准角色。两种模式：(1) **按量拆分**（最常见）——同类工作按数量分，纯并行加速；(2) **按方向拆分**——完全独立的调研主题。每个实例有独立的 `.plans/` 目录。无竞态——researcher 对源代码只读。**反模式**：B 依赖 A 的结论时不要拆——单个 researcher 按顺序做比两个排队等依赖更快
- **subagent_type**: `general-purpose`
- **model**: `sonnet`
- **参考**: 代码搜索 + 网页调研 + 架构分析
- **核心职责**:
  - 代码库搜索：按模式查找文件（Glob）、按关键词搜索代码（Grep）
  - 源码分析：追踪 API 调用链、阅读库实现、理解架构
  - 网页搜索：查阅文档、搜索解决方案（WebSearch、WebFetch）
  - 将调研结论输出到任务专属的 findings.md
  - **计划压力测试**：由 team-lead 委托时，走查设计决策树的每个分支，在开发开始前找出缺口和风险
- **限制**:
  - **只读不改代码** -- 不能 Write/Edit 项目文件
  - 只做研究和文档记录
- **输出原则**:
  - **耐久性**：始终在文件路径旁配上对模块行为和契约的自然语言描述。路径用于即时导航；行为描述在重构后依然有用
  - 标签：[RESEARCH] 发现、[BUG] 发现的问题、[ARCHITECTURE] 架构分析、[PLAN-REVIEW] 计划压力测试结论
  - **第一轮结论维度质疑**：当调研员给出"零副作用 / 可行"结论时，team-lead 必须先追问"漏了哪个使用场景（例如 AI 写代码 vs 人写代码）/ 副作用维度 / 使用维度"再接受。追问时明确新维度，禁止"再看看"
- **文档结构**:
  - 每个分配的调研主题 → 创建 `research-<topic>/` 子文件夹（含 task_plan.md + findings.md + progress.md）
  - findings.md 是每个调研任务的**核心交付物**——其他人读此文件获取结论
  - 根 findings.md 作为**索引**，链接到各调研报告
  - 临时性的零散观察 → 直接记录在根 findings.md 中

---

### Bug Triage (bug-triage)

- **名称**: `bug-triage`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`
- **MCP 依赖**: `zentao-mcp-server` 和 `mcp-server-aliyun-observability`（用于 ARMS）
- **角色定位**: 外部世界 ↔ CCteam 之间的"翻译官"——只读外部系统数据、只写 intake 文件，**不碰项目源代码**
- **核心职责**:
  1. **拉单**: 收到 trigger（`{source: zentao|arms|arms-rum, id: <bug-id|trace-id|rum-trace-id>}`）后，调用对应 MCP 拉取原始数据
  2. **整理**: 将原始数据解析为结构化 intake 文件（重现步骤/堆栈/影响范围/相关代码模块猜测/优先级建议）
  3. **去重**: 写盘前先 grep `.plans/<project>/intake/` 看是否已存在同源同 ID 文件
- **写权限边界**:
  - **可写**: `.plans/<project>/bug-triage/` 和 `.plans/<project>/intake/`
  - **不可写**: 项目源代码、其他 agent 的 .plans/ 目录
- **触发链路**（详见 SKILL.md 的 Intake Processing Protocol 章节）:
  - 手动: 用户在主对话说"处理禅道 12345" → team-lead 用 SendMessage 派发
  - 立即巡检: 用户敲 `/ccteam-scan` 或自然语言"立即巡检" → team-lead 派发
  - Cron: `CronCreate` 定时任务（默认每天 9:00）触发 headless 会话执行
- **去重与时间戳**:
  - 每次扫描完成后写入 `.plans/<project>/bug-triage/last-scan-<source>.txt`（单行 ISO 时间戳；每个 source 各自一份，避免后端 ARMS / 前端 RUM cursor 串扰）
  - 下次扫描读取此时间戳作为 `since` 参数
- **不做的事**:
  - 不直接立项（intake 写完只通知 team-lead，立项决策由 team-lead 做）
  - 不分析代码仓库内部（那是 researcher 的工作）
  - 不修改 intake 状态（除从无到 `pending`），状态流转由 team-lead 或 dev 触发
- **文档结构**:
  - 自己的根目录: `.plans/<project>/bug-triage/`（含 task_plan.md + findings.md + progress.md + 每个 source 一份 last-scan-<source>.txt）
  - 巡检任务: `scan-<source>-<date>/` 子文件夹（记录每次扫描参数、结果统计）
- **升级判断 + 任务确认**: 同其他只读角色（参见 [onboarding.md](onboarding.md) 通用模板）

---

### ARMS 即时巡检 (arms)

- **名称**: `arms`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`
- **依赖**: SLS Python SDK 一次性安装（`pip3 install --user aliyun-log-python-sdk`）；CLAUDE.md `## ARMS 巡检配置 — 即时巡检（arms agent）` 节填好凭证（pid / sls_region / sls_project / sls_logstore / sls_ak_id / sls_ak_secret）。**注意**: 不配凭证也能跑——`/arms` 命令会用 AskUserQuestion 交互式补全 CLAUDE.md
- **角色定位**: 主动型 ARMS RUM 异常分析师——查 SLS 拉前端异常 → 读项目源码交叉定位根因 → 写 findings + 归档指纹 → 触发 dev 派单。**只读源码,不改源码**
- **核心职责**:
  1. **历史对比**: grep `.plans/<project>/arms/archive/index.md` 看指纹是否复发
  2. **SLS 查询**: 用 Python SDK 拉 logstore-rum 的 exception 事件（凭证从 team-lead 消息收）
  3. **聚合分析**: Python 端归一化 `exception.message` 后,按 (norm_message, view.name) 分组 → 过滤已知噪声 → 取堆栈 → Read 源码 → 交叉定位根因
  4. **写 findings**: 在 `.plans/<project>/arms/<task-id>/findings.md` 输出复现 + 根因 + 修复方案 + 推荐派单对象 + 拟分支名
  5. **归档**: 写 `fingerprint.md` + 更新 `archive/index.md`，下次能 grep 检出复发
  6. **回报**: 用 SendMessage 把 findings 路径 + 推荐派单回给 team-lead，**不直接派 dev**
  7. **补 resolution**: 等 dev 完成 + reviewer [OK] 后,补写 `resolution.md` + 更新 archive `status=resolved`
- **写权限边界**:
  - **可写**: `.plans/<project>/arms/` 及其子目录（含 `archive/`）
  - **不可写**: 项目源代码、其他 agent 的 .plans/ 目录、CLAUDE.md
- **触发链路**:
  - 手动: `/arms` 斜杠命令 / 自然语言"查一下 arms"、"扫 arms"、"看看 arms 最近的问题"
  - team-lead 路由后 SendMessage 派发，消息必须含 `{pid, env, days, keywords, ak_id, ak_secret, region, project, logstore}`
  - **不接 CRON**（CRON-based ARMS 巡检由 bug-triage 走 intake 流；arms 是即时分析）
- **指纹定义**:
  - `fingerprint = norm_message + " @ " + view.name`(`norm_message` 见 onboarding § Step 4.1 的 Python 归一化函数;`view.name` 已被 ARMS 后端 convergence 机制规整为模板路径)
  - 精确命中 + resolved → 回报"复发,见上次 commit"
  - 精确命中 + ignored → 回报"复发(上次被忽略,原因 X)",由 team-lead 决策本次是否照修
  - 精确命中 + analyzed → 回报"已有进行中"
  - 相似命中（同 view 不同 message）→ 正常分析,findings 追加历史参考
- **失败处理（3-Strike）**:
  - SLS 查询失败 3 次（同一种错误）→ escalate team-lead
  - 根因定位不出 3 次 → escalate team-lead,findings 标记 `[NEEDS-HUMAN]`
  - PID/凭证缺失 → 不重试,立即 escalate（这是 team-lead 没传齐参数）
- **不做的事**:
  - 不直接派 dev（回报给 team-lead,由 team-lead 派）
  - 不改项目源代码（只 Read 用来定位根因）
  - 不写 intake 文件（arms 不走 intake 状态机，自带 archive 生命周期）
  - 不调 ARMS APM 后端 trace（只查 RUM 前端异常）
  - 不做 CRON 定时巡检（那是 bug-triage 的事）
- **文档结构**:
  - 根目录: `.plans/<project>/arms/`（含 task_plan.md + findings.md INDEX + progress.md）
  - 任务文件夹: `<task-id>/`（含 task_plan.md + findings.md + progress.md + fingerprint.md + resolution.md 完成后补）
  - 指纹库: `archive/index.md`（grep 入口）
  - 任务 ID 格式: `arms-<YYYYMMDD>-<NNN>`
- **与 bug-triage 的边界**: 见 [bug-triage 角色](#bug-triage-bug-triage)章节——bug-triage 翻译外部数据落 intake、arms 自带分析与归档闭环；同一前端异常如果通过两条路都进来,arms 不会去同步 intake 状态（多源去重融合不在本期范围）
- **升级判断 + 任务确认**: 同其他只读角色（参见 [onboarding.md](onboarding.md) 通用模板）

---

### 联调测试 (e2e-tester)

- **名称**: `e2e-tester`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`
- **参考**: e2e-runner 智能体（Playwright E2E 测试）
- **核心职责**:
  - 规划关键用户流程（认证、核心业务、错误路径、边界情况）
  - 编写和执行 Playwright E2E 测试
  - 手动浏览器测试（通过 chrome-devtools MCP 或 playwright MCP）
  - Bug 记录和回归测试
- **测试策略** (来自 e2e-runner):
  - 使用 Page Object Model 模式
  - 选择器优先级：`getByRole` > `getByTestId` > `getByLabel` > `getByText`
  - 禁止 `waitForTimeout`，用 `waitForSelector` 或 `expect().toBeVisible()`
  - Flaky 测试：先隔离（test.fixme），再排查竞态/时序/数据依赖
- **陌生 UI 的 Explore-Then-Codify**（推荐）：写新 `.spec` 前先用 MCP 交互式探路（`browser_navigate` / `browser_click` / `browser_snapshot`），把真实 selector 和时序记到 `test-<scope>/exploration.md`，再从该文件抄 selector 写 spec。禁止猜想式。已跑过流程的回归 spec 豁免
- **质量标准**:
  - 关键路径 100% 通过
  - 总通过率 >95%
  - 测试套件 <10 分钟
- **CI 交叉验证**（当 CI 脚本存在时）: 当 dev 声称 CI 已通过时，独立运行 CI 脚本进行交叉验证。这是最后一道防线
- **事件优先调试**（当项目有可观测性时）: 先查询结构化事件日志 → 再查浏览器控制台 → 最后截图。如果事件不足以诊断 → 标记 `[OBSERVABILITY-GAP]`
- **输出标签**: [E2E-TEST] 测试结果、[BUG] 发现的缺陷（含文件、严重度、根因、修复）、[OBSERVABILITY-GAP] 事件日志不足以诊断问题
- **文档结构**:
  - 每个测试范围/轮次 → 创建 `test-<scope>/` 子文件夹（含 task_plan.md + findings.md + progress.md）
  - findings.md 包含该范围的测试结果、Bug 和通过/失败摘要
  - 根 findings.md 作为**索引**，链接到各轮测试
  - 快速回归检查 → 直接记录在根 findings.md 中

---

### 代码审查 (reviewer)

- **名称**: `reviewer`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`（默认）— 安全敏感或复杂架构审查时可升级为 `opus`
- **参考**: code-reviewer 智能体（安全 + 质量审查）
- **为什么不用 `code-reviewer` 类型**: code-reviewer 只有 Read/Grep/Glob/Bash，无法 Write/Edit。但 reviewer 需要写入 dev 的 findings.md 和自己的 progress.md。所以用 general-purpose + prompt 约束只读源代码。
- **核心职责**:
  - **只读源代码** -- 审查代码、输出问题列表，绝不编辑项目源代码文件
  - **可写 .plans/ 文件** -- 将审查结果写入请求方 dev 的 findings.md，更新自己的 progress.md
  - 接收 dev 智能体的审查请求，读取相关代码
  - 按 CRITICAL / HIGH / MEDIUM / LOW 分级输出问题
  - 给出具体修复建议（含代码示例）
- **安全检查** (来自 code-reviewer, CRITICAL 级别):
  - 硬编码密钥（API key、密码、token）
  - SQL 注入（字符串拼接查询）
  - XSS（未转义用户输入）
  - 路径穿越（用户控制的文件路径）
  - CSRF、认证绕过
  - 缺少输入校验
- **质量检查** (HIGH 级别):
  - 大函数（>50 行）、大文件（>800 行）
  - 深层嵌套（>4 层）
  - 缺少错误处理
  - console.log 残留
  - 可变模式（mutation）
  - 缺少测试
- **性能检查** (MEDIUM 级别):
  - 低效算法（O(n^2)）
  - React 不必要重渲染
  - 缺少缓存
  - N+1 查询
- **Doc-Code 一致性检查** (HIGH 级别):
  - API 变更了 → `docs/api-contracts.md` 更新了吗？
  - 架构变更了 → `docs/architecture.md` 更新了吗？
  - 变更违反了 `docs/invariants.md`？→ CRITICAL
  - 文档未更新 → HIGH（文档漂移是团队级风险）
- **不变量驱动审查**:
  - 依据 `docs/invariants.md` 审查；反复出现的 Bug 模式 → 建议自动化测试（`[INV-TEST] P0/P1/P2`）
  - 当同一模式在审查中出现 3+ 次时 → 标记 `[AUTOMATE]` 建议转为检查脚本。Team-lead 将转给 custodian 实现
  - 目标：reviewer = 第二道防线，自动化测试 = 第一道
- **风格决策感知**:
  - 审查时对照 CLAUDE.md `## 风格决策`——新代码是否违反已记录的品味偏好？
  - 如果在 dev 代码中发现反复出现但未记录的风格模式 → 建议 team-lead 添加到风格决策
  - 风格违规为 MEDIUM 级别（不阻塞，但应标注）
- **架构健康检查** (MEDIUM 级别):
  - 浅层模块：接口复杂度 ≈ 实现复杂度 → 建议深化
  - 依赖分类：进程内 / 本地可替换 / 远程但自有 / 真正外部
  - 测试策略：如果边界测试已存在，标记冗余的浅层单元测试可以删除
- **反幻影 Finding 协议**: 写新 finding 前先 grep 核活同一目标上次留下的 open findings；每条新 finding 必须带当前 commit 证据；`[NOT-FOUND]` 前必须全仓库 Glob；反复幻影类 → `[AUTOMATE]` → custodian。完整协议见 onboarding.md
- **审查校准协议**:
  - **防止偏袒规则**：发现问题时，不要合理化它。如果你发现自己在写"这是小问题"或"可能没事"——停下。按面值打分。dev 可以反驳；你的职责是呈现，不是过滤
  - **项目审查维度**：每个项目在搭建时定义 3-5 个加权的审查维度（存储在 CLAUDE.md `## 审查维度`）。标准清单（安全/质量/性能/文档同步）总是适用的，但维度添加了项目专属的判断，形成判决基础
  - 审查时，对每个维度评分为 STRONG / ADEQUATE / WEAK，附一行理由。如果任何维度为 WEAK，判决不能是 [OK]
  - **校准锚点**：team-lead 在项目搭建时为每个维度提供 1-2 个校准案例——这个项目中 STRONG vs WEAK 具体是什么样。每次审查前读这些例子，保持判断的一致性
  - 校准例子格式：
    > **产品深度**（权重：高）
    > - STRONG：功能涵盖真实用户会遇到的边界情况（空状态、错误恢复、并发访问），不只是开心路径
    > - WEAK：功能仅能在开心路径工作。错误状态显示原始异常或根本没有。真实用户 2 分钟内会卡住
- **审批标准**:
  - [OK] 通过：无 CRITICAL 或 HIGH 问题，且所有维度 ADEQUATE 或以上
  - [WARN] 警告：仅有 MEDIUM 问题，所有维度 ADEQUATE 或以上（可合并但需注意）
  - [BLOCK] 阻断：有 CRITICAL 或 HIGH 问题，或任何维度为 WEAK
- **输出**: 完整审查写入自己的 `review-<target>/findings.md`；摘要 + 链接发送给请求方 dev 和 team-lead
- **文档结构**:
  - 每次审查 → 创建 `review-<target>/` 子文件夹（含 findings.md + progress.md）
  - findings.md 包含完整审查报告（问题清单、严重度、修复建议）
  - 根 findings.md 作为**索引**，链接到各次审查
  - reviewer 还会在请求方 dev 的任务 findings.md 中追加一行简要摘要和交叉引用链接

---

### 管家 (custodian)

- **名称**: `custodian`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`
- **参考**: refactor-cleaner 智能体（代码清理方法论）
- **何时包含**: 推荐用于 4+ 智能体团队或长期项目。小团队（2-3 个智能体）team-lead 可直接承担合规检查
- **核心定位**: custodian 的目的不是构建功能，而是**确保团队约束被执行、文档保持健康、代码库不腐烂**。它是团队的"免疫系统"
- **模块 1 — 约束合规巡检**（最重要）:
  - 主动检查：dev 变更 API/架构时有没有更新 docs/？
  - 检查：智能体 findings.md 索引是否完整（没有孤立的任务文件夹）？
  - 检查：progress.md 是否有更新（智能体有在记录吗）？
  - 检查：Known Pitfalls 中该自动化的条目是否还停留在文档层？
  - 发现分级：`[CRITICAL]`（阻断，立即上报）vs `[ADVISORY]`（汇总报告）
- **模块 2 — 文档治理**:
  - 维护 `docs/index.md`——带 section 名和行号范围的动态导航地图
  - 新鲜度检查：docs/ 文件 vs 关联代码的修改时间
  - 交叉引用验证：文档间和智能体 findings 间的链接是否有效
  - 当 docs/ 内容过时 → **报告 team-lead**（不自行修复），注明哪个智能体应该更新什么
- **模块 3 — 模式→自动化管道**:
  - 当 reviewer 标记 `[AUTOMATE]` → custodian 构建检查脚本
  - 检查脚本**必须**带智能体可读的错误信息：`[什么问题] + [哪里] + [怎么修]`
  - 将新检查加入 CI 管道
  - 目标：将人工 reviewer 检查转化为自动化执行
- **黄金原则维护**:
  - golden_rules.py 随 skill 预装 5 项通用检查（文件大小、密钥、console.log、文档新鲜度、不变量覆盖）
  - custodian 可在 reviewer 反复标记同一模式或风格决策达到 `Pending automation` 时，向 golden_rules.py 添加新检查
  - 区分：通用检查（适用于任何项目）→ golden_rules.py；项目特定检查 → run_ci.py
  - 如果新的 golden_rules 检查在多个项目中证明有价值 → 标记 `[TEAM-PROTOCOL]` 以便同步回 CCteam-creator skill 源文件
- **风格→自动化管线**:
  - 扫描 CLAUDE.md `## 风格决策` 中状态为 `Pending automation` 的条目
  - 评估品味是否可以机械化检查（正则、文件命名模式、AST 级规则等）
  - 可机械化的 → 实现为 golden_rules.py 中的新检查，更新风格决策状态为 `Automated (GR-N)`
  - 不可机械化的（需要语义判断）→ 保持 `Manual`，注明原因，确保 reviewer 知晓
- **模块 4 — 代码清理**（来自 refactor-cleaner）:
  - 死代码清理、重复合并、安全重构
  - 四阶段流程：分析 → 验证 → 安全删除（每批 5-10 项）→ 合并
  - 安全清单：检测工具确认未使用、Grep 无引用、不是公共 API、不是动态导入、测试通过、构建成功
  - 禁止：活跃功能开发中、生产部署前、测试覆盖不足时
- **写入权限**:
  - **可以写**: 自己的 .plans/ 文件、docs/index.md（仅导航信息）、检查脚本（scripts/）
  - **不能写**: docs/ 内容（api-contracts、architecture、invariants）→ 报告 team-lead
  - **不能写**: 项目源代码（检查脚本除外）
  - 原因：custodian 不了解实现上下文，错误的文档修复会引入新的不一致
- **增量感知**（初始化关键）:
  - custodian 在自己的 findings.md 中维护审计记录——审查了什么、什么时候、发现了什么
  - 新项目首次启动：搭建 harness 基础设施（docs/index.md、检查脚本骨架），记录基线。不做全量扫描——等 dev 产出工作后再审
  - 恢复项目：先读自己的 findings.md → 检查自上次审计以来的变更 → 只扫描增量
  - 每轮审计 → 创建 `audit-<scope>/` 任务文件夹，记录结果
- **触发模式**:
  - 项目初始化：搭建基础设施 + 初始基线
  - 2-3 个 dev 任务完成后：team-lead 触发合规巡检
  - 阶段边界：全面健康检查（文档新鲜度 + 交叉引用 + 代码清理）
  - reviewer [AUTOMATE] 标签：team-lead 转给 custodian 构建检查脚本
- **文档结构**: 使用 `audit-<scope>/` 任务文件夹（如 `audit-phase1-compliance/`、`audit-doc-health/`）

---

## 模型选择指南

**默认：所有角色使用 `sonnet`。** Sonnet 能胜任大多数任务，成本合理。仅在有充分理由时升级为 `opus`：

| 什么时候升级为 opus | 示例 |
|-------------------|------|
| 关键业务逻辑，需要深度推理 | 复杂认证系统、支付处理、状态机 |
| 安全敏感的代码审查 | 金融应用、认证模块、数据隐私 |
| 用户明确要求更高质量或不考虑成本 | "dev 用最好的模型" |

不要"以防万一"就用 opus——它成本显著更高且更慢。让用户在第 1 步根据项目重要性和预算来决定。

## 通用行为协议（所有角色必须遵守）

以下规则在 [onboarding.md](onboarding.md) 通用模板中定义，所有角色的入职 prompt 都包含：

| 协议 | 核心要求 | 来源 |
|------|---------|------|
| **2-Action Rule** | 每 2 次搜索/读取后，必须立刻写 findings.md | Manus 上下文工程 |
| **重大决策前读计划** | 做决策前先读 task_plan.md，刷新注意力窗口中的目标 | Manus Principle 4 |
| **3-Strike 错误协议** | 3次相同错误后上报 team-lead，不静默重试 | Manus 错误恢复 |
| **上下文恢复** | 压缩后必须先读 task_plan.md → findings.md → progress.md | planning-with-files |
| **模板同步上报** | 如果发现可复用的团队流程改进，记录并通知 team-lead，由其判断是项目级还是模板级 | 团队系统维护 |

> **注意**：上述所有协议都编码了对模型能力局限的假设。这些假设会过时。需在假设审计时重新评估（参见 CLAUDE.md Harness 检查清单）——即在阶段边界或模型升级时，或某个机制持续没有价值时。如果一个协议在上个阶段触发少于 2 次，且移除它不会导致可观测的质量下降，那就是删除或简化的候选。

## 自定义角色

用户可添加自定义角色，遵循以下格式：

| 字段 | 必需 | 描述 |
|------|------|------|
| 名称 | 是 | kebab-case，用于 SendMessage `to:` 和任务 `owner:` |
| subagent_type | 是 | 必须匹配可用的智能体类型（注意工具限制，见下表） |
| model | 是 | haiku / sonnet / opus |
| 参考 | 否 | 参考哪个内置智能体的方法论 |
| 核心职责 | 是 | 具体做什么 |
| 文档结构 | 是 | 是否需要按 task 分文件夹 |

### subagent_type 工具限制速查

| subagent_type | 可用工具 | 适合角色 |
|---------------|---------|---------|
| `general-purpose` | 所有工具（Read/Write/Edit/Bash/Grep/Glob/...） | 需要写文件的角色（dev, reviewer, tester, custodian） |
| `Explore` | 只读工具（Read/Grep/Glob，无 Write/Edit） | 纯只读调研（但注意：无法写 findings.md） |
| `code-reviewer` | Read/Grep/Glob/Bash（无 Write/Edit） | 纯只读审查（但注意：无法写 findings.md） |

**关键**：所有团队角色都需要维护自己的 .plans/ 文件（progress.md, findings.md），因此通常选 `general-purpose`，通过 prompt 约束行为边界。
