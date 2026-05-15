## 整体调用关系

### 整体流程
研发输入(任一)
    ├─ 自然语言: "查一下 arms 现在的问题"
    ├─ 自然语言: "看一下 arms trace abc123"
    ├─ 斜杠命令: /arms  或  /arms abc123
    └─
     ↓
  team-lead 路由 + [团队存在性检查]
     ↓
  SendMessage(arms)
     ↓
  arms 内部 (read-only on code):
    1. 历史对比 grep .plans/<project>/arms/archive/index.md
    2. 拉 ARMS 数据 (aliyun-observability MCP)
    3. Read 相关代码 + 交叉分析根因
    4. 在 .plans/<project>/arms/<id>/ 创建 task folder, 写:
         - task_plan.md
         - findings.md  (复现 + 根因 + 修复方案 + 拟分支名 + 推荐派单对象)
         - progress.md
         - fingerprint.md (堆栈+消息+路径,供下次 grep)
    5. 更新 archive/index.md 指纹索引
    6. 回报 team-lead 含推荐派单
     ↓
  team-lead 立即派 dev (无中转用户):
    SendMessage(backend-dev | frontend-dev) 含:
      - arms findings.md 路径
      - task metadata: source=arms  ← 触发 dev 的"本地 commit,不 push"子协议
     ↓
  dev 内部:
    - 在 .plans/<project>/<agent>/task-arms-<id>/ 创建 task folder
         - task_plan.md (Read 自 arms findings)
         - findings.md  (实施过程发现)
         - progress.md  (实施日志)
    - git checkout -b fix/arms-<id>
    - 实施
    - SendMessage(reviewer) 内部 review
    - [OK] → 本地 commit (按 ARMS commit 模板,不 push)
    - 回报 team-lead
     ↓
  team-lead 通知 arms "完成,commit <hash>"
     ↓
  arms 在 .plans/<project>/arms/<id>/ 补写:
    - resolution.md (commit hash + branch + reviewer verdict)
    - 更新 archive/index.md 标记为 resolved
     ↓
  team-lead 给用户的总结:
    - 复用历史 / 新问题
    - 根因一句话
    - 实施摘要 (改了什么)
    - reviewer verdict
    - 本地分支名 + commit hash
    - "请自行走你的合并流程"
     ↓
  用户决定:
    ├─ "OK / 收到"       → 流程结束 (用户自己走合并)
    └─ "重做 / 改方向"   → team-lead 重派 arms

### 文件结构 (.plans 视角)

  .plans/<project>/
    arms/                                ← arms agent 根 (NEW)
      task_plan.md                       ← arms 总览
      findings.md                        ← INDEX 链向各 task folder
      progress.md                        ← 工作日志
      archive/
        index.md                         ← 指纹库 (供 step 1 grep)
      <task-id>/                         ← 每个 ARMS 任务
        task_plan.md
        findings.md                      ← 复现+根因+方案+派单对象
        progress.md
        fingerprint.md                   ← 错误堆栈指纹
        resolution.md                    ← dev 完成后补写

    backend-dev/  (或 frontend-dev/)     ← 现有结构,新增一个 task folder
      task_plan.md                       ← agent 总览 (现有)
      findings.md                        ← INDEX (现有)
      progress.md                        ← 现有
      task-auth/                         ← 现有任务
        task_plan.md / findings.md / progress.md
      task-arms-<id>/                    ← NEW: arms 派来的任务
        task_plan.md (Read 自 arms)
        findings.md  (实施发现)
        progress.md  (实施日志)

  → task_plan.md / findings.md / progress.md 每个角色 + 每个 task folder 都有,不省。



## 按这个理解,研发的"一天"应该长这样:

