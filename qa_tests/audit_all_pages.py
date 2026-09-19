from playwright.sync_api import sync_playwright
import json

viewports = [
    (1920, 1080),
    (1440, 900),
    (1366, 768),
    (1024, 768),
    (768, 1024),
    (390, 844),
    (375, 667)
]

pages_to_test = [
    ('/', 'Overview'),
    ('/applications', 'Applications'),
    ('/applications/inventory-api', 'AppDetail-Overview'),
    ('/applications/inventory-api/deployments', 'AppDetail-Deployments'),
    ('/applications/inventory-api/environments', 'AppDetail-Environments'),
    ('/applications/inventory-api/infrastructure', 'AppDetail-Infrastructure'),
    ('/applications/inventory-api/automation', 'AppDetail-Automation'),
    ('/applications/inventory-api/monitoring', 'AppDetail-Monitoring'),
    ('/applications/inventory-api/logs', 'AppDetail-Logs'),
    ('/activity', 'Activity'),
    ('/settings', 'Settings'),
    ('/create-application', 'CreateApplication')
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    results = []
    
    for width, height in viewports:
        is_desktop = width >= 768
        for path, name in pages_to_test:
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.goto(f'http://localhost:3000{path}', wait_until='networkidle')
            page.wait_for_timeout(600)
            
            check = page.evaluate('''(isDesktop) => {
                const docScroll = document.documentElement.scrollWidth;
                const docClient = document.documentElement.clientWidth;
                const bodyScroll = document.body.scrollWidth;
                const winW = window.innerWidth;
                const sidebar = document.querySelector('aside');
                const sidebarRight = (isDesktop && sidebar) ? sidebar.getBoundingClientRect().right : 0;
                
                // Find all elements that overflow window width
                const overflowingElements = [];
                const clippedLeftElements = [];
                
                const all = document.querySelectorAll('main *, header *');
                for (const el of all) {
                    // Skip fixed/absolute overlays, modals, tooltips
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.display === 'none' || style.visibility === 'hidden') continue;
                    
                    const rect = el.getBoundingClientRect();
                    // Check right overflow
                    if (rect.right > winW + 1 && el.scrollWidth > el.clientWidth && style.overflowX !== 'auto' && style.overflowX !== 'scroll') {
                        overflowingElements.push({
                            tag: el.tagName,
                            id: el.id,
                            className: (el.className || '').toString().slice(0, 50),
                            rect: { left: rect.left, right: rect.right, width: rect.width }
                        });
                    }
                    
                    // Check if content is pushed left under sidebar on desktop
                    if (isDesktop && rect.left < sidebarRight - 1 && rect.width > 0 && rect.height > 0) {
                        clippedLeftElements.push({
                            tag: el.tagName,
                            id: el.id,
                            className: (el.className || '').toString().slice(0, 50),
                            rect: { left: rect.left, right: rect.right, width: rect.width }
                        });
                    }
                    
                    // Check if content is clipped on left (< 0) on mobile
                    if (!isDesktop && rect.left < -1 && rect.width > 0 && rect.height > 0) {
                        clippedLeftElements.push({
                            tag: el.tagName,
                            id: el.id,
                            className: (el.className || '').toString().slice(0, 50),
                            rect: { left: rect.left, right: rect.right, width: rect.width }
                        });
                    }
                }
                
                return {
                    docScroll,
                    docClient,
                    hasDocOverflow: docScroll > docClient,
                    overflowingCount: overflowingElements.length,
                    clippedLeftCount: clippedLeftElements.length,
                    overflowingSample: overflowingElements.slice(0, 3),
                    clippedLeftSample: clippedLeftElements.slice(0, 3)
                };
            }''', is_desktop)
            
            status = "PASS" if not check['hasDocOverflow'] and check['clippedLeftCount'] == 0 else "FAIL"
            results.append({
                "viewport": f"{width}x{height}",
                "page": name,
                "status": status,
                "docScroll": check['docScroll'],
                "docClient": check['docClient'],
                "hasDocOverflow": check['hasDocOverflow'],
                "clippedLeftCount": check['clippedLeftCount'],
                "clippedSample": check['clippedLeftSample'],
                "overflowSample": check['overflowingSample']
            })
            if status == "FAIL":
                print(f"FAIL: {width}x{height} - {name}: overflow={check['hasDocOverflow']} ({check['docScroll']}>{check['docClient']}), clippedLeft={check['clippedLeftCount']}", flush=True)
                if check['clippedLeftSample']:
                    print("  Clipped left:", check['clippedLeftSample'], flush=True)
                if check['overflowingSample']:
                    print("  Overflow:", check['overflowingSample'], flush=True)
            else:
                print(f"PASS: {width}x{height} - {name} ({check['docClient']}px)", flush=True)
            page.close()
    browser.close()
