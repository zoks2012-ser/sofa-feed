# -*- coding: utf-8 -*-
import asyncio, os, sys
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except Exception:
    stealth_async = None

BASE = "https://www.sofascore.com"
ENDPOINTS = {"football_live": "/api/v1/sport/football/events/live"}
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

        # 1) naslovna strana + cekanje da se Cloudflare izazov odradi
        await page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
        for _ in range(12):  # do ~36s: cekaj dok se vidi "Just a moment"
            title = (await page.title()) or ""
            if "just a moment" not in title.lower() and "moment" not in title.lower():
                break
            await page.wait_for_timeout(3000)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        title = (await page.title()) or ""
        cookies = await ctx.cookies()
        has_clear = any(c["name"] == "cf_clearance" for c in cookies)
        print("HOMEPAGE title=%r | cookies=%d | cf_clearance=%s"
              % (title, len(cookies), has_clear))

        # 2) pozovi API iz iste strane (nosi kolacic sam)
        for name, path in ENDPOINTS.items():
            url = BASE + path
            data = await page.evaluate(
                """async (u) => {
                    try {
                        const r = await fetch(u, {headers: {'Accept':'application/json'}, credentials:'include'});
                        return {status: r.status, body: await r.text()};
                    } catch (e) { return {status: -1, body: String(e)}; }
                }""", url)
            status, body = data.get("status"), data.get("body") or ""
            print("== %s -> HTTP %s, %d bytes ==" % (name, status, len(body)))
            print(body[:200]); print()
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
