# ARMS 全流程优化 — 设计文档

| 字段 | 值 |
|------|-----|
| 文档日期 | 2026-05-17 |
| 作者 | motou |
| 状态 | Draft / 待 review |
| 基础版本 | 0.2.0 (targeted fix mode via ARMS URL) |
| 后继版本 | 0.3.0 (P1) / 0.4.0 (P2) / P3 视调研 |
| 关联文档 | `ARMS.md` (现有 7 步流程), `2026-05-15-ccteam-arms-design.md` (0.1.x ARMS 闭环设计), `2026-05-17-arms-targeted-fix-design.md` (0.2.0 targeted 模式) |
| 语言 | cn 中文版 |

---

## 1. 背景与目标

### 1.1 现有状态（0.2.0）

ARMS 端到端闭环已经跑通 7 步:

```
用户 /arms (batch) 或 /arms <URL> (targeted)
  → team-lead 路由 + 配置补全
  → arms agent 7 步分析 (历史对比 → SLS query → 聚合 → 根因 → findings → fingerprint → 回报)
  → team-lead 派 dev (source=arms, mr_skip=true)
  → dev 实施 + reviewer 审 + 本地 commit
  → arms 补 resolution.md + archive 标 resolved
  → team-lead 总结给用户
```

### 1.2 First Principles 诊断

按"问题本质而非现状"评估, 当前流程在两端薄弱:

**入口**: `/arms` 是 **pull 模式**。研发得主动想起来才查, 期间错误已积累 N 小时。这是真正的瓶颈 — 不是 7 步内某步要优化, 而是触发方式错了。

**出口**: dev commit + `resolution.md` = resolved, 但**没有数据证明错误真的消失**。"修复 ≠ 解决", 没回访的闭环是假闭环。

**流程内 5 个次要问题**:
1. `team-lead` 强依赖 (`team-snapshot.md` 不存在就报错) — 让"偶尔查 ARMS"的用户被挡在外
2. fingerprint 用 `view.name` — SPA URL 带参数会漂; H5 多入口同 view; 后端无 view
3. reviewer 是另一个 LLM agent — agent 审 agent 是 echo chamber, 多半橡皮图章
4. dev task folder 复制 `task_plan/findings` 副本 — 浪费 + 不同步源
5. `archive/index.md` 用 markdown grep — 当前能撑, 但做了主动巡检后数据量必爆

### 1.3 本次改造目标

| 维度 | 现状 | 目标 |
|------|------|------|
| 触发方式 | 用户 pull (`/arms`) | IDE 启动时 push (SessionStart hook) |
| 修复闭环 | commit 即 resolved | T+24h / T+7d 数据回访验证 |
| 数据层 | markdown grep | SQLite, 90 天 retention |
| fingerprint 稳定性 | `conv_message + view.name` | `conv_message + stack_top_frame(file:fn)` |
| 流程入门 | 必须先组团 | 无 team 轻量模式可跑 |
| dev 同步源 | 复制 3 文件副本 | `source.ref` 单行引用 |
| reviewer | LLM agent (echo chamber) | lint+test+checklist (确定性) |
| ARMS UI | 单向消费 | (P3 调研后) 反写根因 + commit |

### 1.4 不做的事（明确范围外）

- ❌ 外部 IM 推送 (钉钉/飞书 webhook) — 用户选了仅 Claude Code 内通知
- ❌ 团队共享 inbox (`.plans` 不主动 git commit, 当前为个人 inbox)
- ❌ 服务器/CI 24×7 调度 (跑在用户本机, 跟着 Claude Code 起停)
- ❌ ARMS 之外的监控源 (SLS 日志服务/Prometheus 等)
- ❌ 多团队/跨项目指纹库共享
- ❌ 改造非 ARMS 任务的 reviewer (改造仅限 source=arms)

---

## 2. 三段式实施策略

