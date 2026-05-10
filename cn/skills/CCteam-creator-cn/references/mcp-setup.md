# MCP 配置指南

> 本文档面向**首次配置** CCteam-creator 阿里云集成的用户。一次性操作，配置完成后 skill 流程会自动校验。

## 必装 MCP 清单

| MCP | 用途 | 必须 vs 可选 |
|-----|------|-------------|
| `alibabacloud-devops-mcp-server` (云效) | dev 提 MR 到 Codeup | 启用 Codeup 集成时必须 |
| `zentao-mcp-server` (禅道) | bug-triage 拉禅道 Bug 单 | 启用禅道触发源时必须 |
| `mcp-server-aliyun-observability` (阿里云观测) | bug-triage 查 ARMS 错误事件 | 启用 ARMS 巡检时必须 |

## 1. 云效 (Yunxiao) MCP

### 1.1 获取 access token

1. 登录云效 → 个人设置 → 个人访问令牌
2. 创建 token，勾选权限: 代码管理（读+写）+ 项目管理（读+写）
3. 复制 token（只显示一次，妥善保存）

### 1.2 添加到 Claude Code MCP 配置

编辑 `~/.claude/mcp.json` 或项目级 `.mcp.json`，加入：

```json
{
  "mcpServers": {
    "yunxiao": {
      "command": "npx",
      "args": ["-y", "alibabacloud-devops-mcp-server"],
      "env": {
        "YUNXIAO_ACCESS_TOKEN": "<你的 token>",
        "YUNXIAO_API_BASE_URL": "https://openapi-rdc.aliyuncs.com"
      }
    }
  }
}
```

如果你用的是 Region 版云效（专属域名），把 `YUNXIAO_API_BASE_URL` 改成 `https://<your-org>.devops.aliyuncs.com`。

### 1.3 验证连通

重启 Claude Code，在主对话里说: "用 yunxiao 工具列出我的项目"。应能返回项目列表。

## 2. 禅道 (ZenTao) MCP

### 2.1 准备账号

需要禅道账号（开发者权限即可），知道你的禅道 URL（如 `https://zentao.your-company.com`）。

### 2.2 添加 MCP 配置

编辑 `~/.claude/mcp.json`：

```json
{
  "mcpServers": {
    "zentao": {
      "command": "npx",
      "args": ["-y", "zentao-mcp-server"],
      "env": {
        "ZENTAO_URL": "https://zentao.your-company.com",
        "ZENTAO_ACCOUNT": "<用户名>",
        "ZENTAO_PASSWORD": "<密码>",
        "ZENTAO_SKIP_SSL": "false"
      }
    }
  }
}
```

> **安全提醒**: 不要把 `~/.claude/mcp.json` 提交到 git。如果项目用 `.mcp.json`（项目级），加到 .gitignore。

### 2.3 验证连通

主对话: "用 zentao 工具列出最近的 5 个 bug"。

## 3. 阿里云观测 (Observability) MCP（用于 ARMS）

