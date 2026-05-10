# CCteam-creator 阿里云生态集成 — 设计文档

| 字段 | 值 |
|------|-----|
| 文档日期 | 2026-05-10 |
| 作者 | motou |
| 状态 | Draft → 待用户复审 |
| 范围 | Phase 1 (skill 改造)；Phase 2/3 (本地网关 + Chrome 插件) 后期独立设计 |
| 起点版本 | 当前目录 fork 自 jessepwj/CCteam-creator @ v1.4.3 |
| 目标版本 | 0.1.0（重新起步，作为新项目维护） |

---

## 1. 背景与目标

### 1.1 上游项目定位

`CCteam-creator` 是一个 Claude Code 插件 (skill)，作用是把 Claude Code 主对话变成 "team-lead"，并在背后并行 spawn 多个角色化 sub-agent (`backend-dev` / `frontend-dev` / `researcher` / `e2e-tester` / `reviewer` / `custodian`)。所有协作通过 `.plans/<project>/` 下的结构化 markdown 持久化，避免 context compact 后状态丢失。

上游的局限：**所有角色都是"内部协作"角色，从不主动接触外部系统**。无法从禅道/云效拉真实工作项，无法用 ARMS 监控数据做触发，无法把代码推到企业 Codeup 仓库。

### 1.2 本次改造目标

让 CCteam 能与阿里云企业生态闭环工作：

```
[禅道 Bug 单] ──user触发──┐
                          ├──→ bug-triage (新角色)
[ARMS 错误巡检]──cron触发──┘         │
                                      ↓ 整理成 task brief，落盘
                          .plans/<project>/intake/<source>-<id>.md
                                      │
                                      ↓ team-lead 决策立项 + 分配
                          backend-dev / frontend-dev (增强)
                                      │
                                      ↓ TDD + 实现
                                  reviewer (评审通过)
                                      │
                                      ↓ git push + 调 yunxiao MCP 提 MR
                                [Codeup MR] ←── 人工合入（CCteam 边界外）
```

### 1.3 不做的事（YAGNI）

- ❌ 不自动回写禅道关闭 Bug（人工合入后用户自己点关闭）
- ❌ 不做 ARMS 上线后验证（ARMS 在本设计中是触发源，不是验证端）
- ❌ 不做 "P0 错误自动立项" 的激进策略（所有 intake 都需 team-lead 人工 accept）
- ❌ 不在 Phase 1 做浏览器插件 / 本地 HTTP 网关（属 Phase 2/3）

---

## 2. 新角色：`bug-triage`

### 2.1 角色定义

| 字段 | 值 |
|------|-----|
| Name | `bug-triage` |
| subagent_type | `general-purpose` |
| model | `sonnet` |
| 写入权限 | 仅 `.plans/<project>/bug-triage/` 和 `.plans/<project>/intake/` |
| MCP 依赖 | `zentao-mcp-server`、`mcp-server-aliyun-observability`（用于 ARMS） |
| 角色定位 | 外部世界 ↔ CCteam 之间的"翻译官"——只读、只写 intake 文件，不碰源代码 |

### 2.2 核心职责

1. **拉单**：收到 trigger（`{source: zentao|arms, id: <bug-id|trace-id>}`）后，调用对应 MCP 拉取原始数据
2. **整理**：将原始数据解析成结构化 intake 文件——重现步骤 / 堆栈 / 影响范围 / 相关代码模块猜测 / 优先级建议
3. **去重**：写盘前先 grep `.plans/<project>/intake/` 看是否已有同源同 ID 的文件，避免巡检重复触发产生噪声

### 2.3 Intake 文件格式

路径：`.plans/<project>/intake/<source>-<id>.md`

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

### 2.4 状态机

