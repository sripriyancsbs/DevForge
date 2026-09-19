from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    viewports = [
        (1920, 1080),
        (1440, 900),
        (1366, 768),
        (1024, 768),
        (768, 1024),
        (390, 844),
        (375, 667)
    ]
    for width, height in viewports:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto('http://localhost:3000/applications', wait_until='networkidle')
        page.wait_for_timeout(1000)
        
        doc_scroll = page.evaluate('document.documentElement.scrollWidth')
        doc_client = page.evaluate('document.documentElement.clientWidth')
        
        info = page.evaluate('''() => {
            const sidebar = document.querySelector('aside');
            const main = document.querySelector('main');
            const table = document.querySelector('table');
            const tableContainer = table ? table.parentElement : null;
            const appCell = document.querySelector('table td:first-child');
            
            return {
                sidebarWidth: sidebar ? sidebar.getBoundingClientRect().width : 0,
                sidebarRight: sidebar ? sidebar.getBoundingClientRect().right : 0,
                main: main ? {
                    left: main.getBoundingClientRect().left,
                    right: main.getBoundingClientRect().right,
                    width: main.getBoundingClientRect().width,
                    scrollWidth: main.scrollWidth,
                    clientWidth: main.clientWidth
                } : null,
                tableContainer: tableContainer ? {
                    left: tableContainer.getBoundingClientRect().left,
                    right: tableContainer.getBoundingClientRect().right,
                    width: tableContainer.getBoundingClientRect().width,
                    scrollWidth: tableContainer.scrollWidth,
                    clientWidth: tableContainer.clientWidth
                } : null,
                table: table ? {
                    left: table.getBoundingClientRect().left,
                    right: table.getBoundingClientRect().right,
                    width: table.getBoundingClientRect().width
                } : null,
                firstCell: appCell ? {
                    left: appCell.getBoundingClientRect().left,
                    right: appCell.getBoundingClientRect().right,
                    width: appCell.getBoundingClientRect().width
                } : null
            };
        }''')
        print(f"=== Viewport {width}x{height} ===")
        print(f"Doc: scrollWidth={doc_scroll}, clientWidth={doc_client}, overflow={doc_scroll > doc_client}")
        print(f"Sidebar: width={info['sidebarWidth']}, right={info['sidebarRight']}")
        print(f"Main: {json.dumps(info['main'])}")
        print(f"TableContainer: {json.dumps(info['tableContainer'])}")
        print(f"Table: {json.dumps(info['table'])}")
        print(f"FirstCell: {json.dumps(info['firstCell'])}")
        print()
    browser.close()
