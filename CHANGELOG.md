# CHANGELOG

## 0.1.4 - 2026-05-16

> Minor: ARMS RUM 即时巡检 (`/arms` 命令) + UX gap closure surfaced by real-project validation against `daji-customer-service`.
> Minor 版本：新增 ARMS RUM 即时巡检（`/arms` 命令） + 在真实项目 `daji-customer-service` 验证暴露的 UX 缺口修复。

### Added / 新增
- **`/arms` slash command + `arms` agent** for active ARMS RUM exception triage (CN only this release):
  - New role `arms` (sonnet, read-only on source code) — queries SLS via Python SDK, normalizes/groups exceptions, cross-locates root cause from project source, archives fingerprints in `.plans/<project>/arms/archive/`, dispatches dev with `source=arms` task envelope.
  - New ARMS sub-protocol for backend-dev / frontend-dev: **local commit, no MR** — team does not auto-merge; user owns final merge decision. Distinct from intake-driven bug fixes which still go through Codeup MR.
  - Fingerprint = `normalize_message(exception.message) + " @ " + view.name` — `view.name` already URL-normalized by ARMS convergence backend; `norm_message` strips UUIDs/timestamps/long IDs in Python.
  - Archive lifecycle: `analyzed` → `resolved` / `ignored`, with recurrence detection on next scan.
  - Files: `commands/arms.md`, `cn/skills/CCteam-creator-cn/references/onboarding.md § arms`, `references/roles.md § arms`, `references/templates.md § ARMS 巡检配置/archive/fingerprint/resolution`, `SKILL.md` Step 1.2.4 + 1.3 + Key Rules.
  
  新增 `/arms` 斜杠命令和 `arms` 角色——主动型 ARMS RUM 异常分析师：用 Python SDK 查 SLS、Python 端归一化分组、读项目源码交叉定位、归档指纹、派 dev（走"本地 commit、不走 MR"子协议，与 intake 流的 Codeup MR 互不影响）。

### Fixed / 修复（真实项目验证暴露）
- **Existing team has no path to add `arms` role**: original `/arms` errored with "请重新 `/CCteam-creator-cn` 组团" when team-snapshot lacked arms, conflicting with project CLAUDE.md's "Never create a new team". Now `/arms` §4 follows /ccteam-scan's temp-spawn pattern: `Agent(team_name=<当前团队>, ...)` joins the existing team, §8 asks user whether to make it permanent.
  现有团队无 arms 角色升级路径：原版直接报错，与项目 CLAUDE.md "Never create a new team" 冲突。改为临时 spawn + team_name 参数加入团队，§8 询问是否永久加入花名册。
- **`.convergence` field hallucination**: 0.1.4 design assumed `exception.message.convergence` and `view.name.convergence` were ARMS-queryable suffix fields. Doc/SDK lookup confirms "收敛/convergence" is a backend URL normalization mechanism, not a separate field. Replaced with Python-side `normalize_message()` (regex strips UUID/timestamp/long-numeric-ID) + new Step 3.2 field discovery probe to verify actual log keys before grouping.
  `.convergence` 字段是设计幻觉：ARMS 文档证实 convergence 是后端 URL 归一化机制而非可查询字段；改用 Python 端 `normalize_message()` + Step 3.2 字段探测。
- **macOS system Python pip install permission failure**: `pip install aliyun-log-python-sdk` fails on macOS system Python without `--user`. SKILL/roles/onboarding now all use `pip3 install --user`.
  macOS 系统 Python `pip install` 缺 `--user` 装不上：全文统一为 `pip3 install --user`。
- **Dead-end error UX when CLAUDE.md ARMS config missing or partial-placeholder**: original `/arms` errored if section missing or fields like `<your-pid>`. Now `/arms` §2 detects placeholder values (`<...>` / `your-...` / `xxx` / `TODO` / cred fields <8 chars) and interactively补全 via AskUserQuestion (region/env enums) + text input (PID/project/logstore/AK), writes back to CLAUDE.md before continuing.
  CLAUDE.md ARMS 配置缺失或半填占位时的死胡同：检测 `<...>` / `your-...` / `xxx` / `TODO` 等占位 → AskUserQuestion + 文本输入交互式补全 → 自动写回 CLAUDE.md。
- **arms onboarding Step 1 missing task folder skeleton**: subsequent steps would fail to write progress.md. Added skeleton creation at Step 1.
  arms onboarding Step 1 缺任务文件夹建骨架：补上,后续 step 才能写 progress.md。
- **SLS error handling un-classified**: `LogException` (errorCode=ProjectNotExist/Unauthorized/...) lacked guidance on which to retry vs escalate. Added classification table in onboarding Step 3.3.
  SLS `LogException` 错误未分类：补错误码分类表（ProjectNotExist / Unauthorized / WriteQuotaExceed 等的处理路径）。

### Notes / 备注
- **CN-only this release**: English skill (`skills/CCteam-creator/`) has not been updated; `/arms` and `arms` role are CN-skill exclusive in 0.1.4. EN parity scheduled for follow-up.
  本版本仅 CN：英文版 skill 暂未同步，/arms 和 arms 角色仅 CN skill 提供，EN 待补。
