from mcp.server.fastmcp import FastMCP
from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time
import urllib.parse
import json

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

def check_security_block(page) -> bool:
    """检查页面是否被风控拦截"""
    if "login.1688.com" in page.url or "login.taobao.com" in page.url or "punish" in page.url or "验证码拦截" in page.title or \
       page.ele('x://*[contains(text(), "滑块") or contains(text(), "验证码") or contains(text(), "安全验证")]', timeout=2):
        return True
    return False

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
    
    return "已给用户预留了60秒窗口期用于手动登录和消除验证码。当前的 Cookie 和状态已保存在本地，请重新尝试调用抓取工具获取数据。"

@mcp.tool()
def search_1688_products(keyword: str, page_num: int = 1) -> str:
    """
    核心功能 1：智能搜货与源头工厂发现。
    搜索 1688 商品，返回带商业标签的数据列表（包括商品标题、价格、成交额、店铺名称、牛头标、发货地、店铺年限等）。
    AI 可基于返回的原始 JSON 数据，帮用户过滤出真正的“源头工厂”、“广东货源”等。
    
    参数:
        keyword: 搜索关键词（如 "挂脖小风扇"）
        page_num: 翻页页码，默认为 1
    """
    page = get_browser()
    # 拼接 1688 搜索 URL
    encoded_kw = urllib.parse.quote(keyword.encode('gbk'))
    url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_kw}&beginPage={page_num}"
    
    page.get(url)
    page.wait.load_start()
    time.sleep(3) # 等待列表渲染
    
    if check_security_block(page):
        return json.dumps({"error": "ERROR_AUTH_REQUIRED", "message": "触发了安全验证或需要登录。请调用 update_auth_cookie 工具。"})
    
    # 滚动页面到底部以加载图片和全部列表
    page.scroll.to_bottom()
    time.sleep(2)
    
    results = []
    
    try:
        # 1688 搜索列表的商品卡片
        offer_list = page.eles('.sm-offer-item') or page.eles('.offer-list-row-offer') or page.eles('x://div[contains(@class, "offer-card")]')
        
        for index, offer in enumerate(offer_list[:20]): # 取前20个避免过长
            item_data = {}
            # 标题与链接
            title_ele = offer.ele('.offer-title', timeout=1) or offer.ele('.title', timeout=1) or offer.ele('x://*[contains(@class, "title")]//a', timeout=1)
            if title_ele:
                item_data['title'] = title_ele.text
                item_data['url'] = title_ele.attr('href')
                
            # 价格
            price_ele = offer.ele('.price', timeout=1) or offer.ele('x://*[contains(@class, "price")]', timeout=1)
            if price_ele:
                item_data['price'] = price_ele.text.replace('\n', '')
                
            # 成交额 / 销量
            sales_ele = offer.ele('.sales', timeout=1) or offer.ele('.trade', timeout=1) or offer.ele('x://*[contains(@class, "month-sold")]', timeout=1)
            if sales_ele:
                item_data['sales'] = sales_ele.text
                
            # 公司名称与年限
            company_ele = offer.ele('.company-name', timeout=1) or offer.ele('.company', timeout=1) or offer.ele('x://*[contains(@class, "company")]//a', timeout=1)
            if company_ele:
                item_data['company'] = company_ele.text
                
            year_ele = offer.ele('.cx-year', timeout=1) or offer.ele('.year', timeout=1) or offer.ele('x://*[contains(@class, "year")]', timeout=1)
            if year_ele:
                item_data['cx_year'] = year_ele.text # 诚信通年限
                
            # 标签（源头工厂、牛头标、超级工厂等）
            tags_eles = offer.eles('.icon-label', timeout=1) or offer.eles('.tag', timeout=1) or offer.eles('x://*[contains(@class, "tag") or contains(@class, "label")]')
            item_data['tags'] = [t.text for t in tags_eles if t.text]
            
            # 发货地
            location_ele = offer.ele('.location', timeout=1) or offer.ele('.city', timeout=1) or offer.ele('x://*[contains(@class, "location")]', timeout=1)
            if location_ele:
                item_data['location'] = location_ele.text
                
            results.append(item_data)
            
        return json.dumps({
            "keyword": keyword,
            "page": page_num,
            "count": len(results),
            "items": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": "PARSE_ERROR", "message": f"解析搜索结果失败: {str(e)}"})


@mcp.tool()
def get_product_detail_and_price(url: str) -> str:
    """
    核心功能 2：精准解析阶梯价格、起批量与物流发货信息。
    对于 B 端采购或 C 端找平替，精准算价（起批量 + 阶梯单价 + 快递费）是刚需。
    
    参数:
        url (str): 1688商品详情页链接。
    """
    page = get_browser()
    page.get(url)
    page.wait.load_start()
    time.sleep(3)
    
    if check_security_block(page):
        return "ERROR_AUTH_REQUIRED: 触发了安全验证或需要登录。请调用 update_auth_cookie 工具。"
    
    result_data = {
        "title": "",
        "price_tiers": [],
        "logistics": "",
        "attributes": {}
    }
    
    try:
        # 获取标题
        title_ele = page.ele('.title-text', timeout=2) or page.ele('.title', timeout=2) or page.ele('h1', timeout=2)
        if title_ele:
            result_data['title'] = title_ele.text
            
        # 阶梯价格解析 (重点)
        price_blocks = page.eles('.price-item') or page.eles('x://div[contains(@class, "price-layout")]//div[contains(@class, "price-item")]')
        if not price_blocks: # 尝试备用选择器
             price_blocks = page.eles('x://div[contains(@class, "ladder-price")]//div[contains(@class, "item")]')
             
        for block in price_blocks:
            # 起批量
            batch_ele = block.ele('.price-title', timeout=1) or block.ele('.unit', timeout=1) or block.ele('x://*[contains(@class, "amount")]', timeout=1)
            # 对应单价
            price_val_ele = block.ele('.price-value', timeout=1) or block.ele('.value', timeout=1) or block.ele('x://*[contains(@class, "price")]', timeout=1)
            
            if batch_ele and price_val_ele:
                result_data['price_tiers'].append({
                    "batch": batch_ele.text,
                    "price": price_val_ele.text
                })
                
        if not result_data['price_tiers']:
            # 可能是单价商品
            single_price = page.ele('.price-text', timeout=1) or page.ele('.price', timeout=1)
            if single_price:
                result_data['price_tiers'].append({"price": single_price.text, "batch": "通用价格"})
                
        # 快递/物流信息提取
        logistics_ele = page.ele('x://*[contains(text(), "快递")]/..', timeout=1) or page.ele('.express-info', timeout=1) or page.ele('.logistics-info', timeout=1)
        if logistics_ele:
            result_data['logistics'] = logistics_ele.text.replace('\n', ' ')
            
        # 属性提取
        attr_elements = page.eles('.offer-attr-item') or page.eles('x://div[contains(@class, "attribute-item")]')
        for el in attr_elements:
            name_ele = el.ele('.name', timeout=0.5) or el.ele('x://*[contains(@class, "name") or contains(@class, "label")]', timeout=0.5)
            val_ele = el.ele('.value', timeout=0.5) or el.ele('x://*[contains(@class, "value")]', timeout=0.5)
            if name_ele and val_ele:
                result_data['attributes'][name_ele.text.strip()] = val_ele.text.strip()
                
        return json.dumps(result_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
         return f"获取详情失败: {str(e)}"

@mcp.tool()
def analyze_supplier_reliability(url: str) -> str:
    """
    核心功能 3：供应商深度背调（防坑利器）。
    抓取页面上的工厂/店铺档案数据，包括：回头率、发货速度、诚信通年限、退换货率、是否牛头标超级工厂等。
    大模型可依此判断这是真实源头工厂还是贸易倒爷，适合长期进货还是单次拿样。
    
    参数:
        url (str): 1688商品详情页或工厂首页链接。
    """
    page = get_browser()
    page.get(url)
    page.wait.load_start()
    time.sleep(3)
    
    if check_security_block(page):
         return "ERROR_AUTH_REQUIRED: 触发了安全验证或需要登录。"
         
    supplier_data = {
        "company_name": "",
        "factory_type": "未识别", # 超级工厂、实力商家、普通企业等
        "years": "", # 诚信通年限
        "metrics": {}, # 发货速度、响应率、回头率等指标
        "certifications": [] # 资质认证
    }
    
    try:
        # 公司名
        company_ele = page.ele('.company-name', timeout=2) or page.ele('.shop-name', timeout=2) or page.ele('x://*[contains(@class, "company") and contains(@class, "name")]', timeout=2)
        if company_ele:
            supplier_data['company_name'] = company_ele.text
            
        # 年限
        year_ele = page.ele('.year-num', timeout=1) or page.ele('.cx-year', timeout=1) or page.ele('x://*[contains(@class, "year")]', timeout=1)
        if year_ele:
            supplier_data['years'] = year_ele.text
            
        # 店铺标签（超级工厂等）
        tag_eles = page.eles('.factory-tag', timeout=1) or page.eles('.shop-tag', timeout=1) or page.eles('x://*[contains(@class, "tag") or contains(@title, "超级工厂") or contains(@title, "实力商家")]')
        tags = [t.text or t.attr('title') for t in tag_eles if t.text or t.attr('title')]
        if tags:
            supplier_data['certifications'] = list(set(tags))
            if any("超级工厂" in str(t) for t in tags):
                supplier_data['factory_type'] = "牛头标超级工厂"
            elif any("实力商家" in str(t) for t in tags):
                supplier_data['factory_type'] = "实力商家"
                
        # 核心履约指标 (BSR)
        # 1688 右侧边栏通常包含：货描相符、响应速度、发货速度、回头率
        metric_boxes = page.eles('.score-item') or page.eles('x://*[contains(@class, "indicator-item") or contains(@class, "dsr-item")]')
        for box in metric_boxes:
            title = box.ele('.title', timeout=0.5) or box.ele('x://*[contains(@class, "name")]', timeout=0.5)
            score = box.ele('.score', timeout=0.5) or box.ele('x://*[contains(@class, "value")]', timeout=0.5)
            if title and score:
                supplier_data['metrics'][title.text.strip()] = score.text.strip()
                
        # 单独找回头率
        rep_rate = page.ele('x://*[contains(text(), "回头率")]/../*[contains(@class, "value") or contains(@class, "num")]', timeout=1)
        if rep_rate:
             supplier_data['metrics']['回头率'] = rep_rate.text
             
        return json.dumps(supplier_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"深度背调失败: {str(e)}"

if __name__ == "__main__":
    mcp.run()
