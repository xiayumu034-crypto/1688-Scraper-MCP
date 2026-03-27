# 1688 Scraper MCP 服务

[中文](#chinese) | [English](#english)

---

<a name="chinese"></a>

## 中文 (Chinese)

一个强健、智能且具备反爬绕过能力的 MCP (Model Context Protocol) 服务，专为 1688.com 交互设计。基于 `DrissionPage` 和 `FastMCP` 构建，它允许 Claude 等大语言模型无缝提取 1688 的商品元数据、价格和买家评价，并优雅地处理复杂的登录墙和滑块验证码。

### ✨ 核心特性

- **反爬虫绕过**：采用有头浏览器模式（通过 `DrissionPage`）而非易被检测的无头模式，大幅降低触发 1688 严格反爬机制的概率。
- **交互式身份验证**：当遇到滑块验证或登录墙时，MCP 会向大模型发送 `ERROR_AUTH_REQUIRED` 信号，触发 60 秒的交互窗口，供用户手动扫码或滑块。
- **Cookie 持久化**：将用户会话数据保存在本地 `drission_user_data/`，实现“一次登录，长期抓取”。
- **智能 DOM 解析**：动态适配 1688 复杂多变的 DOM 结构（包括 Ant Design 侧边抽屉、Shadow DOM 以及动态加载的分页），可靠提取标题、阶梯价、属性和分页评价。

### 📦 文件结构

```text
1688_mcp/
├── server.py              # MCP 服务入口及抓取逻辑
├── SKILL.md               # CoPaw 技能描述文件
├── requirements.txt       # Python 依赖
├── README.md              # 说明文档
├── .gitignore             # Git 忽略规则
└── drission_user_data/    # (自动生成) 本地浏览器会话及 Cookie 存储
```

### 🚀 安装与配置

#### CoPaw (一键接入)
如果你正在使用 **CoPaw**，只需对 AI 说“接入 1688mcp”或“帮我查一下 1688”。AI 会自动识别并配置该 MCP 服务。

AI 助手会自动完成以下配置：
1. 在 `agent.json` 中注册 MCP 客户端。
2. 在 `active_skills` 中激活 1688 抓取技能，确保后续所有 1688 相关请求都会强制优先使用此工具。

#### 通用 MCP 客户端 (如 Claude Desktop)
在你的 MCP 配置文件中添加如下内容：
```json
{
  "mcpServers": {
    "1688_Scraper_MCP": {
      "command": "D:/Docker/working/copaw/workspaces/default/1688_mcp/venv/Scripts/python.exe",
      "args": [
        "D:/Docker/working/copaw/workspaces/default/1688_mcp/server.py"
      ],
      "cwd": "D:/Docker/working/copaw/workspaces/default/1688_mcp"
    }
  }
}
```
*(注意：请根据实际路径替换 command 和 args 中的路径。)*

### 🛠️ 提供的工具

1. `get_1688_product_base_info(url: str)`：提取商品标题、阶梯价格和属性。
2. `get_1688_product_reviews(url: str)`：处理分页并从侧边抽屉提取前 20 条买家评价。
3. `update_auth_cookie(url: str)`：开启 60 秒窗口供人工处理验证码或登录。
4. `analyze_product_competitiveness(url: str)`：一键获取综合数据供大模型进行竞争力分析。

### ⚠️ 重要提示
- **请勿开启无头模式**：1688 的机器人检测会永久封锁标准无头请求。代码硬编码为 `co.headless(False)` 以确保稳定性。
- **编码问题**：服务强制 `sys.stdout` 使用 `utf-8` 编码，防止在 Windows 系统通过 stdio 交互时产生乱码。

### 📄 开源协议
MIT License

---

<a name="english"></a>

## English

A robust, intelligent, and anti-anti-scraping MCP (Model Context Protocol) server designed specifically for interacting with 1688.com. Built on top of `DrissionPage` and `FastMCP`, it allows Large Language Models (LLMs) like Claude to seamlessly extract product metadata, pricing, and buyer reviews from 1688 while elegantly handling complex login walls and slider captchas.

### ✨ Features

- **Anti-Scraping Bypass**: Uses a headed browser approach (via `DrissionPage`) rather than a detectable headless mode, massively reducing the chance of triggering 1688's strict anti-bot mechanisms.
- **Interactive Auth Resolution**: When a slider captcha or login wall is encountered, the MCP gracefully alerts the LLM (`ERROR_AUTH_REQUIRED`), which can then trigger a 60-second interactive window for the user to manually scan a QR code or solve the slider.
- **Cookie Persistence**: Stores user session data locally in `drission_user_data/`, meaning you only need to log in once for long-term uninterrupted scraping.
- **Smart DOM Parsing**: Dynamically adapts to 1688's varied and complex DOM structures (including Ant Design drawers, Shadow DOMs, and dynamically loaded pagination) to reliably extract titles, tiered prices, attributes, and paginated buyer reviews.

### 🚀 Installation & Setup

#### CoPaw (One-Click Setup)
If you are using **CoPaw**, simply ask the agent to "activate 1688mcp" or "help me with 1688". The AI will automatically configure itself to use this MCP server and prioritize it for all 1688-related tasks.

#### Generic MCP Client (e.g., Claude Desktop)
Add the following configuration to your MCP client's config file:
```json
{
  "mcpServers": {
    "1688_Scraper_MCP": {
      "command": "D:/Docker/working/copaw/workspaces/default/1688_mcp/venv/Scripts/python.exe",
      "args": [
        "D:/Docker/working/copaw/workspaces/default/1688_mcp/server.py"
      ],
      "cwd": "D:/Docker/working/copaw/workspaces/default/1688_mcp"
    }
  }
}
```
*(Note: Replace paths with your actual absolute paths.)*
