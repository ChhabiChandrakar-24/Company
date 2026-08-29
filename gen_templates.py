import os

base_dir = "ai_search/templates/ai_search"

templates = {
    "dashboard.html": """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>AI Search Optimization Engine - Dashboard</h2>
    <div class="row mt-4">
        <div class="col-md-2"><div class="card p-3 bg-primary text-white"><h5>Overall</h5><h3>{{ avg_overall }}</h3></div></div>
        <div class="col-md-2"><div class="card p-3"><h5>SEO</h5><h3>{{ avg_seo }}</h3></div></div>
        <div class="col-md-2"><div class="card p-3"><h5>AEO</h5><h3>{{ avg_aeo }}</h3></div></div>
        <div class="col-md-2"><div class="card p-3"><h5>GEO</h5><h3>{{ avg_geo }}</h3></div></div>
        <div class="col-md-2"><div class="card p-3"><h5>LLMO</h5><h3>{{ avg_llmo }}</h3></div></div>
        <div class="col-md-2"><div class="card p-3"><h5>E-E-A-T</h5><h3>{{ avg_eeat }}</h3></div></div>
    </div>
    <div class="row mt-4">
        <div class="col-md-3"><strong>Total Websites:</strong> {{ websites_count }}</div>
        <div class="col-md-3"><strong>Total Scans:</strong> {{ scans_count }}</div>
        <div class="col-md-3"><strong>Open Issues:</strong> {{ issues_count }} ({{ critical_issues }} Critical)</div>
        <div class="col-md-3"><strong>Open Recs:</strong> {{ recs_count }}</div>
    </div>
    <div class="mt-4">
        <a href="{% url 'ai_search:website_list' %}" class="btn btn-primary">Manage Websites</a>
    </div>
</div>
{% endblock %}
""",
    "website_list.html": """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Websites <a href="{% url 'ai_search:add_website' %}" class="btn btn-success btn-sm">Add New</a></h2>
    <ul class="list-group mt-3">
    {% for w in websites %}
        <li class="list-group-item"><a href="{% url 'ai_search:website_detail' w.id %}">{{ w.name }}</a> ({{ w.base_url }})</li>
    {% endfor %}
    </ul>
</div>
{% endblock %}
""",
    "add_website.html": """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Add Website</h2>
    <form method="POST">
        {% csrf_token %}
        <div class="form-group"><label>Name</label><input type="text" name="name" class="form-control" required></div>
        <div class="form-group"><label>Base URL</label><input type="url" name="base_url" class="form-control" required></div>
        <div class="form-group"><label>Organization Name</label><input type="text" name="organization_name" class="form-control"></div>
        <button type="submit" class="btn btn-primary mt-2">Save</button>
    </form>
</div>
{% endblock %}
""",
    "website_detail.html": """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>{{ website.name }} <a href="{% url 'ai_search:start_scan' website.id %}" class="btn btn-primary btn-sm">Start New Scan</a></h2>
    <p>URL: {{ website.base_url }}</p>
    <h4>Scan History</h4>
    <ul class="list-group">
    {% for scan in scans %}
        <li class="list-group-item"><a href="{% url 'ai_search:scan_detail' scan.id %}">Scan #{{ scan.id }}</a> - Status: {{ scan.status }} - Overall Score: {{ scan.overall_score }} ({{ scan.started_at|date }})</li>
    {% endfor %}
    </ul>
</div>
{% endblock %}
""",
    "scan_detail.html": """
{% extends "base.html" %}
{% block content %}
<div class="container mt-4">
    <h2>Scan #{{ scan.id }} for {{ scan.website.name }}</h2>
    <p>Status: {{ scan.status }}</p>
    {% if scan.status == 'completed' %}
        <div class="row">
            <div class="col-md-2">Overall: {{ scan.overall_score }}</div>
            <div class="col-md-2">SEO: {{ scan.seo_score }}</div>
            <div class="col-md-2">AEO: {{ scan.aeo_score }}</div>
            <div class="col-md-2">GEO: {{ scan.geo_score }}</div>
            <div class="col-md-2">LLMO: {{ scan.llmo_score }}</div>
            <div class="col-md-2">E-E-A-T: {{ scan.eeat_score }}</div>
        </div>
        <h4 class="mt-4">Issues Detected</h4>
        <ul class="list-group">
        {% for issue in issues %}
            <li class="list-group-item">
                <strong>[{{ issue.severity|upper }}] [{{ issue.category|upper }}]</strong> {{ issue.title }}<br>
                <small>{{ issue.description }}</small>
                {% for rec in issue.recommendations.all %}
                    <br><span class="text-success">Recommendation: {{ rec.description }}</span>
                {% endfor %}
            </li>
        {% endfor %}
        </ul>
    {% endif %}
</div>
{% endblock %}
"""
}

for name, content in templates.items():
    with open(os.path.join(base_dir, name), "w", encoding="utf-8") as f:
        f.write(content.strip())
print("Templates generated.")