- **Validation methodology**: Driven by real-project run in `daji-customer-service` rather than spec-only acceptance. The 4 fixed gaps were invisible from the 13-criteria design checklist; all surfaced only when simulating a first-time user flow. This validation pattern is now captured in user memory for future feature work.
  验证方法学：本次 UX 修复是在真实项目 `daji-customer-service` 跑一遍流程暴露的，不是 spec-only 验收。13 项验收清单全过的功能仍有 4 处缺口，仅在模拟新用户首次流程时暴露——此验证模式已写入记忆。

## 0.1.3 - 2026-05-11

> Patch: completes the 0.1.2 source=arms-rum rollout — bug-triage onboarding/role/template files now match the /ccteam-scan command spec.
> Patch：补完 0.1.2 source=arms-rum 的下沉——bug-triage onboarding/role/template 现已与 /ccteam-scan 命令规范一致。

### Fixed / 修复
- **bug-triage onboarding inconsistency** with 0.1.2 spec:
  After 0.1.2 introduced `source=arms-rum` and `last-scan-<source>.txt` in `commands/ccteam-scan.md` and the source enum, the per-agent guidance in `references/onboarding.md`, `roles.md`, and `templates.md` was not updated. Result: an actually-spawned bug-triage would still try the old MCP name `alibabacloud-api` and a single `last-scan.txt`, contradicting the v0.1.2 scan command. Now in sync (EN+CN).
  bug-triage onboarding 与 0.1.2 规范不一致：0.1.2 在 ccteam-scan.md 和 source 枚举里引入了 `source=arms-rum` 和 `last-scan-<source>.txt`，但 bug-triage 的 onboarding/roles/templates 里的具体步骤说明没同步改。实际 spawn 出来的 bug-triage 还在用旧 MCP 名 `alibabacloud-api` 和单个 `last-scan.txt`——与 v0.1.2 命令规范矛盾。本版本同步完毕（EN+CN）。

### Notes / 备注
- Continuation of 0.1.2 — together they make ARMS RUM end-to-end self-consistent across docs / scan command / agent behavior.
  0.1.2 的延续——两版合起来让 ARMS RUM 的端到端在文档 / 扫描命令 / agent 行为上自洽。

## 0.1.2 - 2026-05-11

> Patch: Step 0 fallback regression fix + manual install completeness + ARMS RUM source.
> Patch：Step 0 fallback 回归修复 + 手动安装完整性 + ARMS RUM source 接入。

### Fixed / 修复
- **Step 0 Update Check fallback chain regression** (introduced in 0.1.1):
  Previous `ls ... | head -1 | xargs cat 2>/dev/null || ...` silently exits 0 when files are missing, never falling through. Replaced with a single `ls -t` over all 4 candidate paths + `[ -n "$PJ" ] && cat "$PJ"` guard. Verified against both real-machine multi-version cache and fresh smoke-install layouts.
  Step 0 Update Check fallback 链回归修复（0.1.1 引入）：原命令在文件缺失时静默 exit 0 永不 fall through；改为单条 ls -t 跨所有候选路径选最新 + [ -n ] 守卫，多版本缓存和新装两种环境均验证通过。
- **README manual install missed `.claude-plugin/` copy**:
  `cp -r skills/CCteam-creator ~/.claude/skills/...` only carries SKILL.md + references/ + scripts/ — `plugin.json` lives at repo root, not in the skill dir. Result: manual-install users had no version metadata, Step 0 silently skipped despite README line 223 promising notification. Added second `cp -r .claude-plugin ~/.claude/skills/<name>/` for both EN and CN install paths, plus a callout explaining why.
  README 手动安装漏复制 `.claude-plugin/` 目录：手动安装用户拿不到 version 元数据，Step 0 静默跳过；新增第 2 行 cp 命令并加说明。

### Added / 新增
- **`source: arms-rum`** added to bug-triage source enum (frontend RUM exception triage):
  - `roles.md` / `templates.md` / `intake-protocol.md(.cn)`: enum extended `zentao | arms` → `zentao | arms | arms-rum`
  - `commands/ccteam-scan.md` rewritten: accepts 3 sources with explicit MCP mapping table (arms→`mcp-server-aliyun-observability` uvx; arms-rum→OpenAPI Explorer streamable-http; zentao→`zentao-mcp-server` npm); per-source last-scan tracking via `last-scan-<source>.txt` to avoid cross-contamination of `since` cursors between backend ARMS and frontend RUM
  
  bug-triage source 枚举加 arms-rum；/ccteam-scan 命令重写支持 3 个 source 及其各自 MCP 映射，per-source last-scan 追踪。

### Notes / 备注
- This release pairs with 0.1.1's mcp-setup.md § 3.4 (Aliyun OpenAPI Explorer Streamable HTTP for ARMS RUM) — together they complete the frontend RUM integration story end-to-end (config + trigger).
  本版本配合 0.1.1 的 mcp-setup.md § 3.4——两版合起来端到端打通前端 RUM 集成（配置 + 触发）。
