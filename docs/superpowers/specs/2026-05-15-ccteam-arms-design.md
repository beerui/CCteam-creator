# CCteam-creator ARMS 端到端闭环 — 设计文档

| 字段 | 值 |
|------|-----|
| 文档日期 | 2026-05-15 |
| 作者 | motou |
| 状态 | Draft |
| 基础版本 | 0.1.3 (已有阿里云集成: bug-triage / dev MR / intake / /ccteam-scan / CRON) |
| 语言 | 本轮仅 cn 中文版, en 版暂不维护 |

---

## 1. 背景与目标

### 1.1 现有状态

当前 CCteam-creator 0.1.3 已有阿里云生态集成:
- `bug-triage` 角色: 拉禅道 Bug 单 / ARMS cron 巡检, 翻译外部数据到 intake 文件
- `dev` MR 协议: git push + Yunxiao MCP 创建 MR
- `/ccteam-scan` 斜杠命令
- Intake Processing Protocol (6 状态机)
- MCP 安装指南 (zenTao / Yunxiao / aliyun-observability)

### 1.2 本次改造目标

让 CCteam-team-lead 下的团队能**主动处理 ARMS RUM 前端异常**, 形成完整闭环:

```
用户 /arms 或自然语言
  ↓
team-lead 路由
  ↓
arms 角色 (只读): 查 SLS → 分析根因 → 写 findings → 归档指纹
  ↓
team-lead 自动派 dev
  ↓
dev 实施 → reviewer 审查 → 本地 commit (不走 MR)
  ↓
用户审查 → 自行合并或重做
  ↓
归档 (指纹入库 → 下次可检出复发)
```

### 1.3 核心决策记录

| 决策 | 结论 | 原因 |
|------|------|------|
| bug-triage 升级? | 不升级,独立新建 `arms` 角色 | bug-triage 定位是外部数据翻译, arms 需要分析代码+根因能力 |
| 组团降级? | 不降级,团队是前置条件 | 任务需要持久化 .plans/ 归档和对比 |
| 实施前等确认? | 不等,一气呵成 | 快速闭环, reviewer 做质量门 |
| 走 MR? | 不走,本地 commit | 用户项目无法合并到 dev 分支 |
| 失败升级方式 | 统一 escalate team-lead (3-Strike) | agent 判断类型复杂, team-lead 统一处理 |
| 数据来源 | SLS 直查 (logstore-rum) | ARMS RUM 数据存在 SLS; mcp-server-aliyun-observability 无 RUM 工具 |
| SLS 查询方式 | 纯 prompt 内嵌 Python 指令 | 不依赖额外 MCP/脚本文件, agent 用 Bash 执行 |
| 默认环境 | 生产 (prod) | 安全性考量, 用户显式指定才查其他环境 |
| PID 获取 | 优先 CLAUDE.md 配置, 无则 GetRumApps 列应用让用户选 | 项目预先配好最常用应用 |

### 1.4 不做的事

- ❌ 自动合并到 dev/prod 分支 (用户手动合并)
- ❌ CRON 自动巡检 (后期单独设计)
- ❌ ARMS 上线后验证回路
- ❌ 多源去重融合 (zentao + arms 同一问题的跨源关联)
- ❌ 回写禅道

---

## 2. 角色: arms

### 2.1 角色定义

| 字段 | 值 |
|------|-----|
| Name | `arms` |
| subagent_type | `general-purpose` |
| model | `sonnet` |
| 读取权限 | SLS RUM 数据 + 项目源码 (只读) |
| 写入权限 | `.plans/<project>/arms/` 目录 (含 archive/) |
| 不写 | 项目源码、其他 agent 的 .plans/ 目录 |
| 依赖 | SLS logstore-rum 可查 + CLUADE.md `## ARMS 巡检配置` 段 |
| 触发 | `/arms` 斜杠命令 / 自然语言 ARMS 关键词 |

### 2.2 与其他角色的边界

