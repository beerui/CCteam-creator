# CHANGELOG

## 0.3.1 - 2026-05-17

> Patch: T16 真 e2e 验证回炉, 修 fingerprint 归一化不足 / hook 不读 default_env / brief highlight 选条三个 bug.

### Fixed / 修复

- **fingerprint 归一化** (P0): `arms_lib/fingerprint.py` 新增 `normalize_for_fingerprint(text)`, 两条规则: (1) 前端构建产物 chunk hash `/name-AbCd1234.js` → `/name-{HASH}.js` (兼容 6-32 字符 base64url alphabet, 覆盖 vite/webpack contenthash); (2) ISO 时间戳毫秒尾巴 `.453Z` → `.{MS}Z`. `compute_fingerprint` 与 `aggregate_exceptions` 入口都调归一化, 与 SQLite 存储 / select_fingerprint_match 一致. **真 e2e 现场坐实**: daji 测试服 6 → 2 (5 条 ARMS 测试错误因毫秒戳拆开), 当前 prod 7 → 4 (4 条 CSS preload 因 chunk hash 拆开).
- **SessionStart hook 读 default_env** (P1): 新增 `arms_lib/config.py:load_config(arms_dir)` 读 `.plans/<project>/arms/config.json`. hook 之前硬编码 `env="prod"`, 与 commands/arms.md 承诺的"先读 default_env, 缺失才用 prod"冲突, 导致接入项目想做"测试服日常巡检"走不通. `/arms` 用户命令仍读 CLAUDE.md (向后兼容).
- **brief highlight 按 count desc 排序** (P3): `_run_scan` 返回 new_items 前 `sort(key=count, reverse=True)`, 让 brief 的"首条新增"自然选最值得 highlight 的指纹 (而非 SQLite 表查询顺序).
- `_emit_failure` brief 重试命令使用动态 `default_env` (此前硬编码 `prod`, 跟 default_env 修复一并处理)

### Added / 新增

- `scripts/arms_lib/config.py` — per-project 配置加载 (JSON, 容错 fallback). 未来 P2 字段 (retention_days / ignore_patterns) 在此扩展, 无需新 .env 变量.
- 22 个新单元测试: fingerprint norm 13 + sls collapse 2 + config 4 + hook default_env/sort 3. 全套从 54 → 76 全绿.

### Docs

- `commands/arms.md` §11 末尾加 "Hook 配置: config.json" 一节, 说明 hook 与 `/arms` 命令的配置分裂 (hook 走 config.json, 命令走 CLAUDE.md)

## 0.3.0 - 2026-05-17

> Minor: P1 全面优化 ARMS 流程 — 从 "用户主动 /arms pull" 升级为 "IDE 启动自动 push brief"; markdown 指纹库迁移到 SQLite (90d retention); fingerprint 键改用 stack_top_frame (代码层不变量, 替代 view.name)。
> Minor: P1 ARMS overhaul — switch from "user-pull /arms" to "IDE-push brief via SessionStart hook"; migrate markdown fingerprint store to SQLite (90d retention); fingerprint key uses stack_top_frame (code-layer invariant) instead of view.name.

### Added / 新增

- SQLite 指纹库 `.plans/<project>/arms/archive.db` (3 表: fingerprints / occurrences / meta + ON DELETE CASCADE)
- Python 包 `scripts/arms_lib/` — `db.py` / `fingerprint.py` / `sls.py` / `inbox.py` / `retention.py` 五个模块, 单元测试覆盖率 ≥80%
- `scripts/arms-migrate-archive.py` — 一次性把旧 `archive/index.md` 迁到 SQLite, 旧文件保留为 `index.md.legacy` 只读快照
- `scripts/arms-on-session.py` — Claude Code SessionStart hook 入口 (shell 采集, ≤15s 预算, 失败不阻塞 IDE 启动)
- `.claude/settings.json` — 配置 SessionStart hook 触发 arms-on-session.py
- `/arms task=<task-id>` — 单条深挖模式 (commands/arms.md §11), 跳过 SLS 查询直接走根因分析阶段
- 90 天 retention 策略 — `status IN ('resolved', 'ignored') AND resolved_at < now - 90d` 自动清理; `analyzed` 永不删

### Changed / 变更

