---
description: ARMS 即时巡检 — 查 SLS RUM 异常、分析根因、自动派 dev 修复
---

立即触发一次 ARMS RUM 异常分析。team-lead 请按以下步骤操作。

> **设计原则**: 这个命令是"零门槛即时可用"的——遇到缺失依赖(团队没 arms、CLAUDE.md 没配置)**不要直接报错**,而是**用 AskUserQuestion 交互式补全**。死胡同提示是最差的 UX。

## 1. 前置: 团队存在 & 项目识别 & live team hydration

1. 读 `.plans/` 下的项目目录,确定 `<project>`(通常一个目录)
2. 读 `.plans/<project>/team-snapshot.md`:
   - **不存在** → 直接报错: "请先 `/CCteam-creator-cn` 组团后再运行 `/arms`",停止
   - 存在 → 进入步骤 3
3. **检查 live team 是否 hydrate**(snapshot 是磁盘状态,live team 是 Claude Code 会话内存里的实例):
   - 检查 `~/.claude/teams/<project>/config.json` 是否存在
   - **存在** → 团队已 hydrate,跳到 §2
   - **不存在** → 团队冷状态(snapshot 在但 Claude Code 没实例化过)。**惰性 hydrate**:
     ```
     TeamCreate(team_name="<project>", agent_type="team-lead", description="<project> 项目 - /arms 触发的惰性 hydrate")
     ```
     **关键**: 只 TeamCreate 起 shell,**不要复活** snapshot 里的原 4-5 个角色——/arms 不是 team mode 激活,后续只需要临时 spawn arms。原角色保持冷,用户后续真要 team mode 时再走 /CCteam-creator-cn 恢复流程。
   - hydrate 完成 → 进入 §2

> **为什么要 hydrate**: V5 实测发现 — snapshot 文件存在 ≠ live team 存在。`team_name=<project>` 参数指代的是 live team(`~/.claude/teams/<project>/config.json`),如果 live team 没 hydrate,§4 的 `Agent(team_name=...)` 会**silently 失败或行为不可预期**(实测会创建 arms-2/arms-3 等不期望的命名)。先 hydrate 确保 §4 spawn 在正确的团队上下文里。

## 2. 检查 + 补全 ARMS 即时巡检配置(.env + CLAUDE.md)

**设计原则(0.1.6 起)**: 真值落 `.env`(被 `.gitignore`),CLAUDE.md 只落 `${VAR}` 引用。这两个文件配合形成"配置 + 凭证"分离:

| 文件 | 角色 | 内容 |
|---|---|---|
| `.env` | 凭证 / 配置真值 | `ARMS_AK_ID='...'` / `SLS_PROJECT='...'` 等真值 |
| `CLAUDE.md` `## ARMS 巡检配置` 节 | 引用 + 文档 | `sls_ak_id: ${ARMS_AK_ID}` + 获取方式注释 |

读项目 CLAUDE.md,在文中 grep `## ARMS 巡检配置 — 即时巡检（arms agent）`:

