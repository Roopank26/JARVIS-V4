import re
html = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/index.html', encoding='utf-8').read()
js_files = ['app.js','stages.js','chat.js','panels.js','widgets.js','boot.js']
html_ids = set(re.findall(r'id="([^"]+)"', html))
ref_ids = set()
for f in js_files:
    js = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/js/' + f, encoding='utf-8').read()
    ref_ids.update(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js))
missing = ref_ids - html_ids
if missing:
    print('7. Missing IDs FAIL:', ', '.join(sorted(missing)))
else:
    print('7. All JS-referenced IDs exist: PASS')
