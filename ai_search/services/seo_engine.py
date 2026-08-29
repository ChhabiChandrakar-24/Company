def analyze_seo(page_data, all_titles):
    score = 100
    issues = []
    
    # Titles
    title = page_data.get('title')
    if not title:
        score -= 15
        issues.append({'title': 'Missing Title Tag', 'description': 'The page does not have a title tag.', 'severity': 'critical', 'category': 'seo'})
    elif all_titles.count(title) > 1:
        score -= 5
        issues.append({'title': 'Duplicate Title Tag', 'description': 'The title tag is duplicated across multiple pages.', 'severity': 'high', 'category': 'seo'})
        
    # Meta Description
    meta_desc = page_data.get('meta_description')
    if not meta_desc:
        score -= 10
        issues.append({'title': 'Missing Meta Description', 'description': 'The page does not have a meta description.', 'severity': 'high', 'category': 'seo'})
        
    # H1 Heading
    h1s = page_data.get('h1_headings', [])
    if not h1s:
        score -= 10
        issues.append({'title': 'Missing H1 Heading', 'description': 'The page does not have an H1 heading.', 'severity': 'high', 'category': 'seo'})
    elif len(h1s) > 1:
        score -= 2
        issues.append({'title': 'Multiple H1 Headings', 'description': 'The page has multiple H1 headings which may confuse search engines.', 'severity': 'medium', 'category': 'seo'})
        
    # Images Alt Text
    images_count = page_data.get('images_count', 0)
    images_with_alt = page_data.get('images_with_alt', 0)
    if images_count > 0 and images_with_alt < images_count:
        score -= 5
        issues.append({'title': 'Missing Image Alt Text', 'description': f'{images_count - images_with_alt} images are missing alt text.', 'severity': 'medium', 'category': 'seo'})
        
    # Canonical tags
    if not page_data.get('canonical_url'):
        score -= 5
        issues.append({'title': 'Missing Canonical Tag', 'description': 'No canonical tag is present on this page.', 'severity': 'low', 'category': 'seo'})
        
    # Internal linking
    internal_links = page_data.get('internal_links_count', 0)
    if internal_links == 0:
        score -= 5
        issues.append({'title': 'No Internal Links', 'description': 'The page has no internal links.', 'severity': 'high', 'category': 'seo'})
        
    # Structured data
    if not page_data.get('has_structured_data'):
        score -= 2
        issues.append({'title': 'Missing Structured Data', 'description': 'No JSON-LD structured data found.', 'severity': 'low', 'category': 'seo'})
        
    return max(0, score), issues