| 维度 | arms | bug-triage | backend-dev / frontend-dev |
|------|------|-------------|---------------------------|
| 触发源 | 用户主动 `/arms` | 禅道 / 未来 CRON | 用户主动需求 / arms 派单 / intake accept |
| 写源码 | ❌ 不写 | ❌ 不写 | ✅ 写 |
| 分析深度 | ✅ 交叉代码定位根因 | ❌ 只翻译外部数据 | ✅ 实现修复 |
| 输出 | findings + fingerprint | intake 文件 | commit (含 ARMS 任务: 不走 MR) |
| 历史对比 | ✅ 自身 archive | ❌ 无 | ❌ 无 |

### 2.3 触发方式

详见第 4 节。

---

## 3. 核心流程: 7 步闭环

### 3.1 完整调用关系

```
用户 → "/arms" / "查一下 arms 的问题"
   ↓
team-lead 路由 + [团队存在性检查]
  .plans/<project>/team-snapshot.md 不在 → 报错引导率先 /CCteam-creator-cn 组团
   ↓
SendMessage(arms, { pid, env, days, keywords, ak_id, ak_secret, region, project, logstore })
```

### 3.2 arms 内部 7 步

```
 ┌─ [step 1] 读 PID ──────────────────────────────────
 │  1.1 从 team-lead 消息中取 pid
 │  1.2 pid 为空 → 调 aliyun-sdk API GetRumApps
 │      → 列出应用 → team-lead 报告用户选
 │  1.3 确定: {app_name, pid, env(默认prod)}
 └──────────────────────────────────────────────────────
          ↓
 ┌─ [step 2] 历史对比 ──────────────────────────────
 │  动作: grep .plans/<project>/arms/archive/index.md
 │        fingerprint: exception.message.convergence + " @ " + view.name.convergence
 │  输出: 精确命中 / 相似命中 / 无记录
 │  → 精确命中且 resolved → 回报 "复发" (跳过分析)
 │  → 精确命中且 analyze → 回报 "进行中"
 │  → 相似命中 → 继续分析, findings 追加参考节
 │  → 无记录 → 正常走
 └──────────────────────────────────────────────────────
          ↓
 ┌─ [step 3] 查询 SLS ──────────────────────────────
 │  动作: Bash tool 执行 Python 查询
 │  ┌───────────────────────────────────────────────┐
 │  │ from aliyun.log import LogClient, GetLogsRequest │
 │  │ client = LogClient(f"https://{region}.log.aliyuncs.com", ak_id, ak_secret)
 │  │ req = GetLogsRequest(project, logstore,
 │  │     fromTime=now - days*86400,
 │  │     toTime=now,
 │  │     query=f"app.id:{pid} AND event_type:exception AND app.env:{env}")
 │  └───────────────────────────────────────────────┘
 │  失败 3 次 → escalate team-lead
 └──────────────────────────────────────────────────────
          ↓
 ┌─ [step 4] 聚合分析 ──────────────────────────────
 │  4.1 按 exception.message.convergence 分组计数
 │  4.2 过滤已知噪声 (CLAUDE.md arms_ignore_patterns)
 │  4.3 取堆栈 → Read 对应源码 → 交叉定位
 │  4.4 输出: 异常聚合表 + 每种的根因 + 修复方案推荐
 │  失败(定位不出) 3 次 → escalate team-lead
 └──────────────────────────────────────────────────────
          ↓
 ┌─ [step 5] 写 findings.md ──────────────────────────
 │  路径: .plans/<project>/arms/<task-id>/findings.md
 │  内容:
 │  - 概览 (应用/环境/PID/时间)
 │  - 异常聚合表 (错误 | 环境 | 页面 | 次数 | 最新)
 │  - 根因分析 (堆栈+代码定位)
 │  - 修复方案推荐 (方案 A / 方案 B)
 │  - 推荐派单 (backend-dev / frontend-dev)
 │  - 拟分支名: fix/arms-<task-id>
 └──────────────────────────────────────────────────────
          ↓
 ┌─ [step 6] 归档 ─────────────────────────────────────
 │  写 fingerprint.md + 更新 archive/index.md
 │  详见第 5 节
 └──────────────────────────────────────────────────────
          ↓
 ┌─ [step 7] 回报 team-lead ──────────────────────────
 │  ┌─────────────────────────────────────────────────┐
 │  │ ARMS 分析完成:                                    │
 │  │ - 应用: 大集客服 (daily)                          │
 │  │ - 异常聚合: 3 种, 最高频 "xxx" (N次)              │
 │  │ - 环境: prod  /  回溯: 7 天                       │
 │  │ - 推荐派单: frontend-dev                           │
 │  │ - 分析报告: .plans/arms/<id>/findings.md          │
 │  └─────────────────────────────────────────────────┘
 └──────────────────────────────────────────────────────
```

