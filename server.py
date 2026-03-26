from mcp.server.fastmcp import FastMCP
from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time

# 初始化 FastMCP 服务器
mcp = FastMCP("1688_Scraper_MCP")

_browser_instance = None

def get_browser() -> ChromiumPage:
    """
    初始化并获取配置好的 ChromiumPage 实例。
    主要配置：使用本地用户数据目录来持久化 Cookie，避免重复登录。
    保持有头模式，以便遇到验证码时人工介入。
    """
    global _browser_instance
    if _browser_instance is not None:
        try:
            # test if it's alive
            _browser_instance.title
            return _browser_instance
        except:
            _browser_instance = None

    co = ChromiumOptions()
    # 设置用户数据目录，持久化保存 Cookies / 登录状态
    user_data_path = os.path.join(os.path.dirname(__file__), 'drission_user_data')
    co.set_user_data_path(user_data_path)
    
    # 强制不使用无头模式（1688对无头检测极严，且需要弹出窗口供用户滑块验证）
    co.headless(False)
    
    # 绕过部分自动化检测特征
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-infobars')
    
    _browser_instance = ChromiumPage(co)
    return _browser_instance

@mcp.tool()
def update_auth_cookie(url: str = "https://login.1688.com/") -> str:
    """
    当你尝试抓取 1688 数据遇到权限问题（如：要求登录、频繁访问触发滑块验证码）时，调用此工具。
    工具会打开一个真实浏览器窗口，请提示用户在弹出的浏览器中手动完成登录或滑块验证。
    """
    page = get_browser()
    page.get(url)
    
    # 给用户预留 60 秒时间手动处理登录或验证码
    time.sleep(60)
    
    # 因为配置了 user_data_path，浏览器会自动保存成功验证后的 Cookie 到本地。
    return "已给用户预留了60秒窗口期用于手动登录和消除验证码。当前的 Cookie 和状态已保存在本地，请重新尝试调用抓取工具获取数据。"

@mcp.tool()
def get_1688_product_base_info(url: str) -> str:
    """
    获取 1688 商品的基础信息（标题、价格、属性等）。
    参数:
        url (str): 1688商品详情页链接。
    """
    page = get_browser()
    page.get(url)
    
    page.wait.load_start()
    time.sleep(2) # 给予一些动态加载时间
    
    # 检测是否被重定向到登录页或者出现滑块/验证码弹窗
    if "login.1688.com" in page.url or "login.taobao.com" in page.url or "punish" in page.url or "验证码拦截" in page.title or \
       page.ele('x://*[contains(text(), "滑块") or contains(text(), "验证码") or contains(text(), "安全验证")]', timeout=2):
        return "ERROR_AUTH_REQUIRED: 触发了安全验证或需要登录。请调用 update_auth_cookie 工具，并提示用户在弹出的浏览器中手动验证。"
    
    try:
        # 尝试提取标题
        page_title = page.title
        title = page_title.split(' - ')[0] if ' - ' in page_title else page_title
        if not title.strip() or title == "阿里1688首页":
            title_elements = page.eles('h1', timeout=2)
            if len(title_elements) > 1:
                title = title_elements[1].text
            elif title_elements:
                title = title_elements[0].text
            else:
                title_ele = page.ele('.title-text', timeout=2) or page.ele('.title', timeout=2)
                title = title_ele.text if title_ele else "未获取到标题"
        
        # 尝试提取价格
        price_elements = page.eles('.price-info') or page.eles('.price-text') or page.eles('.price')
        prices = [el.text.replace('\n', '') for el in price_elements if el.text.strip()]
        price_str = ", ".join(prices) if prices else "未获取到价格"
        
        # 尝试提取商品属性
        attributes = []
        attr_elements = page.eles('.ant-table-row') or page.eles('.offer-attr-item')
        for el in attr_elements:
            attributes.append(el.text.replace("\n", ": "))
            
        result = f"【商品基础信息】\n" \
                 f"标题: {title}\n" \
                 f"价格: {price_str}\n" \
                 f"属性:\n" + "\n".join(attributes)
                 
        return result
    except Exception as e:
        return f"获取商品基础信息解析失败: {str(e)}\n注意：可能是因为 1688 DOM 结构发生变化，或页面尚未完全加载。"