- **节存在且全 `${VAR}` 引用**(pid + sls_region + sls_project + sls_logstore + sls_ak_id + sls_ak_secret 全是 `${VAR}` 形式) → 验证 `.env` 含对应变量(Read .env 解析),进入 §3
- **节缺失 / 引用不全 / 字段值是占位 / 字段值是明文** → **交互式补全 + 落 .env**:

  **占位识别**(任一为真即视为缺失):
  - 包含 `<...>` 包裹(如 `<your-pid>`、`<ACCESS_KEY>`)
  - 等于 `your-...` / `xxx` / `TODO` / `FIXME` / `your-pid-here` 等明显占位
  - 长度 < 8 字符(凭证字段)

  **明文识别**(0.1.6 新增):
  - 字段值**不**是 `${VAR}` 形式且不是占位 → 视为明文,**降级处理**: 把明文搬到 .env 对应变量,CLAUDE.md 改为 `${VAR}` 引用;提醒用户"已把明文从 CLAUDE.md 移到 .env"

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
       "请把只读 RAM 子账号的 **AK ID** 和 **AK Secret** 粘进来(两个值,各一行)。建议用只读策略,如 `AliyunLogReadOnlyAccess`"
  3. **写入 .env**(项目根)使用约定变量名:
     ```
     VITE_APP_ARMS_PID='<pid>'             # VITE_ 前缀因为 src/utils/arms.ts 也用同 PID(常见)
     SLS_REGION='<region>'
     SLS_PROJECT='<project>'
     SLS_LOGSTORE='<logstore>'
     ARMS_AK_ID='<ak_id>'                  # 复用 sourcemap 上传变量名,若该子账号 RAM 策略已含 SLS 读
     ARMS_AK_SECRET='<ak_secret>'
     ```
     - 用 `Read .env` 看现有内容 → 用 Edit 在末尾追加(若文件不存在 → Write 新建)
  4. **确保 .gitignore 含 `.env`**: Read `.gitignore` grep `^.env$` → 没有则 Edit 追加。**这一步不可跳过**,否则下次 `git add .` 会 staged 凭证
  5. **写入 CLAUDE.md**: 用 Edit 在末尾追加 `## ARMS 巡检配置 — 即时巡检（arms agent）` section,内容**只含 `${VAR}` 引用 + 获取方式注释**(用 references/templates.md § 即时巡检模板填充)。**严禁**把真值复制进 CLAUDE.md。
  6. 顺带提醒用户:
     ```
     已完成 ARMS 配置三件套:
     - .env (含真值, 被 .gitignore 保护)
     - .gitignore (已加 .env)
     - CLAUDE.md (含 ${} 引用 + 获取方式注释)

     凭证只在 team-lead 解引用时存在于内存,不会写到 .plans/。
     ```

  > **可选**: 如果项目装了 `arms-rum` MCP(检查工具列表是否含 `mcp__arms-rum__GetRumApps`),且用户不知道 PID,可以直接调 GetRumApps 拉应用列表,用 **AskUserQuestion** 让用户选,**省去手输 PID 这一步**。

## 3. 解析参数 + 解引用 .env

从用户附带的自然语言或显式参数中识别(参数可省,用默认):

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pid` | CLAUDE.md `pid` (解引用 .env) | ARMS RUM 应用 ID |
| `env` | `default_env` (CLAUDE.md) → `prod` | 环境过滤(prod/daily/pre/all);先读 CLAUDE.md `default_env` 字段,缺失才用硬编码 `prod`;显式指定才查非生产 |
| `days` | 7 | 回溯天数 |
| `keywords` | 空 | 错误消息子串过滤(透传给 SLS query) |

**关键: ${VAR} 解引用步骤(0.1.6 新)**

CLAUDE.md ARMS 节里的 `${VAR}` 引用必须**在 team-lead 这一层解开**,把真值传给 arms agent(arms 收到时已是真值,不需要自己解 .env):

1. Read 项目根 `.env`,parse 成 `key=value` 字典(去引号、去空白)
2. 遍历 CLAUDE.md ARMS 节里所有 `${VAR}` 出现位置,从字典取值替换
3. 任一引用解不出(变量在 .env 缺失)→ **escalate**,提示用户"`.env` 缺 `<VAR_NAME>`,请按 CLAUDE.md 注释填好后重试"
4. 解完后,真值**只存在于 team-lead 内存**,用 SendMessage / Agent prompt 时传给 arms;**绝不**回写 CLAUDE.md 或 .plans/

> **为什么 team-lead 解引用,不让 arms 解**: arms 是 general-purpose subagent,默认不知道 .env 规则、不熟悉 python-dotenv 等库,且 team-lead 解一次给所有下游用比每个 agent 自己解更高效安全。这是控制平面 / 数据平面分离的体现。

**示例语义识别**:
- "/arms" → 默认全套
- "/arms env=all" / "查一下所有环境" → env=all
- "/arms days=1" / "最近 1 天" → days=1
- "/arms keywords=验证码" / "查含验证码的错误" → keywords=验证码

**单点修复模式触发(0.2.0 新增)**: 检查首位置参,若以 `http://` 或 `https://` 开头 → 走 §10 单点修复路径,**不要**继续 §4-§9 批量流程。

