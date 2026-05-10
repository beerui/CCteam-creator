# CCteam-creator 阿里云生态集成 — 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 fork 后的 CCteam-creator 上加 `bug-triage` 角色 + dev MR 自动提交协议 + intake 文件协议 + `/ccteam-scan` 斜杠命令 + ARMS Cron 巡检，让 CCteam 能与禅道/云效/ARMS 闭环工作。

**Architecture:** 纯 prompt 工程改造，无运行时代码。改动主要落在 6 类文件：role 定义 (`roles.md`) / onboarding prompt (`onboarding.md`) / CLAUDE.md 模板 (`templates.md`) / SKILL.md 主流程 / 用户配置文档 (`mcp-setup.md` + `intake-protocol.md`) / 顶层元信息 (`plugin.json` 等)。cn 先行 en 后跟，因为用户主用中文。

**Tech Stack:** Markdown / JSON / Claude Code skill 平台约定 / git。无测试框架，验证靠 grep/structural 检查 + 手动 smoke test。

**Spec:** `docs/superpowers/specs/2026-05-10-ccteam-aliyun-design.md`（必读，本 plan 的所有"内容来源于 spec §X"引用都指这个文件）

---

## File Structure（最终态参考 spec §6）

| 路径 | 操作 | 由哪个 Task 负责 |
|------|------|----------------|
| `cn/skills/CCteam-creator-cn/references/roles.md` | 改 | Task 2 |
| `cn/skills/CCteam-creator-cn/references/onboarding.md` | 改 | Task 3 |
| `cn/skills/CCteam-creator-cn/references/templates.md` | 改 | Task 4 |
| `cn/skills/CCteam-creator-cn/references/mcp-setup.md` | 新建 | Task 5 |
| `cn/skills/CCteam-creator-cn/SKILL.md` | 改 | Task 6 |
| `commands/ccteam-scan.md` | 新建 | Task 7 |
| `docs/intake-protocol.cn.md` | 新建 | Task 8 |
| `.claude-plugin/plugin.json` | 改 | Task 9 |
| `.claude-plugin/marketplace.json` | 改 | Task 9 |
| `README_CN.md` | 改 | Task 10 |
| `CHANGELOG.md` | 新建 | Task 10 |
| `LICENSE` | 改 | Task 10 |
| `skills/CCteam-creator/references/roles.md` | 改 | Task 12 |
| `skills/CCteam-creator/references/onboarding.md` | 改 | Task 13 |
| `skills/CCteam-creator/references/templates.md` | 改 | Task 14 |
| `skills/CCteam-creator/references/mcp-setup.md` | 新建 | Task 15 |
| `skills/CCteam-creator/SKILL.md` | 改 | Task 16 |
| `docs/intake-protocol.md` | 新建 | Task 16 |
| `README.md` | 改 | Task 16 |

---

## Task 1: 准备 — 切分支并验证起点状态

**Files:**
- Modify: 无（准备工作）

- [ ] **Step 1: 确认当前分支干净，新建工作分支**

```bash
git status
git checkout -b feat/aliyun-integration
```

Expected: `git status` 显示 `nothing to commit, working tree clean`，分支切换成功。

- [ ] **Step 2: 验证 spec 文件已 commit、可被引用**

```bash
ls docs/superpowers/specs/2026-05-10-ccteam-aliyun-design.md
git log --oneline -3 docs/superpowers/specs/
```

Expected: spec 文件存在，git log 看到 spec 提交。

- [ ] **Step 3: 记录起点信息到 plan 顶部（不提交）**

无需操作，只是确认你知道：当前在 `feat/aliyun-integration` 分支，从 master `cef90ef` 派生。所有 task 在此分支上推进。

---

## Task 2: cn — 在 roles.md 加 bug-triage + 增强 dev 的 MR 协议

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/references/roles.md`

参考 spec §2.1 (bug-triage 定义)、spec §3 (dev MR 协议)。

- [ ] **Step 1: 阅读现有 roles.md 找插入点**

读 `cn/skills/CCteam-creator-cn/references/roles.md`。识别：
- "Explorer/Researcher (researcher)" 章节末尾 → bug-triage 插在这里之后（两者都是 read-only，归类相邻）
- "Backend Dev (backend-dev)" / "Frontend Dev (frontend-dev)" 各自章节末尾 → 追加 MR Submission Protocol 子节

- [ ] **Step 2: 在 researcher 章节后插入 bug-triage 章节**

在 researcher 章节的结束分隔符 `---` 之后、e2e-tester 章节之前，插入：

```markdown
### Bug Triage (bug-triage)

- **Name**: `bug-triage`
- **subagent_type**: `general-purpose`
- **model**: `sonnet`
- **MCP 依赖**: `zentao-mcp-server` 和 `mcp-server-aliyun-observability`（用于 ARMS）
- **角色定位**: 外部世界 ↔ CCteam 之间的"翻译官"——只读外部系统数据、只写 intake 文件，**不碰项目源代码**
- **核心职责**:
  1. **拉单**: 收到 trigger（`{source: zentao|arms, id: <bug-id|trace-id>}`）后，调用对应 MCP 拉取原始数据
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
  - 每次扫描完成后写入 `.plans/<project>/bug-triage/last-scan.txt`（单行 ISO 时间戳）
  - 下次扫描读取此时间戳作为 `since` 参数
- **不做的事**:
  - 不直接立项（intake 写完只通知 team-lead，立项决策由 team-lead 做）
  - 不分析代码仓库内部（那是 researcher 的工作）
  - 不修改 intake 状态（除从无到 `pending`），状态流转由 team-lead 或 dev 触发
- **Documentation Structure**:
  - 自己的根目录: `.plans/<project>/bug-triage/`（含 task_plan.md + findings.md + progress.md + last-scan.txt）
  - 巡检任务: `scan-<source>-<date>/` 子文件夹（记录每次扫描参数、结果统计）
- **Escalation Judgment + Task Confirmation**: 同其他 read-only 角色（参见 onboarding.md 通用模板）

---
```

操作命令（用 Edit）：找到 researcher 章节末尾的 `---` 分隔符（注意它出现在 e2e-tester 标题前），在它之后插入上述内容。

- [ ] **Step 3: 验证插入成功**

```bash
grep -c "### Bug Triage (bug-triage)" cn/skills/CCteam-creator-cn/references/roles.md
grep -A 1 "### Bug Triage" cn/skills/CCteam-creator-cn/references/roles.md | head -3
```

Expected: 第一条返回 `1`；第二条显示 bug-triage 标题和首行字段。

- [ ] **Step 4: 在 backend-dev 章节末尾追加 MR Submission Protocol**

找到 backend-dev 章节末尾（即下一个 `---` 分隔符之前的最后一项 bullet），在最后一项 bullet 之后、`---` 之前，插入：

```markdown
- **MR Submission Protocol** (when integrated with Yunxiao Codeup):
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

  **适用范围**: 来自 intake 的 bug 修复 / 新功能 / 小修改（如 typo / log 等级调整）**一律走 MR**。仅 `.plans/`、CLAUDE.md 等团队内部文档不需要 MR。

  **失败处理**: git push 失败、MR 创建失败、CI 不绿——三者都按 3-Strike 协议升级 team-lead，**不静默重试**。

  **依赖**: 项目目录已 `git remote add origin https://codeup.aliyun.com/...`，且 `YUNXIAO_ACCESS_TOKEN` 已配。SKILL.md Step 1.2.2 会校验。
```

- [ ] **Step 5: 在 frontend-dev 章节末尾追加同样的 MR Submission Protocol**

frontend-dev 章节做同样的追加（与 backend-dev 完全相同的内容）。这是**有意重复**——agent 可能只读自己角色的章节，不能假设它会去 backend-dev 章节查找。

- [ ] **Step 6: 验证两处 MR 协议都加上**

```bash
grep -c "MR Submission Protocol" cn/skills/CCteam-creator-cn/references/roles.md
```

Expected: 返回 `2`（backend-dev + frontend-dev 各一处）。

- [ ] **Step 7: 在文件末尾的"角色推荐表"或类似汇总位置加 bug-triage 行**

如果 cn/roles.md 末尾没有汇总表，跳过此步。如果有（参考 en 版结尾），加一行：

```
| Bug Triage | bug-triage | — | sonnet | 拉外部 Bug/Error 数据 → 写 intake，read-only on code |
```

- [ ] **Step 8: 提交**

```bash
git add cn/skills/CCteam-creator-cn/references/roles.md
git commit -m "$(cat <<'EOF'
feat(cn/roles): add bug-triage role + MR submission protocol for devs

