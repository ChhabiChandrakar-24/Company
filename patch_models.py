import sys
with open('website/models.py', 'r', encoding='utf-8') as f:
    content = f.read()
old = '("faq", "FAQ"), ("contact", "Contact"), ("cta", "Call to action"),'
new = '("faq", "FAQ"), ("contact", "Contact"), ("cta", "Call to action"),\n        ("policy", "Legal / Policy Document"),'
if old in content:
    content = content.replace(old, new)
    with open('website/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated models.py")
else:
    print("Pattern not found")