- arms agent Step 2 (历史对比): `grep archive/index.md` → SQLite SELECT fingerprints
- arms agent Step 6 (归档): `archive/index.md` 追加行 → INSERT to `archive.db.fingerprints`
- arms resolution / ignored 路径: 改写 SQLite (`update_fingerprint_status`), 不再触碰 archive/index.md
- fingerprint 键: `conv_message + view.name` → `SHA1(conv_message + ' @ ' + stack_top_frame)`; stack_top_frame 解析 Chrome V8 / Firefox / 纯路径, 跳过 node_modules / chunk-vendors / .min.js, 转义 Windows 路径 + URL query 字符串
- SLS query 构造: 抽出纯函数 `_build_query`, 对 `keywords` 做引号+反斜杠转义 + 控制字符拒绝 (防 SLS query injection)
- dev agent task folder: 不再复制 `task_plan.md` / `findings.md` 副本, 改用 `source.ref` 单行引用 arms task folder (避免不同步源)

### Fixed / 修复

- `update_fingerprint_status` docstring 明确为终态转移 (resolved/ignored), 不适合增量更新 last_seen_*
- `init_schema` 一次性设置 `conn.row_factory = sqlite3.Row` + `PRAGMA foreign_keys = ON`, 不再在 select_fingerprint_match 内部副作用
- SessionStart hook 的 `last_global_scan` 改在 render + brief 全部成功后才写, 避免 render 异常导致下次 24h 内静默跳过
- `arms-on-session.py` 启动时 `_load_dotenv(cwd/.env)` 自动加载 .env (零依赖, 已存在 env 不覆盖); 修复"集成项目首次开 session 必看'巡检失败'兜底"问题 — hook 是独立子进程, 不继承 shell 的 .env

### Docs

- 新增 `docs/superpowers/specs/2026-05-17-arms-flow-overhaul-design.md` (P1+P2+P3 三段式设计)
- 新增 `docs/superpowers/plans/2026-05-17-arms-p1-impl.md` (P1 16-task 实施计划)
- 更新 `ARMS.md` 顶部加 "P1 自动巡检模式 (0.3.0+)" 一节 + 0.2.0 整体流程 mermaid 图
- 更新 `cn/skills/CCteam-creator-cn/references/onboarding.md` arms / dev 角色说明

### Not in scope / 不在本期范围

- en 英文版 `skills/CCteam-creator/references/onboarding.md` 中的 ARMS 段尚未存在, en 同步留给后续 i18n
- P2: Step 9 修复后 24h/7d 回访验证、reviewer 改造、多 URL targeted、team-lead 解耦轻量模式
- P3: ARMS OpenAPI 反写调研 / 浏览器扩展兜底

## 0.2.0 - 2026-05-17

> Minor: `/arms` 新增单点修复(targeted fix)模式,arms agent 协议扩展 `mode` 字段。
> Minor: New targeted fix mode for `/arms` via ARMS console URL + optional keywords. arms agent protocol extended with `mode` field.

### Added / 新增

- **`/arms <ARMS_URL> [keywords="..."]`** 单点修复模式
  - 首位置参以 `http(s)://` 开头触发,自动跳过批量扫描,直接反查 SLS 对应时间窗口里的 exception 事件
  - 0 命中 → 提示"请精化 keywords 或扩大窗口",不写 findings;1 fingerprint → 自动走完 7 步;≥2 fingerprints → team-lead 用 AskUserQuestion 列候选给用户选 1
  - 派 dev / reviewer / resolution 流程与批量模式完全一致(本地 commit + 不 push,见 ARMS 子协议)
  - 实现: `commands/arms.md` §10 self-contained 单点路径;`onboarding.md` arms agent 加"模式与差异"小节
  Added single-shot targeted fix path: `/arms <URL>` parses time window + filters from ARMS rum-explorer URL, reverse-queries SLS with optional keywords narrowing.

- **arms agent 协议字段扩展**: `mode: batch | targeted`、`target_app_id`、`target_from_ts`、`target_to_ts`、`target_env`(向后兼容,缺省 batch)
  Protocol fields added for targeted mode; backward compatible.

### Changed / 调整

- `onboarding.md` arms agent Step 5 概览节模板:加可选 `模式 / URL / keywords` 字段
- `onboarding.md` § Known Pitfalls 加"ARMS URL 单点解析的硬性失败"条目,明确**不要 fallback batch**(否则违反单点初衷)

## 0.1.7 - 2026-05-16

> Patch: 2 处 0.1.6 真实端到端验证暴露的缺口修复 + platform 限制文档化。
> Patch: 2 gaps closed from 0.1.6 real end-to-end validation against `/Users/motou/Desktop/daji-customer-service` + platform limitation documented.

### Fixed / 修复

