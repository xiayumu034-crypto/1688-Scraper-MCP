from mcp.server.fastmcp import FastMCP
from DrissionPage import ChromiumPage, ChromiumOptions
import os
import time
import urllib.parse
import json
import sys

# 强制设置输出编码为 UTF-8，防止 Windows 控制台乱码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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
    # 保持登录状态的数据目录
    user_data_path = os.path.join(os.path.dirname(__file__), 'drission_user_data')
    co.set_user_data_path(user_data_path)
    co.headless(False)
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-infobars')
    # 性能优化：禁用图片加载
    co.set_pref('profile.managed_default_content_settings.images', 2)
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
    智能搜货工具。在 Python 端完成产地和厂家过滤，只返回高质量结果，节省 80% Token。
    参数:
        keyword: 搜索词
        location_filter: 发货地过滤（如 "山东", "广东"）
        only_factory: 是否仅保留源头工厂/实力商家
        max_results: 返回给大模型的最大结果数（默认 5）
    """
    page = get_browser()
    encoded_kw = urllib.parse.quote(keyword.encode('gbk'))
    page.get(f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded_kw}&beginPage={page_num}")
    page.wait.load_start()
    time.sleep(5) # 等待渲染
    
    if check_security_block(page):
        return json.dumps({"error": "ERROR_AUTH_REQUIRED"})
    
    page.scroll.to_bottom()
    time.sleep(2)
    
    results = []
    try:
        # 支持 2026 版 1688 最新 UI 架构的选择器
        offer_list = page.eles('.search-offer-item') or \
                     page.eles('.sm-offer-item') or \
                     page.eles('.offer-list-row-offer') or \
                     page.eles('x://div[contains(@class, "offer-card")]')
        
        for offer in offer_list:
            if len(results) >= max_results:
                break
                
            item_data = {}
            text_content = offer.text
            
            # --- 过滤逻辑 (Python 本地执行) ---
            if location_filter and location_filter not in text_content:
                continue
            
            # 工厂标签库
            factory_keywords = ["厂", "工厂", "加工", "源头", "牛头", "生产"]
            if only_factory and not any(kw in text_content for kw in factory_keywords):
                continue

            # 提取详情
            title_ele = offer.ele('.offer-title-row') or offer.ele('.title') or offer.ele('.offer-title')
            if not title_ele: continue
            
            item_data['title'] = title_ele.text
            # 提取链接
            item_data['url'] = title_ele.attr('href') or \
                              title_ele.ele('tag:a').attr('href') or \
                              offer.ele('tag:a').attr('href')
            
            price_ele = offer.ele('.offer-price-row') or offer.ele('.price')
            if price_ele: item_data['price'] = price_ele.text.replace('\n', '')
            
            comp_ele = offer.ele('.offer-shop-row') or offer.ele('.company-name')
            if comp_ele: item_data['company'] = comp_ele.text
            
            results.append(item_data)
            
        return json.dumps({"count": len(results), "items": results}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"error": f"搜索解析失败: {str(e)}"})

@mcp.tool()
def get_product_detail_and_price(url: str) -> str:
    """获取商品真实阶梯价格与物流，自动剔除冗余属性。"""
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
            
        # 精简属性集
        core_keys = ["材质", "规格", "产地", "适用", "重量", "尺寸"]
        attr_els = page.eles('.offer-attr-item')
        for el in attr_els[:12]:
            k = el.ele('.name', timeout=0.5)
            v = el.ele('.value', timeout=0.5)
            if k and v and any(ck in k.text for ck in core_keys):
                result['core_attrs'][k.text.strip()] = v.text.strip()
                
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
         return f"获取详情失败: {str(e)}"

@mcp.tool()
def get_product_reviews(url: str, max_meaningful_count: int = 15) -> str:
    """
    深度评价扫描。自动进入“全部评价”界面，针对粉尘、结团、粘底等核心负面词进行嗅探。
    """
    page = get_browser()
    page.get(url)
    page.wait.load_start()
    time.sleep(5)

    if check_security_block(page):
        return "ERROR_AUTH_REQUIRED"

    # 尝试进入全部评价界面
    more_btn = page.ele('.evaluation-more') or page.ele('x://*[contains(text(), "全部评价")]')
    if more_btn:
        more_btn.click()
        time.sleep(3)

    valid_reviews = []
    # 核心痛点监测词
    pain_points = ["粉尘", "尘", "化粉", "碎", "散", "结团", "不结团", "粘底", "臭", "味道"]
    
    try:
        pages_scraped = 0
        while len(valid_reviews) < max_meaningful_count and pages_scraped < 3:
            items = page.eles('.review-content') or page.eles('.content-text') or page.eles('.comment-item')
            if not items: break

            for item in items:
                text = item.text.strip()
                if len(text) < 10: continue # 过滤短好评
                
                # 优先权重：包含痛点关键词的评价
                if any(k in text for k in pain_points):
                    valid_reviews.append(text[:200]) # 截断防爆屏
                elif len(text) > 40: # 或者是长的真实评价
                    valid_reviews.append(text[:200])

                if len(valid_reviews) >= max_meaningful_count: break

            pages_scraped += 1
            next_btn = page.ele('x://button[contains(text(), "下一页")]') or page.ele('.next-page')
            if next_btn and next_btn.is_enabled():
                next_btn.click()
                time.sleep(2)
            else:
                break

        return json.dumps({
            "total_extracted": len(valid_reviews),
            "reviews": valid_reviews
        }, ensure_ascii=False)

    except Exception as e:
        return f"获取评价失败: {str(e)}"

@mcp.tool()
def analyze_supplier_reliability(url: str) -> str:
    """供应商深度背调：回头率、牛头标、经营年限。"""
    page = get_browser()
    page.get(url)
    time.sleep(3)
    if check_security_block(page): return "ERROR_AUTH_REQUIRED"
         
    sd = {"company": "", "verified": False, "years": "N/A", "metrics": {}}
    try:
        body_text = page.ele('tag:body').text
        sd['company'] = (page.ele('.company-name') or page.ele('.shop-name')).text
        
        # 实力认证检测
        sd['verified'] = any(k in body_text for k in ["源头工厂", "实力商家", "超级工厂"])
        
        # 经营年限提取
        import re
        year_match = re.search(r'(\d+)年', body_text)
        if year_match: sd['years'] = year_match.group(0)
                
        # 回头率数据
        rep = page.ele('x://*[contains(text(), "回头率")]/../*[contains(@class, "value")]')
        if rep: sd['metrics']['回头率'] = rep.text
             
        return json.dumps(sd, ensure_ascii=False)
    except Exception as e:
        return f"背调失败: {str(e)}"

if __name__ == "__main__":
    mcp.run()
