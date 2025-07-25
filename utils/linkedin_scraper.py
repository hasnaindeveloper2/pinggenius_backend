from playwright.async_api import async_playwright
import asyncio

async def scrape_linkedin_profile(linkedin_url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(linkedin_url)

        await page.wait_for_timeout(3000)  # wait for content to load

        name = await page.locator("h1").inner_text()
        headline = await page.locator("div.text-body-medium.break-words").first.inner_text()
        location = await page.locator("span.text-body-small.inline.t-black--light.break-words").first.inner_text()

        await browser.close()

        return {
            "name": name.strip(),
            "headline": headline.strip(),
            "location": location.strip(),
            "linkedin": linkedin_url
        }


asyncio.run(scrape_linkedin_profile("https://www.linkedin.com/in/hasnainxdev/"))