```
pending ──accept──→ accepted ──dev完成MR──→ in_review ──人工合入──→ done
   │                                              │
   ├──reject──→ rejected (终态)                   ├──MR 被拒/关闭──→ rejected (终态)
   │
   ├──merge──→ merged (终态，merged_into 指向真正的 task)
   │
   └──defer──→ 保持 pending，下次会话再处理
```

| 状态 | 含义 | 触发者 |
|------|------|--------|
| `pending` | 已落盘，等待 team-lead 决策 | bug-triage |
| `accepted` | team-lead 已立项，task 文件夹已创建 | team-lead |
| `in_review` | dev 已完成 + MR 已提交，等待人工合入 | dev |
| `done` | MR 已合入 | team-lead 手工 / 后期可自动检测 |
| `rejected` | 决定不修（含 MR 被拒） | team-lead |
| `merged` | 合并到已有 task | team-lead |

### 2.5 触发链路

#### (a) 手动触发（chat）

用户在主对话说："处理禅道 12345"。

```
team-lead 解析意图
  ↓
SendMessage(to: "bug-triage", message: "拉禅道 bug 12345 → 落 intake")
  ↓
bug-triage 调用 zentao MCP fetch bug 12345
  ↓
解析、去重检查、写 intake/zentao-12345.md
  ↓
回报 team-lead："intake/zentao-12345.md 已落盘，建议 P1，请决策"
  ↓
team-lead 汇报给用户、走 §2.6 决策流程
```

#### (b) 手动立即巡检（chat / 斜杠命令）

用户在主对话说："立即巡检 / 扫一下 ARMS / 现在巡检一次"，或敲 `/ccteam-scan`。

```
team-lead 解析参数 (source / project / since / severity)
  ↓
SendMessage(to: "bug-triage", message: "立即巡检任务: source=arms, project_id=X, since=<last-scan>, severity_threshold=P1")
  ↓
bug-triage 读 .plans/<project>/bug-triage/last-scan.txt 获取 since
  ↓
调用 alibabacloud-api MCP 查 ARMS 错误事件
  ↓
按 severity_threshold 过滤、grep 去重、批量写 intake/arms-*.md
  ↓
更新 last-scan.txt = 当前时间
  ↓
回报 team-lead：N 个新 intake，列表
```

参数默认值：

| 参数 | 默认 | 用户覆盖示例 |
|------|------|-------------|
| source | arms | "扫一下禅道" → zentao |
| project_id | CLAUDE.md 中配置 | "扫 project-X" |
| since | last-scan.txt 中的时间戳（首次为 24h 前） | "扫最近 7 天" |
| severity_threshold | P0 + P1 | "把 P2 也带上" |

#### (c) Cron 定时巡检

```
[Cron 9:00 触发，prompt: "执行 ARMS 巡检 → bug-triage → intake → 退出，不进对话"]
  ↓
启动 headless Claude Code 会话（项目目录下）
  ↓
读 CLAUDE.md → 加载 team-lead 协议
  ↓
若 team 健在：SendMessage(bug-triage)；否则：临时 spawn bug-triage
  ↓
bug-triage 走与 (b) 同样的链路
  ↓
完成后会话退出（不进入对话循环）
```

Cron 任务由 SKILL.md Step 1 在用户确认 "启用 ARMS 巡检" 时通过 `CronCreate` 工具创建：

| 字段 | 值 |
|------|-----|
| schedule | 默认 `0 9 * * *`（每天 9:00），用户可改 |
| prompt | 见上方 |
| 工作目录 | 项目根目录 |

### 2.6 Team-lead 处理 intake 的协议

写入项目 CLAUDE.md 模板的新章节 `## Intake Processing Protocol`，每次主会话启动 / compact 恢复后自动加载。

**主动汇报**：team-lead 必须在每次会话启动 / compact 恢复后：

1. 检查 `.plans/<project>/intake/` 目录
2. 列出所有 `status: pending` 的 intake 文件
3. 一段简洁汇报告诉用户：
   ```
   发现 <N> 个新 intake 待决策：
   - intake/zentao-12345.md  [P1] <一句话>
   - intake/arms-trace-abc.md [P2] <一句话>
   要我现在过一遍并提建议吗？
   ```
