from mcp.server.fastmcp import FastMCP
from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time
import urllib.parse
import json

mcp = FastMCP("1688_Scraper_MCP")

_browser_instance = None

def get_browser() -> ChromiumPage:
    global _browser_instance
    if _browser_instance is not None:
        try:
            _browser_instance.title
            return _browser_instance
        except:
            _browser_instance = None

    co = ChromiumOptions()
    user_data_path = os.path.join(os.path.dirname(__file__), 'drission_user_data')
    co.set_user_data_path(user_data_path)
    co.headless(False)
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-infobars')
    _browser_instance = ChromiumPage(co)
    return _browser_instance

def check_security_block(page) -> bool:
    if "login.1688.com" in page.url or "login.taobao.com" in page.url or "punish" in page.url or "验证码拦截" in page.title or \
       page.ele('x://*[contains(text(), "滑块") or contains(text(), "验证码") or contains(text(), "安全验证")]', timeout=2):
        return True
    return False

@mcp.tool()
def update_auth_cookie(url: str = "https://login.1688.com/") -> str:
    page = get_browser()
    page.get(url)
    time.sleep(60)
    return "已预留60秒窗口期用于手动过风控。当前状态已保存在本地，请重试工具。"

@mcp.tool()
def search_1688_products(keyword: str, page_num: int = 1, location_filter: str = "", only_factory: bool = False, max_results: int = 5) -> str:
    """
    智能搜货。所有过滤工作都在 Python 本地完成以节省 Token。
    参数:
        keyword: 关键词
        page_num: 页码
        location_filter: 可选，指定发货地（如"广东"、"义乌"），Python 会在本地丢弃不符合的数据。
        only_factory: 可选，如果为 True，Python 本地只保留带有"生产厂家"或"牛头标"的商品。
        max_results: 返回给大模型的最大结果数，默认只返回前 5 个最精准的，防 Token 溢出。
    """
    page = get_browser()
    encoded_kw = urllib.parse.quote(keyword.encode('gbk'))
    page.get(f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_kw}&beginPage={page_num}")
    page.wait.load_start()
    time.sleep(3)
    
    if check_security_block(page):
        return json.dumps({"error": "ERROR_AUTH_REQUIRED"})
    
    page.scroll.to_bottom()
    time.sleep(2)
    
    results = []
    try:
        offer_list = page.eles('.sm-offer-item') or page.eles('.offer-list-row-offer') or page.eles('x://div[contains(@class, "offer-card")]')
        
        for offer in offer_list:
            if len(results) >= max_results:
                break
                
            item_data = {}
            # 基础提取
            loc_ele = offer.ele('.location', timeout=0.5) or offer.ele('.city', timeout=0.5)
            location_text = loc_ele.text if loc_ele else ""
            
            # Python端：发货地过滤
            if location_filter and location_filter not in location_text:
                continue
                
            tags_eles = offer.eles('.icon-label', timeout=0.5) or offer.eles('.tag', timeout=0.5)
            tags_text = [t.text for t in tags_eles if t.text]
            
            # Python端：工厂过滤
            if only_factory and not any(kw in str(tags_text) for kw in ["厂", "牛头"]):
                continue

            title_ele = offer.ele('.offer-title', timeout=0.5) or offer.ele('.title', timeout=0.5)
            if title_ele: item_data['title'] = title_ele.text
            if title_ele: item_data['url'] = title_ele.attr('href')
            
            price_ele = offer.ele('.price', timeout=0.5)
            if price_ele: item_data['price'] = price_ele.text.replace('\n', '')
            
            sales_ele = offer.ele('.sales', timeout=0.5) or offer.ele('.trade', timeout=0.5)
            if sales_ele: item_data['sales'] = sales_ele.text
            
            comp_ele = offer.ele('.company-name', timeout=0.5)
            if comp_ele: item_data['company'] = comp_ele.text
            
            item_data['tags'] = tags_text
            item_data['location'] = location_text
            results.append(item_data)
            
        return json.dumps({"count": len(results), "items": results}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"解析失败: {str(e)}"})