### 3.3 team-lead 接回报后

```
team-lead:
  1. 给用户的简报:
     "ARMS 分析完成, 大集web(prod) 发现 X 种异常:
      - conv list failed 8次 [P2]
      - token无效 2次 [P3]
      已派 frontend-dev 处理, 分支 fix/arms-<id>"

  2. SendMessage(frontend-dev, {
       source: "arms",
       findings_path: ".plans/arms/<id>/findings.md",
       branch: "fix/arms-<id>",
       task_metadata: {
         arms_id: "<id>",
         mr_skip: true,          // ARMS 任务不走 MR
         commit_template: "arms"  // 用 ARMS commit 模板
       }
     })

  3. dev 内部:
     - Read findings.md
     - 创建 .plans/<agent>/task-arms-<id>/ 三件套
     - git checkout -b fix/arms-<id>
     - 实施
     - SendMessage(reviewer) 内部 review
     - [OK] → 本地 commit (不 push)
     - 回报 team-lead

  4. team-lead 通知 arms "完成, commit <hash>"
     → arms 补写 resolution.md
     → 更新 archive/index.md status=resolved

  5. team-lead 给用户最终总结:
     "修复完成:
      - 根因: <一句话>
      - 分支: fix/arms-<id>
      - commit: <hash>
      - reviewer: [OK]
      - 请自行走你的合并流程"

  6. 用户决定:
     - "OK / 收到" → 流程结束
     - "重做 / 改方向" → team-lead 重派 arms
```

### 3.4 findings.md 关键字段

| SLS 字段 | 含义 | agent 用途 |
|-----------|------|-----------|
| `exception.message` | 原始错误消息 | 展示给用户/dev |
| `exception.message.convergence` | 聚合后消息 (去参数差异) | 指纹匹配 + 分组 |
| `exception.stack` | JS 堆栈 | 定位代码文件:行号 |
| `view.name` | 页面 URL | 复现入口 |
| `view.name.convergence` | 聚合后页面路径 | 指纹匹配 |
| `app.env` | 环境 (prod/daily/pre/local) | 严重度判断 |
| `event_id` | 唯一事件 ID | 追溯 |
| `session.id` | 会话 ID | session 回放 |
| `user.id` | 用户标识 | 业务上下文 |
| `times` | 同 session 发生次数 | 频次分析 |

---

## 4. 触发方式

### 4.1 斜杠命令: `/arms`

文件: `commands/arms.md`

```markdown
---
description: ARMS 即时巡检 — 拉 RUM 错误事件、分析并派单
---

## 用法

/arms [pid=<PID>] [env=<ENV>] [days=<N>] [keywords=<KW>]

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| pid | CLAUDE.md `ARMS 巡检配置 > pid` | 应用 PID; 无则 GetRumApps 列应用选 |
| env | **prod** | 环境过滤; 显式指定才查非生产 |
| days | 7 | 回溯天数 |
| keywords | 空 | 错误消息关键词过滤 |

## 示例

- `/arms` — 默认查当前应用的生产 7 天错误
- `/arms env=all` — 查所有环境
- `/arms days=1` — 最近 1 天
- `/arms keywords=验证码` — 过滤含"验证码"的错误

## 控制流

1. 检查 .plans/<project>/team-snapshot.md 存在否
   → 不存在: "请先 /CCteam-creator-cn 组团后再运行 /arms"
2. team-lead 补全参数 (read CLAUDE.md 的 ARMS 配置)
3. 无 pid → GetRumApps → AskUser 选应用
4. SendMessage(arms, {pid, env, days, keywords, ak, secret, region, project, logstore})
5. arms 回报后 → 派 dev
6. dev 完成 + reviewer [OK] → 归档
```