| Phase | 主线 | 范围 | 工期 | 版本 |
|-------|-----|------|-----|------|
| **P1** | 数据基建 + 主动巡检 | SQLite + fingerprint 换源 + SessionStart hook + inbox + dev folder 引用化 | ~1 周 | 0.3.0 |
| **P2** | 闭环 + UX 收尾 | Step 9 (24h/7d 回访) + 多 URL targeted + team-lead 解耦 + reviewer 改造 | ~1 周 | 0.4.0 |
| **P3** | 调研型 | ARMS OpenAPI 反写可行性调研 → 实施 / 浏览器扩展 / 砍掉 | 不限 | 视结果 |

**依赖**:
- P2.1 (24h 回访) 依赖 P1 SQLite `occurrences` 表
- P2.4 (reviewer checklist) 依赖 P1 fingerprint 新定义（按类型生成 checklist）
- P3 独立, 但需要 P1 fingerprint 定义稳定

**决策门槛**: 每个 Phase 完成后跑一次真实 SLS e2e 验证（呼应「真实用户验证优于 spec 完整」原则）, 通过才视作 Phase 终态。

---

## 3. 数据层重构（贯穿所有 Phase）

### 3.1 SQLite Schema

位于 `.plans/<project>/arms/archive.db`:

```sql
CREATE TABLE fingerprints (
  task_id           TEXT PRIMARY KEY,           -- arms-YYYYMMDD-NNN
  conv_message      TEXT NOT NULL,              -- 收敛后错误消息
  stack_top_frame   TEXT NOT NULL,              -- 'src/pages/agent/api/conv.js:onResponse'
  view_name         TEXT,                       -- 辅助字段, 不参与指纹判定
  env               TEXT NOT NULL,              -- prod/daily/pre/local
  app               TEXT NOT NULL,              -- pid 对应应用名
  pid               TEXT NOT NULL,
  status            TEXT NOT NULL,              -- analyzed/resolved/ignored
  resolved_by       TEXT,                       -- backend-dev/frontend-dev
  commit_hash       TEXT,                       -- P1 立, P2 填
  branch            TEXT,                       -- 同上
  created_at        INTEGER NOT NULL,           -- unix ts
  resolved_at       INTEGER,
  last_seen_at      INTEGER,                    -- 最近一次该指纹被观测到
  last_seen_count   INTEGER DEFAULT 0
);
CREATE INDEX idx_fp_match ON fingerprints(conv_message, stack_top_frame, env);
CREATE INDEX idx_fp_status_resolved ON fingerprints(status, resolved_at);

CREATE TABLE occurrences (                       -- P2 才大量写入, P1 先建表
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id     TEXT NOT NULL REFERENCES fingerprints(task_id),
  occurred_at INTEGER NOT NULL,
  count       INTEGER NOT NULL,
  source      TEXT NOT NULL                     -- 'scan' / 'verify-24h' / 'verify-7d'
);
CREATE INDEX idx_occ_task ON occurrences(task_id, occurred_at);

CREATE TABLE meta (                              -- 元数据单行表
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- 关键 key:
--   last_global_scan         (unix ts, SessionStart 用)
--   pending_verifies         (JSON array of {task_id, verify_at, delay})
--   schema_version           (语义版本)
```

### 3.2 90 天 Retention 策略

| 表 | 保留规则 | 清理时机 |
|----|---------|---------|
| `fingerprints` | `status IN ('resolved','ignored') AND resolved_at < now - 90d` 删 | SessionStart 触发巡检前顺手 DELETE |
| `occurrences` | `occurred_at < now - 90d` 删 | 同上 |
| `fingerprints` 中 `status='analyzed'` | **永不自动删** | (怕删了进行中任务) |
| `meta` | 不清理 | — |

**容量估算**: 5 指纹/天 × 90 天 + 5 × 5 occurrences/指纹 ≈ 2,700 行, ~500KB。完全在 SQLite 舒适区。

### 3.3 Fingerprint 新定义

**键**: `SHA1(conv_message + ' @ ' + stack_top_frame)`, 同时存原文便于 debug

**顶帧解析**:
```python
def extract_top_frame(stack: str) -> str:
    """
    输入: 多行 stack trace 字符串
    输出: 'file.js:function_name' 或 'file.js:line' (无函数名时)
    
    兼容三种格式:
      - 'at fn (file.js:L:C)'           # Chrome V8
      - 'fn@file.js:L:C'                 # Firefox/Safari
      - 'file.js:L:C'                    # 纯文件路径
    
    跳过:
      - node_modules/* 帧
      - chunk-vendors* / webpack-internal:* 帧
      - 任何 .min.js 帧 (找下一个有 sourcemap 的)
    
    失败 → 返回 '<unparseable>', 原文存 fingerprint.md
    """
```

