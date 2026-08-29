import threading
from django.utils import timezone
from ai_search.models import WebsiteScan, CrawledPage, AnalysisIssue, Recommendation
from .crawler import crawl_website
from .seo_engine import analyze_seo
from .aeo_engine import analyze_aeo
from .geo_engine import analyze_geo
from .llmo_engine import analyze_llmo
from .eeat_engine import analyze_eeat
from .recommendation_engine import generate_recommendations

def run_scan_in_background(scan_id):
    thread = threading.Thread(target=process_scan, args=(scan_id,))
    thread.daemon = True
    thread.start()

def process_scan(scan_id):
    try:
        scan = WebsiteScan.objects.get(id=scan_id)
    except WebsiteScan.DoesNotExist:
        return
        
    scan.status = 'running'
    scan.started_at = timezone.now()
    scan.save()
    
    website = scan.website
    
    try:
        # Crawl website
        raw_pages = crawl_website(website.base_url, max_pages=website.max_crawl_pages)
        
        # Save pages
        crawled_pages_objs = []
        all_crawled_urls = [p['url'] for p in raw_pages if 'url' in p]
        all_titles = [p.get('title') for p in raw_pages if p.get('title')]
        
        total_seo, total_aeo, total_geo, total_llmo = 0, 0, 0, 0
        total_eeat = 0
        page_count = 0
        
        for data in raw_pages:
            if not data.get('url'):
                continue
                
            page = CrawledPage.objects.create(
                scan=scan,
                url=data['url'],
                status_code=data.get('status_code'),
                title=data.get('title'),
                meta_description=data.get('meta_description'),
                canonical_url=data.get('canonical_url'),
                robots_meta=data.get('robots_meta'),
                language=data.get('language'),
                h1_headings=data.get('h1_headings', []),
                h2_headings=data.get('h2_headings', []),
                h3_headings=data.get('h3_headings', []),
                word_count=data.get('word_count', 0),
                images_count=data.get('images_count', 0),
                images_with_alt=data.get('images_with_alt', 0),
                internal_links_count=data.get('internal_links_count', 0),
                external_links_count=data.get('external_links_count', 0),
                has_structured_data=data.get('has_structured_data', False),
            )
            crawled_pages_objs.append(page)
            
            # If not 200, skip analysis for this page
            if data.get('status_code') != 200:
                continue
                
            # Run engines
            seo_score, seo_issues = analyze_seo(data, all_titles)
            aeo_score, aeo_issues = analyze_aeo(data)
            geo_score, geo_issues = analyze_geo(data, website)
            llmo_score, llmo_issues = analyze_llmo(data)
            eeat_score, eeat_issues = analyze_eeat(data, website, all_crawled_urls)
            
            total_seo += seo_score
            total_aeo += aeo_score
            total_geo += geo_score
            total_llmo += llmo_score
            total_eeat += eeat_score
            page_count += 1
            
            # Save issues and recommendations
            all_issues = seo_issues + aeo_issues + geo_issues + llmo_issues + eeat_issues
            for issue_data in all_issues:
                issue = AnalysisIssue.objects.create(
                    scan=scan,
                    page=page,
                    title=issue_data['title'],
                    description=issue_data['description'],
                    severity=issue_data['severity'],
                    category=issue_data['category']
                )
                Recommendation.objects.create(
                    issue=issue,
                    description=generate_recommendations(issue)
                )
        
        # Calculate aggregates
        if page_count > 0:
            scan.seo_score = int(total_seo / page_count)
            scan.aeo_score = int(total_aeo / page_count)
            scan.geo_score = int(total_geo / page_count)
            scan.llmo_score = int(total_llmo / page_count)
            scan.eeat_score = int(total_eeat / page_count)
            
            # Overall score: Simple weighted average (can be configured)
            # SEO: 30%, AEO: 20%, GEO: 20%, LLMO: 15%, EEAT: 15%
            scan.overall_score = int(
                (scan.seo_score * 0.30) +
                (scan.aeo_score * 0.20) +
                (scan.geo_score * 0.20) +
                (scan.llmo_score * 0.15) +
                (scan.eeat_score * 0.15)
            )
        else:
            scan.seo_score = 0
            scan.aeo_score = 0
            scan.geo_score = 0
            scan.llmo_score = 0
            scan.eeat_score = 0
            scan.overall_score = 0
            
        scan.status = 'completed'
        
    except Exception as e:
        scan.status = 'failed'
        print(f"Scan {scan_id} failed: {e}")
        
    finally:
        scan.completed_at = timezone.now()
        scan.save()
