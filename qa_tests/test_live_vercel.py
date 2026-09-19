from playwright.sync_api import sync_playwright
import sys

BASE_URL = "https://frontend-two-self-3343htd1ck.vercel.app"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    console_errors = []
    network_errors = []
    
    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
    page.on('requestfailed', lambda req: network_errors.append(f"{req.method} {req.url} - {req.failure}"))
    
    print(f"Navigating to {BASE_URL}...")
    resp = page.goto(BASE_URL, wait_until='networkidle')
    print(f"Response status: {resp.status}")
    page.wait_for_timeout(1000)
    
    title = page.title()
    print(f"Page title: {title}")
    
    doc_scroll = page.evaluate("document.documentElement.scrollWidth")
    doc_client = page.evaluate("document.documentElement.clientWidth")
    print(f"Viewport 1920x1080: scrollWidth={doc_scroll}, clientWidth={doc_client}, overflow={doc_scroll > doc_client}")
    
    print(f"Console errors ({len(console_errors)}):", console_errors[:5])
    print(f"Network errors ({len(network_errors)}):", network_errors[:5])
    
    browser.close()
