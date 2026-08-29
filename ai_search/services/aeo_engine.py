import re

def analyze_aeo(page_data):
    score = 100
    issues = []
    
    # Check for question-based headings
    all_headings = page_data.get('h1_headings', []) + page_data.get('h2_headings', []) + page_data.get('h3_headings', [])
    has_question_heading = any('?' in h for h in all_headings)
    
    if not has_question_heading:
        score -= 20
        issues.append({'title': 'No Question-Based Headings', 'description': 'Adding conversational, question-based headings improves Answer Engine Optimization.', 'severity': 'medium', 'category': 'aeo'})
        
    # Check for FAQ structured data
    has_structured = page_data.get('has_structured_data', False)
    if not has_structured:
        score -= 20
        issues.append({'title': 'No FAQ/Structured Data', 'description': 'FAQ Structured Data (JSON-LD) is highly recommended for Answer Engines.', 'severity': 'high', 'category': 'aeo'})
        
    # Check for clear summaries/answers (basic heuristic: short paragraphs after headings, but we'll use word count for now as a proxy)
    if page_data.get('word_count', 0) < 300:
        score -= 10
        issues.append({'title': 'Thin Content for Answers', 'description': 'Page content is too brief to provide comprehensive answers to user queries.', 'severity': 'medium', 'category': 'aeo'})
        
    return max(0, score), issues
