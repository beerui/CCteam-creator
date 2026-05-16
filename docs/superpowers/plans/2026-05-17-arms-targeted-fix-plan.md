# /arms 单点修复模式 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `/arms` 命令新增"单点修复"分支：用户在 ARMS 控制台拷一条 rum-explorer URL（可选 keywords）后,系统反查 SLS 精确到一条 fingerprint,复用现有 arms agent 7 步骨架完成根因分析 → 派 dev → reviewer → resolution。在真实的 daji-customer-service 项目里跑通 ArmsTestError 验证案例。

**Architecture:** 不新增 agent。`commands/arms.md` 新增 §10 单点路径(self-contained);`cn/skills/CCteam-creator-cn/references/onboarding.md` arms agent 7 步加 `mode: targeted` 分支差异表;复用 dev / reviewer / archive 流。版本 0.2.0(minor)。

**Tech Stack:** Markdown 协议文档(plugin commands + skill onboarding) / Python aliyun-log-python-sdk(arms agent 跑 SLS) / Claude Code Agent 工具(team_name spawn) / 3 个 plugin manifest JSON。

---

## File Structure

| 文件 | 改动 | 说明 |
|---|---|---|
| `commands/arms.md` | 修改 | §3 参数解析末尾加首参 URL 检测;末尾追加 §10 单点修复(targeted)整节 |
| `cn/skills/CCteam-creator-cn/references/onboarding.md` | 修改 | arms agent § 7 步流程前插入"模式与差异表"小节;§ Known Pitfalls 加 URL 解析边界 |
| `cn/skills/CCteam-creator-cn/references/templates.md` | 修改 | findings.md 模板加可选 `模式` 字段 |
| `CHANGELOG.md` | 修改 | 新增 0.2.0 section |
| `.claude-plugin/marketplace.json` | 修改 | version 0.1.7 → 0.2.0 |
| `.claude-plugin/plugin.json` | 修改 | version 0.1.7 → 0.2.0 |
| `cn/.claude-plugin/plugin.json` | 修改 | version 0.1.7 → 0.2.0 |
| `/Users/motou/Desktop/daji-customer-service/.plans/daji-cs/arms/arms-20260517-001/` | 新建(验证产出) | 验证跑出来的 findings/fingerprint/resolution + archive 一行 |

---

## Task 1: commands/arms.md §3 加首参 URL 检测分流

**Files:**
- Modify: `commands/arms.md:85-112` (§3 解析参数 + 解引用 .env)

- [ ] **Step 1.1: Read §3 当前内容确认行号**

Run: 读 `commands/arms.md` 85-112 行确认插入点

- [ ] **Step 1.2: 在 §3 末尾(line 112 后)插入首参 URL 检测**

Edit `commands/arms.md`,在 "**示例语义识别**:" 块之后追加:

```markdown
**单点修复模式触发(0.2.0 新增)**: 检查首位置参,若以 `http://` 或 `https://` 开头 → 走 §10 单点修复路径,**不要**继续 §4-§9 批量流程。
```

- [ ] **Step 1.3: 验证 Edit 落点正确**

读 §3 节末尾,确认新行在"示例语义识别"列表之后、§4 之前

- [ ] **Step 1.4: 不 commit(待 Task 5 一起)**

---

## Task 2: commands/arms.md 末尾追加 §10 单点修复整节

**Files:**
- Modify: `commands/arms.md:272` (末尾追加)

- [ ] **Step 2.1: 在文件末尾追加 §10 整节内容**

Edit `commands/arms.md`,在 "频繁调用注意 SLS 配额" 这一最后 bullet 之后追加:

```markdown

## 10. 单点修复模式(targeted fix, 0.2.0 新增)

当 §3 检测到首位置参为 `http(s)://...` 时,走本节;§1/§2/§4(team 检查 + 配置三件套)仍执行,只是 §3 之后分支到这里。

### 10.1 解析 ARMS URL

ARMS rum-explorer URL 形如:
```
https://arms.console.aliyun.com/?spm=...#/rum/rum-explorer/cn-hangzhou
  ?groupKey=exception
  &from=now-1h&to=now
  &refresh=off
  &filters=%5B%7B%22key%22%3A%22app.id%22%2C%22opt%22%3A%22contain%22%2C%22value%22%3A%5B%22<PID>%22%5D%7D%5D
```

team-lead 用 Bash + python3 解析(不需要新模块):

