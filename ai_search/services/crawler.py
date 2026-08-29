import requests
from bs4 import BeautifulSoup
import re
import socket
from urllib.parse import urlparse, urljoin

def is_safe_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    try:
        ip = socket.gethostbyname(parsed.hostname)
        if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.'):
            return False
        parts = ip.split('.')
        if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
            return False
    except:
        return False
    return True

def extract_page_data(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    data = {}
    data['title'] = soup.title.string.strip() if soup.title and soup.title.string else None
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    data['meta_description'] = meta_desc['content'].strip() if meta_desc and meta_desc.has_attr('content') else None
    
    canonical = soup.find('link', rel='canonical')
    data['canonical_url'] = canonical['href'].strip() if canonical and canonical.has_attr('href') else None
    
    robots = soup.find('meta', attrs={'name': 'robots'})
    data['robots_meta'] = robots['content'].strip() if robots and robots.has_attr('content') else None
    
    html_tag = soup.find('html')
    data['language'] = html_tag.get('lang') if html_tag else None
    
    data['h1_headings'] = [h.get_text(strip=True) for h in soup.find_all('h1')]
    data['h2_headings'] = [h.get_text(strip=True) for h in soup.find_all('h2')]
    data['h3_headings'] = [h.get_text(strip=True) for h in soup.find_all('h3')]
    
    text_content = soup.get_text(separator=' ')
    words = re.findall(r'\b\w+\b', text_content)
    data['word_count'] = len(words)
    
    images = soup.find_all('img')
    data['images_count'] = len(images)
    data['images_with_alt'] = sum(1 for img in images if img.get('alt') and img.get('alt').strip())
    
    internal_links = 0
    external_links = 0
    parsed_base = urlparse(url)
    base_domain = parsed_base.netloc
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('#') or href.startswith('javascript:'):
            continue
        link_parsed = urlparse(href)
        if not link_parsed.netloc or link_parsed.netloc == base_domain:
            internal_links += 1
        else:
            external_links += 1
            
    data['internal_links_count'] = internal_links
    data['external_links_count'] = external_links
    
    ld_json = soup.find('script', type='application/ld+json')
    data['has_structured_data'] = bool(ld_json)
    
    return data

def crawl_url(url, timeout=10):
    if not is_safe_url(url):
        return {'status_code': None, 'error': 'Unsafe or invalid URL'}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AISearchOptimizationEngine/1.0;)'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        data = extract_page_data(response.text, response.url)
        data['status_code'] = response.status_code
        data['raw_content'] = response.text
        data['final_url'] = response.url
        return data
    except requests.RequestException as e:
        return {'status_code': None, 'error': str(e)}

def crawl_website(base_url, max_pages=10):
    visited = set()
    to_visit = [base_url]
    results = []
    
    base_domain = urlparse(base_url).netloc
    
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        
        visited.add(url)
        data = crawl_url(url)
        data['url'] = url
        results.append(data)
        
        if data.get('status_code') == 200 and data.get('raw_content'):
            soup = BeautifulSoup(data['raw_content'], 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                    continue
                next_url = urljoin(url, href)
                next_url_parsed = urlparse(next_url)
                next_url = next_url_parsed._replace(fragment='').geturl()
                
                if next_url_parsed.netloc == base_domain and next_url not in visited and next_url not in to_visit:
                    to_visit.append(next_url)
                    
    return results
