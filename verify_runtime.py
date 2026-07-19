import re

html = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/index.html', encoding='utf-8').read()
css_files = ['theme.css','layout.css','components.css','chat.css','aicore.css','panels.css','animations.css','responsive.css']
js_files = ['app.js','stages.js','chat.js','panels.js','widgets.js','boot.js']

# Check getElementById references
js_id_refs = set()
for f in js_files:
    js = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/js/' + f, encoding='utf-8').read()
    ids = re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js)
    js_id_refs.update(ids)

html_ids = set(re.findall(r'id="([^"]+)"', html))
missing_ids = js_id_refs - html_ids

print("=== Event Listener ID References ===")
if missing_ids:
    print(f"  FAIL: Missing IDs: {', '.join(sorted(missing_ids))}")
else:
    print("  PASS: All getElementById references exist in HTML")

# Check CSS classes referenced in JS exist in CSS files
print("\n=== CSS Class References ===")
js_class_refs = set()
for f in js_files:
    js = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/js/' + f, encoding='utf-8').read()
    classes = re.findall(r"className\s*=\s*['\"]([^'\"]+)['\"]", js)
    for c in classes:
        js_class_refs.update(c.split())
    classlist = re.findall(r"classList\.\w+\(['\"]([^'\"]+)['\"]\)", js)
    js_class_refs.update(classlist)

# Collect all CSS classes from all CSS files
css_classes = set()
for f in css_files:
    css = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/css/' + f, encoding='utf-8').read()
    # Match .classname patterns
    matches = re.findall(r'\.([a-zA-Z_][\w-]*)', css)
    css_classes.update(matches)

missing_classes = js_class_refs - css_classes
if missing_classes:
    print(f"  FAIL: Missing CSS classes: {', '.join(sorted(missing_classes))}")
else:
    print("  PASS: All dynamically used CSS classes are defined in CSS files")