### 4.2 自然语言触发

team-lead 从用户输入识别:

| 用户输入 | 意图 |
|----------|------|
| "查一下 arms" / "巡检" / "扫 arms" | 默认巡检 |
| "看看 / 查一下 <trace>" | 特定事件 |
| "arms 最近有什么问题" | 默认 7 天 |
| "arms 生产环境" | env=prod |
| 含 `arms` + `查/看/扫/巡检` 等 | → 路由给 arms |

---

## 5. 历史档案 + 指纹匹配

### 5.1 指纹定义

```
fingerprint = exception.message.convergence + " @ " + view.name.convergence
```

### 5.2 存档结构

```
.plans/<project>/arms/
├── task_plan.md              ← arms 总览
├── findings.md               ← INDEX
├── progress.md               ← 工作日志
├── archive/
│   └── index.md              ← 指纹库 (grep-able)
│
└── <task-id>/
    ├── findings.md           ← 分析报告 (arms 写)
    ├── fingerprint.md        ← 指纹数据 (arms 写)
    ├── progress.md           ← 工作日志
    └── resolution.md         ← dev 完成后补写
```

### 5.3 archive/index.md 格式

```markdown
# ARMS Archive Index

## 2026-05
| task-id | fingerprint | env | severity | status | resolved_at |
|---------|-------------|-----|----------|--------|------------|
| arms-20260514-001 | conv list failed: 33001 @ /agent | daily | P2 | resolved | 2026-05-14 |
| arms-20260515-001 | token无效或已过期 @ /agent | daily | P3 | analyzed | — |

## 2026-04
...
```

### 5.4 fingerprint.md 格式

```markdown
---
task_id: arms-20260514-001
source: arms_rum
pid: c67ee5ri5a@a02e69a18ed6a39
app_name: 大集客服
env: daily
status: resolved
created_at: 2026-05-14T10:00:00+08:00
resolved_at: 2026-05-14T16:00:00+08:00
---

## 指纹

- convergence_message: conv list failed: 33001
- convergence_view: /agent
- full_message: conv list failed: 33001
- stack_summary: at onResponse (xxx.js:631:67170)

## 修复方案

- 原因: API 超时未处理
- 方案: 增加重试逻辑
- 分支: fix/arms-20260514-001
- commit: abc1234
- reviewer: [OK]
```

### 5.5 匹配判定

| 结果 | 条件 | 行为 |
|------|------|------|
| 精确命中 + resolved | fingerprint (含 env) 一致 | 跳过, 回报"复发 — 上次修复方案: <方案>" |
| 精确命中 + analyzed | 同上, 但未完成 | 跳过, 回报"已有进行中的任务" |
| 相似命中 | view 一致, message 不同 | 继续分析, findings 追加"同页面历史参考" |
| 无匹配 | grep 无结果 | 正常走 step 3-7 |

### 5.6 生命周期

| 阶段 | 触发 | 动作 |
|------|------|------|
| created | arms 完成分析 | 写 fingerprint.md + 更新 index status=analyzed |
| resolved | dev 完成 + reviewer [OK] | arms 补 resolution.md + 更新 index status=resolved |
| ignored | 用户说"不修" | 更新 index status=ignored |
| expired | resolved/ignored > 30 天 | custodian 移 archive/expired/ |

---

## 6. SLS 查询实现

### 6.1 纯 prompt 方案

arms agent 的 SLS 查询不依赖独立脚本或 MCP, 而是通过 onboarding prompt 中的 Python 指令, 用 Bash tool 执行:

