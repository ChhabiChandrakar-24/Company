import json
import re

transcript_path = r"C:\Users\CHHABI\.gemini\antigravity\brain\1823a982-3799-4763-b302-66964e3a9a92\.system_generated\logs\transcript_full.jsonl"
models_content = ""

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('type') == 'TOOL_RESPONSE':
            content = data.get('content', '')
            if 'file:///c:/Users/CHHABI/Downloads/bk/horilla/website/models.py' in content or 'website/models.py' in content:
                # We need the one that has 400+ lines
                if len(content) > 10000 and 'WebsiteSection' in content and 'class WebsitePage' in content:
                    models_content = content
                    break

if models_content:
    lines = []
    for line in models_content.splitlines():
        # match line numbers
        match = re.match(r"^(\d+):\s(.*)$", line)
        if match:
            lines.append((int(match.group(1)), match.group(2)))
    
    if lines:
        lines.sort()
        with open('website/models_recovered.py', 'w', encoding='utf-8') as out:
            for num, text in lines:
                out.write(text + "\n")
        print(f"Recovered {len(lines)} lines!")
    else:
        print("Could not parse lines.")
else:
    print("Could not find the content in transcript.")
