import logging
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None

def get_rule_based_recommendation(title):
    mapping = {
        'Missing Title Tag': 'Add a unique and descriptive <title> tag to this page that accurately summarizes its main topic.',
        'Duplicate Title Tag': 'Ensure every page has a unique <title> tag to avoid confusing search engines.',
        'Missing Meta Description': 'Add a compelling meta description (150-160 characters) summarizing the page content.',
        'Missing H1 Heading': 'Add a single <h1> heading describing the primary topic of the page.',
        'Multiple H1 Headings': 'Consolidate multiple <h1> headings into a single primary <h1>, and use <h2> for sub-sections.',
        'Missing Image Alt Text': 'Add descriptive alt="" attributes to all images to improve accessibility and image SEO.',
        'Missing Canonical Tag': 'Add a <link rel="canonical" href="..."> tag to prevent duplicate content issues.',
        'No Internal Links': 'Add links pointing to other relevant pages on your website to help engines crawl your site.',
        'Missing Structured Data': 'Implement JSON-LD structured data (like Organization or Article schema) to provide explicit clues about the meaning of a page.',
        'No Question-Based Headings': 'Add headings formatted as questions (e.g., "What is X?") to directly target user queries and Answer Engines.',
        'No FAQ/Structured Data': 'Add FAQPage structured data to highlight questions and answers to Answer Engines.',
        'Thin Content for Answers': 'Expand the content to comprehensively answer common questions related to this topic.',
        'Missing Brand Identity in Title': 'Append your organization name to the title tag (e.g., "Page Topic - Company Name").',
        'Lack of Structured Content': 'Break up long text using descriptive <h2> and <h3> headings.',
        'No External References': 'Where appropriate, cite and link to authoritative external sources to build credibility.',
        'Non-Descriptive Headings': 'Make headings more descriptive (use 3-5 words) to provide better context to LLMs.',
        'Poor Content Structure': 'Organize the content logically with clear semantic headings rather than relying solely on paragraphs.',
        'Missing Semantic Data': 'Add appropriate Schema.org markup to help LLMs understand entities mentioned on the page.',
        'Insecure Protocol (HTTP)': 'Install an SSL certificate and redirect all HTTP traffic to HTTPS.',
        'Missing About Page': 'Create a detailed About Us page explaining who you are, your expertise, and your mission.',
        'Missing Contact Page': 'Create a Contact page with real-world contact information (address, phone, email).',
        'Missing Privacy/Terms Page': 'Add clear Privacy Policy and Terms of Service pages and link them in the footer.'
    }
    return mapping.get(title, 'Review this issue and apply standard optimization best practices.')

def generate_recommendations(issue):
    title = issue.title
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    if api_key and genai:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"You are an AI Search Optimization expert. Provide a highly actionable, 2-sentence recommendation to fix this issue on a website:\nIssue: {title}\nDescription: {issue.description}\nCategory: {issue.category.upper()}"
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API generation failed for issue '{title}': {e}")
            # Fallback happens below
    
    # Fallback to rule-based
    return get_rule_based_recommendation(title)
