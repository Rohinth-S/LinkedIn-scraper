#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def test_browsers():
    playwright = await async_playwright().start()
    
    try:
        # Test Chromium
        browser = await playwright.chromium.launch(headless=True)
        print("✅ Chromium browser launched successfully!")
        await browser.close()
        
        # Test Firefox as fallback
        browser = await playwright.firefox.launch(headless=True)
        print("✅ Firefox browser launched successfully!")
        await browser.close()
        
    except Exception as e:
        print(f"❌ Browser launch failed: {str(e)}")
    
    await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_browsers())