4. 用户决定走哪条路径：
   - **Accept**：创建 `dev/<source>-<id>/` 任务文件夹，更新 intake `status: accepted`、`assigned_to`、`task_path`，SendMessage 派给 dev
   - **Reject**：更新 `status: rejected`、`reject_reason`，文件保留作为历史
   - **Merge**：把 intake 内容追加到已有 task 的 findings.md，更新 intake `status: merged`、`merged_into`
   - **Defer**：保持 `pending`，下次会话再决策

### 2.7 时间戳与归档

- **last-scan.txt**：单行 ISO 时间戳，格式 `2026-05-10T15:30:42+08:00`，路径 `.plans/<project>/bug-triage/last-scan.txt`。bug-triage 每次扫描完成后写入。
- **intake 归档**：`done` / `rejected` / `merged` 状态的文件保留供审计；超过 30 天的终态 intake 由 custodian 月度移到 `.plans/<project>/intake/_archive/`；没装 custodian 的小团队，team-lead 看到 intake/ 文件超过 50 个时一次性提议归档。

---

## 3. 现有角色增强：`backend-dev` / `frontend-dev`

在 `references/roles.md` 的 dev 条目末尾追加 `MR Submission Protocol` 章节，并在 `references/onboarding.md` 的 dev onboarding prompt 里加对应步骤说明。**不新增角色**。

### 3.1 提 MR 完整步骤

```
1. 跑 CI (golden_rules.py + tests)              ← 必须全绿
2. 等待 reviewer 内部评审                       ← 必须 [OK] (不能 [WARN]/[BLOCK])
3. git checkout -b bugfix/<source>-<external-id>
4. git add + commit (commit message 模板见 §3.2)
5. git push origin <branch>
6. 调用 yunxiao MCP 创建 MR (字段见 §3.3)
7. 把 MR URL 写回 intake 文件 frontmatter (status: in_review, mr_url: <url>)
8. 通知 team-lead："MR 已提交，等待人工合入：<url>"
```

### 3.2 Commit message 模板

```
fix(<module>): <一句话描述>

关联: <source>-<external-id>
原因: <root cause 一行>
方案: <fix approach 一行>

Internal-Review: PASS (.plans/<project>/reviewer/review-<task>/findings.md)
CI: PASS

Co-Authored-By: Claude (CCteam) <noreply@anthropic.com>
```

### 3.3 MR 描述模板

```markdown
## 关联
- 来源: 禅道 Bug #12345 / ARMS Trace abc123
- 原始链接: <external_link>
- 严重级: P1

## Root Cause
[一段说明]

## Fix
[改动描述 + 关键代码片段]

## Test Coverage
- 新增单测: <count>
- 修改/新增 E2E: <count>
- CI: PASS（golden_rules + tests + type-check 全绿）

## Internal Review
- Reviewer Verdict: [OK]
- 详细评审: <链接到 .plans/.../review-xxx/findings.md，或粘贴关键摘要>

## 风险与影响范围
[影响哪些模块/接口，是否有 breaking change]

## 人工合入前 checklist
- [ ] 检查分支无冲突
- [ ] 确认 CI 在 Codeup 流水线上也通过
- [ ] 必要的话灰度
```

### 3.4 适用范围

| 场景 | 是否走 MR 流程 |
|------|-------------|
| 来自 intake 的 bug 修复 | **必须** |
| 用户直接说"实现 X 功能"的新功能 | **必须** |
| 用户说"快速改个 typo / 调整 log 等级" | **必须**（无小修改豁免） |
| 改的是 `.plans/` 文件、CLAUDE.md 等团队内部文档 | **不需要**（这些不是项目源代码） |

### 3.5 失败处理

