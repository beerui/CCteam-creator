# Intake Protocol — User Manual

> This doc targets **human users**. It explains the intake state machine, field meanings, and the manual operations you need to perform.
> The agent-facing protocol lives at `skills/CCteam-creator/references/templates.md § Intake Processing Protocol`.

## What is an intake

The "delivery slip at the door" between the external world (Zentao bugs / ARMS errors) and CCteam. Every time bug-triage pulls new data, it writes an intake file to `.plans/<project>/intake/<source>-<id>.md`.

An intake is **not** a "tasked work item". It's a **candidate pool** — the team lead (team-lead) decides whether to officially turn it into a task only after reviewing it.

## State Machine

```
pending ──accept──→ accepted ──dev completes MR──→ in_review ──human merge──→ done
   │                                                     │
   ├──reject──→ rejected (terminal)                      ├──MR rejected/closed──→ rejected (terminal)
   │
   ├──merge──→ merged (terminal)
   │
   └──defer──→ stays pending
```

| State | Meaning | Trigger |
|-------|---------|---------|
| `pending` | Written, awaiting team-lead decision | bug-triage on write |
| `accepted` | Tasked, task folder created | team-lead |
| `in_review` | dev finished + MR submitted, awaiting human merge | dev |
| `done` | MR merged | team-lead manually / when you say "merged" |
| `rejected` | Decided not to fix (incl. MR rejected) | team-lead |
| `merged` | Combined with an existing task | team-lead |

## frontmatter Fields

```yaml
---
source: zentao | arms | arms-rum    # origin (arms = backend APM, arms-rum = frontend RUM)
external_id: 12345          # external system ID
severity: P0|P1|P2|P3       # severity
created_at: 2026-05-10T10:30:00+08:00
status: pending             # current state
external_link: https://...  # link to original system
---
```

When state evolves from pending, frontmatter gains:
- `assigned_to: <agent>` — on accept
- `task_path: ...` — on accept
- `mr_url: <url>` — on in_review
- `merged_into: ...` — on merge
- `reject_reason: <one-liner>` — on reject

## Manual Operations You'll Perform

### 1. Morning: open Claude Code

team-lead will proactively brief you on new intakes — N items pending decision. **Just talk to it**:
- "1 accept; 2 reject because it's user error not a bug; 3 defer"
- Or simply: "walk through them all and recommend"

### 2. After human merge, tell the team

After a human merges the MR on Codeup, return to Claude Code and say:
- "Zentao 12345's MR has been merged"

team-lead will update that intake's `status: done`.

### 3. Look up a historical intake

```bash
ls .plans/<project>/intake/
cat .plans/<project>/intake/<source>-<id>.md
```

Or just say to team-lead: "show me the status of intake/<id>".

### 4. Cleanup when intakes pile up

Terminal-state intakes (`done` / `rejected` / `merged`) are kept for audit by default. If the file count gets noisy:
- With custodian → "have custodian archive terminal-state intakes older than 30 days"
- Without custodian → "archive terminal-state intakes older than 30 days" — team-lead moves them to `_archive/`

## Manual Immediate Scan

Don't want to wait for tomorrow morning's 9:00? Trigger immediately:
- Slash command: `/ccteam-scan`
- Or natural language: "scan now", "scan ARMS", "look for new errors"

Parameters can be overridden inline:
- "scan Zentao" — change source to Zentao
- "scan the last 7 days" — broaden time window
- "include P2 too" — relax severity threshold

## MR Description Template (filled by dev)

```markdown
## Related
- Source: Zentao Bug #12345 / ARMS Trace abc123
- Original link: <external_link>
- Severity: P1

## Root Cause
[an explanation paragraph]

## Fix
[change description + key code snippets]

## Test Coverage
- New unit tests: <count>
- Modified/new E2E tests: <count>
- CI: PASS (golden_rules + tests + type-check all green)

## Internal Review
- Reviewer Verdict: [OK]
- Detailed review: <link to .plans/.../review-xxx/findings.md, or paste key summary>

## Risk and Impact Scope
[which modules/endpoints affected, breaking changes?]

## Pre-Merge Checklist
- [ ] Branch has no conflicts
- [ ] CI also passes on Codeup pipeline
- [ ] Canary deploy if needed
```

## FAQ

**Q: Why doesn't bug-triage assign work to dev directly?**
A: Intentional — many ARMS "errors" are noise (404s, user input errors, transient third-party failures). Routing through intake-then-team-lead lets you filter, so the team isn't drowned in auto-assigned work.

**Q: Can I edit intake files manually?**
A: Yes, but tell team-lead afterwards: "I manually flipped intake 12345 to rejected" — so it's not confused on the next scan.

**Q: A bug exists in both Zentao and ARMS — won't it get processed twice?**
A: Currently they're two independent intakes (zentao-12345.md + arms-trace-abc.md). When team-lead sees them, you can manually merge one into the other. Cross-source dedup may come later; not implemented yet.
