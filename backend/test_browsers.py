#!/usr/bin/env python3
import asyncio
import os
from playwright.async_api import async_playwright

# Set environment variable
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'

async def test_all_browsers():
    playwright = await async_playwright().start()
    
    print("Testing browser installations...")
    
    # Test 1: Default Chromium
    try:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.example.com')
        title = await page.title()
        print(f"✅ Default Chromium: {title}")
        await browser.close()
    except Exception as e:
        print(f"❌ Default Chromium failed: {str(e)}")
    
    # Test 2: Chromium with explicit path
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            executable_path="/pw-browsers/chromium-1169/chrome-linux/chrome"
        )
        page = await browser.new_page()
        await page.goto('https://www.example.com')
        title = await page.title()
        print(f"✅ Explicit Chromium: {title}")
        await browser.close()
    except Exception as e:
        print(f"❌ Explicit Chromium failed: {str(e)}")
    
    # Test 3: Firefox
    try:
        browser = await playwright.firefox.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.example.com')
        title = await page.title()
        print(f"✅ Firefox: {title}")
        await browser.close()
    except Exception as e:
        print(f"❌ Firefox failed: {str(e)}")
    
    await playwright.stop()
    print("\nBrowser testing completed!")

if __name__ == "__main__":
    asyncio.run(test_all_browsers())