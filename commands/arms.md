---
description: ARMS 即时巡检 — 查 SLS RUM 异常、分析根因、自动派 dev 修复
---

立即触发一次 ARMS RUM 异常分析。team-lead 请按以下步骤操作:

## 1. 前置门禁

1. **检查团队存在性**: 读 `.plans/<project>/team-snapshot.md`
   - 不存在 → 直接报错: "请先 `/CCteam-creator-cn` 组团后再运行 `/arms`",**停止**
2. **检查 arms 角色在册**: 读 team-snapshot.md 的花名册
   - 没有 `arms` → 报错: "本团队未启用 ARMS 即时巡检。可以重新 `/CCteam-creator-cn` 走 Step 1.2.4 增配,或直接走 `/ccteam-scan source=arms-rum` 走 intake 流"
3. **读 CLAUDE.md `## ARMS 巡检配置 — 即时巡检（arms agent）` 节**,取出 `pid`、`sls_*` 凭证、默认 env、默认 days

## 2. 解析参数

从用户附带的自然语言或显式参数中识别(参数可省,用默认):

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pid` | CLAUDE.md `pid` | ARMS RUM 应用 ID;无则走 §3 兜底 |
| `env` | `prod` | 环境过滤(prod/daily/pre/all);显式指定才查非生产 |
| `days` | 7 | 回溯天数 |
| `keywords` | 空 | 错误消息子串过滤(透传给 SLS query) |

**示例语义识别**:
- "/arms" → 默认全套
- "/arms env=all" / "查一下所有环境" → env=all
- "/arms days=1" / "最近 1 天" → days=1
- "/arms keywords=验证码" / "查含验证码的错误" → keywords=验证码

## 3. PID 兜底(仅当 CLAUDE.md 无 pid 时)

按以下顺序兜底,直到拿到 pid:

1. **优先用 arms-rum MCP**: 如果项目装了 `mcp__arms-rum__GetRumApps`(检查工具列表):
   - 调 `GetRumApps` 拉应用列表
   - 用 `AskUserQuestion` 让用户选,落入参数
2. **MCP 不存在**: 报错引导
   ```
   未在 CLAUDE.md 配置 pid,且未装 arms-rum MCP。
   解决方案:
     a. 把 ARMS 应用 ID 写入 CLAUDE.md `## ARMS 巡检配置 — 即时巡检（arms agent）` 节
     b. 或者装 arms-rum MCP(见 references/mcp-setup.md § 3.4),再重跑 /arms
   ```
   **停止**

## 4. 派发给 arms

```
SendMessage(to: "arms"):
任务: ARMS 即时巡检
- pid: <来自 CLAUDE.md / 用户选择>
- env: <解析得到, 默认 prod>
- days: <解析得到, 默认 7>
- keywords: <解析得到, 可空>
- ak_id: <CLAUDE.md sls_ak_id>
- ak_secret: <CLAUDE.md sls_ak_secret>
- region: <CLAUDE.md sls_region>
- project: <CLAUDE.md sls_project>
- logstore: <CLAUDE.md sls_logstore>

按 onboarding § arms 的 7 步流程执行,完成后回报 findings.md 路径 + 推荐派单。
```

## 5. 收到 arms 回报后

arms 回报包含: 异常聚合数、最高频异常、推荐派单角色、findings.md 路径、拟分支名、历史对比(新问题/相似/复发)。

按场景分支:

- **新问题或相似命中** → SendMessage(to: 推荐角色) 派 dev,消息含:
  ```
  source: arms
  arms_task_id: arms-<YYYYMMDD>-<NNN>
  findings_path: .plans/<project>/arms/<task-id>/findings.md
  branch: fix/arms-<task-id>
  mr_skip: true
  commit_template: arms
  ```
- **复发(精确命中 status=resolved)** → 不派 dev,直接告知用户:
  ```
  ARMS 复发: <fingerprint>
  上次修复 commit: <hash>(分支 <branch>)
  可能修复未合并到主干 / 修复有遗漏 / 同一根因新场景。
  要重做分析吗? 还是先 git 合并查看?
  ```
- **已有进行中(精确命中 status=analyzed)** → 告知用户:
  ```
  已有 in-progress 的 arms 任务: <task-id>
  当前状态: analyzed(已写 findings,等 dev 实施)
  要催 dev 吗? 还是查看现有报告?
  ```

## 6. dev 完成 + reviewer [OK] 后

team-lead 通知 arms 补 resolution:

```
SendMessage(to: "arms"):
任务: 补 resolution
- arms_task_id: <task-id>
- commit: <hash>
- branch: <branch>
- reviewer_verdict: [OK]
- 完整审查报告: <reviewer findings 路径>

补写 resolution.md + 更新 archive/index.md status=resolved。
```

## 7. 最终给用户的总结

```
ARMS 任务完成:
- 根因: <一句话, 取自 findings.md>
- 分支: fix/arms-<task-id>
- commit: <hash>(本地, 未推送)
- reviewer: [OK]
- 归档: .plans/<project>/arms/<task-id>/(含 findings + resolution + fingerprint)
- 请自行走你的合并流程。
```

## 8. 后续 — 用户决定不修时

任何时候用户对一个已分析(`status=analyzed`)的 arms 任务说"先不修了" / "可以忽略" / "这个不用管":

```
SendMessage(to: "arms"):
任务: 标记 ignored
- arms_task_id: <task-id>
- 忽略原因: <转述用户的一句话, 如"业务方接受该报错">
按 onboarding § 用户决定不修时(ignored) 更新 archive。
```

更新完成后,下次同指纹再出现 arms 会按"复发"路径报告(而非新问题),用户能看到"这个之前你说不用管,现在又复现了"。

## 注意

- **本命令不走 MR**: ARMS 任务的 dev 子协议是"本地 commit + 不 push"(见 references/roles.md § dev → ARMS 子协议),与 intake / feat 任务的 MR 流互不影响
- **不替代 CRON 巡检**: `/arms` 是"现在想立刻看一眼"的场景;每日定时扫描请用 `/ccteam-scan` (走 bug-triage + intake 流)
- **凭证只在会话内**: arms agent 不持久化 ak_secret,不会写入 fingerprint.md / findings.md
- **频繁调用注意 SLS 配额**: SLS 查询有 RPS 上限,默认 days=7 一次查 500 条,正常使用不会触限
