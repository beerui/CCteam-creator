---
description: 立即触发 bug-triage，扫描外部错误源（ARMS 后端 / ARMS RUM 前端 / 禅道）并落 intake
---

立即执行一次外部系统巡检。team-lead 请按以下步骤操作:

1. **解析参数**（从用户附带的自然语言中识别）:
   - `source`: 默认 `arms`（后端 APM 错误事件）；用户可指定 `arms-rum`（前端 RUM JS 异常）或 `zentao`（禅道 Bug 单）
   - `project_id` (source=arms): 从 CLAUDE.md `## ARMS 巡检配置` 节读取；用户可临时覆盖
   - `rum_app_id` (source=arms-rum): 从 CLAUDE.md `## ARMS RUM 巡检配置` 节读取；首次未配置可让用户用 `GetRumApps` 工具拉应用列表后选定
   - `since`: 默认从 `.plans/<project>/bug-triage/last-scan-<source>.txt` 读取（首次为 24h 前；不同 source 各维护各自的 last-scan 文件）
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
   - source: <解析得到, 例 arms / arms-rum / zentao>
   - 对应 ID: <由 source 决定 — arms→project_id, arms-rum→rum_app_id, zentao→无需 ID>
   - since: <解析得到>
   - severity_threshold: <解析得到>

   完成后回报新增的 intake 文件清单（路径 + severity + 一句话）。
   ```

4. **接收回报后**:
   - 把新增的 intake 数量、最高严重级简报给用户
   - 提示用户可走 `## Intake Processing Protocol` 对每条决策

**source 与 MCP 映射**（详见 references/mcp-setup.md）:
- `source=arms` → `mcp-server-aliyun-observability` (PyPI, uvx 启动；§ 3.1-3.3 配置)
- `source=arms-rum` → 阿里云 OpenAPI Explorer 创建的 Streamable HTTP MCP Service（§ 3.4 配置）
- `source=zentao` → `zentao-mcp-server` (npm；§ 2 配置)

**注意**: 此命令不替代 cron 自动巡检，仅供"现在我想立刻看一次"的场景。频繁手动调用可能让外部 API 配额吃紧（尤其 ARMS）。
