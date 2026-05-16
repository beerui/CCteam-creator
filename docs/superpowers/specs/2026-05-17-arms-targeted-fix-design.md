# /arms 单点修复模式（targeted fix）— 设计文档

- 日期: 2026-05-17
- 版本: 0.2.0 (minor: 新增命令分支 + arms agent 协议扩展)
- 状态: design

## 1. 背景与动机

现有 `/arms` 是**批量窗口模式**：SLS query 一次拉 500 条，按 `(message.convergence, view.name)` 归一化后 Top 5-10 入 findings.md，全量入 fingerprint 库。

用户在 ARMS 控制台手动定位到一条具体异常后，希望让 Claude 直接修这一条，**不需要再走全量扫描**。本期新增"单点修复模式"，复用现有 7 步骨架但只处理单条 fingerprint。

## 2. 命令形态

```
/arms                               # 现有：批量窗口扫描
/arms env=daily days=1              # 现有：批量带参
/arms <ARMS_URL>                    # 新增：单点修复（仅 URL）
/arms <ARMS_URL> keywords="..."     # 新增：单点修复 + 关键词缩范围
```

**首位置参分流规则**：以 `http://` 或 `https://` 开头 → 单点路径；否则走批量路径。

**keywords 可选**：缺省时 SLS 查询不加关键词过滤；用户多于一条聚合时由 team-lead 用 AskUserQuestion 让用户选 1。

## 3. URL 解析（team-lead 层）

ARMS rum-explorer URL 形如：
```
https://arms.console.aliyun.com/?spm=...#/rum/rum-explorer/cn-hangzhou
  ?groupKey=exception
  &from=now-1h&to=now
  &refresh=off
  &filters=%5B%7B%22key%22%3A%22app.id%22%2C%22opt%22%3A%22contain%22%2C%22value%22%3A%5B%22c67ee5ri5a%40a02e69a18ed6a39%22%5D%7D%5D
```

**解析输出**：
| 字段 | 来源 | 必需 | 说明 |
|---|---|---|---|
| `region` | path 段（如 `/rum-explorer/cn-hangzhou`）| 是 | 与 CLAUDE.md `sls_region` 比对，不一致 → escalate |
| `app_id` | `filters` 数组中 `key=app.id` 的 `value[0]` | 是 | 与 CLAUDE.md `pid` 比对，不一致 → escalate |
| `from_ts`, `to_ts` | `from / to` 参数 | 是 | 支持 `now-Xh/Xd/Xm`、unix ms、ISO 8601 |
| `env` | `filters` 中可选的 `app.env` | 否 | 缺省时不加 env 过滤（等价 env=all）|

**相对时间解析**：
- `now` → 当前 unix ts（秒）
- `now-1h` → 当前 - 3600
- `now-7d` → 当前 - 7×86400
- `now-30m` → 当前 - 1800
- 纯数字（13 位）→ unix ms ÷ 1000
- ISO 8601 → datetime.fromisoformat → ts

**解析失败处理**：
- 不是 `arms.console.aliyun.com` 域 → escalate "非 ARMS 控制台 URL"
- 不是 `rum-explorer` 路径 → escalate "请给 rum-explorer 页面 URL，APM 链路 URL 不支持"
- 缺 `app.id` filter → escalate "URL 未含 app.id 过滤，请在控制台先选定应用"
- region 与 CLAUDE.md 不符 → escalate "URL region=X，CLAUDE.md region=Y，请确认是同一应用"
- app_id 与 CLAUDE.md `pid` 不符 → 提示用户"URL 应用与当前项目 .env 配置不一致，是否切换配置？"

## 4. SLS 反查 query（arms agent 内）

```python
query = f"app.id:{APP_ID} AND event_type:exception"
if ENV:                          # URL 解析出 env filter
    query += f" AND app.env:{ENV}"
if KEYWORDS:                     # 用户显式给的关键词
    query += f' AND "{KEYWORDS}"'
req = GetLogsRequest(
    PROJECT, LOGSTORE,
    fromTime=FROM_TS, toTime=TO_TS,
    query=query,
    line=50,                     # 单点不需要 500
)
```

错误分类与批量路径相同（onboarding § Step 3.4）。