> **前置依赖**: 安装 [uv](https://github.com/astral-sh/uv)——此 MCP 是 Python 包，通过 `uvx` 运行：
> `curl -LsSf https://astral.sh/uv/install.sh | sh`
> 验证: `uvx --version`

### 3.1 准备 AccessKey

1. 阿里云控制台 → AccessKey 管理 → 创建 AccessKey（建议用 RAM 子用户，不要用主账号）
2. 给 RAM 用户授权 `AliyunARMSReadOnlyAccess`（最小权限）
3. 记录 AccessKey ID + AccessKey Secret

### 3.2 添加 MCP 配置

```json
{
  "mcpServers": {
    "aliyun-observability": {
      "command": "uvx",
      "args": ["mcp-server-aliyun-observability", "--transport", "stdio"],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "<你的 AK ID>",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "<你的 AK Secret>",
        "ALIBABA_CLOUD_REGION_ID": "cn-hangzhou"
      }
    }
  }
}
```

> **已验证可用**: PyPI 包 `mcp-server-aliyun-observability` v1.0.8+——覆盖 ARMS / SLS / 应用实时监控。最新版本见 https://pypi.org/project/mcp-server-aliyun-observability/。

### 3.3 验证连通

主对话: "用 aliyun-observability 工具查询 ARMS 应用列表，region cn-hangzhou"。

### 3.4 (可选) 前端 RUM 异常检测

> **何时需要**: 你的项目用了 ARMS RUM (Real User Monitoring) 监控前端 JS 错误 / Web Vitals / 页面性能。
> **与 3.1-3.3 的区别**: 3.1-3.3 装的 `mcp-server-aliyun-observability` 覆盖**后端** APM（应用监控）。前端 **RUM** 是独立产品线，下面的流程独立部署，按需启用。

**为什么不装 npm/pip 包**: ARMS RUM 走阿里云 OpenAPI Explorer 的"按需打包 MCP Service"模式——在 web 控制台勾选你需要的 API，平台直接返回 **Streamable HTTP Endpoint**，Claude Code 远程对接，本地不安装包。

**步骤**:

1. 登录 [阿里云 OpenAPI Explorer](https://api.aliyun.com)
2. 顶部菜单进 **MCP Server / MCP 服务管理**
3. 创建 MCP Service：
   - **产品**: 应用实时监控服务 ARMS（API 版本 `2019-08-08`）
   - **勾选 API（推荐）**:
     - `SearchRumExceptions` — 前端异常查询（JS Error）
     - `GetRumApps` — 列 RUM 应用，拿 appId
     - `SearchRumLogs` — 异常 Session 详情
     - `SearchRumPv` / `SearchRumStatTrend` — PV / 趋势（可选）
   - **鉴权**: 用现有 AccessKey；**先**去 RAM 控制台给该 AK 绑策略 `AliyunARMSReadOnlyAccess`
4. 创建完成后控制台返回 **JSON 配置块 + Streamable HTTP Endpoint**
5. 把控制台给的完整 JSON 块复制到 `~/.claude/mcp.json` 的 `mcpServers` 下（一般形如 `{"type": "streamable-http", "url": "<endpoint>"}`，但**以控制台实际返回的 JSON 为准**，schema 可能演进）
6. **重启 Claude Code**（新 MCP server 必须在会话启动时加载，热更新无效）
7. 验证：主对话说 "列出 arms-rum 工具"——应能看到 `mcp__arms-rum__SearchRumExceptions` 等工具

## 4. Codeup git remote 配置

dev 提 MR 之前，项目本地仓库必须已绑定 Codeup 远程：

```bash
cd <你的项目根目录>
git remote add origin https://codeup.aliyun.com/<org>/<repo>.git
# 或 SSH: git remote add origin git@codeup.aliyun.com:<org>/<repo>.git
git push --dry-run  # 验证凭证
```

如果用 HTTPS，需要在云效个人设置里生成 Git 凭证。

## 5. 集成自检脚本

CCteam-creator SKILL.md Step 1.2.2 会逐项校验。如果你想在 setup 之前手动确认，跑：

```bash
# 1. 确认 ~/.claude/mcp.json 存在并包含上述三项
cat ~/.claude/mcp.json | python3 -m json.tool

# 2. 确认项目目录 git remote 已配
git -C <project-dir> remote -v | grep codeup

# 3. 让 Claude Code 列工具，确认三个 MCP 都加载成功
# 在主对话说: "列出当前可用的 MCP 工具"
```

## 常见问题

**Q: 我只想试集成一两个工具，必须三个都装吗？**
A: 不必。只要禅道集成 → 装 zentao MCP；只要 Codeup 提 MR → 装云效 MCP；要 ARMS 后端 APM → 装阿里云观测 MCP；要 ARMS 前端 RUM → 走 3.4 的 OpenAPI Explorer 流程。SKILL.md Step 1.2.1 会按需校验。

**Q: zentao MCP 第三方维护，安全吗？**
A: 它需要禅道账号密码 → 数据流向: 你的本地 npx 进程 → 你的禅道服务器（局域网/内网）。不出本地。但建议:
- 用专门的低权限禅道账号
- 不把密码提交到 git
- 定期 rotate

**Q: `zentao-mcp-server` 启动后所有 API 调用都返回 302 跳登录页（但浏览器登录正常），怎么办？**
A: 这几乎都是**禅道服务器端 nginx PATH_INFO 配置缺失**，不是凭证问题。`zentao-mcp-server` 用 REST 风格 URL（如 `/api.php/v1/tokens`），依赖 nginx 把 `/v1/tokens` 拆成 `PATH_INFO` 传给 PHP。如果 nginx 没配，整个路径被当字符串扔回，禅道不识别 → 兜底重定向到登录页。

诊断：
```bash
curl -i -X POST https://<your-zentao>/api.php/v1/tokens
# 当前症状：HTTP/1.1 302 (Location 跳 /index.php?m=user&f=login&...)
# 修复后期望：HTTP/1.1 4xx + JSON 体
```

修复（给运维一行话，禅道后台不用动）：在禅道服务器 nginx 的 `location ~ \.php` 段加：
```nginx
fastcgi_split_path_info ^(.+\.php)(/.*)$;
fastcgi_param PATH_INFO $fastcgi_path_info;
```
重启 nginx 后再跑上面 curl 验证。

**Q: ARMS 巡检会不会消耗大量 API 调用？**
A: bug-triage 每次扫描调 1-3 次 API（list 错误事件 + 可能查 trace 详情）。一天一次的话，月度 API 调用在 100 次量级，不会触发限流。