**兼容性**:
- 无 stack 的事件: `stack_top_frame = '<no-stack>'`, 退化用 `view_name` 辅助
- 解析失败: `stack_top_frame = '<unparseable>'`, 原文落 `fingerprint.md`

---

## 4. Phase 1 详细设计

### 4.1 SQLite 迁移

**脚本**: `scripts/arms-migrate-archive.py` (一次性)

**逻辑**:
1. 读现有 `.plans/<project>/arms/archive/index.md` 月度表格
2. 对每行解析: task_id, fingerprint (旧格式 `message @ view`), status, env, ...
3. 拆 fingerprint → conv_message + view_name (旧的 view.name 直接搬, 不重算 stack_top_frame, 留空)
4. 写入 `archive.db.fingerprints` 表, `stack_top_frame` 字段填 `<legacy>`
5. 写入 `meta.schema_version = '1.0'`, `meta.last_global_scan` 不写
6. 把旧 `index.md` 改名为 `archive/index.md.legacy`, 保留只读快照

**调用**: SessionStart hook 首次跑时检测 `archive.db` 不存在 → 自动调 migrate 脚本

### 4.2 Fingerprint 换源

**影响范围**: arms agent 的 Step 2 (历史对比) 和 Step 6 (写 fingerprint)

**Step 2 改动**:
- 当前: `grep archive/index.md`
- 改: `SELECT task_id, status FROM fingerprints WHERE conv_message=? AND stack_top_frame=? AND env=?`
- 命中判定: 精确命中 (含 env) / 相似命中 (仅 conv_message 同, view 不同) / 无记录

**Step 6 改动**:
- 当前: 写 fingerprint.md + 更新 index.md
- 改: 写 fingerprint.md (人类可读) + INSERT 一行到 fingerprints 表 (机器可查)

**`<legacy>` 数据兼容**: 旧 fingerprint 的 stack_top_frame 是 `<legacy>`, 不参与精确匹配, 但仍能通过 conv_message + env 触发"相似命中"。

### 4.3 SessionStart Hook 自动巡检

**架构 — "采集自动, 根因 on-demand"**:

```
Claude Code 启动
  ↓
SessionStart hook (settings.json)
  ↓
scripts/arms-on-session.py 跑 (shell, 不调 LLM)
  ↓
检查 meta.last_global_scan
  ├─ ≤24h → exit 0, 无输出
  └─ >24h → 数据采集子流程
      ├─ pip 检查 aliyun-log-python-sdk (缓存 ~/.cache/arms-deps/)
      ├─ 读 .env (ak_id, secret, region, project, logstore, pid)
      ├─ SLS query event_type:exception, days=1, env=prod
      ├─ 收敛 + 提 stack_top_frame
      ├─ 比对 fingerprints 表
      │   ├─ 新 → INSERT (status=analyzed, 无 findings)
      │   └─ 复发 → UPDATE last_seen_at/count
      ├─ 清 90 天过期数据
      ├─ 写 inbox.md 最新汇总
      └─ stdout 输出简短 brief (作为 SessionStart context 注入 model)
  ↓
model 在第一次响应前看见 brief, 呈现给用户
  ↓
用户决定: 深挖某条 → /arms task=<task-id> 触发 arms agent Step 4-7 根因 + findings
       忽略 → 继续其他工作
```

**`.claude/settings.json` 配置**:
```jsonc
{
  "hooks": {
    "SessionStart": [
      { 
        "command": "python3 scripts/arms-on-session.py", 
        "timeout": 30000
      }
    ]
  }
}
```

**`scripts/arms-on-session.py` 关键约定**:
- 失败 → `exit 1` + stderr 输出错误, **不阻塞** Claude Code 启动 (hook 失败 ≠ IDE 不能用)
- 性能预算: 总耗时 ≤ 15s (SLS 网络 + SQLite 写)
- 若 SLS 失败 → 输出 brief 但内容是 "巡检失败: <reason>, 上次成功 N 小时前"