| 时刻 | 研发动作 | AI 应该的状态 | 现状差距 |
| --- | --- | --- | --- |
| 项目首次接入 CCteam | 跑一个命令，比如 `/ccteam-init` | 扫描代码 → 反向生成项目规则、架构、任务模板，落到项目根可见位置 | 完全缺（这是 A2+C1+C2+C3 的真正含义） |
| 早上打开 IDE | 不做任何动作 | 已经加载项目所有规则、ARMS 巡检结果、待办 intake | 部分有（CLAUDE.md+intake）但研发不知道在哪、不可见 |
| 接到一个 bug 单 | 直接说「修一下禅道 12345」 | 自动按项目规则切分支、写代码、走 review、提 MR | 已支持（bug-triage+dev MR） |
| 写一个新功能 | 描述需求 | AI 按项目「任务卡片模板」先输出规划、再实施 | 任务卡片缺 |
| 想 review 一段代码 | 「review 一下这块」 | reviewer 角色按项目规则审 | reviewer 角色在，但触发方式不标准 |
| 跨会话/跨人接手 | 打开同一项目 | AI 知道之前进度、之前决定 | 已支持（.plans+CLAUDE.md）但需要懂结构 |
| 大任务召唤团队 | 「这个项目要重构 auth 模块，组团做」 | 才召唤完整 team（现有 5 步 setup） | 现状即满足 |