@mcp.tool()
def get_product_detail_and_price(url: str) -> str:
    """获取商品真实价格与物流，已在 Python 端剔除无用冗余属性，极省 Token。"""
    page = get_browser()
    page.get(url)
    page.wait.load_start()
    time.sleep(3)
    
    if check_security_block(page):
        return "ERROR_AUTH_REQUIRED"
    
    result = {"title": "", "tiers": [], "logistics": "", "core_attrs": {}}
    try:
        title_ele = page.ele('.title-text', timeout=1) or page.ele('.title', timeout=1)
        if title_ele: result['title'] = title_ele.text
            
        price_blocks = page.eles('.price-item') or page.eles('x://div[contains(@class, "ladder-price")]//div[contains(@class, "item")]')
        for block in price_blocks:
            b_ele = block.ele('.price-title', timeout=0.5) or block.ele('.unit', timeout=0.5)
            p_ele = block.ele('.price-value', timeout=0.5) or block.ele('.value', timeout=0.5)
            if b_ele and p_ele:
                result['tiers'].append(f"{b_ele.text}: {p_ele.text}")
                
        log_ele = page.ele('x://*[contains(text(), "快递")]/..', timeout=0.5) or page.ele('.express-info', timeout=0.5)
        if log_ele: result['logistics'] = log_ele.text.replace('\n', ' ')
            
        # 仅提取高价值属性，丢弃几十个长尾属性
        core_keys = ["材质", "风格", "产地", "适用", "重量", "尺寸"]
        attr_els = page.eles('.offer-attr-item')
        for el in attr_els[:10]: # 最多看前10个属性防Token爆炸
            k = el.ele('.name', timeout=0.5)
            v = el.ele('.value', timeout=0.5)
            if k and v and any(ck in k.text for ck in core_keys):
                result['core_attrs'][k.text.strip()] = v.text.strip()
                
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
         return f"获取详情失败: {str(e)}"

@mcp.tool()
def get_product_reviews(url: str, max_meaningful_count: int = 20) -> str:
    """
    智能评价拉取。Python 端自动过滤“默认好评”及短字数水军评价。
    只向大模型返回有真实反馈的高质量长评价，极大节省 Token 且提高总结质量。
    参数:
        max_meaningful_count: 返回的最多的【有效】评价数量，默认 20 条（精华）。
    """
    page = get_browser()
    page.get(url)
    page.wait.load_start()
    time.sleep(3)

    if check_security_block(page):
        return "ERROR_AUTH_REQUIRED"

    valid_reviews = []
    junk_words = ["默认好评", "此用户没有填写评价", "系统默认", "还不错", "挺好的", "满意"]
    
    try:
        review_tab = page.ele('x://*[contains(@class, "tab") and (contains(text(), "评价") or contains(text(), "评论"))]', timeout=2)
        if review_tab:
            review_tab.click()
            time.sleep(2)

        pages_scraped = 0
        while len(valid_reviews) < max_meaningful_count and pages_scraped < 10: # 最多翻10页防死循环封号
            items = page.eles('.review-item') or page.eles('x://*[contains(@class, "remark-item")]')
            if not items: break

            for item in items:
                if len(valid_reviews) >= max_meaningful_count: break
                
                content_ele = item.ele('.review-content', timeout=0.5)
                text = content_ele.text.strip() if content_ele else ""
                
                # --- Python 端的硬核洗词 (NLP Pre-processing) ---
                if len(text) < 5: 
                    continue # 太短的废话直接丢弃
                if any(jw in text for jw in junk_words) and len(text) < 15:
                    continue # 包含常见水军词且不够长的丢弃

                sku_ele = item.ele('.review-sku', timeout=0.5)
                valid_reviews.append({
                    "content": text[:150], # 截断超长废话，最多150字
                    "sku": sku_ele.text if sku_ele else ""
                })

            pages_scraped += 1
            next_btn = page.ele('x://*[contains(@class, "next") and not(contains(@class, "disabled"))]', timeout=0.5)
            if next_btn and next_btn.is_clickable():
                next_btn.click()
                time.sleep(1.5)
            else:
                break

        return json.dumps({
            "extracted_valuable_reviews": len(valid_reviews),
            "reviews": valid_reviews
        }, ensure_ascii=False)

    except Exception as e:
        return f"获取评价失败: {str(e)}"

@mcp.tool()
def analyze_supplier_reliability(url: str) -> str:
    """提取核心 BSR 指标。已进行字段精简。"""
    page = get_browser()
    page.get(url)
    time.sleep(3)
    if check_security_block(page): return "ERROR_AUTH_REQUIRED"
         
    sd = {"company": "", "type": "普通", "metrics": {}}
    try:
        sd['company'] = (page.ele('.company-name') or page.ele('.shop-name')).text
        
        tags = [t.text or t.attr('title') for t in page.eles('x://*[contains(@class, "tag") or contains(@title, "超级工厂")]')]
        if any("超级工厂" in str(t) for t in tags): sd['type'] = "超级工厂"
                
        for box in page.eles('.score-item'):
            k = box.ele('.title')
            v = box.ele('.score')
            if k and v: sd['metrics'][k.text] = v.text
            
        rep = page.ele('x://*[contains(text(), "回头率")]/../*[contains(@class, "value")]')
        if rep: sd['metrics']['回头率'] = rep.text
             
        return json.dumps(sd, ensure_ascii=False)
    except Exception as e:
        return "背调失败"

if __name__ == "__main__":
    mcp.run()