- Backward compatible: existing intake files with `source: arms` continue to work; the enum just gained a third valid value.
  向后兼容：已有 `source: arms` intake 文件继续工作，枚举只是多了第 3 个合法值。

## 0.1.1 - 2026-05-11

> Patch release: user-blocking MCP package names + doc/config gaps. No breaking changes.
> Patch 发布：修复用户阻塞性 MCP 包名错误及多处文档/配置缺口。无破坏性变更。

### Fixed / 修复
- **MCP package names corrected** (P0, user-blocking — 0.1.0 docs would 404 on install):
  - `@alibabacloud/api-mcp-server` (npm 404) → `mcp-server-aliyun-observability` (PyPI v1.0.8, `uvx` launch)
  - `@tytt/zentao-mcp` (npm 404) → `zentao-mcp-server` (npm v0.1.0)
  - env var `ALIBABA_CLOUD_REGION` → `ALIBABA_CLOUD_REGION_ID`
  - server name `aliyun-api` → `aliyun-observability`

  MCP 包名修正（P0 用户阻塞——0.1.0 文档会让用户安装时 404）。
- **README project-structure diagram**: cn skill dir `CCteam-creator` → `CCteam-creator-cn`; references list 补全 `mcp-setup.md` (4 files, not 3).
  README 项目结构图：cn 目录名修正 + references 补全 mcp-setup.md。
- **Step 0 Update Check** local cache read: `cat */...plugin.json` corrupted JSON when multiple version dirs co-exist. Now `ls -t | head -1 | xargs cat` (newest by mtime).
  Step 0 多版本 cache 时 `cat *` 破坏 JSON，改为按 mtime 取最新。

### Added / 新增
- **ARMS RUM (frontend) integration path** — mcp-setup.md § 3.4: via Aliyun OpenAPI Explorer "on-demand MCP Service" → Streamable HTTP Endpoint. Distinct from § 3.1-3.3 backend APM coverage.
  mcp-setup.md § 3.4 新增前端 RUM 接入路径（阿里云 OpenAPI Explorer 按需打包 MCP Service → Streamable HTTP）。
- **Zentao nginx PATH_INFO Known Pitfall** — mcp-setup.md FAQ: zentao-mcp-server 全 API 调用 302 跳登录的根因 + 给运维一行修复。
  mcp-setup.md FAQ 加禅道 nginx PATH_INFO 已知陷阱（症状 + 根因 + nginx 修复）。
- **1M-context sonnet spawn pitfall** — SKILL.md "Model default": team-lead 在 `[1m]` 模式下必须 spawn `opus`，sonnet 1M 当前未启用会立即 API 400。
  SKILL.md 加 1M context sonnet spawn 陷阱：[1m] team-lead 必须 spawn opus。
- **`scripts/validate-release.py --check-deps`** — automated check that every npm/PyPI MCP package referenced in mcp-setup.md actually exists. Catches phantom deps before commit.
  validator --check-deps：自动验证 mcp-setup.md 引用的所有 npm/PyPI 包真实存在。
- **`.gitignore`** baseline — ignores `.plans/`, `.claude/settings.local.json`, `__pycache__`, `.DS_Store`, IDE configs.
  新增 .gitignore baseline。

### Notes / 备注
- Version bump from 0.1.0 ensures already-installed users get the Update Check notification on next skill trigger.
  bump 到 0.1.1 让已装用户能收到 Update Check 通知。
- Pure patch release: no API/structure changes; existing `.plans/` project layouts continue to work.
  纯 patch 发布：无 API/结构变更，已有 `.plans/` 项目可继续使用。

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
- CronCreate-based ARMS scheduled scan (default `0 9 * * *`).
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
- plugin.json: name unchanged, version 1.4.3 → 0.1.0, author → motou, keywords add aliyun/yunxiao/zentao/arms.
  plugin.json：name 不变，version 1.4.3 → 0.1.0，author → motou，keywords 增加 aliyun/yunxiao/zentao/arms。
- marketplace.json: same metadata adjustments.
  marketplace.json：同步元信息调整。
- LICENSE: preserve MIT, prepend fork attribution.
  LICENSE：保留 MIT，顶部加 fork 归属。
- README_CN: add fork attribution and 0.1.0 highlights at top.
  README_CN：顶部加 fork 说明和 0.1.0 亮点段。

### Not in this release / 不在本期
- Phase 2: local HTTP gateway bridging external triggers.
  Phase 2: 本地 HTTP 网关，桥接外部触发。
- Phase 3: Chrome extension injecting buttons into Zentao/ARMS pages.
  Phase 3: Chrome 浏览器插件，注入按钮到禅道/ARMS 页面。
- Auto write-back to Zentao on Bug closure.
  Bug 合入后自动回写禅道关闭。
- ARMS post-deploy verification loop.
  ARMS 上线后验证回路。
- en/ skill version sync (deferred to Task 12-16 of impl plan).
  en/ skill 同步翻译（延后到实施 plan 的 Task 12-16）。