```
步骤: 查询 SLS RUM logstore

1. 确认 Python SDK 可用:
   python3 -c "from aliyun.log import LogClient"

2. 执行查询 (team-lead 在 SendMessage 中传入了 ak_id/ak_secret/region/project/logstore):
   python3 -c "
from aliyun.log import LogClient, GetLogsRequest
client = LogClient('https://{region}.log.aliyuncs.com', '{ak_id}', '{ak_secret}')
req = GetLogsRequest('{project}', '{logstore}',
    fromTime={from_ts}, toTime={to_ts},
    query=\"app.id:{pid} AND event_type:exception AND app.env:{env}\",
    line=20)
resp = client.get_logs(req)
for log in resp.get_logs():
    d = log.get_contents()
    print(d.get('exception.message'), d.get('view.name'))
   "
```

### 6.2 凭证传递

- `ak_id`, `ak_secret`, `region`, `project`, `logstore` → 配在 CLAUDE.md `## ARMS 巡检配置`
- team-lead 在 SendMessage 时从 CLAUDE.md 读出来传给 arms
- arms agent 仅在本次会话中使用, 不持久化

---

## 7. 文件改动

| # | 文件 | 操作 | 内容 |
|---|------|------|------|
| F1 | `cn/skills/CCteam-creator-cn/references/roles.md` | 改 | 新增 arms 角色定义 (只读+SLS+分析+归档) |
| F2 | `cn/skills/CCteam-creator-cn/references/onboarding.md` | 改 | 新增 arms 完整 onboarding prompt (7 步 + SLS 查询 + 档案) |
| F3 | `cn/skills/CCteam-creator-cn/references/templates.md` | 改 | 新增: CLAUDE.md ARMS 配置节 / archive/index.md 模板 / fingerprint.md 模板 / resolution.md 模板 |
| F4 | `cn/skills/CCteam-creator-cn/SKILL.md` | 改 | 角色推荐表加 arms / Step 1.2.4 ARMS 问询 / Key Rules 加 arms 规则 |
| F5 | `commands/arms.md` | 新建 | `/arms` 斜杠命令描述 |
| F6 | `cn/skills/CCteam-creator-cn/references/roles.md` | 改 | dev 端 ARMS 子协议 (不 push, 本地 commit) |
| F7 | `cn/skills/CCteam-creator-cn/references/onboarding.md` | 改 | dev onboarding 追加 ARMS 来源说明 |

### 7.1 开发顺序

```
Phase 1: F1 roles.md → F2 onboarding.md → F3 templates.md
Phase 2: F4 SKILL.md → F5 commands/arms.md
Phase 3: F6 roles.md append → F7 onboarding.md append
Phase 4: grep 一致性检查 + 冒烟测试
```

---

## 8. 验收标准

- [ ] `/arms` 命令在团队不存在时报错引导
- [ ] arms agent 能读 CLAUDE.md 的 PID 配置拿应用
- [ ] PID 未配置时 GetRumApps 列出应用让用户选
- [ ] arms agent 能通过 Python SLS SDK 查到 exception 数据
- [ ] 历史对比: 相同 fingerprint 识别为"复发", 跳过分析
- [ ] findings.md 字段齐全 (聚合表 + 根因 + 方案 + 派单)
- [ ] fingerprint.md + archive/index.md 写入正确
- [ ] team-lead 收到回报后自动派 dev
- [ ] dev 接到 ARMS 任务走"本地 commit, 不 push"子协议
- [ ] reviewer 审查通过后才算完成
- [ ] dev 完成后 arms 补 resolution.md + 更新 archive
- [ ] 用户不修 → 更新 archive status=ignored
- [ ] 全流程不依赖额外 MCP (仅 pip install aliyun-log-python-sdk 一次)

---

## 9. 不在本期范围

- CRON 自动 ARMS 巡检 (后续独立设计)
- ARMS 后端 APM / Trace 链路分析 (当前只有 RUM)
- 多触发源跨源去重融合
- ARMS 上线后验证回路
- 自动合并到 dev/prod 分支
- en 英文版同步