3-Strike 协议同样适用：

- **git push 失败**（权限/网络/分支冲突）→ dev 记录 progress.md，escalate to team-lead，**不静默重试**
- **MR 创建失败**（MCP 调用失败/参数错误）→ 同上
- **CI 不绿** → task 不算完成，回去修，不能跳过

### 3.6 配置依赖（项目预备）

dev 要能提 MR，需项目目录预先准备：

1. `git remote` 已指向 Codeup（用户预先 `git remote add origin https://codeup.aliyun.com/...`）
2. yunxiao MCP 已装且 `YUNXIAO_ACCESS_TOKEN` + 项目 ID 已配置
3. CCteam 的 SKILL.md Step 1 末尾会**显式校验**这两项就位——没就位时在 setup 阶段直接卡住

---

## 4. 斜杠命令：`/ccteam-scan`

注册一个斜杠命令作为 "立即巡检" 的正式入口（自然语言识别也保留作为 fallback）。

### 4.1 文件位置

`commands/ccteam-scan.md`（仓库根级 `commands/` 目录，Claude Code 平台约定）

### 4.2 文件内容

prompt 用中文（团队主用语言），团队若在英文会话中调用，team-lead 自动适配：

```markdown
---
description: 立即触发 bug-triage 角色，扫描 ARMS 错误（或禅道 Bug）并落 intake 文件
---

立即执行一次外部系统巡检，参数从用户附带的自然语言中解析：

- source: 默认 arms，用户可指定 zentao
- project_id: 默认从 CLAUDE.md 读取，用户可临时覆盖
- since: 默认从 .plans/<project>/bug-triage/last-scan.txt 读取
- severity_threshold: 默认 P0 + P1，用户可放宽

team-lead 解析后，SendMessage 给 bug-triage 角色（团队若已 retire，临时 spawn）。

bug-triage 完成后回报新增 intake 文件清单。
```

---

## 5. SKILL.md 流程改动

在 `skills/CCteam-creator/SKILL.md`（及 `cn/skills/CCteam-creator-cn/SKILL.md` 同步翻译）做以下三处改动：

> 上游 SKILL.md Step 1 现有结构为 1.1 介绍机制 / 1.2 收集需求 / 1.3 推荐角色 / 1.4 用户可定制项。本设计在 1.2 与 1.3 之间插入三个新子步骤 1.2.1 / 1.2.2 / 1.2.3，原 1.3 / 1.4 顺移不变。

### 5.1 新增子步骤 1.2.1：触发源 / 输出端集成问询

在 "1.2 Gather User Requirements" 末尾、"1.3 Recommend a Team Configuration" 之前插入：

```
1.2.1 外部系统集成（如适用）

询问用户：
- 是否需要从禅道拉 Bug 单作为输入？
- 是否需要从 ARMS 拉错误事件作为输入？
- 是否需要把代码推到云效 Codeup + 自动提 MR？

任一为是 → 进入 1.2.2 MCP 校验。
全否 → 跳过 1.2.2 / 1.2.3，按上游标准流程走 1.3。
```

### 5.2 新增子步骤 1.2.2：MCP 校验

```
1.2.2 MCP 校验（仅当 1.2.1 任一选 "是" 时执行）

对用户回答 "是" 的每一个集成项：
- 检查对应 MCP 是否已装、env 是否齐全
- 缺失时停下，引用 references/mcp-setup.md 引导用户先装好
- 不要在缺失依赖的情况下创建团队，否则后续会失败
```

### 5.3 新增子步骤 1.2.3：是否启用 ARMS 巡检