- **缺口 8: 僵尸 / 完成态 idle / cwd 漂移 member 时盲目复用 → 消息黑洞**
  0.1.6 §4 假设"team 已有 live arms → 复用"。实测发现 3 类伪 live 状态会让"复用"等于"消息丢进黑洞":
  - **僵尸 sonnet**: 老 spawn 没装 shutdown 协议教程,只 `read: true` 不响应
  - **完成态 idle**: 上次任务结束已回报,context 含旧任务记忆,直接复用会重放旧回应
  - **cwd 漂移**: 上次 spawn 用旧项目路径,本次新路径 ≠ agent 内部记忆的路径
  → 0.1.7 commands/arms.md §4 加 **步骤 1a 健康检查**: `SendMessage(to: "arms-N", message: "[health-check]...")` + 等 60 秒 → 收到响应才 alive 复用,timeout / 协议错误 / 旧 finding 重放 → stale,fallback 走 spawn fresh。
  Fixed §4 zombie/stale member detection via SendMessage health-check with 60s timeout.

- **缺口 5 升级修复:`name="arms"` silently rename 治本**
  0.1.6 用 `name="arms"` 时 Claude Code 遇同名 silent 改名 `arms-2`/`arms-3`。0.1.6 §4 注意到这点但**没真正预防**(只是说"先检查 live members 决定复不复用")。0.1.7 起 spawn 用 `name="arms-<task-id>"` 显式唯一(如 `arms-arms-20260516-001`),与本次任务 1:1 绑定,主对话 SendMessage 用同 name 不出错。
  Fixed name collision at root by using unique `name="arms-<task-id>"` instead of bare `"arms"`.

### Documented / 文档化(platform 限制 acknowledge)

- **缺口 9: Agent 工具 `model` 参数无 `[1m]` 变体**(platform 限制,无法 fix,只能文档化)
  Agent 工具 schema enum 硬限制为 `["sonnet", "opus", "haiku"]`,**无法显式选 opus[1m]**。`model: "opus"` 实际 spawn 出来是 200k context 普通 opus,即使主对话(team-lead) 是 `claude-opus-4-7[1m]` 也不继承父级 context。
  - **实测影响**: arms 7 步典型 token 用量 ~50k(input + output),200k 完全够。除非 SLS 返回 100+ 异常事件需要 1M。daji-cs 本次 16 条异常 token 用量 < 60k
  - **当前没 workaround**,直到 Claude Code Agent 工具 schema 升级支持 [1m]
  - → onboarding.md § arms 末尾加 `### Known Pitfalls` 段,acknowledge 此 limitation + 给 token 容量预估 + 缓解建议(line=500 上限、字段筛选)
  Documented platform-level Agent tool model enum limitation in Known Pitfalls.

### Notes / 备注

- **本轮验证产出**: arms-3 在 `/Users/motou/Desktop/daji-customer-service` 跑出 8153 字节 / 168 行 findings.md,发现 **2 个真实可修 bug** + 2 个业务噪声:
  - 🚨 `global is not defined` × 3: Vite `define: { global: 'globalThis' }` 把 ARMS SDK 自带 `var global = window` 误替换 → SDK 内部 `_global.global` 失效。修复: 删除 vite.config.ts 这 3 行
  - 🚨 `conv list failed: 33001` × 9 跨 4 session: 融云 IM `getConversationListByTimestamp` 在 `RC.connect(token)` 完成前被 `useSingleTabGuard` 触发 → IM 未就绪 → 33001。修复: 加 `whenConnected()` wait
  - 业务噪声: `当前会话已转接` / `token无效或已过期` 各 2 次,建议加 `arms_ignore_patterns` 过滤
- **0.1.6 修复实测全部 PASS**: env 默认/`${VAR}` 解引用/.convergence 探测/分支名单前缀 — 全在 daji-cs 真实数据上验证通过
- **0.1.7 验证策略**: 本版本 fix 没有真实项目跑通(因为缺口 8/9 触发条件需要"重复 spawn arms" + "需要 1M 数据"),下一轮 demo 可主动制造场景验证
- **累计**: 24 个 accumulated acceptance points 中,**13 个**(54%)来自真实使用反馈而非设计审视。`real-user-validation-over-spec-completeness` 记忆继续被印证

## 0.1.6 - 2026-05-16

> Patch: ARMS 凭证管理从"明文落 CLAUDE.md"改为".env 引用",安全反模式 → 安全默认。
> Patch: ARMS credential management switched from plaintext-in-CLAUDE.md to `${VAR}`-from-`.env`. Security anti-pattern → security default.

### Changed / 变更(安全模型升级)

