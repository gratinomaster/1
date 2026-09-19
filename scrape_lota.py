import asyncio
import json
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

SEARCH_URL = "https://archive.org/search?tab=all&query=documentary&sort=-date&and%5B%5D=mediatype%3A%22movies%22"
API_URL = ("https://archive.org/advancedsearch.php?q="
           + 'documentary%20AND%20mediatype%3A%22movies%22%20AND%20-access-restricted-item%3Atrue'
           + "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=date&fl%5B%5D=creator"
           + "&sort%5B%5D=-date&rows=80&page=1&output=json")

JS_INJECT = r"""
(() => {
  const script = document.createElement('script');
  script.type = 'application/json';
  script.id = 'lota-data';
  script.textContent = 'ERROR';
  const req = new XMLHttpRequest();
  req.open('GET', '%API%', false);
  req.send(null);
  script.textContent = req.status === 200 ? req.responseText : 'HTTP ' + req.status + ' ' + req.responseText;
  document.body.appendChild(script);
})();
""".replace('%API%', API_URL)


async def main():
    browser = BrowserConfig(headless=True)
    run = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        page_timeout=120000,
        js_code=JS_INJECT,
        delay_before_return_html=6,
    )
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=SEARCH_URL, config=run)
    print("STATUS:", result.success)
    html = result.html or ""
    with open("search_raw.html", "w", encoding="utf-8") as f:
        f.write(html)
    m = re.search(r'<script[^>]*type="application/json"[^>]*id="lota-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        print("lota-data nao encontrado no HTML")
        return
    data = json.loads(m.group(1))
    if "error" in data:
        print("ERRO da API:", data)
        return
    docs = data["response"]["docs"]
    print("numFound:", data["response"]["numFound"])
    print("itens retornados:", len(docs))
    for d in docs[:5]:
        print("-", d.get("date"), "|", d.get("identifier"), "|", d.get("title"))
    with open("lota_items.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())