**stdout brief 格式** (10-30 行):
```
<arms-session-context>
ARMS 巡检: 距上次 26h, 已自动扫描 prod env 最近 24h.

- 🆕 新增指纹 3 条 (详见 inbox.md)
- 🔁 复发指纹 1 条 (上次 commit abc1234 已过 2 周仍出现, 建议复审)
- ⏳ 进行中 2 条

首条新增: "conv list failed: 33001" @ src/pages/agent/api/conv.js:onResponse (8 次, daily)
完整列表: .plans/<project>/arms/inbox.md
深挖某条 → /arms task=<task-id>; 忽略 → 不动作
</arms-session-context>
```

**Model 处理约定**: 在 session 第一次响应前, 把 brief 呈现给用户（不直接触发深挖, 避免不打扰原则）。

### 4.4 Inbox.md 格式

`.plans/<project>/arms/inbox.md` 每次巡检完整重写:

```markdown
# ARMS Inbox · last_scan: 2026-05-17 09:03

## 🆕 新增 (3)

- **[P2] conv list failed: 33001**
  - 位置: src/pages/agent/api/conv.js:onResponse
  - 环境: daily, 8 次
  - 任务: [arms-20260517-001](./arms-20260517-001/)
  - 深挖: `/arms task=arms-20260517-001`

- **[P3] token 验证失败** ...

## 🔁 复发 (1)

- **[P3] token 无效或已过期**
  - 上次: arms-20260430-002, commit `abc1234`, 2026-04-30 标 resolved
  - 复发: 2026-05-15 新增 5 次
  - 建议: `/arms task=arms-20260430-002` 复审

## ⏳ 进行中 (2)

- arms-20260516-003 — frontend-dev 处理中, 分支 `fix/arms-20260516-003`
- arms-20260514-005 — 待 dev 派单

---
_24h 内打开 Claude Code 不会重新扫描; 强制重扫: `/arms env=prod days=1`_
```

### 4.5 Dev Task Folder 引用化

**当前**: `.plans/<project>/frontend-dev/task-arms-<id>/{task_plan.md, findings.md, progress.md}`
（task_plan/findings 是 arms task folder 的副本）

**改为**: `.plans/<project>/frontend-dev/task-arms-<id>/`
- `progress.md` — dev 自己的实施日志（唯一原创）
- `source.ref` — 单行: `../../arms/arms-20260517-001/`

**dev agent 读取约定**:
- 启动时先 `Read source.ref`, 拼绝对路径
- 跳到 arms task folder 读 `task_plan.md` 和 `findings.md`
- 任何更新只写自己的 `progress.md`
- arms task folder 是只读, dev 不能改

**好处**:
- 不同步源问题 (arms 改了 findings, dev 那边自动反映)
- 磁盘占用减少
- task folder 切换 (用户从 arms 视角看 vs dev 视角看) 一致

---

## 5. Phase 2 详细设计

### 5.1 Step 9 — 修复后 24h/7d 回访

**触发链**:
```
dev commit (status=resolved)
  → arms agent 写 resolution.md + UPDATE fingerprints.status='resolved'
  → CronCreate one-shot 安排 T+24h 和 T+7d
      durable: true
      prompt: '<arms-verify task-id=arms-XXX delay=24h/>'
  → 同时 UPSERT meta.pending_verifies (JSON 数组, append 两项)
  → 到点 Claude Code REPL idle 时触发 (若没开则错过, 由 SessionStart 补漏)
  → model 收到 verify prompt, 调 arms agent 的 verify 子流程
```

**verify 子流程**（arms agent 内新增 step）:
1. Read fingerprint 的 conv_message / stack_top_frame / env / resolved_at / commit_hash
2. baseline count = SLS query `[resolved_at - 24h, resolved_at)` 同指纹 count
3. post count = SLS query `[resolved_at, now)` 同指纹 count
4. 判定:
   - `post == 0` 或 `post < baseline * 0.1` → **stable** ✅
   - `baseline * 0.1 ≤ post < baseline * 0.5` → **partial** ⚠️（下降但未消）
   - `post ≥ baseline * 0.5` → **regressed** ❌（基本没修）
