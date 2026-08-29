import os

os.makedirs("website/templates/website/components", exist_ok=True)

def write_comp(name, content):
    with open(f"website/templates/website/components/{name}.html", "w", encoding="utf-8") as f:
        f.write(content)

write_comp("hero", """
<section class="cms-managed-section cms-theme-dark text-white" style="background:#111b35;">
    <div class="container text-center py-5">
        {% if section.heading %}<h1 class="display-4 fw-bold">{{ section.heading }}</h1>{% endif %}
        {% if section.subheading %}<p class="lead mt-3">{{ section.subheading }}</p>{% endif %}
        {% if section.content %}<div class="mt-4">{{ section.content|safe }}</div>{% endif %}
        {% if section.items %}
            <div class="mt-4">
            {% for btn in section.items %}
                <a href="{{ btn.url|default:'#' }}" class="btn btn-warning btn-lg mx-2">{{ btn.title|default:'Click Here' }}</a>
            {% endfor %}
            </div>
        {% endif %}
    </div>
</section>
""")

write_comp("text", """
<section class="cms-managed-section py-5">
    <div class="container">
        {% if section.heading %}<div class="cms-section-heading mb-4 text-center"><h2>{{ section.heading }}</h2></div>{% endif %}
        {% if section.subheading %}<p class="cms-section-subtitle text-center mb-4">{{ section.subheading }}</p>{% endif %}
        {% if section.content %}<div class="content-body">{{ section.content|safe }}</div>{% endif %}
    </div>
</section>
""")

write_comp("image", """
<section class="cms-managed-section text-center py-5">
    <div class="container">
        {% if section.heading %}<h2 class="mb-4">{{ section.heading }}</h2>{% endif %}
        {% if section.image %}<img src="{{ section.image.url }}" alt="{{ section.heading }}" class="img-fluid rounded shadow" style="max-width:100%;">{% endif %}
        {% if section.content %}<div class="mt-4">{{ section.content|safe }}</div>{% endif %}
    </div>
</section>
""")

write_comp("features", """
<section class="cms-managed-section py-5 bg-light">
    <div class="container">
        <div class="cms-section-heading text-center mb-5">
            {% if section.heading %}<h2>{{ section.heading }}</h2>{% endif %}
            {% if section.subheading %}<p class="cms-section-subtitle text-muted">{{ section.subheading }}</p>{% endif %}
        </div>
        <div class="row">
            {% for item in section.items %}
            <div class="col-md-4 mb-4">
                <div class="card h-100 border-0 shadow-sm cms-card">
                    <div class="card-body text-center p-4">
                        <h4 class="card-title">{{ item.title }}</h4>
                        <p class="card-text text-muted">{{ item.description }}</p>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</section>
""")

write_comp("header", """
<header>
    <nav class="navbar navbar-expand-lg navbar-dark" style="background:#111b35;">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">{{ site_settings.company_name|default:"My Website" }}</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {% for page in nav_pages %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ page.get_absolute_url }}">{{ page.title }}</a>
                        </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </nav>
</header>
""")

write_comp("footer", """
<footer class="text-light py-4 text-center mt-auto" style="background:#0a1020;">
    <div class="container">
        <p class="mb-0">&copy; {{ site_settings.company_name|default:"My Website" }}. All Rights Reserved.</p>
    </div>
</footer>
""")

# Fallbacks for others
for comp in ["services", "faq", "team", "testimonials", "contact", "cta"]:
    write_comp(comp, f"<!-- Component {comp} --><section class='cms-managed-section py-5'><div class='container'><h3 class='text-center'>{{{{ section.heading }}}} [{comp} component]</h3></div></section>")

print("Components created!")