- **ARMS 配置改为 `.env` 引用 + CLAUDE.md `${VAR}` 双文件配合**(原 0.1.5 是单文件明文落 CLAUDE.md)。

  **Why**: 0.1.5 设计在 CLAUDE.md 落明文 AK 是反模式 — CLAUDE.md 每次会进 Claude Code 上下文,凭证暴露在 prompt 中、可能被 prompt injection 利用、且 git commit 时容易误提交。把凭证迁移到 `.env`(必须 `.gitignore`),CLAUDE.md 只引用,team-lead 在 §3 解析参数时**临时**解引用传给 arms agent,真值仅存在于 team-lead 内存。
  ARMS credentials moved out of CLAUDE.md (which is always in LLM context) into `.env` (which must be gitignored). team-lead dereferences `${VAR}` only at §3 dispatch time, value lives in memory only.

- **`commands/arms.md §2` 重写为"三件套补全"**:
  1. AskUserQuestion + 文本输入收集真值
  2. 写真值到项目根 `.env`(变量名标准化: `VITE_APP_ARMS_PID` / `SLS_REGION` / `SLS_PROJECT` / `SLS_LOGSTORE` / `ARMS_AK_ID` / `ARMS_AK_SECRET`)
  3. **确保 `.gitignore` 含 `.env`**(不可跳过 — 否则下次 `git add .` staged 凭证)
  4. CLAUDE.md 末尾写 `## ARMS 巡检配置` section,**只含 `${VAR}` 引用 + 获取方式注释**
  5. 占位识别新增"明文识别"分支: CLAUDE.md 字段是明文 → 降级处理(搬到 .env + 改引用)

- **`commands/arms.md §3` 加 `${VAR}` 解引用步骤**: team-lead Read .env → parse 成字典 → 替换 CLAUDE.md ARMS 节里的 `${VAR}` 引用 → 真值通过 SendMessage / Agent prompt 传给 arms。控制平面(team-lead 解凭证)/ 数据平面(arms 用凭证)分离。

- **`templates.md § 即时巡检（arms agent）` 模板** 全面改写: 默认值是 `${VITE_APP_ARMS_PID}` 等引用 + 每行配阿里云控制台获取方式注释 + "第一次设置 checklist"。

### Notes / 备注

- **CN-only**: 同 0.1.4 / 0.1.5,EN skill 暂未同步。
- **向后兼容路径**: 旧版本(0.1.5 及之前)用户的 CLAUDE.md 仍可能含明文 AK。0.1.6 §2 新增"明文识别"分支会**自动迁移** — 检测到明文 → 把明文搬到 .env + CLAUDE.md 改引用 + .gitignore 加 .env,提示用户"已迁移,建议 rotate 已暴露的 AK"。
- **安全建议**: 升级到 0.1.6 后,**强烈建议 rotate** 所有之前在 CLAUDE.md 出现过的 AK — 它已经在多个 prompt 上下文中存在过,默认视为 exposed。
- **真实项目验证**: 0.1.6 是在 `daji-customer-service` 真实项目上做 0.1.5 验证时,用户发现"我希望放到 .env 中统一管理"主动提出的安全升级——又一个 spec-only review 看不到的盲点,只有真实使用才暴露。

## 0.1.5 - 2026-05-16

> Patch: 7 处 V5 (`/arms` 命令)缺口修复,均由 `daji-customer-service` 真实项目端到端验证暴露,**不是设计审视产物**。
> Patch: 7 ARMS-flow gaps closed, all surfaced by real end-to-end run against `daji-customer-service`.

### Fixed / 修复(真实项目验证驱动)

- **缺口 1: `env` 默认值打架 — `default_env` 字段曾是 dead config**
  `commands/arms.md §3` 默认 `env=prod` 硬编码,与 `templates.md` 的 CLAUDE.md `default_env: <prod|daily|...>` 字段冲突——用户在 §2 填的 `default_env` 被命令默认值覆盖,字段成了 dead config。
  → 现在 `env` 默认 `CLAUDE.md.default_env || prod`,尊重用户在 §2 的显式选择。`onboarding.md` 派单消息模板同步。
  Fixed `env` default precedence; `default_env` is no longer dead config.

- **缺口 2: 临时 spawn `run_in_background: false` 阻塞主对话**
  `commands/arms.md §4` 临时 spawn 模板 `run_in_background: false` 让 arms 7 步流程(SDK + SLS + 分析 + 写 5 文件)foreground 阻塞 10-30 分钟,用户无法看进度、无法做别的事。
  → 改为 `run_in_background: true` + 加注释解释 trade-off。background 后用户可继续主对话,arms 完成自动通知 team-lead 触发 §6。
  Fixed temp spawn to run in background (was blocking main conversation 10-30 min).