```python
import urllib.parse, json, re, time
from datetime import datetime

raw = "<user 给的 URL>"
# hash 后面才是真正的 query
fragment = raw.split('#', 1)[1] if '#' in raw else raw
path_query = fragment.split('?', 1)
path, qs = path_query[0], path_query[1] if len(path_query) > 1 else ""
# region 从 path 取(/rum/rum-explorer/<region>)
m = re.search(r'/rum/rum-explorer/([^/?]+)', path)
region = m.group(1) if m else None
params = urllib.parse.parse_qs(qs)

def parse_time(s, now_ts):
    if not s: return None
    if s == "now": return now_ts
    m = re.fullmatch(r'now-(\d+)([smhd])', s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        mult = {"s":1,"m":60,"h":3600,"d":86400}[unit]
        return now_ts - n * mult
    if s.isdigit():
        v = int(s)
        return v // 1000 if v > 10**12 else v   # ms → s
    try:
        return int(datetime.fromisoformat(s).timestamp())
    except ValueError:
        return None

now_ts = int(time.time())
from_ts = parse_time(params.get('from', [None])[0], now_ts)
to_ts = parse_time(params.get('to', [now_ts])[0], now_ts) if params.get('to') else now_ts

filters = json.loads(params.get('filters', ['[]'])[0]) if params.get('filters') else []
app_id = next((f['value'][0] for f in filters if f.get('key') == 'app.id' and f.get('value')), None)
env = next((f['value'][0] for f in filters if f.get('key') == 'app.env' and f.get('value')), None)
```

解析失败处理(任一为真即 escalate,**不要继续**):
- 域不是 `arms.console.aliyun.com` → "非 ARMS 控制台 URL"
- 路径不含 `/rum/rum-explorer/` → "请给 RUM exception 浏览页 URL,APM 链路 URL 不支持"
- `app_id` 为空 → "URL 未含 app.id 过滤,请在控制台先选定应用"
- `from_ts` 为空 → "URL 缺 from 参数,无法确定时间窗口"
- `region` 与 CLAUDE.md `sls_region` 不符 → "URL region=X,CLAUDE.md region=Y,请确认是同一应用"
- `app_id` 与 CLAUDE.md `pid`(.env 解引用后)不符 → AskUserQuestion 让用户决定(切配置 / 取消)

### 10.2 解析可选 keywords

从原始命令文本(URL 之后的部分)正则提取 `keywords="..."` 或 `keywords=值`(简单值不含空格时):

```python
m = re.search(r'keywords\s*=\s*(?:"([^"]*)"|(\S+))', user_input)
keywords = m.group(1) or m.group(2) if m else None
```

`keywords` 缺省视为 None,SLS query 不加关键词过滤。

### 10.3 派单给 arms(targeted mode)

按 §4 的三层检查 + 健康验证 spawn 或复用 arms(逻辑不变),SendMessage 派单消息追加 5 个 targeted 字段:

```
任务: ARMS 即时巡检
- pid: <app_id>             # URL 解析的优先,与 .env 一致校验通过后用
- ak_id / ak_secret: ...    # .env 解引用
- region / project / logstore: ...

(targeted 模式专属)
- mode: targeted
- target_app_id: <URL 解析 app_id>
- target_from_ts: <unix s>
- target_to_ts: <unix s>
- target_env: <URL 解析 env, 空字符串表示 all>
- keywords: <用户给的, 空字符串表示无关键词过滤>

按 onboarding § arms 的 7 步流程执行,**注意当前 mode=targeted 见 onboarding § 模式与差异表**。
```

### 10.4 收到 arms 回报后

arms 在 mode=targeted 下回报有 3 种形态:

**形态 A: 0 命中**
```
ARMS 单点查询: 0 命中
- URL 时间窗口: <from_ts> ~ <to_ts>
- keywords: <值或空>
```
team-lead 告诉用户:"URL/keywords 无匹配 exception 事件,请精化 keywords 或扩大 URL 时间窗口"。**不写 findings.md**,不创建任务文件夹。

**形态 B: 1 fingerprint(走完 7 步)**
与 §6 批量模式回报相同(含 findings_path / branch / 推荐派单)。team-lead 按 §6 派 dev。

