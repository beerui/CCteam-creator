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