单次 ARMS 任务的 7 步序列

  用户 → "/arms" / "查一下 arms 的问题"
     ↓
  team-lead 路由 (团队存在检查)
     ↓
  SendMessage(arms, message: {source, keywords?, pid?})

  arms agent 收到后:

   ┌─ [step 1] 读 PID ──────────────────────────────────
   │  1.1 读 CLAUDE.md 的 `## ARMS 巡检配置` 节取 PID
   │  1.2 无配置 → 调 GetRumApps → 列应用 → AskUser "选哪个 PID"
   │  1.3 ✓ 定型: 大集web / 大集H5 / 大集客服
   └──────────────────────────────────────────────────────
            ↓
   ┌─ [step 2] 历史对比 ──────────────────────────────
   │  动作: grep .plans/<project>/arms/archive/index.md
   │        fingerprint: exception.message + view.name
   │  输出: 精确命中 / 相似命中 / 无记录
   │  (详见第 4 节)
   └──────────────────────────────────────────────────────
            ↓
   ┌─ [step 3] 查询 SLS ──────────────────────────────
   │  动作: SLS GetLogs 请求
   │     query = "app.id:{pid} AND event_type:exception"
   │     fromTime = 7 天前 (最新错误)
   │     toTime = now
   │     line = 20 (限最近 20 条)
   │  输出: List[dict] — 每条含:
   │    - timestamp, app.env
   │    - exception.message, exception.stack
   │    - view.name, user.id, session.id
   │  失败 3 次 → escalate team-lead (3-Strike)
   └──────────────────────────────────────────────────────
            ↓
   ┌─ [step 4] 聚合分析 ──────────────────────────────
   │  对 step 3 的结果做聚合:
   │  4.1 按 exception.message.convergence 分组计数
   │  4.2 排除已知噪声 (用户预设的 ignore patterns)
   │  4.3 聚合格式:
   │      message (收敛后) | 环境 | page | 次数 | stack (第一条)
   │  4.4 定位根因:
   │      - 读 stack 中 js 文件路径 → Read 对应源码
   │      - 读代码上下文 → 确认根因
   │  失败(分析不出来) 3 次 → escalate team-lead
   └──────────────────────────────────────────────────────
            ↓
   ┌─ [step 5] 写 findings.md ──────────────────────────
   │  路径: .plans/<project>/arms/<task-id>/findings.md
   │  模板:
   │  ┌─────────────────────────────────────────────────┐
   │  │ # ARMS 分析报告                                 │
   │  │                                                 │
   │  │ ## 概览                                         │
   │  │ - 来源任务: /arms <keywords>                    │
   │  │ - 应用: {app.name} ({app.env})                  │
   │  │ - PID: {pid}                                    │
   │  │ - 查询时间: {timestamp}                         │
   │  │                                                 │
   │  │ ## 异常聚合                                     │
   │  │ | 错误 | 环境 | 页面 | 次数 | 最新 |             │
   │  │ |------|------|------|------|------|             │
   │  │ | conv list failed | daily | /agent | 8 | ...  |│
   │  │                                                 │
   │  │ ## 根因分析                                     │
   │  │ - 关键堆栈: ...                                 │
   │  │ - 代码定位: {file}:{line}                       │
   │  │ - 根因描述                                      │
   │  │                                                 │
   │  │ ## 修复方案推荐                                 │
   │  │ 方案 A (推荐): {步骤}                           │
   │  │ 方案 B: {步骤}                                  │
   │  │                                                 │
   │  │ ## 推荐派单                                     │
   │  │ - 推荐角色: backend-dev / frontend-dev          │
   │  │ - 拟分支名: fix/arms-<task-id>                  │
   │  └─────────────────────────────────────────────────┘
   └──────────────────────────────────────────────────────
            ↓
   ┌─ [step 6] 写 fingerprint.md + archive ─────────────
   │  详见第 4 节
   └──────────────────────────────────────────────────────
            ↓
   ┌─ [step 7] 回报 team-lead ──────────────────────────
   │  回报格式(纯文本,简洁):
   │  ┌─────────────────────────────────────────────────┐
   │  │ ARMS 分析完成:                                   │
   │  │ - 应用: 大集客服 (daily)                         │
   │  │ - 异常聚合: 3 种, 最高频: "conv list failed:     │
   │  │   33001" (8次)                                   │
   │  │ - 推荐派单: frontend-dev                          │
   │  │ - 分析报告: .plans/arms/<task-id>/findings.md    │
   │  └─────────────────────────────────────────────────┘
   └──────────────────────────────────────────────────────

  2.2 team-lead 收到回报后

  team-lead:
    1. 展示给用户:
       "ARMS 分析完成, 大集客服(daily) 发现 3 种异常:
        - conv list failed 8次 [P2]
        - 会话已转接 2次 [P3]
        - token无效 2次 [P3]
        已派 frontend-dev 处理, 分支 fix/arms-<id>"

    2. SendMessage(frontend-dev, {findings_path, branch, source=arms})
       (立即派,不等用户,§1.3 已定)

    3. dev 完成后, (review → commit,不走MR)
       → 回报 team-lead
       → team-lead 通知 arms "归档"
       → arms 补写 resolution.md

  2.3 findings.md 字段对照说明

  ┌───────────────────────────────┬────────────────────────────┬───────────────────────┐
  │          fields 字段          │            含义            │         用途          │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ exception.message             │ 原始错误消息               │ dev 看错误原文        │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ exception.message.convergence │ 聚合后的消息               │ 去差异分组(URL参数等) │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ exception.stack               │ JS 堆栈                    │ 定位代码              │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ view.name                     │ 页面 URL                   │ 复现入口              │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ app.env                       │ 环境(prod/daily/pre/local) │ 判断严重性            │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ event_id                      │ 唯一事件 ID                │ 追溯单次              │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ session.id                    │ 会话 ID                    │ 完整 session 回放     │
  ├───────────────────────────────┼────────────────────────────┼───────────────────────┤
  │ exception.binary_images       │ sourcemap 映射             │ dev 分析用            │
  └───────────────────────────────┴────────────────────────────┴───────────────────────┘




  触发方式 — /arms 斜杠命令 + 自然语言

  3.1 两条触发路径

  触发路径 A: 斜杠命令 "/arms"
    ── 适用: 用户主动巡检 / 快速查询
    ── 格式: /arms [参数...]
    ── 特性: 参数结构固定, 解析稳定

  触发路径 B: 自然语言
    ── 适用: 日常随意触发
    ── 示例: "查一下 arms 现在的问题"
             "看看 arms trace abc123"
             "大集web 最近有什么错误"
    ── 特性: team-lead 从语义中提取参数

  3.2 /arms 斜杠命令

  文件: commands/arms.md

  ---
  description: ARMS 即时巡检 — 拉 RUM 错误事件, 分析并派单
  ---

  ## 用法

  /arms [pid=<PID>] [env=<env>] [days=<N>] [keywords=<keyword>]

  ## 参数

  | 参数 | 默认值 | 说明 |
  |------|--------|------|
  | pid | CLAUDE.md 中配置 (ARMS 巡检配置 > pid) | 应用 PID, 有配置优先; 无则不传则列应用让用户选 |
  | env | 全部 | 环境过滤, prod / daily / pre / local |
  | days | 7 | 回溯天数 |
  | keywords | 空 | 错误消息关键词过滤 |

  ## 例子

  - `/arms` — 查当前项目默认应用的最近错误
  - `/arms env=prod` — 只查生产环境
  - `/arms days=1` — 查最近 1 小时错误
  - `/arms keywords=验证码` — 查"验证码"相关错误
  - `/arms pid=c67ee5ri5a@xxx env=daily days=3`

  ## 控制流

  1. 检查 .plans/<project>/team-snapshot.md 是否存在
     - 不存在 → "请先 /CCteam-creator-cn 组团后再运行 /arms"
  2. team-lead 补全参数
     - 无 pid 传 → Read CLAUDE.md 的 ARMS 巡检配置段
     - 无配置 → GetRumApps 列应用 → AskUser
  3. SendMessage(arms, {pid, env, days, keywords})
  4. arms 分析完成后 →
     - team-lead 展示给用户
     - SendMessage(dev, source=arms)
  5. dev 完成 + reviewer [OK] → team-lead 通知 arms 归档

  3.3 自然语言触发规则

  team-lead 从用户输入中识别这些关键词:

  ┌───────────────────────────────────────┬─────────────────┐
  │                用户说                 │      意图       │
  ├───────────────────────────────────────┼─────────────────┤
  │ "查一下 arms" / "巡检" / "扫 arms"    │ 默认巡检        │
  ├───────────────────────────────────────┼─────────────────┤
  │ "看看 / 看下 / 查一下 <trace 或 PID>" │ 特定 PID 或事件 │
  ├───────────────────────────────────────┼─────────────────┤
  │ "arms 最近有什么问题"                 │ 默认 7 天       │
  ├───────────────────────────────────────┼─────────────────┤
  │ "arms 生产环境"                       │ env=prod        │
  ├───────────────────────────────────────┼─────────────────┤
  │ "/arms"                               │ 直接命中命令    │
  └───────────────────────────────────────┴─────────────────┘

  识别规则: 包含 arms + 查/看/扫/巡检 等动作词 → 路由给 arms。

  3.4 团队不存在时的行为

  不自动组团,只报错引导:

  未检测到团队的 .plans/<project>/team-snapshot.md。
  请先运行 /CCteam-creator-cn 配置团队, 再执行巡检。


  历史档案 + 指纹匹配 + 归档策略

  4.1 指纹定义

  fingerprint = exception.message.convergence + " @ " + view.name.convergence

  从 SLS 返回的数据中取 exception.message.convergence 和 view.name.convergence 两个字段拼接:

  例: "conv list failed: 33001 @ /agent"
  例: "token无效或已过期 @ /agent"
  例: "global is not defined @ /agent/login"

  4.2 匹配判定

  archive/index.md 格式

  # ARMS Archive Index

  ## 2026-05
  | task-id | fingerprint | severity | env | resolved_by | resolution |
  |---------|-------------|----------|-----|-------------|------------|
  | arms-20260514-001 | token无效或已过期 @ /agent | P3 | daily | backend-dev | fix/arms-20260514-001, 已合入 daily |
  | arms-20260514-002 | conv list failed: 33001 @ /agent | P2 | daily | backend-dev | fix/arms-20260514-002, 已合入 daily |

  ## 2026-04
  ...

  匹配规则

  ┌──────────┬─────────────────────────────────────────────┬───────────────────────────────────────┐
  │   结果   │                    条件                     │               arms 行为               │
  ├──────────┼─────────────────────────────────────────────┼───────────────────────────────────────┤
  │ 精确命中 │ fingerprint 完全一致(含 env)                │ 跳过→报告"复发(上次修复于 , 方案: )"  │
  ├──────────┼─────────────────────────────────────────────┼───────────────────────────────────────┤
  │ 相似命中 │ fingerprint 中 view.name 一致, message 不同 │ 在 findings.md 追加"同页面历史参考"节 │
  ├──────────┼─────────────────────────────────────────────┼───────────────────────────────────────┤
  │ 无记录   │ grep 无匹配                                 │ 正常走 step 3-7                       │
  └──────────┴─────────────────────────────────────────────┴───────────────────────────────────────┘

  4.3 单个任务的 archive 条目

  .plans/<project>/arms/<task-id>/
  ├── findings.md          ← 分析报告
  ├── progress.md          ← 工作日志
  ├── fingerprint.md       ← 指纹数据 (供下次 grep)
  └── resolution.md        ← dev 完成后的终态 (补写)

  fingerprint.md

  ---
  task_id: arms-20260514-001
  source: arms_rum
  pid: c67ee5ri5a@a02e69a18ed6a39
  app_name: 大集客服
  created_at: 2026-05-14T10:00:00+08:00
  resolved_at: 2026-05-14T16:00:00+08:00
  status: resolved
  ---

  ## 指纹信息

  - convergence_message: conv list failed: 33001
  - convergence_view: /agent
  - env: daily
  - app: 大集客服

  ## 定位

  - 错误消息: conv list failed: 33001
  - 页面: /agent
  - 堆栈摘要: at onResponse (xxx.js:631:67170)
    at lf (xxx.js:20:32226)
  - 定位文件: src/pages/agent/api/conv.js:42

  ## 修复方案

  - 原因: API 接口超时未处理
  - 方案: 增加超时重试逻辑
  - 分支: fix/arms-20260514-001
  - commit: abc1234
  - 合并去向: daily 分支

  4.4 归档生命周期

  ┌──────┬───────────────────────────────────┬────────────────────────────────────────────────────────────┐
  │ 阶段 │             触发时机              │                            动作                            │
  ├──────┼───────────────────────────────────┼────────────────────────────────────────────────────────────┤
  │ 创建 │ arms 完成分析(step 5)             │ 写 fingerprint.md + 更新 archive/index.md(状态 analyzed)   │
  ├──────┼───────────────────────────────────┼────────────────────────────────────────────────────────────┤
  │ 完成 │ dev 修复 + reviewer [OK] + commit │ arms 补写 resolution.md; 更新 index 状态为 resolved        │
  ├──────┼───────────────────────────────────┼────────────────────────────────────────────────────────────┤
  │ 归档 │ resolved 超过 30 天               │ custodian 移到 arms/archive/expired/ 或 team-lead 手工清理 │
  ├──────┼───────────────────────────────────┼────────────────────────────────────────────────────────────┤
  │ 跳过 │ 用户说"这个不修"                  │ 更新状态为 ignored, 保留档案供参考                         │
  └──────┴───────────────────────────────────┴────────────────────────────────────────────────────────────┘

  4.5 步骤 1 中历史对比的完整逻辑

  step 1 读 archive/index.md
    └─ grep fingerprint (精确匹配 convergence_message + view)
         │
         ├─ 精确命中 + status=resolved
         │   └─ → 跳过本次任务, 回报 team-lead "复发"
         │
         ├─ 精确命中 + status=analyzed (dev 还没修完)
         │   └─ → 跳过, 回报 "已有进行中的任务"
         │
         ├─ 相似命中 (同 view, 不同 message)
         │   └─ → 继续分析, 在 findings.md 追加参考节
         │
         └─ 无匹配
             └─ → 正常 step 3