def analyze_geo(page_data, website):
    score = 100
    issues = []
    
    # Organization identity
    title = page_data.get('title', '') or ''
    org_name = website.organization_name if website and website.organization_name else ''
    
    if org_name and org_name.lower() not in title.lower():
        score -= 15
        issues.append({'title': 'Missing Brand Identity in Title', 'description': f'The organization name "{org_name}" is missing from the page title. Generative engines look for clear brand signals.', 'severity': 'medium', 'category': 'geo'})
        
    # Structured content
    h2s = page_data.get('h2_headings', [])
    if len(h2s) < 2:
        score -= 15
        issues.append({'title': 'Lack of Structured Content', 'description': 'The page has very few H2 headings. Generative AI prefers well-structured, segmented content.', 'severity': 'medium', 'category': 'geo'})
        
    # External references (attribution)
    ext_links = page_data.get('external_links_count', 0)
    if ext_links == 0:
        score -= 10
        issues.append({'title': 'No External References', 'description': 'No external links found. Generative engines value content that cites authoritative external sources.', 'severity': 'low', 'category': 'geo'})
        
    return max(0, score), issues
