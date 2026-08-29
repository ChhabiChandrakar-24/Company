
import re

with open("website/admin.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("WebsiteSubmission,\n)", "WebsiteSubmission,\n    PortfolioProject,\n    Testimonial,\n    FAQ,\n)")
content += "\nadmin.site.register(PortfolioProject)\nadmin.site.register(Testimonial)\nadmin.site.register(FAQ)\n"

with open("website/admin.py", "w", encoding="utf-8") as f:
    f.write(content)

