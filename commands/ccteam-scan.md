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