5. INSERT `occurrences (task_id, occurred_at=now, count=post, source='verify-24h')`
6. 追加到 `resolution.md` 的 `## Verification` 节
7. **regressed** → 通过下次 SessionStart inbox 标红, 在新增/复发栏之外加 "⚠️ 回归" 栏

**补漏机制**（错过 cron）:
- SessionStart hook 顺手检查 `meta.pending_verifies` 中 verify_at < now 但未跑的项
- 自动补跑（仍走 verify 子流程）, 跑完从 pending 列表移除

### 5.2 多 URL Targeted

**接口扩展**:
```
/arms https://arms.console.aliyun.com/...                            # 单 URL (0.2.0 现有)
/arms https://... https://... https://...                            # 多 URL (P2 新增)
/arms env=prod days=1 keywords=conv,token                            # batch (现有)
```

**多 URL 解析逻辑**:
- 每个 URL 提取 `(pid, trace_id 或 event_id, time_range, env)`
- 合并 SLS query: `pid:X AND (event_id:A OR event_id:B OR ...)`
- line cap: `min(50 * N, 500)` 防爆
- 走原 batch 路径（聚合 + 根因）
- 输出**一个 findings.md** 含分节: "## 来源 1 / ## 来源 2 / ## 来源 3"
- 跨 URL 命中同指纹 → 自动去重, findings 标 "3 个来源指向同一指纹"

### 5.3 Team-Lead 强依赖解耦

**当前**:
```
/arms → 检查 .plans/<project>/team-snapshot.md
  └─ 不存在 → 报错 "请先 /CCteam-creator-cn 组团后再运行 /arms"
```

**改为**:
```
/arms → 检查 team-snapshot.md
  ├─ 存在 → 现有完整路径（team-lead 路由 + 派 dev）
  └─ 不存在 → 轻量路径:
      ├─ Read CLAUDE.md 的 ARMS 巡检配置段
      ├─ Agent tool 临时 spawn arms agent (subagent_type=general-purpose)
      ├─ 凭证直接从 .env 取 (不走 hydrate)
      ├─ 跑 Step 1-7 完整流程
      ├─ 结果落 .plans/<project>/arms/ (仍然存)
      └─ 回报用户: "无 team 模式, 分析已完成, 请自行处理 commit/分支"
          (不派 dev, 不调 reviewer, 用户自己决定后续)
```

**开关**: `ARMS_LIGHT_MODE` 环境变量 / CLAUDE.md 配置项
- `auto` (默认) — 自动判断 team-snapshot.md 是否存在
- `always` — 永远走轻量, 即使有 team
- `never` — 永远走完整, 不存在就报错（回到现状）

### 5.4 Reviewer 角色改造（仅限 ARMS 任务）

**前提**: 改造**仅限 `source=arms` 任务**, 其他任务的 reviewer 不动。

**当前**:
```
dev 写完 → SendMessage(reviewer) → reviewer agent 看 diff 给 [OK] → dev commit
```

**改为**:
```
dev 写完 → 自跑:
  1. lint  — 复用项目自带 (eslint/prettier/black/...)
  2. test  — 项目自带, scope 到修改文件相关测试
  3. checklist — 按 ARMS 任务类型自动生成 (从 fingerprint 的 conv_message + stack_top_frame 推断类型)
  4. 全过 → 自动生成 commit message (按 ARMS commit 模板) + PR template (不自动开 PR)
  5. 任一不过 → 报 team-lead, team-lead 选: 回 dev 修 / 告诉用户卡点
```

**checklist 模板**（位于 `.claude/arms-review-checklists/<task-type>.md`, 项目级可定制）:

| 任务类型 | 自动判定关键词 | checklist 项 |
|---------|---------------|-------------|
| 异常类 | "Error", "throw", "uncaught" | try/catch / 日志 / error boundary / 用户友好 fallback UI |
| 超时类 | "timeout", "abort", "ECONN" | timeout 参数 / 重试逻辑 / abort signal / 用户提示 |
| 数据类 | "undefined", "null", "TypeError" | input validation / fallback 值 / TS 类型 / 单元测试 case |
| 网络类 | "fetch", "XHR", "5xx" | error handling / 重试 / 降级方案 |

