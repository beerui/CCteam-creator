# Intake 协议 — 用户操作手册

> 本文档面向**人类用户**，解释 intake 状态机、字段含义，以及你需要手动操作的场景。
> 给 agent 看的协议在 `cn/skills/CCteam-creator-cn/references/templates.md § Intake Processing Protocol`。

## 什么是 intake

外部世界（禅道 Bug / ARMS 错误）进入 CCteam 的"门口快递单"。bug-triage 每次拉到新数据，会写一个 intake 文件落到 `.plans/<project>/intake/<source>-<id>.md`。

intake 不等于"已立项的任务"。它是**候选 task 池**——团队负责人 (team-lead) 看完后才决定是否立项。

## 状态机

```
pending ──accept──→ accepted ──dev完成MR──→ in_review ──人工合入──→ done
   │                                              │
   ├──reject──→ rejected (终态)                   ├──MR 被拒/关闭──→ rejected (终态)
   │
   ├──merge──→ merged (终态)
   │
   └──defer──→ 保持 pending
```

| 状态 | 含义 | 谁触发 |
|------|------|--------|
| `pending` | 已落盘，等 team-lead 决策 | bug-triage 写入时 |
| `accepted` | 已立项，task 文件夹已建 | team-lead |
| `in_review` | dev 已完成 + MR 已提，等人工合入 | dev |
| `done` | MR 已合入 | team-lead 手工 / 你告诉它"已合入了" |
| `rejected` | 决定不修（含 MR 被拒） | team-lead |
| `merged` | 合并到已有 task | team-lead |

## frontmatter 字段

```yaml
---
source: zentao | arms | arms-rum    # 来源（arms = 后端 APM, arms-rum = 前端 RUM）
external_id: 12345          # 外部系统的 ID
severity: P0|P1|P2|P3       # 严重级
created_at: 2026-05-10T10:30:00+08:00
status: pending             # 当前状态
external_link: https://...  # 跳转原始系统的链接
---
```

状态从 pending 演进时 frontmatter 会追加:
- `assigned_to: <agent>` — accept 时
- `task_path: ...` — accept 时
- `mr_url: <url>` — in_review 时
- `merged_into: ...` — merge 时
- `reject_reason: <一句话>` — reject 时

## 你需要手动操作的场景

### 1. 早上打开 Claude Code

team-lead 会主动汇报新 intake，告诉你 N 个待决策。**直接对它说**就行：
- "1 号 accept、2 号 reject 因为不是 bug 是用户误操作、3 号 defer"
- 或直接 "都过一遍并给我建议"

### 2. MR 合入后告诉团队

人工把 MR 合入 Codeup 之后，回到 Claude Code 说一句：
- "禅道 12345 的 MR 已合入"

team-lead 会更新对应 intake 的 `status: done`。

### 3. 想看历史某个 intake

```bash
ls .plans/<project>/intake/
cat .plans/<project>/intake/<source>-<id>.md
```

或直接对 team-lead 说"展示 intake/<id> 的状态"。

### 4. intake 太多想清理

终态 intake (`done` / `rejected` / `merged`) 默认保留供审计。如果文件多到影响导航：
- 有 custodian 角色 → "请 custodian 归档 30 天前的终态 intake"
- 没 custodian → 你直接说 "归档 30 天前的终态 intake"，team-lead 会移到 `_archive/`

## 立即手动巡检

不想等明早 9 点，现在就要扫一次：
- 斜杠命令: `/ccteam-scan`
- 或自然语言: "立即巡检"、"扫一下 ARMS"、"现在看看新错误"

参数可临时覆盖：
- "扫一下禅道" — 把数据源改成禅道
- "扫最近 7 天" — 扩大时间窗口
- "把 P2 也带上" — 放宽严重级阈值

## MR 描述模板（dev 提 MR 时填充）

```markdown
## 关联
- 来源: 禅道 Bug #12345 / ARMS Trace abc123
- 原始链接: <external_link>
- 严重级: P1

## Root Cause
[一段说明]

## Fix
[改动描述 + 关键代码片段]

## Test Coverage
- 新增单测: <count>
- 修改/新增 E2E: <count>
- CI: PASS（golden_rules + tests + type-check 全绿）

## Internal Review
- Reviewer Verdict: [OK]
- 详细评审: <链接到 .plans/.../review-xxx/findings.md，或粘贴关键摘要>

## 风险与影响范围
[影响哪些模块/接口，是否有 breaking change]

## 人工合入前 checklist
- [ ] 检查分支无冲突
- [ ] 确认 CI 在 Codeup 流水线上也通过
- [ ] 必要的话灰度
```

## 常见问题

**Q: bug-triage 为什么不直接派单给 dev？**
A: 故意不直接派——ARMS 的"错误"很多是噪声（404、用户输入错误、第三方临时故障）。先落 intake 让你过一遍，避免团队被自动派单淹没。

**Q: 我能手动改 intake 文件吗？**
A: 可以，但建议改完告诉 team-lead 一声"我手动把 intake 12345 改成 rejected 了"，免得它下次扫描时被你的修改困惑。

**Q: 同一个 bug 在禅道和 ARMS 都被抓到了，会重复处理吗？**
A: 当前版本是两个独立 intake（zentao-12345.md + arms-trace-abc.md）。team-lead 看到时可以手动 merge 一个到另一个。后期可能加跨源融合，目前暂未做。