@mcp.tool()
def get_1688_product_reviews(url: str) -> str:
    """
    获取指定 1688 商品的买家评论数据。
    参数:
        url (str): 1688商品详情页链接。
    """
    page = get_browser()
    page.get(url)
    
    page.wait.load_start()
    time.sleep(3)
    
    if "login.1688.com" in page.url or "login.taobao.com" in page.url or "punish" in page.url or "验证码拦截" in page.title or \
       page.ele('x://*[contains(text(), "滑块") or contains(text(), "验证码") or contains(text(), "安全验证")]', timeout=2):
        return "ERROR_AUTH_REQUIRED: 触发了安全验证或需要登录。请调用 update_auth_cookie 工具，并提示用户在弹出的浏览器中手动验证。"
        
    try:
        # 寻找“评价”或“买家评价”相关的标签页并点击
        # 1688 逻辑：优先点击“查看全部评价”，如果没有再找常规Tab
        view_all_btn = page.ele('x://*[contains(text(), "查看全部评价")]', timeout=3)
        if view_all_btn:
            view_all_btn.click()
            time.sleep(3)
        else:
            review_tab = page.ele('x://*[contains(@class, "tab") and contains(text(), "评价")]', timeout=3) \
                      or page.ele('x://*[contains(text(), "买家评价")]', timeout=3) \
                      or page.ele('x://*[contains(text(), "商品评价")]', timeout=3) \
                      or page.ele('x://*[contains(text(), "评价(")]', timeout=3)
                      
            if review_tab:
                review_tab.click()
                time.sleep(3) # 等待评论Ajax加载
            else:
                return "未在页面上找到‘评价’标签，可能该商品无评价或 DOM 结构不匹配。"
            
        # 提取评论内容
        reviews = []
        page_num = 1
        
        while len(reviews) < 20:
            review_elements = page.eles('.content-text', timeout=2) or page.eles('.review-content', timeout=2) or page.eles('.remark-content', timeout=2) or page.eles('.comment-content', timeout=2) or page.eles('.eval-content', timeout=2)
            
            current_page_reviews = []
            for el in review_elements:
                t = el.text.strip()
                if t and t not in reviews:
                    reviews.append(t)
                    current_page_reviews.append(t)
                    
            if not current_page_reviews:
                break
                
            if len(reviews) >= 20:
                break
                
            # Click next page (handling antd pagination)
            next_btn = page.ele('.ant-pagination-next', timeout=2) \
                       or page.ele('x://button[contains(text(), "下一页") or contains(text(), "下一页")]', timeout=2) \
                       or page.ele('x://a[contains(text(), "下一页")]', timeout=2) \
                       or page.ele('.next-page', timeout=2) \
                       or page.ele('.btn-next', timeout=2)
                       
            if next_btn:
                btn_class = next_btn.attr("class") or ""
                if "ant-pagination-disabled" in btn_class or "disabled" in btn_class or next_btn.attr("aria-disabled") == "true":
                    break
                next_btn.click()
                page_num += 1
                time.sleep(3)
            else:
                break

        reviews = reviews[:20]
                
        if not reviews:
            # 尝试另一种通用匹配
            return "成功切换到评价页面，但未找到具体的评论文本。如果需要详细分析，可以尝试使用更精确的 CSS Selector。"
            
        return "【最新买家评价】\n- " + "\n- ".join(reviews)
    except Exception as e:
        return f"获取商品评价失败: {str(e)}"

@mcp.tool()
def analyze_product_competitiveness(url: str) -> str:
    """
    一键获取 1688 商品的基础信息和买家评价，供大模型进行综合数据分析。
    大模型可以基于返回的综合数据，输出【产品优缺点】、【价格竞争力】、【买家核心痛点】、【供应商可靠性】等分析。
    """
    base_info = get_1688_product_base_info(url)
    
    if "ERROR_AUTH_REQUIRED" in base_info:
        return base_info
        
    reviews = get_1688_product_reviews(url)
    
    return f"=== 商品基础数据 ===\n{base_info}\n\n=== 评价数据 ===\n{reviews}\n\n请根据上述数据，生成一份包含产品优缺点、价格竞争力、买家核心痛点、供应商可靠性的分析报告。"

if __name__ == "__main__":
    # 本地启动测试或直接运行 MCP
    # 默认通过 stdin/stdout 与 AI Client (如 Claude Desktop) 交互
    mcp.run()