```
1.2.3 是否启用 ARMS 定时巡检（仅当 1.2.1 选了 ARMS 时执行）

若启用：
- 询问 schedule（默认 "0 9 * * *"）
- 询问 project_id (ARMS 中的项目标识)
- 询问 severity_threshold (默认 P0 + P1)
- 创建 CronCreate 任务（参见 §2.5(c)）
- 把配置记入 CLAUDE.md `## ARMS 巡检配置` 节
```

### 5.4 Step 3.5 增加：CLAUDE.md 模板加 Intake Processing Protocol

`references/templates.md` 中的 CLAUDE.md 模板增加 §2.6 描述的章节。同时模板要根据团队是否包含 bug-triage 动态决定是否注入。

### 5.5 角色推荐表更新

Step 1.3 推荐角色表加一行：

```
| Bug Triage | bug-triage | — | sonnet | 拉外部 Bug/Error 数据 → 写 intake，read-only on code |
```

并在 "Recommendation principles" 中加一条：

```
- bug-triage 仅在用户确认接入禅道或 ARMS 时推荐
- bug-triage 与 researcher 都是 read-only，但职责不同：researcher 关注代码内部研究，bug-triage 关注外部系统数据搬运
```

---

## 6. 文件结构（最终态）

```
CCteam-creator/                              ← 当前目录，fork 本体
├── .claude-plugin/
│   ├── plugin.json                          ← 改 version/keywords/description/author
│   └── marketplace.json                     ← 同步改 version/description
├── commands/                                ← 【新增目录】
│   └── ccteam-scan.md                       ← 【新增】斜杠命令
├── skills/CCteam-creator/                   ← 名字不变
│   ├── SKILL.md                             ← 改：Step 1 / Step 3.5 / 角色表
│   ├── references/
│   │   ├── roles.md                         ← 改：新增 bug-triage；dev 加 MR 协议
│   │   ├── onboarding.md                    ← 改：新增 bug-triage onboarding；dev onboarding 加 MR 步骤
│   │   ├── templates.md                     ← 改：CLAUDE.md 模板加 intake 协议、ARMS 巡检配置；新增 intake 文件模板
│   │   └── mcp-setup.md                     ← 【新增】MCP 安装清单 + 鉴权 + 自检
│   └── scripts/golden_rules.py              ← 不变
├── cn/skills/CCteam-creator-cn/             ← 名字不变，全量同步翻译
│   ├── SKILL.md                             ← 同步翻译
│   ├── references/
│   │   ├── roles.md                         ← 同步翻译
│   │   ├── onboarding.md                    ← 同步翻译
│   │   ├── templates.md                     ← 同步翻译
│   │   └── mcp-setup.md                     ← 【新增】中文版
│   └── scripts/golden_rules.py              ← 不变
├── docs/
│   ├── release-guide.md                     ← 沿用
│   ├── intake-protocol.md                   ← 【新增】英文，给人类用户看
│   ├── intake-protocol.cn.md                ← 【新增】中文版
│   ├── superpowers/specs/                   ← 本文档所在
│   └── images/                              ← 沿用
├── scripts/validate-release.py              ← 沿用
├── README.md                                ← 改：增加 "新增能力" 段落
├── README_CN.md                             ← 同步改
├── LICENSE                                  ← 沿用 MIT，保留上游版权
└── CHANGELOG.md                             ← 【新增】单文件双语并存
```

### 6.1 plugin.json 终态

```json
{
  "name": "CCteam-creator",
  "description": "Multi-agent team orchestration for Claude Code, with native Aliyun ecosystem integration (Yunxiao Codeup MR / Zentao bug intake / ARMS error monitoring).",
  "version": "0.1.0",
  "author": { "name": "motou" },
  "homepage": "<待定，仓库地址定后填>",
  "license": "MIT",
  "keywords": [
    "claude-code", "agent-teams", "multi-agent",
    "orchestration", "planning", "skills",
    "aliyun", "yunxiao", "zentao", "arms"
  ]
}
```

### 6.2 marketplace.json 终态

```json
{
  "name": "ccteam",
  "owner": { "name": "motou" },
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

### 6.3 上游归属

- **LICENSE**：保留 MIT 全文 + 顶部新增一行：
  ```
  Forked from jessepwj/CCteam-creator (MIT) — extended for Aliyun ecosystem integration.
  ```
- **README** / **README_CN** 第一段：
  ```
  Based on jessepwj/CCteam-creator v1.4.3, extended with Aliyun ecosystem integration
  (Yunxiao Codeup MR / Zentao bug intake / ARMS error monitoring).
  ```

---

## 7. 开发顺序

由于 cn 是用户主用语言：

1. 先在 `cn/skills/CCteam-creator-cn/` 完整设计中文版
2. 在 cn 上实测（用户主场景验证）
3. 验证通过后翻译到英文版
4. CHANGELOG 同时更新双语
5. plugin.json / marketplace.json / README / 顶层文件最后统一更新

## 8. 配置依赖前置条件（用户操作）

第一次使用扩展能力前，用户需自行准备：

| 项 | 操作 | 验证 |
|----|------|------|
| zentao MCP | `npx -y zentao-mcp-server` 配置到 ~/.claude/mcp.json，env 填 ZENTAO_URL/ACCOUNT/PASSWORD | claude 启动后可见 zentao 工具 |
| yunxiao MCP | `npx -y alibabacloud-devops-mcp-server` 配置，env 填 YUNXIAO_ACCESS_TOKEN | 同上 |
| aliyun-observability MCP (for ARMS) | 装 `mcp-server-aliyun-observability` (PyPI, `uvx` 启动)，配 AccessKey + RAM 权限（最少 ARMS 只读） | 同上 |
| Codeup git remote | `git remote add origin https://codeup.aliyun.com/<org>/<repo>.git` 并配 SSH key 或 HTTPS 凭证 | `git push --dry-run` 不报错 |

详细安装与连通性自检脚本见 `references/mcp-setup.md`（一期交付物）。

## 9. 验收标准（Phase 1）

- [ ] 全新项目能用扩展版 SKILL.md 完成 Step 0-5 setup，Step 1 正确询问触发源 / MCP / 巡检
- [ ] MCP 缺失时 setup 在 1.x.1 步骤显式卡住，引用 mcp-setup.md
- [ ] bug-triage 能从禅道拉一个真实 Bug 单 → 落 intake 文件 → 字段齐全
- [ ] bug-triage 能从 ARMS 巡检 → 过滤后批量写 intake → last-scan.txt 正确更新
- [ ] 重复触发同一 Bug → bug-triage 检出已存在不重写
- [ ] team-lead 在会话启动 / compact 恢复后能主动汇报 pending intake
- [ ] dev 完成代码 → reviewer [OK] → 自动 git push → 调 yunxiao MCP 提 MR → MR URL 写回 intake
- [ ] CI 不绿时 dev 拒绝 push（卡在第 1 步）
- [ ] reviewer 未给 [OK] 时 dev 拒绝 push（卡在第 2 步）
- [ ] CronCreate 创建的 ARMS 巡检任务能定时触发并完成 intake 写盘
- [ ] `/ccteam-scan` 斜杠命令可用，参数解析正确
- [ ] cn 版与 en 版功能对等
- [ ] CHANGELOG.md 列出从 v1.4.3 → 0.1.0 的所有变更

## 10. 不在本期范围（明确归档）

- Phase 2：本地 HTTP 网关 (bridge service)，把外部 trigger 转成 inbox 文件
- Phase 3：Chrome 浏览器插件，向禅道/ARMS 页面注入按钮
- 自动回写禅道（Bug 关闭、状态同步）
- ARMS 上线后验证回路（修复 → 部署 → ARMS 验证 → 自动 done）
- "P0 错误自动立项" 激进策略
- 多触发源去重的"跨源融合"（同一 issue 同时在禅道和 ARMS 出现，目前是两个独立 intake，未来可能加 link/dedupe）

这些都需要在本期完成且稳定运行后再独立 brainstorm。
