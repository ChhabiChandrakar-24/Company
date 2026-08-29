def analyze_llmo(page_data):
    score = 100
    issues = []
    
    # Descriptive headings (check length of headings)
    headings = page_data.get('h2_headings', [])
    short_headings = [h for h in headings if len(h.split()) < 2]
    if short_headings:
        score -= 15
        issues.append({'title': 'Non-Descriptive Headings', 'description': 'Some headings are too short (1 word). LLMs prefer descriptive headings for context.', 'severity': 'medium', 'category': 'llmo'})
        
    # Content structure
    if len(headings) == 0 and page_data.get('word_count', 0) > 300:
        score -= 20
        issues.append({'title': 'Poor Content Structure', 'description': 'Long content without H2 headings is difficult for LLMs to parse effectively.', 'severity': 'high', 'category': 'llmo'})
        
    # Structured data
    if not page_data.get('has_structured_data'):
        score -= 15
        issues.append({'title': 'Missing Semantic Data', 'description': 'No structured data found. LLMs use Schema markup to understand entities.', 'severity': 'medium', 'category': 'llmo'})
        
    return max(0, score), issues
