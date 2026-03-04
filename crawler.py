import argparse
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import urllib.parse as parse
import re

def crawl_danawa(keyword, max_items=10):
    """
    다나와 통합검색 크롤러
    """
    print("Danawa Search Crawler (Lowest Price Sort)")
    
    encoded_keyword = parse.quote(keyword)
    
    # 낮은 가격순 정렬 파라미터 (sort=priceASC)
    url = f"https://search.danawa.com/dsearch.php?k1={encoded_keyword}&module=goods&act=dispMain&sort=priceASC"
    print(f"Loading URL: {url}")
    
    try:
        # curl_cffi를 사용하여 브라우저 핑거프린트 우회 (다나와도 WAF가 있을 수 있으므로)
        response = requests.get(url, impersonate="chrome120", headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://danawa.com/'
        })
        
        if response.status_code != 200:
            print(f"ERROR: Failed to fetch page. Status code {response.status_code}")
            return []
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 상품 리스트는 عادة li.prod_item 클래스 안에 있습니다.
        items = soup.select('li.prod_item')
        if not items:
            print("상품 리스트를 찾을 수 없거나 결과가 없습니다.")
            return []
            
        results = []
        print(f"\n데이터 추출 중... (목표: {max_items}개)")
        
        for item in items:
            if len(results) >= max_items:
                break
                
            try:
                # 상품명
                title_el = item.select_one('p.prod_name a')
                if not title_el: continue
                name = title_el.text.strip()
                if not name: continue
                
                # 링크 (onclick 자바스크립트에 있는 pcode 추출 혹은 href 사용)
                link = title_el.get('href', '')
                if title_el.has_attr('onclick') and "dnbItemInfo" in title_el['onclick']:
                    match = re.search(r"dnbItemInfo\('([0-9]+)'", title_el['onclick'])
                    if match:
                        pcode = match.group(1)
                        link = f"https://prod.danawa.com/info/?pcode={pcode}"
                
                # 가격
                price_el = item.select_one('p.price_sect a strong, p.price_sect strong')
                if not price_el: continue
                price_text = price_el.text.replace(',', '').replace('원', '').strip()
                price = int(price_text) if price_text.isdigit() else 0
                if price <= 0: continue
                
                # 판매처
                shop = "N/A"
                mall_el = item.select_one('.mall_name')
                if mall_el:
                    if mall_el.find('img'):
                        shop = mall_el.find('img').get('alt', '알수없음')
                    else:
                        shop = mall_el.text.strip()
                else:
                    shop = "다나와 가격비교"  # mall_name이 없고 가격비교 텍스트만 있는 경우
                    
                results.append({
                    "상품명": name,
                    "가격": price,
                    "판매처": shop,
                    "링크": link
                })
                print(f"[{len(results)}] {name[:30]}... | {price:,}원 | {shop}")
                
            except Exception as e:
                # 개별 아이템 파싱 에러는 무시하고 다음으로 넘어감
                continue
                
        if results:
            df = pd.DataFrame(results)
            csv_name = f"danawa_search_{keyword}_top{len(results)}.csv"
            df.to_csv(csv_name, index=False, encoding='utf-8-sig')
            print(f"\n✅ 성공! {len(results)}개 상품 리스트가 {csv_name} 파일로 저장되었습니다.")
            
        return results
        
    except Exception as e:
        print(f"Critical error: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Danawa Crawler')
    parser.add_argument('--keyword', type=str, default='기계식 키보드', help='Search keyword')
    args = parser.parse_args()
    
    crawl_danawa(args.keyword)
