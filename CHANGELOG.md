# CHANGELOG

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