## 4. 检查 + 补全 arms 角色

**三层检查 + 健康验证**(snapshot 花名册 vs live team 成员 vs liveness):

1. 读 `~/.claude/teams/<project>/config.json` 的 `members` 数组(§1 步骤 3 已 hydrate 保证存在),grep `name == "arms"`(或任何 `arms-*` 命名):
   - **有 live arms / arms-N member** → 进入步骤 1a **健康检查**(不能盲目复用)
   - **没有 live arms member** → 进入步骤 2

   **步骤 1a: 健康检查(0.1.7 新增)**

   live member 可能处于以下任一非健康态:
   - **僵尸 sonnet** (老 spawn 没装 shutdown 协议教程,只 `read: true` 不响应)
   - **完成态 idle** (上次任务结束已回报,context 含旧任务记忆,直接复用会重放上次回应)
   - **跨任务 cwd 漂移** (上次 spawn 用旧项目路径,本次新路径)

   检查策略:
   ```
   SendMessage(to: "arms", message: "[health-check] team-lead 询问: 你当前空闲吗? 上次任务 ID? 请用一句话确认 alive")
   等待 60 秒
   ```

   - 60 秒内收到 plain text 响应("是,空闲,上次任务 arms-XXXX") → **alive**,记下 alive_member_name(可能是 arms / arms-2 / arms-3),进入 §5 SendMessage 派单复用
   - 60 秒未响应 / 收到无关响应(如重放旧 findings) / 收到协议错误 → **stale**,走步骤 2 spawn fresh,用**唯一 name** `arms-<task-id>`(如 `arms-arms-20260516-001`)避免与旧 member 冲突

2. 读 `.plans/<project>/team-snapshot.md` 的花名册表,grep `^| arms `:
   - **arms 在花名册**(snapshot 上但未 hydrate) → 走"花名册 spawn"路径:从 snapshot 入职 prompt section Read 完整 prompt,`Agent(name="arms-<task-id>", team_name="<project>", ..., prompt=<snapshot 的 prompt>)` 加入 team(name 含 task-id 保唯一,避免 silently 改名)
   - **arms 不在花名册** → **不要报错**,走"临时 spawn"路径(参考 /ccteam-scan 对 bug-triage 的处理):

  ```
  Agent(
    subagent_type: "general-purpose",
    model: "opus",                      # 推荐 opus, 注意见下方 platform 限制
    name: "arms-<task-id>",             # 0.1.7: 用 task-id 后缀,避免 silently 改名
    team_name: "<当前团队名,从 team-snapshot 头信息读>",
    description: "ARMS 即时巡检",
    prompt: <把 cn/skills/CCteam-creator-cn/references/onboarding.md § arms 整段 + 本次任务参数(§3 解析得到的 pid/env/days/keywords + CLAUDE.md 的 ak/secret/region/project/logstore)拼起来>,
    run_in_background: true
  )
  ```

  spawn 时**带上 team_name 参数**,这样 arms 会加入团队、能用 SendMessage 与其他 agent 通信。本次会话结束后是否保留在花名册由用户决定(见 §8)。

  > **0.1.7 起 `name` 用 `arms-<task-id>` 而非纯 `arms`**: 实测 0.1.6 用 `name="arms"` 时,如果 team 里已有同名僵尸/idle member,Claude Code **silently 改名**为 `arms-2`/`arms-3`,导致主对话与 spawn 时期望的 SendMessage `to: "arms"` 收件方不一致。task-id 后缀(如 `arms-arms-20260516-001`)保证 name 与本次任务 1:1 绑定,SendMessage 时也用同 name。

  > **为什么先做健康检查再决定复用**: 0.1.6 §4 假设"有 live member → alive → 复用",**实测发现**有 3 类伪 live 状态(僵尸 sonnet / 完成态 idle / cwd 漂移)会让"复用"实际等于"消息丢进黑洞"。0.1.7 强制 SendMessage ping + 60s 等待,有响应才信。

  > **关于 model 选择**: `model: "opus"` 实际 spawn 出的是 **200k context 普通 opus**,**不是 1M context opus[1m]** — Agent 工具 model enum 限制为 `["sonnet","opus","haiku"]`,无法显式选 [1m]。arms 7 步典型 token 用量 ~50k,200k 完全够;除非 SLS 返回 100+ 异常事件需要 1M。详见 onboarding § Known Pitfalls。

  > **为什么 `run_in_background: true`**: arms 7 步流程(SDK 装 + SLS 查 + 归一化 + 根因定位 + 写 5 文件 + 归档)在 sonnet 上一般 10-15 分钟,opus 上 5-10 分钟。foreground 会阻塞主对话期间用户无法看进度、无法 abort、无法做别的事。background 后用户可继续与主对话交互,arms 完成自动通知 team-lead 触发 §6。

  > **临时 spawn 与花名册 spawn 的区别**: 临时 spawn 把任务参数**直接拼进 prompt**(一次性发送);花名册 spawn 是先 SendMessage 然后 agent 按 onboarding 接受任务。临时 spawn 走完即结束,花名册 spawn 留存待复用。