- **缺口 3: snapshot 存在但 live team 未 hydrate 时 spawn 失败**
  `commands/arms.md §1` 仅检查磁盘 snapshot 文件,不检查 Claude Code 内存的 live team。"组完团关 Claude Code → 几天后再开 → /arms"流程下 live team 是冷的,`Agent(team_name=<project>)` 行为不可预期(实测会 silently 创建 arms-2/arms-3 等不期望命名)。
  → §1 加 step 3 检查 `~/.claude/teams/<project>/config.json` 存在,不存在则 `TeamCreate(team_name=<project>)` **惰性 hydrate**(只起 shell,不复活原 4-5 角色——/arms 不是 team mode 激活)。
  Fixed `/arms` §1 to lazily hydrate live team when only the snapshot exists.

- **缺口 4: `shutdown_request` 协议在 general-purpose subagent 不被识别**
  实测发现 arms 收到 `{"type":"shutdown_request","request_id":"..."}` 后仅 `read: true` 然后无视——general-purpose subagent 默认不知道协议响应规范,team-lead 无法 graceful 终止它。
  → `onboarding.md § 团队沟通` 加新 sub-section `### 协议响应`,显式教所有团队成员两种协议消息 (`shutdown_request` / `plan_approval_request`) 的回应格式 + echo `request_id` 规则。
  Fixed protocol response education in onboarding (all roles benefit, not just arms).

- **缺口 5: spawn 同名 silently 创建 arms-2 不复用**
  实测 `Agent(name="arms", team_name="daji-cs")` 当 team 已有 arms member 时 **不报错也不覆盖**,silently 创建 `arms-2`。多个 arms 并发写同一 `.plans/<project>/arms/` 目录会产生竞态冲突。
  → `commands/arms.md §4` 改为**两层检查**:先 grep live team `config.json` 的 `members` 数组(name 唯一性)→ 再 grep snapshot 花名册(冷成员)→ 都没才 spawn。spawn 调用补 `name: "arms"` 参数。
  Fixed temp-spawn duplicate-name silent collision.

- **缺口 6: 分支名 `fix/arms-<task-id>` 拼出双前缀 `fix/arms-arms-...`**
  task-id 格式 `arms-<YYYYMMDD>-<NNN>` 本身已含 `arms-` 前缀,与模板的 `fix/arms-` 前缀重复。实测 arms-2 输出的 findings.md 写 `拟分支名: fix/arms-arms-20260516-001`。
  → 全文 7 处模板字符串 `fix/arms-<task-id>` → `fix/<task-id>`(示例值 `fix/arms-20260514-001` 保持不变——那是正确的 `fix/<task-id>` 展开)。涉及: commands/arms.md / onboarding.md (4 处) / roles.md (2 处)。
  Fixed branch name template double-prefix bug.

- **缺口 7: `.convergence` 字段并非全幻觉,实际部署可能存在**
  0.1.4 把 `.convergence` 后缀字段当全幻觉删掉是**过度修正**。daji-cs 真实查询发现 ARMS 后端聚合字段 `exception.message.convergence` 在该 deployment 上**存在且工作**(归一化后是 `conv list failed: {ARMS_NUMBER}`),比 Python 端 normalize 更准、跨实例一致、与 ARMS 控制台聚合视图一致。
  → `onboarding.md § arms Step 3.2` 加 `HAS_CONVERGENCE` 字段探测;Step 4.1 改为**策略选择**: 探测到则优先用 `.convergence` 做分组键(策略 A);没探测到才 fallback 到 Python `normalize_message()`(策略 B,原 0.1.4 实现)。
  Fixed `.convergence` field handling — probe-and-prefer instead of always-fallback.

### Notes / 备注
- **CN-only**: 同 0.1.4,EN skill 暂未同步,本次仅 CN 修复。
- **验证方法学延续**: 0.1.4 引入"真实项目验证"原则(`real-user-validation-over-spec-completeness`),0.1.5 是其延续——所有 7 处缺口均**在跑通一次 /arms 流程的过程中暴露**,无一来自设计文档复盘。设计阶段 13 项验收清单 + 0.1.4 真实项目验证 4 项 + 0.1.5 真实端到端 7 项 = **24 个 acceptance points 累计**,且后两批仅在"用真实凭证、真实 SLS、真实 spawn"的条件下才会出现。
- **`.convergence` 修正语调**: 0.1.4 commit message 写"`.convergence` 字段是设计幻觉"——这个措辞**过强**。准确的描述是"字段存在性因 SLS 部署而异,不能假设"。0.1.5 已用"策略选择"取代"删除"。

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