bug-triage: read-only role that pulls Zentao bugs / ARMS errors and
writes intake files. Does not modify source code or trigger work itself.

backend-dev / frontend-dev: append MR Submission Protocol describing
the post-review push + Yunxiao MCP MR creation flow.

Refs: docs/superpowers/specs/2026-05-10-ccteam-aliyun-design.md §2-§3
EOF
)"
```

---

## Task 3: cn — onboarding.md 加 bug-triage onboarding + dev MR 步骤

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/references/onboarding.md`

- [ ] **Step 1: 阅读 onboarding.md 找现有结构**

读文件的前 ~200 行了解 Common Template 和各角色 onboarding 的写法。识别：每个角色 onboarding = Common Template + 角色专属补充段落。

- [ ] **Step 2: 在 researcher onboarding 之后追加 bug-triage onboarding**

定位"researcher onboarding"章节末尾，在它结束的分隔符（`---` 或下一个 `## ...`）之前，插入：

````markdown
## Bug Triage Onboarding

```
你是 bug-triage，"<project>" 团队的外部数据翻译官。
默认用中文（简体）回复。

[标准 Common Template 头部 — 工作目录 / context recovery 等，参考通用模板]

## 你的特殊职责

你是团队**唯一**与外部系统（禅道、ARMS、云效）打交道的角色。其他 agent 完全不接触外部 API，只读你产出的 intake 文件。

### 输入：你接收的 trigger 形式

team-lead 会用 SendMessage 派发以下三类任务之一：

1. **单条拉单**:
   ```
   拉禅道 bug <id> → 落 intake
   ```
   动作: 用 zentao MCP fetch bug → 解析 → 写 intake/zentao-<id>.md → 回报

2. **巡检任务**:
   ```
   立即巡检任务: source=arms, project_id=X, since=<timestamp>, severity_threshold=P1
   ```
   动作:
   a. 读 `.plans/<project>/bug-triage/last-scan.txt` 校对 since（用消息里的优先）
   b. 调用 alibabacloud-api MCP 查 ARMS（参数: project_id, since, severity）
   c. 按 severity_threshold 过滤
   d. 对每条结果，先 grep `.plans/<project>/intake/<source>-<external_id>.md` 看是否已存在
   e. 已存在 → 跳过；不存在 → 写新 intake
   f. 全部完成后，把当前时间写入 last-scan.txt
   g. 回报: 新增 N 个 intake，列表

3. **重新巡检某段时间**:
   ```
   巡检 source=zentao, since=2026-05-01, severity_threshold=P0
   ```
   动作: 同 2，但 since 用消息里指定的而不是 last-scan.txt

### 输出：intake 文件格式（严格遵守）

路径: `.plans/<project>/intake/<source>-<external_id>.md`

frontmatter 字段（**全部必填**，缺字段会让 team-lead 决策困难）:
- `source`: zentao | arms
- `external_id`: 数字或字符串
- `severity`: P0 | P1 | P2 | P3
- `created_at`: ISO 时间 + 时区，如 `2026-05-10T10:30:00+08:00`
- `status`: `pending`（你只能写这个初始状态；其他状态由 team-lead/dev 后续更新）
- `external_link`: 原始 URL

正文 sections（顺序固定）:
1. `## 现象`（一句话）
2. `## 重现步骤 / 错误堆栈`
3. `## 影响范围`
4. `## 相关代码模块（triage 的猜测）` — 用 grep/find 在项目里猜，错了无所谓，给 dev 一个起点
5. `## 候选修复方向` — 1-2 个，让 dev 不用从零开始
6. `## 原始数据` — 完整 JSON，方便 dev 进一步挖

### 严格的边界

- **绝不修改任何项目源代码**（包括读 README/查代码都可以，写则不行）
- **绝不修改其他 agent 的 .plans/ 目录**
- **绝不直接派单给 dev**（写完 intake 通知 team-lead 即可）
- **绝不做"立项决策"**（这是 team-lead 的权力）
- **去重不可省**（grep 失败比写重复严重得多——重复 intake 会污染团队优先级判断）

### 失败处理（3-Strike）

- MCP 调用失败 3 次（同一种错误） → 升级 team-lead，写入 progress.md
- 解析原始数据失败 → 写一条 `## 解析失败` 块到 intake，状态仍为 `pending`，让 team-lead 看
- 去重 grep 失败（文件系统问题）→ 立刻停，**绝不**继续写入避免重复

### 文档维护频率

- 每次扫描 → 在 progress.md 记一行（时间、source、参数、新增数量）
- 重大决策（比如某规则导致大量过滤）→ findings.md
- last-scan.txt 每次成功扫描后必须更新
```
````

- [ ] **Step 3: 在 backend-dev onboarding 末尾追加 MR 步骤段**

定位 backend-dev onboarding 章节，在该章节的代码块（描述 dev 行为的那一大段）末尾、闭合 ` ``` ` 之前，加一段：

```
## MR 提交流程（当项目集成云效 Codeup 时）

完成代码任务后（**所有代码改动一律走 MR**，包括小修改；仅 .plans/ 和 CLAUDE.md 等团队内部文档不需要）：

1. 确认 CI 全绿（运行 golden_rules.py + 单测 + 类型检查）
2. 等待 reviewer 评审，verdict 必须 [OK]
3. 切分支:
   - 来自 intake 的修复: `git checkout -b bugfix/<source>-<external_id>`
   - 新功能: `git checkout -b feat/<task-name>`
4. commit（用 §角色定义里 commit template）
5. `git push origin <branch>`
6. 调用 yunxiao MCP 工具创建 MR:
   - title: `[<source>-<external_id>] <一句话描述>`
   - description: 用 docs/intake-protocol.cn.md § MR 描述模板填充
   - target branch: master 或 main（按项目实际）
   - labels: `from-zentao` / `from-arms` / `feat`（按场景）
7. 收到 MR URL 后，更新 intake frontmatter:
   - `status: in_review`
   - `mr_url: <url>`
   （用 Edit 工具修改 intake 文件的 frontmatter 块）
8. SendMessage 通知 team-lead: `"MR 已提交：<url>，等待人工合入"`

**任何一步失败 3 次都升级 team-lead，禁止静默重试**。

**git remote 必须已指向 Codeup**——SKILL.md Step 1.2.2 已校验，如果失败说明环境出了问题，停下报告。
```

- [ ] **Step 4: 在 frontend-dev onboarding 末尾追加同样的 MR 步骤段**

frontend-dev onboarding 做同样追加（与 backend-dev 完全相同——重复是有意的）。

- [ ] **Step 5: 验证三处 onboarding 都加上**

```bash
grep -c "## MR 提交流程" cn/skills/CCteam-creator-cn/references/onboarding.md
grep -c "## Bug Triage Onboarding" cn/skills/CCteam-creator-cn/references/onboarding.md
```

Expected: 第一条返回 `2`，第二条返回 `1`。

- [ ] **Step 6: 提交**

```bash
git add cn/skills/CCteam-creator-cn/references/onboarding.md
git commit -m "feat(cn/onboarding): add bug-triage onboarding + dev MR submission steps

bug-triage onboarding: defines trigger types (single/scan/replay),
intake file format (strict frontmatter), boundaries (read-only on code,
no direct dispatch), 3-strike handling.

backend-dev/frontend-dev: append step-by-step MR submission flow
(branch naming, push, yunxiao MCP MR creation, intake status update)."
```

---