**形态 C: ≥2 fingerprints(暂停等用户选)**
```
ARMS 单点查询: N 命中 fingerprint,等待选择:
1. "<norm_message_A>" @ <view.name_A> (×<count>, 最新 <timestamp>)
   样本堆栈: <stack 第 1 行>
2. "<norm_message_B>" @ <view.name_B> (×<count>, 最新 <timestamp>)
   样本堆栈: <stack 第 1 行>
...
```
team-lead 用 AskUserQuestion 列出 N 个候选 + 当 N ≥ 5 时附加 "加 keywords 缩范围重跑" 选项:
- 用户选第 i 个 → SendMessage(arms) "请按 fingerprint #i 继续 Step 4.3+",arms 走完剩余 step
- 用户选"加 keywords 重跑" → 问用户新 keywords → SendMessage(arms) "请用 keywords=... 重跑 Step 3.3",arms 重新查
- 用户选"取消" → SendMessage(arms) "本次任务取消,清理半成品任务文件夹"

### 10.5 后续步骤

形态 B/C 选完后,§7(dev 完成 + reviewer)、§8(总结)、§9(用户决定不修)流程**与批量完全一致**。
```

- [ ] **Step 2.2: 验证 §10 已加在文件末尾(在最后一条 bullet 之后)**

读 `commands/arms.md` 最后 100 行确认结构

- [ ] **Step 2.3: 不 commit**

---

## Task 3: onboarding.md arms agent 加"模式与差异表"

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/references/onboarding.md:1040-1054` (arms agent 7 步前)

- [ ] **Step 3.1: 在"### 7 步闭环"之前(line 1054 前)插入模式说明**

Edit `cn/skills/CCteam-creator-cn/references/onboarding.md`,在 line 1054 `### 7 步闭环（按顺序执行）` 之前追加:

```markdown
### 模式与差异(0.2.0 新增)

team-lead 派单消息可能含 `mode` 字段:

- **`mode: batch`(缺省)**: 现有批量窗口扫描,7 步无变化
- **`mode: targeted`**: 单点修复,7 步有以下差异

| Step | batch 模式 | targeted 模式差异 |
|---|---|---|
| 1 任务文件夹 | 不变 | 不变,task-id 仍 `arms-<YYYYMMDD>-<NNN>` |
| 2 历史对比 | grep archive 预筛 | 不变 |
| 3.3 SLS 查询 | `query=app.id:{PID} AND event_type:exception`,line=500,fromTime = now - DAYS×86400 | `query=app.id:{target_app_id} AND event_type:exception [+ AND app.env:{target_env} 若有] [+ AND "{keywords}" 若有]`,line=50,fromTime=`target_from_ts`,toTime=`target_to_ts` |
| 4.1 归一化策略 | 探测 HAS_CONVERGENCE 选 A/B | 不变 |
| 4.2 分组 | 取 Top 5-10 | 按 fingerprint 计数后分支: 0 命中 → 回报 "0 命中" 给 team-lead **不写 findings, 不归档**, 任务结束; 1 fingerprint → 直接 Step 4.3; ≥2 fingerprints → 回报候选清单给 team-lead 暂停,等 team-lead 回 "请按 fingerprint #i 继续" 再 Step 4.3 |
| 4.3 根因 | 对每个 Top 高频异常做 | 仅对 1 条(或 team-lead 选定的那条) |
| 5 findings.md | 概览/聚合表/根因/方案/派单/历史参考 | 概览节加一行 `模式: 单点修复 (URL: <原 URL>, keywords: <值或空>)`; 异常聚合表只 1 行 |
| 6 fingerprint + archive | 写 fingerprint.md + archive/index.md 加一行 | 不变(archive 一行就够) |
| 7 回报 | 标准回报 | 标准回报 + 注明"单点修复" |

**0/N 分支的具体回报格式见 commands/arms.md §10.4**
```

- [ ] **Step 3.2: 验证插入点正确,前后无章节号断裂**

读 `cn/skills/CCteam-creator-cn/references/onboarding.md` 1040-1100 行确认

- [ ] **Step 3.3: 不 commit**

---

## Task 4: onboarding.md § Known Pitfalls 加 URL 解析边界

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/references/onboarding.md:1308-1326` (§ Known Pitfalls)

- [ ] **Step 4.1: 在 § Known Pitfalls 末尾(在 `convergence` 字段那条 bullet 后)追加新条目**

Edit `cn/skills/CCteam-creator-cn/references/onboarding.md`,在最后一条 bullet 后追加:

```markdown

