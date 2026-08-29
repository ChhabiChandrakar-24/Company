from urllib.parse import urlparse

def analyze_eeat(page_data, website, all_crawled_urls):
    score = 100
    issues = []
    
    # HTTPS Check
    url = page_data.get('url', '')
    if url and not url.startswith('https://'):
        score -= 30
        issues.append({'title': 'Insecure Protocol (HTTP)', 'description': 'The page is not using HTTPS. Security is a baseline requirement for Trust.', 'severity': 'critical', 'category': 'eeat'})
        
    # Check for About/Contact/Privacy links in the site (using all crawled urls as proxy or internal links)
    has_about = any('about' in u.lower() for u in all_crawled_urls)
    has_contact = any('contact' in u.lower() for u in all_crawled_urls)
    has_privacy = any('privacy' in u.lower() or 'terms' in u.lower() for u in all_crawled_urls)
    
    if not has_about:
        score -= 10
        issues.append({'title': 'Missing About Page', 'description': 'No "About" page detected. Transparency about the organization builds Trust.', 'severity': 'high', 'category': 'eeat'})
        
    if not has_contact:
        score -= 10
        issues.append({'title': 'Missing Contact Page', 'description': 'No "Contact" page detected. Easy access to contact info is essential for Trust.', 'severity': 'high', 'category': 'eeat'})
        
    if not has_privacy:
        score -= 10
        issues.append({'title': 'Missing Privacy/Terms Page', 'description': 'No Privacy Policy or Terms of Service detected.', 'severity': 'high', 'category': 'eeat'})
        
    return max(0, score), issues
