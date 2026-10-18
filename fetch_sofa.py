# -*- coding: utf-8 -*-
# Feasibility test: can a real headless Chromium (GitHub Actions cloud robot)
# get past SofaScore's Cloudflare challenge and read the public JSON API?

import asyncio
import os
import sys

from playwright.async_api import async_playwright

try:
    from playwright_stealth import stealth_async
except Exception:
    stealth_async = None

BASE = "https://www.sofascore.com"

ENDPOINTS = {
    "football_live": "/api/v1/sport/football/events/live",
}

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


async def main():
    os.makedirs("out", exist_ok=True)
    all_ok = True
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        ctx = await browser.new_context(locale="en-US", user_agent=UA)
        page = await ctx.new_page()
        if stealth_async:
            try:
                await stealth_async(page)
            except Exception:
                pass

        await page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(7000)

        for name, path in ENDPOINTS.items():
            url = BASE + path
            data = await page.evaluate(
                """async (u) => {
                    try {
                        const r = await fetch(u, {headers: {'Accept': 'application/json'}});
                        return {status: r.status, body: await r.text()};
                    } catch (e) {
                        return {status: -1, body: String(e)};
                    }
                }""",
                url,
            )
            status = data.get("status")
            body = data.get("body") or ""
            print("== %s -> HTTP %s, %d bytes ==" % (name, status, len(body)))
            print(body[:200])
            print()
            with open(os.path.join("out", name + ".json"), "w") as f:
                f.write(body)
            if status != 200 or body.strip().startswith('{"error"'):
                all_ok = False

        await browser.close()

    if not all_ok:
        print("RESULT: BLOCKED - Cloudflare izazov nije probijen sa ovog IP-a.")
        sys.exit(1)
    print("RESULT: OK - podaci stizu.")


if __name__ == "__main__":
    asyncio.run(main())
