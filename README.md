# 1688 Scraper MCP Server

A robust, intelligent, and anti-anti-scraping MCP (Model Context Protocol) server designed specifically for interacting with 1688.com. Built on top of `DrissionPage` and `FastMCP`, it allows Large Language Models (LLMs) like Claude to seamlessly extract product metadata, pricing, and buyer reviews from 1688 while elegantly handling complex login walls and slider captchas.

## ✨ Features

- **Anti-Scraping Bypass**: Uses a headed browser approach (via `DrissionPage`) rather than a detectable headless mode, massively reducing the chance of triggering 1688's strict anti-bot mechanisms.
- **Interactive Auth Resolution**: When a slider captcha or login wall is encountered, the MCP gracefully alerts the LLM (`ERROR_AUTH_REQUIRED`), which can then trigger a 60-second interactive window for the user to manually scan a QR code or solve the slider.
- **Cookie Persistence**: Stores user session data locally in `drission_user_data/`, meaning you only need to log in once for long-term uninterrupted scraping.
- **Smart DOM Parsing**: Dynamically adapts to 1688's varied and complex DOM structures (including Ant Design drawers, Shadow DOMs, and dynamically loaded pagination) to reliably extract titles, tiered prices, attributes, and paginated buyer reviews.

## 📦 File Structure

```text
1688_mcp/
├── server.py              # Main MCP server entry point and scraping logic
├── requirements.txt       # Python dependencies
├── README.md              # Documentation
├── .gitignore             # Git ignore rules
└── drission_user_data/    # (Auto-generated) Local browser session and cookie storage
```

## 🚀 Installation & Setup

1. **Prerequisites**: 
   - Python 3.10 or higher.
   - Google Chrome installed in its default location.

2. **Clone and Install Dependencies**:
   ```bash
   # It is recommended to use a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   
   pip install -r requirements.txt
   ```

3. **Configure MCP Client (e.g., Claude Desktop or CoPaw)**:
   Add the following configuration to your MCP client's config file (like `claude_desktop_config.json` or CoPaw's `config.json`):
   ```json
   {
     "mcpServers": {
       "1688_Scraper_MCP": {
         "command": "<YOUR_PATH>/1688_mcp/venv/Scripts/python.exe",
         "args": [
           "<YOUR_PATH>/1688_mcp/server.py"
         ]
       }
     }
   }
   ```
   *Note: Adjust the paths according to your actual project location.*

## 🛠️ Provided Tools

The server exposes the following tools to the LLM via the MCP protocol:

1. `get_1688_product_base_info(url: str)`
   - **Description**: Extracts the product title, tiered pricing, and key attributes.
   - **Returns**: Formatted text containing the base product data.

2. `get_1688_product_reviews(url: str)`
   - **Description**: Automatically locates the review tab/drawer, handles pagination, and extracts up to 20 recent buyer reviews.
   - **Returns**: A list of real buyer review texts.

3. `update_auth_cookie(url: str)`
   - **Description**: Triggered when `ERROR_AUTH_REQUIRED` is encountered. Pops up a visible browser window for 60 seconds, allowing the user to manually complete the captcha or scan the login QR code.

4. `analyze_product_competitiveness(url: str)`
   - **Description**: A macro-tool that bundles base info and reviews, returning a comprehensive dataset designed for the LLM to analyze product pros/cons, pricing competitiveness, and supplier reliability.

## ⚠️ Important Notes
- **Do not run this server in standard Headless mode**. 1688's bot detection will permanently block standard headless requests. The script is hardcoded to `co.headless(False)` for stability.
- **Encoding**: The server forces `utf-8` encoding on `sys.stdout` to prevent character garbling when interacting via stdio on Windows machines.

## 📄 License
MIT License
