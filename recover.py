import json
import re

transcript_path = r"C:\Users\CHHABI\.gemini\antigravity\brain\1823a982-3799-4763-b302-66964e3a9a92\.system_generated\logs\transcript_full.jsonl"
models_lines = {}

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('type') == 'TOOL_RESPONSE' and 'file:///c:/Users/CHHABI/Downloads/bk/horilla/website/models.py' in data.get('content', ''):
            content = data.get('content', '')
            # parse the lines
            # format is `<line_number>: <original_line>`
            for file_line in content.splitlines():
                match = re.match(r"^(\d+):\s(.*)$", file_line)
                if match:
                    num = int(match.group(1))
                    text = match.group(2)
                    models_lines[num] = text

# Write out the reconstructed file
if models_lines:
    max_line = max(models_lines.keys())
    with open(r"c:\Users\CHHABI\Downloads\bk\horilla\website\models_recovered.py", "w", encoding="utf-8") as out:
        for i in range(1, max_line + 1):
            out.write(models_lines.get(i, "") + "\n")
    print(f"Recovered {len(models_lines)} lines out of {max_line}")
else:
    print("No lines found in transcript.")
