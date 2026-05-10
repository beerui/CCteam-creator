# MCP Setup Guide

> This document targets users **first-time configuring** the CCteam-creator Aliyun integration. It's a one-time setup; the skill flow validates everything afterwards.

## Required MCP Inventory

| MCP | Purpose | Required vs. Optional |
|-----|---------|-----------------------|
| `alibabacloud-devops-mcp-server` (Yunxiao) | dev submits MR to Codeup | Required when Codeup integration is enabled |
| `@tytt/zentao-mcp` (Zentao) | bug-triage pulls Zentao bugs | Required when Zentao trigger source is enabled |
| `alibabacloud-api-mcp-server` (Aliyun OpenAPI) | bug-triage queries ARMS error events | Required when ARMS scan is enabled |

## 1. Yunxiao MCP

### 1.1 Get an access token

1. Log in to Yunxiao → Personal Settings → Personal Access Tokens
2. Create a token; check permissions: Code (read+write) + Project (read+write)
3. Copy the token (shown only once — keep it safe)

### 1.2 Add to Claude Code MCP config

Edit `~/.claude/mcp.json` or project-level `.mcp.json`:

```json
{
  "mcpServers": {
    "yunxiao": {
      "command": "npx",
      "args": ["-y", "alibabacloud-devops-mcp-server"],
      "env": {
        "YUNXIAO_ACCESS_TOKEN": "<your token>",
        "YUNXIAO_API_BASE_URL": "https://openapi-rdc.aliyuncs.com"
      }
    }
  }
}
```

If you're on Region Edition Yunxiao (dedicated domain), set `YUNXIAO_API_BASE_URL` to `https://<your-org>.devops.aliyuncs.com`.

### 1.3 Verify connectivity

Restart Claude Code and ask in the main chat: "Use the yunxiao tool to list my projects". You should get back a project list.

## 2. Zentao MCP

### 2.1 Prepare credentials

You need a Zentao account (developer permissions are enough) and your Zentao URL (e.g. `https://zentao.your-company.com`).

### 2.2 Add MCP config

Edit `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "zentao": {
      "command": "npx",
      "args": ["-y", "@tytt/zentao-mcp"],
      "env": {
        "ZENTAO_URL": "https://zentao.your-company.com",
        "ZENTAO_ACCOUNT": "<username>",
        "ZENTAO_PASSWORD": "<password>",
        "ZENTAO_SKIP_SSL": "false"
      }
    }
  }
}
```

> **Security note**: Do not commit `~/.claude/mcp.json` to git. If your project uses `.mcp.json` (project-level), add it to .gitignore.

### 2.3 Verify connectivity

Main chat: "Use the zentao tool to list the 5 most recent bugs."

## 3. Aliyun OpenAPI MCP (for ARMS)

### 3.1 Prepare AccessKey

1. Aliyun Console → AccessKey Management → Create AccessKey (use a RAM sub-user, not the master account)
2. Grant the RAM user `AliyunARMSReadOnlyAccess` (least privilege)
3. Record the AccessKey ID + AccessKey Secret

### 3.2 Add MCP config

```json
{
  "mcpServers": {
    "aliyun-api": {
      "command": "npx",
      "args": ["-y", "@alibabacloud/api-mcp-server"],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "<your AK ID>",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "<your AK Secret>",
        "ALIBABA_CLOUD_REGION": "cn-hangzhou"
      }
    }
  }
}
```

> The npm package name `@alibabacloud/api-mcp-server` follows the official repo `aliyun/alibabacloud-api-mcp-server` README. Before configuring, verify the latest npm package name and env variable names at https://github.com/aliyun/alibabacloud-api-mcp-server.

### 3.3 Verify connectivity

Main chat: "Use the aliyun-api tool to query the ARMS application list, region cn-hangzhou."

## 4. Codeup git remote setup

Before dev can submit MRs, the project's local repo must be bound to a Codeup remote:

```bash
cd <your project root>
git remote add origin https://codeup.aliyun.com/<org>/<repo>.git
# Or SSH: git remote add origin git@codeup.aliyun.com:<org>/<repo>.git
git push --dry-run  # verify credentials
```

For HTTPS, you need to generate Git credentials in Yunxiao Personal Settings.

## 5. Integration Self-Check

CCteam-creator SKILL.md Step 1.2.2 validates each item. If you want to confirm manually before setup, run:

```bash
# 1. Confirm ~/.claude/mcp.json exists and contains the three MCPs above
cat ~/.claude/mcp.json | python3 -m json.tool

# 2. Confirm the project's git remote is configured
git -C <project-dir> remote -v | grep codeup

# 3. Have Claude Code list tools to confirm all three MCPs loaded
# In main chat say: "List the currently available MCP tools"
```

## FAQ

**Q: I only want to try one or two of the integrations. Do I need all three?**
A: No. Only Zentao integration → install zentao MCP; only Codeup MR → install yunxiao MCP; ARMS scan → install Aliyun OpenAPI MCP. SKILL.md Step 1.2.1 validates on demand.

**Q: zentao MCP is third-party-maintained — is it safe?**
A: It uses your Zentao account credentials. Data flow: your local npx process → your Zentao server (LAN/intranet). Stays local. Recommendations:
- Use a dedicated low-privilege Zentao account
- Never commit credentials to git
- Rotate periodically

**Q: Does ARMS scanning consume a lot of API calls?**
A: bug-triage calls 1-3 APIs per scan (list error events + possibly trace details). Once a day puts monthly calls in the ~100 range — well below rate limits.