## Task 4: cn — templates.md 加 CLAUDE.md 章节 + intake 文件模板

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/references/templates.md`

- [ ] **Step 1: 阅读 CLAUDE.md 模板找插入点**

读 templates.md，定位 CLAUDE.md 模板代码块（一个大的 ``` 包起来的 markdown）。识别：
- "Team Roster" 表 → 加 bug-triage 行（仅当团队选了它时）
- 模板末尾或合适位置 → 插入 `## Intake Processing Protocol` 节
- 模板末尾 → 插入 `## ARMS 巡检配置` 节（仅当启用了 cron）

- [ ] **Step 2: 在 Team Roster 表加 bug-triage 行（条件性）**

在表格末尾（custodian 之前或之后，按字母序或 read-only 分组）加：

```
| bug-triage | Bug Triage | sonnet | 拉外部 Bug/Error 数据 → 写 intake（read-only on code） |
```

并在表格上方说明里加一句："bug-triage 仅在用户在 SKILL.md Step 1.2.1 选择了'禅道/ARMS 集成'时才会出现在 roster 中。"

- [ ] **Step 3: 在 CLAUDE.md 模板尾部加 Intake Processing Protocol 章节**

在 CLAUDE.md 模板的 ``` 代码块结束之前，追加：

````markdown
## Intake Processing Protocol

> 仅当团队包含 bug-triage 角色时启用本节。

每次主会话启动 / compact 恢复后，team-lead **必须**:

1. 检查 `.plans/<project>/intake/` 目录是否存在
2. 列出所有 `status: pending` 的 intake 文件（用 grep 或读 frontmatter）
3. 用一段简洁汇报告诉用户:
   ```
   发现 <N> 个新 intake 待决策：
   - intake/zentao-12345.md  [P1] <一句话>
   - intake/arms-trace-abc.md [P2] <一句话>
   要我现在过一遍并提建议吗？
   ```
4. 用户决策的 4 条路径:
   - **Accept**: 创建 `.plans/<project>/<dev>/<source>-<id>/` task 文件夹，更新 intake `status: accepted` + `assigned_to` + `task_path`，SendMessage 派给 dev
   - **Reject**: 更新 `status: rejected` + `reject_reason`，文件保留供审计
   - **Merge**: 把 intake 内容追加到已有 task 的 findings.md，更新 `status: merged` + `merged_into`
   - **Defer**: 保持 `pending`，下次会话再决策
5. 处理完后，给用户一行总结（accepted N / rejected M / deferred K）

### intake 状态机

```
pending ──accept──→ accepted ──dev完成MR──→ in_review ──人工合入──→ done
   │                                              │
   ├──reject──→ rejected (终态)                   ├──MR 被拒/关闭──→ rejected (终态)
   │
   ├──merge──→ merged (终态，merged_into 指向真正的 task)
   │
   └──defer──→ 保持 pending
```

### 归档策略

- 终态 intake (`done` / `rejected` / `merged`) **保留** 供审计
- 超过 30 天的终态 intake 由 custodian 月度移到 `.plans/<project>/intake/_archive/`
- 没装 custodian 的小团队: team-lead 看到 intake/ 文件超过 50 个时，一次性提议归档
````

- [ ] **Step 4: 在 CLAUDE.md 模板尾部加 ARMS 巡检配置章节**

````markdown
## ARMS 巡检配置

> 仅当 SKILL.md Step 1.2.3 启用了 ARMS 巡检时填充。

- **schedule**: `0 9 * * *`（cron 表达式，可改）
- **project_id**: `<ARMS 项目标识>`
- **severity_threshold**: P0 + P1（可改）
- **CronCreate task ID**: `<创建后填入>`

巡检触发链路、参数说明详见 SKILL.md § Intake Processing Protocol 和 docs/intake-protocol.cn.md。
````

- [ ] **Step 5: 在 templates.md 尾部加 intake 文件模板章节**

在文件末尾追加新章节：

````markdown
## Intake 文件模板

由 bug-triage 在写新 intake 文件时使用。路径: `.plans/<project>/intake/<source>-<external_id>.md`。

```markdown
---
source: zentao | arms
external_id: 12345 | trace-abc123
severity: P0 | P1 | P2 | P3
created_at: 2026-05-10T10:30:00+08:00
status: pending
external_link: https://zentao.example.com/bug-12345
---

## 现象
[一句话描述]

## 重现步骤 / 错误堆栈
[禅道里的重现步骤 OR ARMS 的堆栈+trace]

## 影响范围
[受影响用户/接口/功能]

## 相关代码模块（triage 的猜测）
- src/auth/login.ts:42
- src/middleware/session.ts

## 候选修复方向
[1-2 个可能的入手点，让 dev 不用从零开始]

## 原始数据
[完整的禅道 Bug 字段 / ARMS 错误事件 JSON]
```

### 后续状态新增的字段

当状态从 pending 演进时，team-lead/dev 在 frontmatter 追加:

- `assigned_to: <agent-name>` (accept 时)
- `task_path: .plans/<project>/<dev>/<source>-<id>/` (accept 时)
- `mr_url: <url>` (in_review 时)
- `merged_into: <existing-task-path>` (merge 时)
- `reject_reason: <一句话>` (reject 时)

### last-scan.txt 格式

由 bug-triage 维护，路径 `.plans/<project>/bug-triage/last-scan.txt`。
- 单行
- ISO 时间戳带时区，例如 `2026-05-10T15:30:42+08:00`
- 每次扫描成功完成后写入（覆盖）
- 用于下次扫描的 `since` 参数默认值
````

- [ ] **Step 6: 验证三段都已添加**

```bash
grep -c "## Intake Processing Protocol" cn/skills/CCteam-creator-cn/references/templates.md
grep -c "## ARMS 巡检配置" cn/skills/CCteam-creator-cn/references/templates.md
grep -c "## Intake 文件模板" cn/skills/CCteam-creator-cn/references/templates.md
```

Expected: 三条都返回 `1`。

- [ ] **Step 7: 提交**

```bash
git add cn/skills/CCteam-creator-cn/references/templates.md
git commit -m "feat(cn/templates): add intake protocol + ARMS config + intake file template

- CLAUDE.md template: add Intake Processing Protocol (state machine,
  team-lead boot-time scan, 4 decision paths, archival policy)
- CLAUDE.md template: add ARMS scan config section
- New section: Intake file template + last-scan.txt format

These let team-lead and bug-triage work consistently across sessions."
```

---

## Task 5: cn — 创建 mcp-setup.md（MCP 安装指南）

**Files:**
- Create: `cn/skills/CCteam-creator-cn/references/mcp-setup.md`

- [ ] **Step 1: 写完整的 mcp-setup.md**

```markdown
# MCP 配置指南

> 本文档面向**首次配置** CCteam-creator 阿里云集成的用户。一次性操作，配置完成后 skill 流程会自动校验。

## 必装 MCP 清单

| MCP | 用途 | 必须 vs 可选 |
|-----|------|-------------|
| `alibabacloud-devops-mcp-server` (云效) | dev 提 MR 到 Codeup | 启用 Codeup 集成时必须 |
| `zentao-mcp-server` (禅道) | bug-triage 拉禅道 Bug 单 | 启用禅道触发源时必须 |
| `mcp-server-aliyun-observability` (阿里云观测) | bug-triage 查 ARMS 错误事件 | 启用 ARMS 巡检时必须 |

## 1. 云效 (Yunxiao) MCP

### 1.1 获取 access token

1. 登录云效 → 个人设置 → 个人访问令牌
2. 创建 token，勾选权限: 代码管理（读+写）+ 项目管理（读+写）
3. 复制 token（只显示一次，妥善保存）

### 1.2 添加到 Claude Code MCP 配置

编辑 `~/.claude/mcp.json` 或项目级 `.mcp.json`，加入：

```json
{
  "mcpServers": {
    "yunxiao": {
      "command": "npx",
      "args": ["-y", "alibabacloud-devops-mcp-server"],
      "env": {
        "YUNXIAO_ACCESS_TOKEN": "<你的 token>",
        "YUNXIAO_API_BASE_URL": "https://openapi-rdc.aliyuncs.com"
      }
    }
  }
}
```

如果你用的是 Region 版云效（专属域名），把 `YUNXIAO_API_BASE_URL` 改成 `https://<your-org>.devops.aliyuncs.com`。