## 5. 归一化 + 0/1/N 分支（arms agent 内）

复用现有 Step 4.1 策略选择（`HAS_CONVERGENCE` 探测）。归一化后按 `(norm_message, view.name)` 计数。

| 命中数 | 分支 |
|---|---|
| 0 | arms 回报 team-lead "URL/keywords 无匹配事件"，team-lead 告诉用户"请精化 keywords 或扩大 URL 时间窗口"，**不写 findings** |
| 1 fingerprint | arms 直接进入 Step 4.3 根因 → Step 5/6/7 写完 |
| ≥2 fingerprints | arms **回报 team-lead 候选清单**（每条含 norm_message / view.name / 次数 / 最新时间 / 一条样本堆栈摘要），**暂停**等 team-lead 反馈选择 |

**N 分支的二次交互**：
1. team-lead 用 AskUserQuestion 让用户从 N 个候选里选 1：
   ```
   找到 N 条 fingerprint，选一条修复:
   - 选项 1: "<norm_message>" @ <view.name> (×次数, 最新 <时间>)
   - 选项 2: ...
   - ...
   - 加 keywords 缩范围重跑 (N≥5 时附加此选项)
   ```
2. 用户选 1 → team-lead SendMessage 回 arms "请按 fingerprint #X 继续"
3. arms 进入 Step 4.3 仅分析选中的 1 条

## 6. arms agent 协议扩展（onboarding § arms 7 步加 targeted 分支）

team-lead 派单消息新增 3 个字段（在原 pid / env / days / keywords / ak / ... 后追加）：

```
mode: targeted               # 新增, "batch" 或 "targeted", 缺省 batch
target_app_id: <URL解析>     # 新增, mode=targeted 必填
target_from_ts: <URL解析>    # 新增, mode=targeted 必填
target_to_ts: <URL解析>      # 新增, mode=targeted 必填
target_env: <URL解析或空>    # 新增
```

arms 收到 `mode: targeted` 时：
| 7 步 step | 行为变化 |
|---|---|
| Step 1 任务文件夹 | 不变，task-id 仍 `arms-<YYYYMMDD>-<NNN>` |
| Step 2 历史对比 | 不变 |
| Step 3.3 正式查询 | 用 §4 的 targeted query 替换批量 query，line=50 |
| Step 4.1 归一化 | 不变 |
| Step 4.2 分组 | 不取 Top 5-10，按 §5 规则进 0/1/N 分支 |
| Step 4.3 根因 | 仅 1 条聚合 |
| Step 5 findings.md | 概览区注明 `模式: 单点修复 (URL: <user 给的>, keywords: <值或空>)`；异常聚合表只 1 行 |
| Step 6 fingerprint + archive | 不变（archive/index.md 仍记一行）|
| Step 7 回报 | 不变；推荐派单同批量 |

batch mode（缺省）行为完全不变，向后兼容。

## 7. fingerprint 状态分支（与批量相同）

Step 6 的 archive 再次指纹匹配规则不变：
- 命中 `status=resolved` → findings 改为"复发"摘要，团长侧告诉用户"上次修复 commit X，可能修复未合并 / 有遗漏 / 同根因新场景"
- 命中 `status=analyzed` → 终止本任务，回报"已有进行中任务 <task-id>"，团长展示给用户旧 findings
- 命中 `status=ignored` → findings 改为"复发（上次被忽略）"摘要，团长侧告诉用户"上次说不修 @ <date>，本次是否照修？"

## 8. 派 dev / reviewer / resolution（完全复用现有流程）

team-lead 收到 arms 回报后的派单消息与批量路径一致：
```
source: arms
arms_task_id: arms-<YYYYMMDD>-<NNN>
findings_path: .plans/<project>/arms/<task-id>/findings.md
branch: fix/<task-id>
mr_skip: true
commit_template: arms
```

dev 走 onboarding § ARMS 来源任务子协议（本地 commit + 不 push）。
reviewer 完成 [OK] 后 team-lead 通知 arms 补 resolution（不变）。

## 9. 错误处理