- **ARMS URL 单点解析的硬性失败**(0.2.0 新增): targeted 模式下,team-lead 解析 URL 时如果遇到以下情况 → **不要尝试 fallback 走 batch**,直接 escalate 给用户:
  - 非 `arms.console.aliyun.com` 域(用户拷错链接)
  - 路径不含 `/rum/rum-explorer/`(可能是 APM trace 或 dashboards 链接)
  - 缺 `filters` 中的 `app.id`(用户在控制台没选应用就拷)
  - 缺 `from` 参数(用户拷的是状态未保存的 URL)
  - region/app_id 与 .env 不符(可能误粘了别的项目的 URL)
  
  fallback batch 会让用户以为"我让它修这一条,它却扫了全部"——违反单点初衷。
```

- [ ] **Step 4.2: 不 commit**

---

## Task 5: templates.md findings.md 模板加"模式"字段

**Files:**
- Modify: `cn/skills/CCteam-creator-cn/references/templates.md` (§ ARMS findings.md 模板)

- [ ] **Step 5.1: 找到 findings.md 模板位置**

Run: `grep -n "## 概览" /Users/motou/Desktop/CCteam-creator/cn/skills/CCteam-creator-cn/references/templates.md` 定位

- [ ] **Step 5.2: 在"## 概览"模板的末尾(其他基础字段之后)加可选行**

Edit templates.md,把现有的概览模板形如:

```markdown
## 概览
- 应用: <app_name>
- PID: <pid>
- env: <env>
- 回溯窗口: <days> 天
- 异常总数: <N>
```

改为:

```markdown
## 概览
- 应用: <app_name>
- PID: <pid>
- env: <env>
- 回溯窗口: <days> 天 / **或** 时间区间: <from_iso> ~ <to_iso>(targeted 模式)
- 异常总数: <N>
- 模式: <batch | targeted>(targeted 时附 `URL: <原 URL>` 和 `keywords: <值或空>`)
```

- [ ] **Step 5.3: 不 commit**

---

## Task 6: CHANGELOG.md 加 0.2.0 section

**Files:**
- Modify: `CHANGELOG.md` (顶部)

- [ ] **Step 6.1: 读 CHANGELOG.md 顶部确认 0.1.7 section 位置**

Run: `head -50 /Users/motou/Desktop/CCteam-creator/CHANGELOG.md`

- [ ] **Step 6.2: 在 0.1.7 之上插入 0.2.0 section**

Edit CHANGELOG.md,在 `## [0.1.7]` 之上追加:

```markdown
## [0.2.0] - 2026-05-17

### Added

- **`/arms` 单点修复模式**: 首位置参为 ARMS rum-explorer URL 时,从 SLS 反查精确到 1 条 fingerprint,复用 arms agent 7 步骨架完成根因分析 → 派 dev → reviewer → resolution。
  - 命令: `/arms <ARMS_URL> [keywords="..."]`
  - 实现: `commands/arms.md` §10 (self-contained 单点路径); `cn/skills/CCteam-creator-cn/references/onboarding.md` arms agent 7 步加"模式与差异表"
  - 与现有批量模式完全向后兼容(不带 URL 时行为不变)
- arms agent 协议扩展字段: `mode: batch | targeted`、`target_app_id`、`target_from_ts`、`target_to_ts`、`target_env`

### Changed

- `cn/skills/CCteam-creator-cn/references/templates.md` findings.md 模板概览节加可选 `模式` 字段

```

- [ ] **Step 6.3: 不 commit**

---

## Task 7: 3 manifest 同步 bump 到 0.2.0

**Files:**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `cn/.claude-plugin/plugin.json`

- [ ] **Step 7.1: marketplace.json bump**

Read `.claude-plugin/marketplace.json` 看当前结构,把所有 `"version": "0.1.7"` 改 `"0.2.0"`

- [ ] **Step 7.2: 根 plugin.json bump**

Edit `.claude-plugin/plugin.json` 把 `"version": "0.1.7"` 改 `"0.2.0"`

- [ ] **Step 7.3: cn 子 plugin.json bump**

Edit `cn/.claude-plugin/plugin.json` 把 `"version": "0.1.7"` 改 `"0.2.0"`

- [ ] **Step 7.4: 三处版本号一致性自查**

Run: `grep -rn '"version"' /Users/motou/Desktop/CCteam-creator/.claude-plugin/ /Users/motou/Desktop/CCteam-creator/cn/.claude-plugin/`
Expected: 三行均显示 `0.2.0`

---

## Task 8: 提交 0.2.0 release commit

- [ ] **Step 8.1: 看 git status 确认改动文件清单**