**PR template 自动生成**:
```markdown
## ARMS 任务
- task: arms-20260517-001
- 根因: <从 findings.md 复制>

## 改动
- <diff 摘要>

## 验证
- lint: ✅
- test: ✅ (N/M passed)
- checklist (异常类): ✅ try/catch ✅ 日志 ✅ fallback UI
```

---

## 6. Phase 3 设计

### 6.1 调研先行（硬门槛, ~3 天）

**调研问题**:
1. 阿里云 ARMS OpenAPI 是否支持给"RUM 异常事件"加自定义 annotation/note/tag？（主路径）
2. 给"应用层"加全局 note 是否有 API？（次优路径, 把"已知问题清单"挂应用层）
3. ARMS console URL pattern 稳定吗？是 SPA 还是 SSR？（评估浏览器扩展可行性）

**调研产出**: `.plans/<project>/arms/research/p3-feasibility.md` 含
- API 能力清单 + 限制（参考阿里云文档 + 实际 PUT 试探）
- 推荐路径 + 工作量估算
- ROI 判断（值得 / 不值得）

**决策门槛**: 调研完单独跟用户对齐, 三选一:

| 选项 | 路径 | 触发条件 |
|-----|-----|---------|
| A | P3.1 API 反写 | OpenAPI 支持 |
| B | P3.2 浏览器扩展兜底 | API 不支持但 URL 稳定 |
| C | 砍 P3 | 都不划算, P2 完工即终态 |

### 6.2（路径 A）ARMS OpenAPI 反写

dev verify-24h 通过 → 调 ARMS PUT 接口给事件加 annotation:
```python
payload = {
    "commit_hash": "abc1234",
    "root_cause": "...",
    "arms_task_path": ".plans/<project>/arms/arms-20260517-001/",
    "resolved_at": "2026-05-17T16:00:00+08:00",
}
```

**失败处理**: 失败不阻塞 dev commit, 落 `.plans/<project>/arms/.failed_writes.log`, 下次 SessionStart 自动重试

### 6.3（路径 B）浏览器扩展兜底

- Chrome MV3 扩展
- 监听 `https://arms.console.aliyun.com/*` URL pattern
- 注入 sidebar, 通过 native messaging host 查本机 `archive.db`
- 用户在 ARMS UI 看异常时, 自动在侧栏显示「已知问题: commit abc1234 修过 (2026-04-30)」
- 工作量预估: 1-2 周 (manifest + content script + native host + UI)

### 6.4（路径 C）砍掉

P2 完成即视作终态。当前的 inbox.md 复发提醒 + resolution.md 链接已经能解决 80% 的"以前修过这个错误"需求。

---

## 7. 横向关切

### 7.1 测试策略

| 模块 | 测试类型 | 覆盖率目标 |
|------|---------|-----------|
| SQLite migration | pytest 单测 | 100% (path 简单) |
| fingerprint 解析 (extract_top_frame) | pytest 单测 + 多种 stack 格式 fixture | ≥90% |
| SessionStart shell 脚本 (`arms-on-session.py`) | pytest + 假 SLS 响应 fixture | ≥80% |
| arms agent 7-step + verify 子流程 | 集成测试 (fixture 假 SLS) | 关键路径 100% |
| **真实 SLS e2e** | **手动跑一次** | **每个 Phase 完成必须做** |

**真实 e2e 是硬要求** — 呼应「真实用户验证优于 spec 完整」原则。spec 写得再漂亮, 不在真实项目环境跑一遍就不算完。

### 7.2 错误处理 / 失败模式

| 失败场景 | 处理 |
|---------|------|
| SLS query 失败 3 次 | 复用现有 3-Strike 升级 team-lead |
| SQLite 损坏 | `scripts/arms-rebuild.py` 从所有 `fingerprint.md` 副本重建 |
| SessionStart 脚本失败 | exit 1 + stderr, **不阻塞** Claude Code 启动 |
| SessionStart 超时 (>30s) | hook 强制 kill, 留下 "巡检超时" 标记, 下次重试 |
| ARMS API 反写失败 (P3) | 落 `.failed_writes.log`, SessionStart 重试, 永不阻塞 dev commit |
| migrate-archive 失败 | 不动旧 `index.md`, 错误日志到 stderr, 用户介入 |

