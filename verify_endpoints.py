import re

# Check fetch endpoints in JS
js_files = ['app.js','stages.js','chat.js','panels.js','widgets.js','boot.js']
fetch_endpoints = set()
for f in js_files:
    js = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/js/' + f, encoding='utf-8').read()
    # Match fetch('...') or fetch("...")
    matches = re.findall(r"fetch\(['\"]([^'\"]+)['\"]\)", js)
    fetch_endpoints.update(matches)
    # Also match fetch('/api/...'+...) patterns
    matches2 = re.findall(r"fetch\(['\"](/api/[^'\"]+)['\"]", js)
    fetch_endpoints.update(matches2)

# Backend routes from server.py
server = open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/server.py', encoding='utf-8').read()
backend_routes = set()
backend_routes.update(re.findall(r'add_(get|post)\(["\']([^"\']+)', server))

# Also check for WebSocket event handling
ws_events = set()
ws_events.update(re.findall(r"case '([^']+)'", open('C:/Users/LENOVO/JARVIS-V4/jarvis/ui/static/js/app.js', encoding='utf-8').read()))

print("=== Fetch Endpoints ===")
for ep in sorted(fetch_endpoints):
    base_ep = ep.split('?')[0]
    matched = any(base_ep == route[1] or route[1].startswith(base_ep) for route in backend_routes)
    status = "PASS" if matched else "FAIL"
    print(f"  {status}: {ep}")

print("\n=== WebSocket Events ===")
ws_backend = ['status', 'stage', 'token', 'user_message', 'assistant_message', 'plan', 'step', 'tool', 'task', 'suggestion', 'error', 'toast', 'plugin', 'activity']
for ev in ws_events:
    status = "PASS" if ev in ws_backend else "FAIL"
    print(f"  {status}: {ev}")