Run: `cd /Users/motou/Desktop/CCteam-creator && git status`
Expected files changed:
- commands/arms.md
- cn/skills/CCteam-creator-cn/references/onboarding.md
- cn/skills/CCteam-creator-cn/references/templates.md
- CHANGELOG.md
- .claude-plugin/marketplace.json
- .claude-plugin/plugin.json
- cn/.claude-plugin/plugin.json
- docs/superpowers/specs/2026-05-17-arms-targeted-fix-design.md (本任务 spec)
- docs/superpowers/plans/2026-05-17-arms-targeted-fix-plan.md (本文)

- [ ] **Step 8.2: git add 仅相关文件(不要 git add -A)**

Run:
```bash
cd /Users/motou/Desktop/CCteam-creator && git add \
  commands/arms.md \
  cn/skills/CCteam-creator-cn/references/onboarding.md \
  cn/skills/CCteam-creator-cn/references/templates.md \
  CHANGELOG.md \
  .claude-plugin/marketplace.json \
  .claude-plugin/plugin.json \
  cn/.claude-plugin/plugin.json \
  docs/superpowers/specs/2026-05-17-arms-targeted-fix-design.md \
  docs/superpowers/plans/2026-05-17-arms-targeted-fix-plan.md
```

- [ ] **Step 8.3: commit**