### 1.3 验证连通

重启 Claude Code，在主对话里说: "用 yunxiao 工具列出我的项目"。应能返回项目列表。

## 2. 禅道 (ZenTao) MCP

### 2.1 准备账号

需要禅道账号（开发者权限即可），知道你的禅道 URL（如 `https://zentao.your-company.com`）。

### 2.2 添加 MCP 配置

编辑 `~/.claude/mcp.json`：

```json
{
  "mcpServers": {
    "zentao": {
      "command": "npx",
      "args": ["-y", "zentao-mcp-server"],
      "env": {
        "ZENTAO_URL": "https://zentao.your-company.com",
        "ZENTAO_ACCOUNT": "<用户名>",
        "ZENTAO_PASSWORD": "<密码>",
        "ZENTAO_SKIP_SSL": "false"
      }
    }
  }
}
```

> **安全提醒**: 不要把 `~/.claude/mcp.json` 提交到 git。如果项目用 `.mcp.json`（项目级），加到 .gitignore。

### 2.3 验证连通

主对话: "用 zentao 工具列出最近的 5 个 bug"。

## 3. 阿里云观测 (Observability) MCP（用于 ARMS）

> **前置依赖**: 安装 [uv](https://github.com/astral-sh/uv)——此 MCP 是 Python 包，通过 `uvx` 运行：
> `curl -LsSf https://astral.sh/uv/install.sh | sh`
> 验证: `uvx --version`

### 3.1 准备 AccessKey

1. 阿里云控制台 → AccessKey 管理 → 创建 AccessKey（建议用 RAM 子用户，不要用主账号）
2. 给 RAM 用户授权 `AliyunARMSReadOnlyAccess`（最小权限）
3. 记录 AccessKey ID + AccessKey Secret

### 3.2 添加 MCP 配置

```json
{
  "mcpServers": {
    "aliyun-observability": {
      "command": "uvx",
      "args": ["mcp-server-aliyun-observability", "--transport", "stdio"],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "<你的 AK ID>",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "<你的 AK Secret>",
        "ALIBABA_CLOUD_REGION_ID": "cn-hangzhou"
      }
    }
  }
}
```

> **已验证可用**: PyPI 包 `mcp-server-aliyun-observability` v1.0.8+——覆盖 ARMS / SLS / 应用实时监控。最新版本见 https://pypi.org/project/mcp-server-aliyun-observability/。

### 3.3 验证连通

主对话: "用 aliyun-observability 工具查询 ARMS 应用列表，region cn-hangzhou"。

## 4. Codeup git remote 配置

dev 提 MR 之前，项目本地仓库必须已绑定 Codeup 远程：

```bash
cd <你的项目根目录>
git remote add origin https://codeup.aliyun.com/<org>/<repo>.git
# 或 SSH: git remote add origin git@codeup.aliyun.com:<org>/<repo>.git
git push --dry-run  # 验证凭证
```

如果用 HTTPS，需要在云效个人设置里生成 Git 凭证。

## 5. 集成自检脚本

CCteam-creator SKILL.md Step 1.2.2 会逐项校验。如果你想在 setup 之前手动确认，跑：

```bash
# 1. 确认 ~/.claude/mcp.json 存在并包含上述三项
cat ~/.claude/mcp.json | python3 -m json.tool

# 2. 确认项目目录 git remote 已配
git -C <project-dir> remote -v | grep codeup

# 3. 让 Claude Code 列工具，确认三个 MCP 都加载成功
# 在主对话说: "列出当前可用的 MCP 工具"
```

## 常见问题

**Q: 我只想试集成一两个工具，必须三个都装吗？**
A: 不必。只要禅道集成 → 装 zentao MCP；只要 Codeup 提 MR → 装云效 MCP；要 ARMS 巡检 → 装阿里云 OpenAPI MCP。SKILL.md Step 1.2.1 会按需校验。

**Q: zentao MCP 第三方维护，安全吗？**
A: 它需要禅道账号密码 → 数据流向: 你的本地 npx 进程 → 你的禅道服务器（局域网/内网）。不出本地。但建议:
- 用专门的低权限禅道账号
- 不把密码提交到 git
- 定期 rotate

**Q: ARMS 巡检会不会消耗大量 API 调用？**
A: bug-triage 每次扫描调 1-3 次 API（list 错误事件 + 可能查 trace 详情）。一天一次的话，月度 API 调用在 100 次量级，不会触发限流。
```

- [ ] **Step 2: 验证文件创建**

```bash
ls -l cn/skills/CCteam-creator-cn/references/mcp-setup.md
wc -l cn/skills/CCteam-creator-cn/references/mcp-setup.md
```

Expected: 文件存在，行数 ~150-200。

- [ ] **Step 3: 提交**

```bash
git add cn/skills/CCteam-creator-cn/references/mcp-setup.md
git commit -m "feat(cn): add mcp-setup.md — first-time MCP install guide

Covers Yunxiao MCP / Zentao MCP / Aliyun API MCP (ARMS) install,
auth, env vars, and connectivity self-check. Includes Codeup git
remote setup. FAQ for common confusion points."
```

---

## Task 6: cn — SKILL.md 改造（Step 1.2.1/1.2.2/1.2.3 + 角色推荐）

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/SKILL.md`

- [ ] **Step 1: 阅读 SKILL.md 找插入点**

读 `cn/skills/CCteam-creator-cn/SKILL.md`，识别：
- "1.2 收集用户需求" 章节末尾 → 插入 1.2.1
- "1.3 推荐团队配置" 章节里的角色表 → 加 bug-triage 行（条件性提示）

- [ ] **Step 2: 在 1.2 末尾、1.3 之前插入 1.2.1 / 1.2.2 / 1.2.3**

```markdown
### 1.2.1 外部系统集成（如适用）

询问用户三个问题（自然对话，不必逐字念）:

1. 是否需要从禅道拉 Bug 单作为开发输入？
2. 是否需要从 ARMS 拉错误事件作为开发输入？
3. 是否需要让 dev 把代码推到云效 Codeup + 自动提 MR？

> **判断指引**: 如果用户在 1.2 提到"内部使用"、"公司在用阿里云"、"和现有 DevOps 流程联动"等线索，主动问起这三项；否则可以一句话扫过、看用户态度。

任一为 "是" → 走 1.2.2 校验对应 MCP 已就位。
全为 "否" → 跳过 1.2.2 / 1.2.3，按上游标准流程走 1.3。

### 1.2.2 MCP 校验（仅当 1.2.1 任一选 "是" 时执行）

对用户回答 "是" 的每一个集成项，校验 MCP 已配置:

| 集成项 | 校验方法 |
|--------|---------|
| 禅道 | 让用户运行 `cat ~/.claude/mcp.json \| grep zentao`；或主对话里说"列出 zentao 工具"看是否返回工具列表 |
| ARMS | 同上，查 aliyun-observability MCP |
| Codeup | 1. 同上查 yunxiao MCP；2. `git -C <project> remote -v` 看是否有 codeup 远程 |

**任一项缺失** → 停在此步，引用 `references/mcp-setup.md`，让用户先装好再回来继续。**绝不**在缺失依赖的情况下创建团队，否则 bug-triage 会立刻失败。

### 1.2.3 是否启用 ARMS 定时巡检（仅当 1.2.1 选了 ARMS 时执行）

询问用户:
- 是否要每天自动巡检 ARMS 错误并落 intake？
- 巡检时间: 默认 `0 9 * * *`（每天 9:00），可改
- ARMS 项目 ID: 用户从 ARMS 控制台复制
- 严重级阈值: 默认 P0 + P1（用户可放宽到 P2）

如启用:
1. 用 `CronCreate` 创建任务（详细参数见 references/templates.md § ARMS 巡检配置）
2. 把配置写入即将生成的 CLAUDE.md（在 Step 3.5 阶段）
3. 把 CronCreate 返回的 task ID 也写入 CLAUDE.md，方便用户日后管理

不启用 → 跳过，用户只能靠手动 `/ccteam-scan` 触发。
```

- [ ] **Step 3: 在 1.3 推荐角色的列表里加 bug-triage 条目**

定位 1.3 的角色推荐表或列表。在合适位置（researcher 之后、reviewer 之前是合理的）加：

```
| Bug Triage | bug-triage | sonnet | 拉外部 Bug/Error → intake，仅当 1.2.1 选了禅道或 ARMS 时推荐 |
```

并在表格下方原"推荐原则"段落里追加一条：

```
- bug-triage 是 1.2.1 选项的下游产物——只在确认 MCP 都到位、且团队需要外部触发源时纳入；不要在没有外部集成需求的项目里加它，会变成空跑的角色
```

- [ ] **Step 4: 在 SKILL.md 顶部"Process"流程列表里加一行说明**

定位 SKILL.md 顶部的 Process 步骤总览（Step 0/1/2/3 那种汇总），在 Step 1 那行下加注：

```
1. **Requirements Consultation** — 介绍机制 + 收集需求；**如启用阿里云生态集成，会触发 1.2.1/1.2.2/1.2.3 子流程**
```

- [ ] **Step 5: 在 SKILL.md 末尾或 Key Rules 章节加一条规则**

```
- **External integration gates**: 启用禅道/ARMS/Codeup 集成的项目，setup 必须先过 Step 1.2.2 MCP 校验；任何缺失依赖都禁止往后走，否则 bug-triage 与 dev 的 MR 流程会在运行时失败
```

- [ ] **Step 6: 验证四处改动都生效**

```bash
grep -c "1.2.1 外部系统集成" cn/skills/CCteam-creator-cn/SKILL.md
grep -c "1.2.2 MCP 校验" cn/skills/CCteam-creator-cn/SKILL.md
grep -c "1.2.3 是否启用 ARMS" cn/skills/CCteam-creator-cn/SKILL.md
grep -c "Bug Triage" cn/skills/CCteam-creator-cn/SKILL.md
grep -c "External integration gates" cn/skills/CCteam-creator-cn/SKILL.md
```

Expected: 五条都至少返回 `1`。

- [ ] **Step 7: 提交**

```bash
git add cn/skills/CCteam-creator-cn/SKILL.md
git commit -m "feat(cn/SKILL): add Step 1.2.1/1.2.2/1.2.3 for Aliyun integration

Step 1.2.1: ask whether to integrate Zentao/ARMS/Codeup
Step 1.2.2: validate corresponding MCPs are installed (hard gate)
Step 1.2.3: optionally configure ARMS scheduled scan via CronCreate

Also: add bug-triage to role recommendation table (conditional on 1.2.1)
and add 'External integration gates' to Key Rules."
```

---

## Task 7: 创建 commands/ccteam-scan.md 斜杠命令

**Files:**
- Create: `commands/ccteam-scan.md`

- [ ] **Step 1: 确认目录不存在则创建**

```bash
ls commands/ 2>&1 || mkdir commands
```

- [ ] **Step 2: 创建 ccteam-scan.md**

```markdown
---
description: 立即触发 bug-triage，扫描 ARMS 错误（或禅道 Bug）并落 intake
---

立即执行一次外部系统巡检。team-lead 请按以下步骤操作:

1. **解析参数**（从用户附带的自然语言中识别）:
   - `source`: 默认 `arms`，用户可指定 `zentao`
   - `project_id`: 默认从 CLAUDE.md `## ARMS 巡检配置` 节读取，用户可临时覆盖
   - `since`: 默认从 `.plans/<project>/bug-triage/last-scan.txt` 读取（首次为 24h 前）
   - `severity_threshold`: 默认 P0 + P1，用户可放宽（如 "把 P2 也带上"）

2. **校验 bug-triage 是否在团队中**:
   - 团队还在 → SendMessage(to: "bug-triage", message: <见 §3>)
   - 团队已 retire（`.plans/<project>/team-snapshot.md` 不存在或团队已结束）→ 临时 spawn:
     ```
     Agent(subagent_type: "general-purpose", prompt: <bug-triage onboarding 简版 + 本次任务>, run_in_background: false)
     ```

3. **派发消息模板**:
   ```
   立即巡检任务:
   - source: <解析得到>
   - project_id: <解析得到>
   - since: <解析得到>
   - severity_threshold: <解析得到>
   
   完成后回报新增的 intake 文件清单（路径 + severity + 一句话）。
   ```

4. **接收回报后**:
   - 把新增的 intake 数量、最高严重级简报给用户
   - 提示用户可走 `## Intake Processing Protocol` 对每条决策

**注意**: 此命令不替代 cron 自动巡检，仅供"现在我想立刻看一次"的场景。频繁手动调用可能让 ARMS API 配额吃紧。
```

- [ ] **Step 3: 验证文件**

```bash
ls -l commands/ccteam-scan.md
head -3 commands/ccteam-scan.md
```

Expected: 文件存在，前 3 行包含 `description:` frontmatter。

- [ ] **Step 4: 提交**

```bash
git add commands/ccteam-scan.md
git commit -m "feat(commands): add /ccteam-scan slash command

Triggers bug-triage to scan ARMS (or Zentao) immediately.
Parses source/project_id/since/severity from natural language.
Falls back to spawning bug-triage if team has retired."
```

---

## Task 8: 创建 docs/intake-protocol.cn.md（用户操作手册）

**Files:**
- Create: `docs/intake-protocol.cn.md`

- [ ] **Step 1: 写文档**

```markdown
# Intake 协议 — 用户操作手册

> 本文档面向**人类用户**，解释 intake 状态机、字段含义，以及你需要手动操作的场景。
> 给 agent 看的协议在 `cn/skills/CCteam-creator-cn/references/templates.md § Intake Processing Protocol`。

## 什么是 intake

外部世界（禅道 Bug / ARMS 错误）进入 CCteam 的"门口快递单"。bug-triage 每次拉到新数据，会写一个 intake 文件落到 `.plans/<project>/intake/<source>-<id>.md`。

intake 不等于"已立项的任务"。它是**候选 task 池**——团队负责人 (team-lead) 看完后才决定是否立项。

## 状态机

```
pending ──accept──→ accepted ──dev完成MR──→ in_review ──人工合入──→ done
   │                                              │
   ├──reject──→ rejected (终态)                   ├──MR 被拒/关闭──→ rejected (终态)
   │
   ├──merge──→ merged (终态)
   │
   └──defer──→ 保持 pending
```

| 状态 | 含义 | 谁触发 |
|------|------|--------|
| `pending` | 已落盘，等 team-lead 决策 | bug-triage 写入时 |
| `accepted` | 已立项，task 文件夹已建 | team-lead |
| `in_review` | dev 已完成 + MR 已提，等人工合入 | dev |
| `done` | MR 已合入 | team-lead 手工 / 你告诉它"已合入了" |
| `rejected` | 决定不修（含 MR 被拒） | team-lead |
| `merged` | 合并到已有 task | team-lead |

## frontmatter 字段

```yaml
---
source: zentao | arms       # 来源
external_id: 12345          # 外部系统的 ID
severity: P0|P1|P2|P3       # 严重级
created_at: 2026-05-10T10:30:00+08:00
status: pending             # 当前状态
external_link: https://...  # 跳转原始系统的链接
---
```

状态从 pending 演进时 frontmatter 会追加:
- `assigned_to: <agent>` — accept 时
- `task_path: ...` — accept 时
- `mr_url: <url>` — in_review 时
- `merged_into: ...` — merge 时
- `reject_reason: <一句话>` — reject 时

## 你需要手动操作的场景

### 1. 早上打开 Claude Code

team-lead 会主动汇报新 intake，告诉你 N 个待决策。**直接对它说**就行：
- "1 号 accept、2 号 reject 因为不是 bug 是用户误操作、3 号 defer"
- 或直接 "都过一遍并给我建议"

### 2. MR 合入后告诉团队

人工把 MR 合入 Codeup 之后，回到 Claude Code 说一句：
- "禅道 12345 的 MR 已合入"
team-lead 会更新对应 intake 的 `status: done`。

### 3. 想看历史某个 intake

```bash
ls .plans/<project>/intake/
cat .plans/<project>/intake/<source>-<id>.md
```

或直接对 team-lead 说"展示 intake/<id> 的状态"。

### 4. intake 太多想清理

终态 intake (`done` / `rejected` / `merged`) 默认保留供审计。如果文件多到影响导航：
- 有 custodian 角色 → "请 custodian 归档 30 天前的终态 intake"
- 没 custodian → 你直接说 "归档 30 天前的终态 intake"，team-lead 会移到 `_archive/`

## 立即手动巡检

不想等明早 9 点，现在就要扫一次：
- 斜杠命令: `/ccteam-scan`
- 或自然语言: "立即巡检"、"扫一下 ARMS"、"现在看看新错误"

参数可临时覆盖：
- "扫一下禅道" — 把数据源改成禅道
- "扫最近 7 天" — 扩大时间窗口
- "把 P2 也带上" — 放宽严重级阈值

## 常见问题

**Q: bug-triage 为什么不直接派单给 dev？**
A: 故意不直接派——ARMS 的"错误"很多是噪声（404、用户输入错误、第三方临时故障）。先落 intake 让你过一遍，避免团队被自动派单淹没。

**Q: 我能手动改 intake 文件吗？**
A: 可以，但建议改完告诉 team-lead 一声"我手动把 intake 12345 改成 rejected 了"，免得它下次扫描时被你的修改困惑。

**Q: 同一个 bug 在禅道和 ARMS 都被抓到了，会重复处理吗？**
A: 当前版本是两个独立 intake（zentao-12345.md + arms-trace-abc.md）。team-lead 看到时可以手动 merge 一个到另一个。后期可能加跨源融合，目前暂未做。
```

- [ ] **Step 2: 验证文件**

```bash
wc -l docs/intake-protocol.cn.md
```

Expected: 100+ 行。

- [ ] **Step 3: 提交**

```bash
git add docs/intake-protocol.cn.md
git commit -m "docs: add intake-protocol.cn.md user manual

Explains state machine, frontmatter fields, manual operations
(morning triage, post-merge cleanup, archive), and FAQ.
Counterpart to templates.md § Intake Processing Protocol (which
targets agents)."
```

---

## Task 9: 更新 plugin.json + marketplace.json

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: 改 plugin.json**

读现有 `.claude-plugin/plugin.json`，整体替换为:

```json
{
  "name": "CCteam-creator",
  "description": "Multi-agent team orchestration for Claude Code, with native Aliyun ecosystem integration (Yunxiao Codeup MR / Zentao bug intake / ARMS error monitoring).",
  "version": "0.1.0",
  "author": {
    "name": "motou"
  },
  "license": "MIT",
  "keywords": [
    "claude-code",
    "agent-teams",
    "multi-agent",
    "orchestration",
    "planning",
    "skills",
    "aliyun",
    "yunxiao",
    "zentao",
    "arms"
  ]
}
```

注: `homepage` 字段暂不填（你的远程仓库地址定了再补）。

- [ ] **Step 2: 校验 plugin.json 是合法 JSON**

```bash
python3 -m json.tool < .claude-plugin/plugin.json
```

Expected: 无错误，输出格式化后的 JSON。

- [ ] **Step 3: 改 marketplace.json**

```json
{
  "name": "ccteam",
  "owner": {
    "name": "motou"
  },
  "metadata": {
    "description": "Multi-agent team orchestration plugins for Claude Code, with Aliyun ecosystem integration.",
    "version": "0.1.0"
  },
  "plugins": [
    {
      "name": "CCteam-creator",
      "source": "./",
      "description": "Multi-agent team orchestration for Claude Code (English)"
    },
    {
      "name": "CCteam-creator-cn",
      "source": "./cn",
      "description": "Multi-agent team orchestration for Claude Code (Chinese)"
    }
  ]
}
```

- [ ] **Step 4: 校验**

```bash
python3 -m json.tool < .claude-plugin/marketplace.json
```

Expected: 无错误。

- [ ] **Step 5: 提交**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump to 0.1.0 — fork rebranded with Aliyun integration

- plugin.json: version 1.4.3 → 0.1.0 (fresh start), author → motou,
  description updated, keywords add aliyun/yunxiao/zentao/arms
- marketplace.json: version 0.1.0, owner → motou, description updated"
```

---

## Task 10: 更新 README_CN.md + 创建 CHANGELOG.md + 改 LICENSE

**Files:**
- Modify: `README_CN.md`
- Create: `CHANGELOG.md`
- Modify: `LICENSE`

- [ ] **Step 1: 在 README_CN.md 顶部加 fork 说明 + 新能力段**

读现有 README_CN.md。在最顶部标题下方、目录之前，插入：

```markdown
> 基于 [jessepwj/CCteam-creator](https://github.com/jessepwj/CCteam-creator) v1.4.3 演进，新增阿里云生态集成（云效 Codeup MR 自动提交 / 禅道 Bug 单 intake / ARMS 错误巡检）。

## 0.1.0 新增能力

- **`bug-triage` 角色**: 拉禅道 Bug 单 / ARMS 错误事件 → 落到 `.plans/<project>/intake/` 候选池
- **dev MR 自动提交**: 评审通过后自动 git push + 调用云效 MCP 创建 MR
- **`/ccteam-scan` 斜杠命令**: 立即触发巡检
- **CronCreate 定时巡检**: 默认每天 9:00 扫 ARMS 错误
- **Intake Processing Protocol**: 6 状态机 + team-lead 主动汇报

详见 [设计文档](docs/superpowers/specs/2026-05-10-ccteam-aliyun-design.md) 和 [intake 用户手册](docs/intake-protocol.cn.md)。
```

- [ ] **Step 2: 创建 CHANGELOG.md**

```markdown
# CHANGELOG

## 0.1.0 - 2026-05-10

> Forked from jessepwj/CCteam-creator v1.4.3, rebooted as 0.1.0 with Aliyun ecosystem integration.
> 从 jessepwj/CCteam-creator v1.4.3 fork 出来，重置为 0.1.0，新增阿里云生态集成。

### Added / 新增
- New role `bug-triage` (read-only): pulls Zentao bugs and ARMS error events, writes structured intake files.
  新增 `bug-triage` 角色（只读）：拉禅道 Bug 单和 ARMS 错误事件，写结构化 intake 文件。
- Dev role MR Submission Protocol: auto git push + Yunxiao MCP MR creation after reviewer [OK].
  dev 角色 MR 提交协议：reviewer [OK] 后自动 git push + 调用云效 MCP 创建 MR。
- `/ccteam-scan` slash command for on-demand external scan.
  `/ccteam-scan` 斜杠命令，按需立即巡检。
- CronCreate-based ARMS scheduled scan (default 0 9 * * *).
  基于 CronCreate 的 ARMS 定时巡检（默认每天 9:00）。
- Intake Processing Protocol with 6-state machine (pending/accepted/in_review/done/rejected/merged).
  Intake 处理协议，6 状态机（pending/accepted/in_review/done/rejected/merged）。
- New SKILL.md sub-steps 1.2.1/1.2.2/1.2.3 for integration setup gating.
  SKILL.md 新增子步骤 1.2.1/1.2.2/1.2.3，集成 setup 门控。
- New reference: `references/mcp-setup.md` (MCP install + auth + self-check).
  新增参考文档：`references/mcp-setup.md`（MCP 安装 + 鉴权 + 自检）。
- New user doc: `docs/intake-protocol.cn.md` (state machine + manual ops manual).
  新增用户文档：`docs/intake-protocol.cn.md`（状态机 + 手动操作手册）。

### Changed / 变更
- plugin.json: name unchanged, version 1.4.3 → 0.1.0, author → motou.
  plugin.json：name 不变，version 1.4.3 → 0.1.0，author → motou。
- marketplace.json: same metadata adjustments.
  marketplace.json：同步元信息调整。

### Not in this release / 不在本期
- Phase 2: local HTTP gateway bridging external triggers.
  Phase 2: 本地 HTTP 网关，桥接外部触发。
- Phase 3: Chrome extension injecting buttons into Zentao/ARMS pages.
  Phase 3: Chrome 浏览器插件，注入按钮到禅道/ARMS 页面。
- Auto write-back to Zentao on Bug closure.
  Bug 合入后自动回写禅道关闭。
- ARMS post-deploy verification loop.
  ARMS 上线后验证回路。
```

- [ ] **Step 3: 在 LICENSE 顶部加 fork 归属**

读 LICENSE。在 MIT 协议正文最顶部、`MIT License` 标题之前，加：

```
Forked from jessepwj/CCteam-creator (MIT) — extended for Aliyun ecosystem integration.
Original copyright preserved below.

```

(注意结尾有空行分隔)

- [ ] **Step 4: 验证三个文件**

```bash
head -10 README_CN.md
ls -l CHANGELOG.md
head -5 LICENSE
```

Expected: README_CN.md 顶部出现 fork 说明；CHANGELOG.md 存在；LICENSE 顶部出现归属行。

- [ ] **Step 5: 提交**

```bash
git add README_CN.md CHANGELOG.md LICENSE
git commit -m "docs: add fork attribution + 0.1.0 changelog + README highlights

- README_CN: fork attribution + 0.1.0 new-features section at top
- CHANGELOG.md: bilingual entry for 0.1.0
- LICENSE: preserve MIT, add fork attribution at top"
```

---

## Task 11: cn smoke test（手动验证）

**Files:** 无修改，仅人工验证

> 本任务**不能省**。前面 10 个 task 都是文档/配置，没有自动化测试可以验证整体走通。需要在一个临时项目上跑一遍 cn skill 的完整流程，记录任何出问题的地方。

- [ ] **Step 1: 在临时目录建一个空项目**

```bash
mkdir -p /tmp/ccteam-smoke && cd /tmp/ccteam-smoke
git init
mkdir -p src && echo "# smoke test project" > README.md
git add . && git commit -m "init"
```

- [ ] **Step 2: 启动一个新的 Claude Code 会话指向该目录**

进入 `/tmp/ccteam-smoke` 目录，启动 claude。**确保已安装本地 CCteam-creator-cn fork**（用 `/plugin marketplace add /Users/motou/Desktop/CCteam-creator` 然后 install ccteam）。

- [ ] **Step 3: 触发 skill，按对话引导走完 Step 1**

主对话: "帮我组个团队做这个项目"。验证清单:
- [ ] team-lead 询问项目类型、用户语言（应识别中文）
- [ ] team-lead 主动问 1.2.1 三个集成问题
- [ ] 选 "都不要" → 跳过 1.2.2/1.2.3，按上游标准走（应等同于上游行为）
- [ ] 重新触发，选 "禅道集成" → 进入 1.2.2，验证 MCP 校验逻辑（如果未装会被拦截）
- [ ] 选 "ARMS 巡检" + 启用 cron → 进入 1.2.3，team-lead 应用 CronCreate 创建任务

- [ ] **Step 4: 验证 bug-triage 角色定义被 team-lead 正确识别**

让 team-lead 推荐角色（1.3）。验证:
- [ ] bug-triage 出现在推荐表
- [ ] team-lead 解释 bug-triage 何时纳入

- [ ] **Step 5: 验证 CLAUDE.md 模板正确填充**

让 team-lead 完成 setup（Step 3.5 生成 CLAUDE.md）。打开生成的 CLAUDE.md:
- [ ] 包含 `## Intake Processing Protocol` 章节
- [ ] 如启用了 ARMS 巡检，包含 `## ARMS 巡检配置` 章节
- [ ] Team Roster 表正确列出 bug-triage（如选了）

- [ ] **Step 6: 验证 `/ccteam-scan` 斜杠命令可用**

在主对话敲 `/ccteam-scan`。验证:
- [ ] Claude Code 识别该斜杠命令并加载内容
- [ ] team-lead 按命令内容尝试派发 bug-triage

- [ ] **Step 7: 记录所有问题**

把发现的 bug、措辞模糊、流程卡顿写到一份文件:

```bash
cat > /tmp/ccteam-smoke/SMOKE_NOTES.md <<'EOF'
# cn Smoke Test Notes

(在这里记录每一项发现的问题: 在哪一步、症状、可能原因)
EOF
```

- [ ] **Step 8: 修复发现的关键问题（在 fork 目录）**

回到 `/Users/motou/Desktop/CCteam-creator`，针对 SMOKE_NOTES.md 中的每个问题：
- 改对应文件
- 提交一个 `fix(cn): <issue>` 风格的 commit

修复后**重新跑 Step 3-6**确认问题解决。

- [ ] **Step 9: 清理临时目录**

```bash
rm -rf /tmp/ccteam-smoke
```

> 修复完成 + smoke test 全过 → 才进入 Task 12。如果 smoke test 暴露了**spec 层面**的设计问题（不是文档错字），停下回到 spec 修订，重新评估 plan。

---

## Task 12: en — 镜像 cn roles.md

**Files:**
- Modify: `skills/CCteam-creator/references/roles.md`

> 此任务及后续 Task 13-16 是把 cn 已验证的内容翻译成英文，结构 1:1 对齐。**不要在英文版引入新逻辑**——发现 cn 错就回去改 cn，再来 mirror。

- [ ] **Step 1: 比照 cn/roles.md 找出 Task 2 加的所有段落**

```bash
git diff master...HEAD -- cn/skills/CCteam-creator-cn/references/roles.md
```

读 diff，识别需要镜像的内容: Bug Triage 章节 + 两处 MR Submission Protocol。

- [ ] **Step 2: 在 en/roles.md 同位置插入英译版本**

英译时保留以下原则：
- 角色名、文件路径、frontmatter 字段名、MCP 包名: 原样不译
- "外部世界 ↔ CCteam 之间的翻译官": → "Translator between the external world and CCteam"
- "MR Submission Protocol": 保留英文，cn 版用的是英文术语
- 命令模板（commit message / MR description）: 改为英文（"关联" → "Related to:" 等）

完整英译内容参考 spec §2-§3，结构与 cn 版一一对应。

- [ ] **Step 3: 验证两处 MR + bug-triage 章节齐全**

```bash
grep -c "Bug Triage (bug-triage)" skills/CCteam-creator/references/roles.md
grep -c "MR Submission Protocol" skills/CCteam-creator/references/roles.md
```

Expected: 第一条 1，第二条 2。

- [ ] **Step 4: 提交**

```bash
git add skills/CCteam-creator/references/roles.md
git commit -m "feat(en/roles): mirror cn — bug-triage role + dev MR protocol"
```

---

## Task 13: en — 镜像 cn onboarding.md

**Files:**
- Modify: `skills/CCteam-creator/references/onboarding.md`

- [ ] **Step 1: diff cn 版本找改动**

```bash
git diff master...HEAD -- cn/skills/CCteam-creator-cn/references/onboarding.md
```

- [ ] **Step 2: 在 en/onboarding.md 同位置插入英译**

主要内容 = bug-triage onboarding + 两处 dev MR 步骤段。术语保持 spec 一致（intake / trigger / scan / etc）。

- [ ] **Step 3: 验证**

```bash
grep -c "Bug Triage Onboarding" skills/CCteam-creator/references/onboarding.md
grep -c "MR Submission Flow" skills/CCteam-creator/references/onboarding.md  # 英文段落标题
```

Expected: 第一条 1，第二条 2。（如果你用了别的英文标题，调整 grep 关键词）

- [ ] **Step 4: 提交**

```bash
git add skills/CCteam-creator/references/onboarding.md
git commit -m "feat(en/onboarding): mirror cn — bug-triage + dev MR steps"
```

---

## Task 14: en — 镜像 cn templates.md

**Files:**
- Modify: `skills/CCteam-creator/references/templates.md`

- [ ] **Step 1-3: diff、镜像、验证（同 Task 13 模式）**

需镜像的三段:
- CLAUDE.md 模板的 `## Intake Processing Protocol` 节
- CLAUDE.md 模板的 `## ARMS Scan Config` 节
- 文件末尾的 `## Intake File Template` 节

- [ ] **Step 4: 验证**

```bash
grep -c "Intake Processing Protocol" skills/CCteam-creator/references/templates.md
grep -c "ARMS Scan Config" skills/CCteam-creator/references/templates.md
grep -c "Intake File Template" skills/CCteam-creator/references/templates.md
```

Expected: 三条都至少 1。

- [ ] **Step 5: 提交**

```bash
git add skills/CCteam-creator/references/templates.md
git commit -m "feat(en/templates): mirror cn — intake protocol + ARMS config + template"
```

---

## Task 15: en — 创建 mcp-setup.md（英文版）

**Files:**
- Create: `skills/CCteam-creator/references/mcp-setup.md`

- [ ] **Step 1: 翻译 cn/mcp-setup.md 到英文**

读 `cn/skills/CCteam-creator-cn/references/mcp-setup.md`，逐节译为英文。技术细节、URL、env 变量名、JSON 配置一字不改。

英译注意：
- "禅道" → "Zentao"
- "云效" → "Yunxiao"
- "阿里云" → "Aliyun" (品牌名)
- 警示框（"安全提醒"等）保留 markdown 格式，措辞自然化

- [ ] **Step 2: 验证**

```bash
wc -l skills/CCteam-creator/references/mcp-setup.md
diff <(grep -c '^##' cn/skills/CCteam-creator-cn/references/mcp-setup.md) <(grep -c '^##' skills/CCteam-creator/references/mcp-setup.md)
```

Expected: 行数相近；二级标题数量相同（结构对齐）。

- [ ] **Step 3: 提交**

```bash
git add skills/CCteam-creator/references/mcp-setup.md
git commit -m "feat(en): add mcp-setup.md (English mirror of cn version)"
```

---

## Task 16: en — 镜像 SKILL.md + README + intake-protocol

**Files:**
- Modify: `skills/CCteam-creator/SKILL.md`
- Modify: `README.md`
- Create: `docs/intake-protocol.md`

- [ ] **Step 1: 镜像 SKILL.md（同 Task 13 模式）**

把 cn/SKILL.md 中 Task 6 加的 Step 1.2.1/1.2.2/1.2.3、推荐表新行、Key Rules 新条目，全部翻译到 en/SKILL.md 同位置。

- [ ] **Step 2: 镜像 README.md**

把 cn/README_CN.md 顶部的 fork 说明 + 0.1.0 新能力段，翻译到 README.md 同位置。

- [ ] **Step 3: 创建 docs/intake-protocol.md（英文版）**

把 docs/intake-protocol.cn.md 翻译为英文。

- [ ] **Step 4: 验证**

```bash
grep -c "1.2.1" skills/CCteam-creator/SKILL.md
grep -c "1.2.2" skills/CCteam-creator/SKILL.md
grep -c "1.2.3" skills/CCteam-creator/SKILL.md
grep -c "0.1.0" README.md
ls docs/intake-protocol.md
```

Expected: 前 4 条 ≥ 1；最后一条文件存在。

- [ ] **Step 5: 提交**

```bash
git add skills/CCteam-creator/SKILL.md README.md docs/intake-protocol.md
git commit -m "feat(en): mirror cn — SKILL.md sub-steps + README + intake protocol doc"
```

---

## Task 17: 最终校验 + 整体 commit + tag v0.1.0

**Files:** 无新改动，仅校验和发布。

- [ ] **Step 1: 跑 release 校验脚本（如果它适配本结构）**

```bash
python3 scripts/validate-release.py
```

如果脚本基于上游设计、不适配本 fork 改动 → 跳过此步，**记录到下个迭代**修改 validate-release.py。如果失败但失败信息明确（比如缺某文件），按提示修。

- [ ] **Step 2: 跨语言一致性检查**

```bash
# 双语章节数应一致
diff <(grep -c "^##" cn/skills/CCteam-creator-cn/references/roles.md) <(grep -c "^##" skills/CCteam-creator/references/roles.md)
diff <(grep -c "^##" cn/skills/CCteam-creator-cn/references/onboarding.md) <(grep -c "^##" skills/CCteam-creator/references/onboarding.md)
diff <(grep -c "^##" cn/skills/CCteam-creator-cn/references/templates.md) <(grep -c "^##" skills/CCteam-creator/references/templates.md)
diff <(grep -c "^##" cn/skills/CCteam-creator-cn/SKILL.md) <(grep -c "^##" skills/CCteam-creator/SKILL.md)
```

Expected: 每对都返回空输出（数字相同）。如果不一致，定位差异、补齐。

- [ ] **Step 3: JSON 校验最后一遍**

```bash
python3 -m json.tool < .claude-plugin/plugin.json > /dev/null && echo plugin.json OK
python3 -m json.tool < .claude-plugin/marketplace.json > /dev/null && echo marketplace.json OK
```

Expected: 两个都打印 OK。

- [ ] **Step 4: 检查 git 状态、确认所有改动已 commit**

```bash
git status
git log --oneline master..HEAD
```

Expected: 工作区干净；可以看到本次所有 task 的 commits 序列。

- [ ] **Step 5: 打 tag**

```bash
git tag -a v0.1.0 -m "Release 0.1.0 — Aliyun ecosystem integration

Forked from jessepwj/CCteam-creator v1.4.3.

New: bug-triage role, dev MR submission via Yunxiao MCP, /ccteam-scan
slash command, CronCreate ARMS scan, intake protocol with 6-state machine.

See CHANGELOG.md for full details."
```

- [ ] **Step 6: 确认 tag**

```bash
git tag -l "v0.1.0"
git show v0.1.0 --stat | head -20
```

Expected: tag 存在；show 显示 release message。

> **Push 到远程仓库**: 由用户决定时机（需要先创建远程仓库，spec §6 已说明）。本 plan 不自动 push。

---

## Self-Review

**Spec coverage**: 对照 spec §1-§10:

- [x] §1 背景目标 → plan 顶部 Goal/Architecture
- [x] §2 bug-triage 角色 → Task 2 (roles) + Task 3 (onboarding) + Task 4 (template)
- [x] §3 dev MR 增强 → Task 2 (roles append) + Task 3 (onboarding append)
- [x] §4 /ccteam-scan → Task 7
- [x] §5 SKILL.md 流程改动 → Task 6
- [x] §6 文件结构 → 全 plan
- [x] §6.1 plugin.json → Task 9
- [x] §6.2 marketplace.json → Task 9
- [x] §6.3 LICENSE/README 归属 → Task 10
- [x] §7 开发顺序（cn 先行）→ Task 2-10 cn，Task 12-16 en
- [x] §8 配置依赖前置 → Task 5 mcp-setup.md
- [x] §9 验收标准 → Task 11 smoke test 覆盖大部分；Task 17 一致性检查覆盖剩余
- [x] §10 不在本期范围 → CHANGELOG 显式列出

**Placeholder scan**:
- 唯一未填充的占位是 `plugin.json` 的 `homepage` 字段——spec 明确说"远程仓库地址定后填"，是已知 deferred item，不算 placeholder
- ARMS MCP 已确认使用 PyPI 包 `mcp-server-aliyun-observability`（v1.0.8+），通过 `uvx` 启动；env 变量 `ALIBABA_CLOUD_REGION_ID`（注意 _ID 后缀）

**Type/naming consistency**:
- intake 状态机 6 状态在所有出现位置（roles.md / templates.md / docs/intake-protocol.cn.md / spec）一致
- last-scan.txt 路径 `.plans/<project>/bug-triage/last-scan.txt` 全文一致
- MCP 包名: `alibabacloud-devops-mcp-server` (云效) / `zentao-mcp-server` (禅道) / `mcp-server-aliyun-observability` (阿里云观测)，全文一致
- Step 编号 1.2.1/1.2.2/1.2.3 全文一致

**Scope check**:
- 17 个 task，cn 5 + 顶层 4 + smoke 1 + en 5 + final 2 = 17，符合预期
- 每个 task 有明确文件、可验证的步骤
- 没有"实现 X 类似 Y"的偷懒引用——en mirror 的几个 task 通过"diff cn 找改动"方式给出可执行步骤，不是 placeholder