| 错误 | 处理 |
|---|---|
| URL 解析失败（非 ARMS / 非 rum-explorer / 缺 filter）| team-lead 直接 escalate 给用户，**不 spawn arms** |
| URL 解析成功但 region/app_id 与 .env 不一致 | team-lead AskUserQuestion 让用户决定（切配置 / 取消）|
| SLS 0 命中 | arms 回报，team-lead 告知用户"无匹配，请精化 keywords 或扩大窗口"，不写 findings.md |
| SLS N≥2 fingerprint | §5 N 分支二次交互 |
| .env 缺 ARMS_AK_ID/SECRET | 走现有 §2 三件套补全流程（不变）|

## 10. 测试 / 验证

**真实项目验证场景**：daji-customer-service 已推 ArmsTestError 测试事件（2026-05-16 23:50 附近，env=daily，view.name=/debug/arms-test）。

验证步骤：
1. 用户从 ARMS 控制台拷一条覆盖 23:50 时间点的 URL（如 from=2026-05-16T23:00&to=2026-05-17T01:00，filter app.id=c67ee5ri5a@a02e69a18ed6a39）
2. 执行 `/arms <URL> keywords="ArmsTestError"`
3. 预期：1 fingerprint → arms 7 步走 targeted 分支 → frontend-dev 收到派单 → 修复（删除/降级测试触发代码）→ reviewer [OK] → resolution
4. 验证文件：
   - `.plans/daji-cs/arms/arms-20260517-001/findings.md` 含"模式: 单点修复"标注，异常聚合表 1 行
   - `.plans/daji-cs/arms/archive/index.md` 新增一行（status=resolved）
   - 本地 commit `fix/arms-20260517-001` 含修复
   - 无 push（本地保留）

**子进程 model**：按用户运行时偏好 `opus[1m]`（1M context Opus）spawn arms / frontend-dev / reviewer。

## 11. 版本与发布

- **版本号**：0.2.0（minor bump，理由：新增命令分支 + arms agent 协议字段 `mode: targeted`，向后兼容但有公开协议扩展）
- **改动文件**：
  - `commands/arms.md`（在 §3 参数解析处增加"首位置参 URL 检测"分流逻辑；在 §4 之前插入单点路径专属步骤，或将单点差异编织进现有 §4-§7。实现方式由 plan 决定）
  - `cn/skills/CCteam-creator-cn/references/onboarding.md`（arms agent 7 步加 targeted 分支差异表 + § Known Pitfalls 增 URL 解析边界条目）
  - `cn/skills/CCteam-creator-cn/references/templates.md`（findings.md 模板加可选 `模式` 字段）
  - `CHANGELOG.md`（新增 0.2.0 section）
  - 三个 manifest 文件 version 同步：
    - `/Users/motou/Desktop/CCteam-creator/.claude-plugin/marketplace.json`
    - `/Users/motou/Desktop/CCteam-creator/.claude-plugin/plugin.json`
    - `/Users/motou/Desktop/CCteam-creator/cn/.claude-plugin/plugin.json`

## 12. 范围排除

明确不做：
- 不支持 ARMS APM 链路 URL（仅 RUM exception）
- 不支持 OPS / SLS console URL 直接传入
- 不实现"取 Top 1 自动派"自动决策（多匹配始终交回用户）
- 不实现"一次修一个 URL 窗口里所有 fingerprint"（违反单点初衷）
- 不修改 batch 路径任何现有行为（严格向后兼容）

## 13. 风险与回退

| 风险 | 缓解 |
|---|---|
| URL 解析正则覆盖不全（ARMS 控制台改 URL 结构）| 留 escalate 出口，让用户手动告知 from/to/app_id |
| N 分支无限循环（用户每次都选"加 keywords 重跑"）| 不限制次数；用户明示放弃即停 |
| SLS 1h 窗口仍返回 50+ 条 | line=50 截断，arms findings 注明"窗口内事件超 50 条，已截断" |
| 单点 vs 批量同任务号冲突 | task-id 用同一序号空间，archive/index.md 一行同样记录，模式字段在 findings.md 区分 |

回退方案：如发现单点路径阻塞批量路径，可临时在 `/arms` 入口禁用 URL 首参分流（一行注释），不影响现网 batch 用户。