```bash
git commit -m "feat(arms): add targeted fix mode via ARMS URL (0.2.0)

- /arms <ARMS_URL> [keywords=...] dispatches arms agent in mode=targeted
- arms agent 7-step protocol extended with batch/targeted branching
- 0/1/N fingerprint match handled; N>=2 triggers AskUserQuestion in team-lead
- backward compatible: /arms with no URL keeps batch behavior
- bump 0.1.7 -> 0.2.0 (minor)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 8.4: 不 push(用户授权时再 push)**

---

## Task 9: 真实项目验证(daji-customer-service)

**Files:**
- 验证产出: `/Users/motou/Desktop/daji-customer-service/.plans/daji-cs/arms/arms-20260517-001/findings.md`
- 验证产出: `/Users/motou/Desktop/daji-customer-service/.plans/daji-cs/arms/archive/index.md` (新增一行)
- 验证产出: daji-cs 项目本地 commit `fix/arms-20260517-001`

- [ ] **Step 9.1: 用户提供 ARMS URL**

team-lead 提示用户:"请去 ARMS 控制台(https://arms.console.aliyun.com)选 daji-cs 应用,从 RUM 异常浏览页拷一条 URL,要求时间窗口覆盖 ArmsTestError 推送时间。然后告诉我 URL,可选附 keywords。"

等待用户回复 URL 字符串。

- [ ] **Step 9.2: 在 daji-customer-service 目录执行 /arms <URL>**

team-lead 自行模拟 `/arms <URL>` 流程:
1. §1 检查 daji-cs team-snapshot.md 存在 + hydrate
2. §2 检查三件套(daji-cs/.env 已有,跳过补全)
3. §3 解析参数:URL → app_id/from_ts/to_ts/env;keywords 取用户输入
4. §3 触发条件检测:首参 http:// → 跳 §10
5. §10.1 解析 URL,验证 region/app_id 与 .env 一致
6. §10.2 解析 keywords
7. §10.3 三层检查 + 健康验证 arms 角色;若需新 spawn,用 `name="arms-arms-20260517-001"`,`model="opus[1m]"`(运行时偏好),`team_name="daji-cs"`,`run_in_background=true`
8. SendMessage 派单(含 mode=targeted + target_* 字段)

- [ ] **Step 9.3: 等待 arms agent 回报(预期形态 B = 1 fingerprint)**

预期 arms 在 daji-cs/.plans/daji-cs/arms/arms-20260517-001/ 下产出:
- progress.md(7 步日志)
- findings.md(概览节含 `模式: 单点修复`,异常聚合表 1 行: ArmsTestError @ /debug/arms-test)
- fingerprint.md(status: analyzed)
- archive/index.md 新增一行

回报含: 推荐派单 = frontend-dev,拟分支 = fix/arms-20260517-001

- [ ] **Step 9.4: team-lead 派 frontend-dev**

SendMessage(to: frontend-dev) 含:
```
source: arms
arms_task_id: arms-20260517-001
findings_path: .plans/daji-cs/arms/arms-20260517-001/findings.md
branch: fix/arms-20260517-001
mr_skip: true
commit_template: arms
```

- [ ] **Step 9.5: frontend-dev 完成修复**

预期 frontend-dev:
- 读 findings 确认是 /debug/arms-test 路由的测试主动 throw
- 因为是测试代码,**两种合理修法**:
  - A: 删除路由 + 组件(测试代码不应入仓)
  - B: 保留路由但用 `import.meta.env.MODE === 'production' && ...` 包条件,生产不真触发
- 自决方案 B(更保守,保留测试入口),本地 commit 到 fix/arms-20260517-001
- 不 push

- [ ] **Step 9.6: frontend-dev 触发 reviewer**

frontend-dev 自行 SendMessage(reviewer) 含 task-id + commit-hash + 文件清单

- [ ] **Step 9.7: reviewer 给 [OK] 或 [WARN]**

预期 reviewer 检查:类型安全 / null 处理 / 与现有 ArmsTestError 路由 wiring / 无回归。给 [OK]。

- [ ] **Step 9.8: team-lead 通知 arms 写 resolution**

SendMessage(arms) 含 task-id + commit + branch + reviewer_verdict

- [ ] **Step 9.9: 验证 arms 补完 resolution.md + archive 更新**

读以下文件确认产出齐全:
- `.plans/daji-cs/arms/arms-20260517-001/resolution.md` 存在
- `.plans/daji-cs/arms/archive/index.md` 中 arms-20260517-001 行 status 从 `analyzed` 改为 `resolved`
- daji-cs 项目 `git log --oneline fix/arms-20260517-001` 含修复 commit

- [ ] **Step 9.10: 验证不影响 daji-cs 原 master 分支**

Run: `cd /Users/motou/Desktop/daji-customer-service && git status && git log --oneline -5`
Expected: 不在 fix/ 分支时,master 干净;fix/ 分支有 1 个 commit 未 merge

---

## Task 10: 收尾报告

- [ ] **Step 10.1: 总结输出给用户**

输出:
- 实现完成: 列出 7 个改动文件 + 1 个新 spec + 1 个新 plan
- 验证完成: daji-cs ArmsTestError 走完 7 步 + dev + reviewer + resolution
- 等用户授权后 git push origin master(0.2.0 release)

- [ ] **Step 10.2: 提醒用户的剩余风险**

- daji-cs 之前 6 个 commits 仍未 push,本次又新增 1 个 0.2.0 commit(共 7 个),需用户授权 push
- daji-cs 内部 fix/arms-20260517-001 分支也未 push,按 ARMS 子协议(本地 commit + 不 push)正常
- AK 凭证早前已多次进入 LLM 上下文,建议轮换

---

## Self-Review

**1. Spec coverage:** Spec §1-13 各章对照 plan:
- §1 背景 — 无对应 task(plan 不实现背景,是说明)✓ 跳过
- §2 命令形态 — Task 1(§3 首参检测)✓
- §3 URL 解析 — Task 2 §10.1 ✓
- §4 SLS query — Task 2 §10.3 + Task 3 模式差异表 Step 3.3 行 ✓
- §5 0/1/N 分支 — Task 2 §10.4 + Task 3 Step 4.2 行 ✓
- §6 arms agent 协议扩展 — Task 3 模式差异表 ✓
- §7 fingerprint 状态分支 — Task 3 Step 6 行(不变,引用 batch 流程) ✓
- §8 派 dev/reviewer/resolution — Task 9 Step 9.4-9.9 ✓
- §9 错误处理 — Task 2 §10.1 解析失败列表 + Task 4 Known Pitfalls ✓
- §10 测试 / 验证 — Task 9 ✓
- §11 版本与发布 — Task 6/7/8 ✓
- §12 范围排除 — 无对应 task(明示 NOT do)✓ 跳过
- §13 风险与回退 — Task 10 Step 10.2 ✓

**2. Placeholder scan:** 无 TBD/TODO/"implement later",所有代码块完整;Task 9 的"用户提供 URL"是必要的人机交互,不是占位。

**3. Type consistency:**
- `mode` 字段值: `batch` / `targeted` — 全文一致 ✓
- `target_app_id` / `target_from_ts` / `target_to_ts` / `target_env` — 全文一致 ✓
- task-id 格式 `arms-<YYYYMMDD>-<NNN>` — 全文一致(单点不用 `arms-fix-*` 另起编号)✓
- 分支名 `fix/<task-id>` 即 `fix/arms-20260517-001` — 一致 ✓
- 命令首参检测条件 `http:// 或 https://` — Task 1/2 一致 ✓
