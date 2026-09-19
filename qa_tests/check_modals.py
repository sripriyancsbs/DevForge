from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width, height in [(375, 667), (1920, 1080)]:
        page = browser.new_page(viewport={'width': width, 'height': height})
        page.goto('http://localhost:3000/applications/inventory-api', wait_until='networkidle')
        page.wait_for_timeout(500)
        
        # Test 1: Notifications dropdown
        bell = page.locator('#top-nav-bell-btn')
        bell.click()
        page.wait_for_timeout(300)
        ov = page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        panel_rect = page.locator('#notifications-panel').bounding_box()
        print(f"Notifications at {width}x{height}: docOverflow={ov}, panel={panel_rect}")
        assert not ov, f"Notifications caused overflow at {width}x{height}"
        bell.click()
        page.wait_for_timeout(200)
        
        # Test 2: Redeploy modal
        page.locator('#header-redeploy-btn').click()
        page.wait_for_timeout(300)
        ov = page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        print(f"RedeployModal at {width}x{height}: docOverflow={ov}")
        assert not ov, f"Redeploy modal caused overflow at {width}x{height}"
        page.locator('#modal-redeploy-cancel-btn').click()
        page.wait_for_timeout(200)
        
        # Test 3: Add Env modal
        page.locator('#header-add-env-btn').click()
        page.wait_for_timeout(300)
        ov = page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        print(f"AddEnvModal at {width}x{height}: docOverflow={ov}")
        assert not ov, f"Add env modal caused overflow at {width}x{height}"
        page.locator('#modal-add-env-cancel-btn').click()
        page.wait_for_timeout(200)
        
        page.close()
    browser.close()
    print("ALL MODALS AND PANELS PASSED!")
