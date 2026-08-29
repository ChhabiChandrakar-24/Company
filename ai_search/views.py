from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from .models import Website, WebsiteScan, AnalysisIssue, Recommendation
from .services.scanner import run_scan_in_background
from django.db.models import Avg

@login_required
@permission_required('ai_search.view_ai_search_dashboard', raise_exception=True)
def dashboard(request):
    websites_count = Website.objects.count()
    scans_count = WebsiteScan.objects.count()
    
    completed_scans = WebsiteScan.objects.filter(status='completed')
    avg_overall = completed_scans.aggregate(Avg('overall_score'))['overall_score__avg'] or 0
    avg_seo = completed_scans.aggregate(Avg('seo_score'))['seo_score__avg'] or 0
    avg_aeo = completed_scans.aggregate(Avg('aeo_score'))['aeo_score__avg'] or 0
    avg_geo = completed_scans.aggregate(Avg('geo_score'))['geo_score__avg'] or 0
    avg_llmo = completed_scans.aggregate(Avg('llmo_score'))['llmo_score__avg'] or 0
    avg_eeat = completed_scans.aggregate(Avg('eeat_score'))['eeat_score__avg'] or 0
    
    issues_count = AnalysisIssue.objects.filter(status='open').count()
    critical_issues = AnalysisIssue.objects.filter(status='open', severity='critical').count()
    recs_count = Recommendation.objects.filter(issue__status='open').count()
    
    recent_scans = WebsiteScan.objects.order_by('-started_at')[:5]
    
    context = {
        'websites_count': websites_count,
        'scans_count': scans_count,
        'avg_overall': int(avg_overall),
        'avg_seo': int(avg_seo),
        'avg_aeo': int(avg_aeo),
        'avg_geo': int(avg_geo),
        'avg_llmo': int(avg_llmo),
        'avg_eeat': int(avg_eeat),
        'issues_count': issues_count,
        'critical_issues': critical_issues,
        'recs_count': recs_count,
        'recent_scans': recent_scans,
    }
    return render(request, 'ai_search/dashboard.html', context)

@login_required
@permission_required('ai_search.view_ai_search_dashboard', raise_exception=True)
def website_list(request):
    websites = Website.objects.all().order_by('-created_at')
    return render(request, 'ai_search/website_list.html', {'websites': websites})

@login_required
@permission_required('ai_search.add_website', raise_exception=True)
def add_website(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        base_url = request.POST.get('base_url')
        org_name = request.POST.get('organization_name')
        
        website = Website.objects.create(
            name=name,
            base_url=base_url,
            organization_name=org_name,
            created_by=request.user
        )
        messages.success(request, f'Website {name} added successfully.')
        return redirect('ai_search:website_detail', website_id=website.id)
        
    return render(request, 'ai_search/add_website.html')

@login_required
@permission_required('ai_search.view_ai_search_dashboard', raise_exception=True)
def website_detail(request, website_id):
    website = get_object_or_404(Website, id=website_id)
    scans = website.scans.order_by('-started_at')
    return render(request, 'ai_search/website_detail.html', {'website': website, 'scans': scans})

@login_required
@permission_required('ai_search.start_scan', raise_exception=True)
def start_scan(request, website_id):
    website = get_object_or_404(Website, id=website_id)
    scan = WebsiteScan.objects.create(website=website)
    run_scan_in_background(scan.id)
    messages.success(request, f'Scan started for {website.name}.')
    return redirect('ai_search:scan_detail', scan_id=scan.id)

@login_required
@permission_required('ai_search.view_ai_search_dashboard', raise_exception=True)
def scan_detail(request, scan_id):
    scan = get_object_or_404(WebsiteScan, id=scan_id)
    issues = scan.issues.all().order_by('severity')
    return render(request, 'ai_search/scan_detail.html', {'scan': scan, 'issues': issues})

@login_required
@permission_required('ai_search.view_ai_search_dashboard', raise_exception=True)
def issue_list(request):
    issues = AnalysisIssue.objects.filter(status='open').order_by('severity', '-detected_at')
    return render(request, 'ai_search/issue_list.html', {'issues': issues})

@login_required
@permission_required('ai_search.manage_recommendations', raise_exception=True)
def recommendation_list(request):
    recs = Recommendation.objects.filter(issue__status='open').select_related('issue')
    return render(request, 'ai_search/recommendation_list.html', {'recommendations': recs})
