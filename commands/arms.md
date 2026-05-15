---
description: ARMS 即时巡检 — 查 SLS RUM 异常、分析根因、自动派 dev 修复
---

立即触发一次 ARMS RUM 异常分析。team-lead 请按以下步骤操作。

> **设计原则**: 这个命令是"零门槛即时可用"的——遇到缺失依赖(团队没 arms、CLAUDE.md 没配置)**不要直接报错**,而是**用 AskUserQuestion 交互式补全**。死胡同提示是最差的 UX。

## 1. 前置: 团队存在 & 项目识别

1. 读 `.plans/` 下的项目目录,确定 `<project>`(通常一个目录)
2. 读 `.plans/<project>/team-snapshot.md`:
   - **不存在** → 直接报错: "请先 `/CCteam-creator-cn` 组团后再运行 `/arms`",停止
   - 存在 → 进入 §2

## 2. 检查 + 补全 ARMS 即时巡检配置(CLAUDE.md)

读项目 CLAUDE.md,在文中 grep `## ARMS 巡检配置 — 即时巡检（arms agent）`:

- **节存在且齐全**(pid + sls_region + sls_project + sls_logstore + sls_ak_id + sls_ak_secret 全有,且**非占位值**) → 直接读出参数,进入 §3
- **节缺失 / 字段不全 / 字段值是占位** → **交互式补全**:

  **占位识别**(任一为真即视为缺失):
  - 包含 `<...>` 包裹(如 `<your-pid>`、`<ACCESS_KEY>`)
  - 等于 `your-...` / `xxx` / `TODO` / `FIXME` / `your-pid-here` 等明显占位
  - 长度 < 8 字符(凭证字段)

  **补全流程**:

  1. 优先用 **AskUserQuestion**(适合有限选项):
     - "SLS region?" — 选项: `cn-hangzhou` / `cn-shanghai` / `cn-beijing` / 其他
     - "默认查询环境?" — 选项: `prod` / `daily` / `pre` / 全部环境
  2. 文本输入(用普通消息问,**一次一组**避免界面拥挤):
     - "请把以下信息粘进来(可分多次回复):
       1) ARMS RUM 应用 PID (如 `c67ee5ri5a@a02e69a18ed6a39`)
       2) SLS project 名
       3) SLS logstore 名 (通常含 `rum`)"
     - 收齐后再问凭证:
       "请把只读 RAM 子账号的 **AK ID** 和 **AK Secret** 粘进来(两个值,各一行)。建议用只读策略,如 `aliyun-log-read-only`"
  3. **写入 CLAUDE.md**: 用 Edit 工具在 CLAUDE.md 末尾追加(若已有该 section 则替换 section 而非整文件覆盖),内容用 references/templates.md § 即时巡检（arms agent）的模板填充。**写完确认一次,然后继续 §3**
  4. 顺带提醒用户: "已把配置写入 CLAUDE.md。建议下次把 `sls_ak_*` 改为环境变量引用(如 `${SLS_AK_ID}`)以提升安全性,但现在我会用明文凭证跑本次分析"

  > **可选**: 如果项目装了 `arms-rum` MCP(检查工具列表是否含 `mcp__arms-rum__GetRumApps`),且用户不知道 PID,可以直接调 GetRumApps 拉应用列表,用 **AskUserQuestion** 让用户选,**省去手输 PID 这一步**。

## 3. 解析参数

从用户附带的自然语言或显式参数中识别(参数可省,用默认):

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pid` | CLAUDE.md `pid` | ARMS RUM 应用 ID |
| `env` | `prod` | 环境过滤(prod/daily/pre/all);显式指定才查非生产 |
| `days` | 7 | 回溯天数 |
| `keywords` | 空 | 错误消息子串过滤(透传给 SLS query) |

**示例语义识别**:
- "/arms" → 默认全套
- "/arms env=all" / "查一下所有环境" → env=all
- "/arms days=1" / "最近 1 天" → days=1
- "/arms keywords=验证码" / "查含验证码的错误" → keywords=验证码

## 4. 检查 + 补全 arms 角色

读 team-snapshot.md 的花名册:

- **arms 在花名册** → 进入 §5,SendMessage 派单
- **arms 不在花名册** → **不要报错**,临时 spawn arms(参考 /ccteam-scan 对 bug-triage 的处理):

  ```
  Agent(
    subagent_type: "general-purpose",
    model: "sonnet",
    team_name: "<当前团队名,从 team-snapshot 头信息读>",
    description: "ARMS 即时巡检",
    prompt: <把 cn/skills/CCteam-creator-cn/references/onboarding.md § arms 整段 + 本次任务参数(§3 解析得到的 pid/env/days/keywords + CLAUDE.md 的 ak/secret/region/project/logstore)拼起来>,
    run_in_background: false
  )
  ```

  spawn 时**带上 team_name 参数**,这样 arms 会加入团队、能用 SendMessage 与其他 agent 通信。本次会话结束后是否保留在花名册由用户决定(见 §8)。

  > **临时 spawn 与花名册 spawn 的区别**: 临时 spawn 把任务参数**直接拼进 prompt**(一次性发送);花名册 spawn 是先 SendMessage 然后 agent 按 onboarding 接受任务。临时 spawn 走完即结束,花名册 spawn 留存待复用。

## 5. 派发给 arms (仅花名册路径)

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

> **§5 提示**: 上面的 `按 onboarding § arms 的 7 步流程` 假设 arms 已经被 spawn 过且 onboarding prompt 已经在它的会话里。如果 §3 走的是"临时 spawn"路径,onboarding prompt 已在 spawn 时一次性传入,这里 SendMessage 就只传任务参数。

## 6. 收到 arms 回报后

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

## 7. dev 完成 + reviewer [OK] 后

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

## 8. 最终给用户的总结

```
ARMS 任务完成:
- 根因: <一句话, 取自 findings.md>
- 分支: fix/arms-<task-id>
- commit: <hash>(本地, 未推送)
- reviewer: [OK]
- 归档: .plans/<project>/arms/<task-id>/(含 findings + resolution + fingerprint)
- 请自行走你的合并流程。
```

**临时 spawn 场景的额外问询**: 如果 §3 是临时 spawn(arms 不在 team-snapshot 花名册),最后多问一句:

```
本次是临时 spawn arms 跑的。要不要把 arms 永久加入团队花名册?
- 是: 我会把 arms 条目写入 .plans/<project>/team-snapshot.md, 以后 /arms 直接复用
- 否: 当前会话结束 arms 状态丢失, 下次 /arms 仍会临时 spawn
```

是 → Edit team-snapshot.md 花名册表追加 arms 行。

## 9. 后续 — 用户决定不修时

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