### 7.3 性能预算

| 指标 | 预算 | 备注 |
|------|------|------|
| SessionStart hook 总耗时 | ≤15s | SLS 网络 + SQLite 写, 实施时验证调整 |
| archive.db 大小 (90 天) | ≤500KB | 容量计算见 §3.2 |
| inbox.md 大小 | ≤50KB | 一屏展示, 旧 inbox 不归档 |
| 单条指纹 SLS query | ≤3s | 包含网络 |

### 7.4 Migration & 向后兼容

| 项 | 处理 |
|----|------|
| 旧 `archive/index.md` | 改名 `archive/index.md.legacy`, 保留只读快照 |
| 旧 `fingerprint.md` 副本 | 保留, 不动 (作为 SQLite 损坏的重建源) |
| 凭证机制 (`.env` + `${VAR}`) | **完全不动**, P1 shell 脚本直接读 |
| `/arms` 命令接口 | **100% 向后兼容**, 多 URL 是叠加, 不替换原参数 |
| team-snapshot.md 已存在的用户 | 走完整路径, 行为不变 |
| 旧 task folder (.plans/arms/arms-2026XXXX-NNN/) | 不动, 新增字段 (commit_hash 等) 通过 SQLite 一次性 backfill |

### 7.5 版本节奏

- P1 完成 → 0.3.0 (minor bump)
- P2 完成 → 0.4.0 (minor bump)
- P3 视调研:
  - 路径 A (API 反写) → 0.5.0 (minor)
  - 路径 B (浏览器扩展) → 0.5.0 + 独立 chrome-ext 仓库
  - 路径 C (砍) → 不 bump

---

## 8. 关键决策记录

| 决策点 | 选择 | 理由 |
|-------|-----|------|
| 通知渠道 | 仅 Claude Code 内 | 0 配置, 本地化, 不打扰他人, 凭证不出本地 |
| 实施策略 | 三段式渐进 | 每段独立可验证, 早期价值早交付, 风险分摊 |
| SessionStart 触发方案 | shell 采集 + brief 注入 + 根因 on-demand | 采集廉价 (shell), 根因昂贵 (LLM), 按需调用; 不依赖 model 自决策, 不依赖 Claude Code CronCreate |
| 不用 CronCreate 做主动巡检 | 改用 SessionStart hook | CronCreate 只在 REPL idle 触发 + 7 天过期, 不如 SessionStart 覆盖率高。注: CronCreate 仍用于 P2 verify 触发(one-shot, durable, +SessionStart 补漏), 两种机制各司其职 |
| commit_hash / branch 字段 | P1 schema 立着 | schema 一步到位, 避免 P2 ALTER TABLE |
| reviewer 改造范围 | 仅 source=arms 任务 | 影响范围可控, 不动现有 dev 流程 |
| 数据保留 | 90 天 | 复发周期 ≤30 天, 季度回溯 ~90 天, 之后价值急剧降低 |
| Fingerprint 键 | conv_message + stack_top_frame | view.name 在 SPA/H5/后端都不稳; 堆栈顶帧是代码层不变量 |
| 性能预算 | SessionStart ≤15s | 实施时验证调整 |
| 数据存储 | SQLite | grep markdown 在主动巡检数据量下必爆 |
| 测试覆盖 | 单元 ≥80%, e2e 必须真实 SLS | 真实环境验证不可省 |

---

## 9. 后续动作

1. ✅ Spec 落盘 (本文档)
2. ⏭️ 用户 review spec → 调整或认可
3. ⏭️ 认可后 invoke `writing-plans` skill → 出 **P1 implementation plan** (P2/P3 暂不展开)
4. ⏭️ P1 plan 用户认可 → 执行
5. ⏭️ P1 跑通真实 SLS e2e → 标 P1 完成
6. ⏭️ 进 P2 plan ...