## 5. 派发给 arms (仅花名册路径)

```
SendMessage(to: "arms"):
任务: ARMS 即时巡检
- pid: <来自 CLAUDE.md / 用户选择>
- env: <解析得到, 默认 CLAUDE.md `default_env` 或 prod>
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
  branch: fix/<task-id>
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
- 分支: fix/<task-id>
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

## 10. 单点修复模式(targeted fix, 0.2.0 新增)

当 §3 检测到首位置参为 `http(s)://...` 时走本节;§1(团队 hydrate)+ §2(三件套补全)+ §4 第一次的健康检查仍执行,§3 之后分支到这里。

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
fragment = raw.split('#', 1)[1] if '#' in raw else raw   # hash 后才是真 query
path_query = fragment.split('?', 1)
path = path_query[0]
qs = path_query[1] if len(path_query) > 1 else ""

m = re.search(r'/rum/rum-explorer/([^/?]+)', path)
region = m.group(1) if m else None
params = urllib.parse.parse_qs(qs)

def parse_time(s, now_ts):
    if not s: return None
    if s == "now": return now_ts
    m = re.fullmatch(r'now-(\d+)([smhd])', s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        mult = {"s":1, "m":60, "h":3600, "d":86400}[unit]
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
to_ts = parse_time(params.get('to', ['now'])[0], now_ts)

filters_raw = params.get('filters', ['[]'])[0]
filters = json.loads(filters_raw) if filters_raw else []
app_id = next((f['value'][0] for f in filters
               if f.get('key') == 'app.id' and f.get('value')), None)
env = next((f['value'][0] for f in filters
            if f.get('key') == 'app.env' and f.get('value')), None)
```

解析失败处理(任一为真 → escalate 给用户,**不要继续也不要 fallback batch**):

- 域不是 `arms.console.aliyun.com` → "非 ARMS 控制台 URL"
- 路径不含 `/rum/rum-explorer/` → "请给 RUM exception 浏览页 URL,APM 链路 URL 不支持"
- `app_id` 为空 → "URL 未含 app.id 过滤,请在控制台先选定应用"
- `from_ts` 为空 → "URL 缺 from 参数,无法确定时间窗口"
- `region` 与 CLAUDE.md `sls_region`(解引用后)不符 → "URL region=X, .env SLS_REGION=Y,请确认是同一应用"
- `app_id` 与 CLAUDE.md `pid`(解引用 .env 后)不符 → AskUserQuestion 让用户决定(切配置 / 取消)

### 10.2 解析可选 keywords

`keywords` 是可选参数。从原始命令文本(URL 之后的部分)正则提取:

```python
m = re.search(r'keywords\s*=\s*(?:"([^"]*)"|(\S+))', user_input)
keywords = (m.group(1) or m.group(2)) if m else None
```

缺省 → SLS query 不加关键词过滤(只靠 URL 时间窗口 + app.id 收敛)。

### 10.3 派单给 arms(targeted mode)

按 §4 的三层检查 + 健康验证 spawn 或复用 arms(逻辑不变),SendMessage 派单消息追加 5 个 targeted 字段:

```
任务: ARMS 即时巡检
- pid: <app_id>             # URL 解析的优先,需与 .env pid 一致
- ak_id / ak_secret: ...    # .env 解引用
- region / project / logstore: ...

(targeted 模式专属)
- mode: targeted
- target_app_id: <URL 解析 app_id>
- target_from_ts: <unix s>
- target_to_ts: <unix s>
- target_env: <URL 解析 env, 空字符串表示 all>
- keywords: <用户给的, 空字符串表示无关键词过滤>

按 onboarding § arms 的 7 步流程执行,**注意 mode=targeted,见 onboarding § 模式与差异**。
```

### 10.4 收到 arms 回报后

mode=targeted 下 arms 回报有 3 种形态:

**形态 A: 0 命中**

```
ARMS 单点查询: 0 命中
- URL 时间窗口: <from_ts> ~ <to_ts>
- keywords: <值或空>
```

team-lead 告诉用户:"URL/keywords 无匹配 exception 事件,请精化 keywords 或扩大 URL 时间窗口"。**不写 findings.md,不创建任务文件夹**(arms agent 已在 Step 4.2 清理半成品)。

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

team-lead 用 AskUserQuestion 列出 N 个候选(N ≥ 5 时附加"加 keywords 缩范围重跑"选项):

- 用户选第 i 个 → SendMessage(arms) "请按 fingerprint #i 继续 Step 4.3+",arms 走完剩余 step
- 用户选"加 keywords 重跑" → 问用户新 keywords → SendMessage(arms) "请用 keywords=... 重跑 Step 3.3"
- 用户选"取消" → SendMessage(arms) "本次任务取消,清理半成品任务文件夹"

### 10.5 后续步骤

形态 B/C 完成 fingerprint 选择后,§7(dev 完成 + reviewer)、§8(总结)、§9(用户决定不修)流程**与批量完全一致**。


---

## §11 单条深挖模式 (P1+ 0.3.0 新增)

### 触发

```
/arms task=arms-20260517-001
```

从 `inbox.md` 链接深挖某条已被 SessionStart 自动采集的指纹。

### 路由逻辑

1. team-lead (或 light 模式直接) 读 `.plans/<project>/arms/archive.db` 的 `fingerprints` 表
2. 找到 `task_id=<task-id>` 的行 → 若不存在报错 "未知 task_id, 检查 inbox.md"
3. 若 `status='analyzed'` 且尚无 findings.md → SendMessage(arms, mode='deepen', task_id=...)
4. arms agent 跳过 Step 1-3 (P1 SessionStart 已采集), 从 Step 4 (根因定位) 开始:
   - Read 该 fingerprint 的 `stack` + `view_name` + `env` + `conv_message`
   - Read 涉及代码文件做交叉根因分析
   - 写 `.plans/<project>/arms/<task-id>/findings.md`
   - 补全 `.plans/<project>/arms/<task-id>/fingerprint.md` (确保 stack_top_frame 等齐)
   - 回报 team-lead 含推荐派单 (走 §6 派 dev)

### 与 §10 (URL targeted) 的关系

| 模式 | 触发 | 用途 |
|------|------|------|
| §10 targeted | `/arms https://arms.console...` | ARMS 后台某条 trace 直接喂入, 含原始 trace_id 信息 |
| §11 deepen | `/arms task=arms-20260517-001` | 已被 SessionStart hook 自动采集的指纹, 触发根因分析阶段 |
