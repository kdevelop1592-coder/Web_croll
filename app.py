from flask import Flask, request, jsonify, render_template, send_file
import os
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import urllib.parse as parse
import re

app = Flask(__name__)

def crawl_danawa(keyword, max_items=10):
    encoded_keyword = parse.quote(keyword)
    url = f"https://search.danawa.com/dsearch.php?k1={encoded_keyword}&module=goods&act=dispMain&sort=priceASC"
    
    try:
        response = requests.get(url, impersonate="chrome120", headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://danawa.com/'
        })
        
        if response.status_code != 200:
            return {"error": f"Failed to fetch page. Status code {response.status_code}"}
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        items = soup.select('li.prod_item')
        if not items:
            return {"error": "상품 리스트를 찾을 수 없거나 결과가 없습니다."}
            
        results = []
        for item in items:
            if len(results) >= max_items:
                break
                
            try:
                title_el = item.select_one('p.prod_name a')
                if not title_el: continue
                name = title_el.text.strip()
                if not name: continue
                
                link = title_el.get('href', '')
                if title_el.has_attr('onclick') and "dnbItemInfo" in title_el['onclick']:
                    match = re.search(r"dnbItemInfo\('([0-9]+)'", title_el['onclick'])
                    if match:
                        pcode = match.group(1)
                        link = f"https://prod.danawa.com/info/?pcode={pcode}"
                
                price_el = item.select_one('p.price_sect a strong, p.price_sect strong')
                if not price_el: continue
                price_text = price_el.text.replace(',', '').replace('원', '').strip()
                price = int(price_text) if price_text.isdigit() else 0
                if price <= 0: continue
                
                shop = "N/A"
                mall_el = item.select_one('.mall_name')
                if mall_el:
                    if mall_el.find('img'):
                        shop = mall_el.find('img').get('alt', '알수없음')
                    else:
                        shop = mall_el.text.strip()
                else:
                    shop = "다나와 가격비교"
                    
                results.append({
                    "상품명": name,
                    "가격": price,
                    "판매처": shop,
                    "링크": link
                })
            except Exception as e:
                continue
                
        if results:
            df = pd.DataFrame(results)
            csv_name = f"danawa_search_{keyword}_top{len(results)}.csv"
            df.to_csv(csv_name, index=False, encoding='utf-8-sig')
            return {"success": True, "data": results, "filename": csv_name}
        else:
            return {"error": "유효한 상품 데이터를 찾지 못했습니다."}
            
    except Exception as e:
        return {"error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    keyword = data.get('keyword', '').strip()
    if not keyword:
        return jsonify({"error": "검색어를 입력해주세요."}), 400
        
    result = crawl_danawa(keyword)
    if "error" in result:
        return jsonify({"error": result["error"]}), 500
        
    return jsonify(result)

@app.route('/api/download/<filename>')
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
