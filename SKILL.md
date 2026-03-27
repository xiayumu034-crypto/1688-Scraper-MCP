# Skill: 1688 Scraper (1688mcp)

This skill allows the agent to interact with 1688.com to extract product information, pricing, and reviews. It uses a headed browser to bypass anti-scraping measures.

## Triggers

- Any mention of "1688", "alibaba.cn", "1688.com".
- Requests to "get product info from 1688".
- Requests to "scrape 1688".
- Requests to "analyze 1688 products".
- Pasting a 1688.com URL.

## Guidelines

1. **Prioritize 1688mcp**: Whenever a 1688-related task is requested, you **MUST** use the tools provided by the `1688_mcp` server instead of generic browser tools.
2. **Handle Auth Gracefully**: If a tool returns `ERROR_AUTH_REQUIRED`, immediately call `update_auth_cookie` and inform the user that a browser window has opened for them to solve a captcha or log in. Wait for them to confirm before retrying.
3. **Session Persistence**: The MCP server handles sessions via `drission_user_data`. Do not worry about cookies unless auth is explicitly required.
4. **Data Extraction**: Use `get_1688_product_base_info` for general details and `get_1688_product_reviews` for buyer feedback.

## Tools (via MCP)

- `get_1688_product_base_info(url)`: Get title, price, and attributes.
- `get_1688_product_reviews(url)`: Get latest reviews.
- `update_auth_cookie(url)`: Manual intervention for login/captcha.
- `analyze_product_competitiveness(url)`: Comprehensive analysis.
