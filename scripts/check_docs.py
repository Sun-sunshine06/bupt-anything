"""Validate rendered documentation, including project-path URLs and search assets."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from build_docs import PAGES, SITE_URL

SITE = Path(__file__).resolve().parents[1] / "site"


def check_site():
    documents = {}
    urls = {}
    titles, descriptions = set(), set()
    for name in PAGES:
        route = "" if name == "index.md" else name.removesuffix(".md") + "/"
        file = SITE / route / "index.html"
        soup = BeautifulSoup(file.read_text(encoding="utf-8"), "html.parser")
        assert soup.html["lang"] == ("en" if name == "overview.en.md" else "zh")
        documents[file.resolve()] = soup
        urls[file.resolve()] = SITE_URL + route
        title = soup.title.get_text(strip=True)
        description = soup.find("meta", attrs={"name": "description"})["content"]
        assert title and title not in titles, f"Missing/duplicate title: {file}"
        assert description and description not in descriptions, f"Missing/duplicate summary: {file}"
        titles.add(title)
        descriptions.add(description)
        assert soup.find("link", rel="canonical")["href"] == SITE_URL + route
        assert soup.find("meta", property="og:url")["content"] == SITE_URL + route
        schema = json.loads(soup.find("script", type="application/ld+json").string)
        assert schema["url"] == SITE_URL + route
        assert schema["@type"] == ("SoftwareSourceCode" if not route else "TechArticle")
        assert soup.select_one("article h1"), f"Missing heading: {file}"

    prefix = urlsplit(SITE_URL).path
    for file, soup in documents.items():
        for tag, attribute in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
            for node in soup.find_all(tag):
                value = node.get(attribute)
                if not value or value.startswith(("mailto:", "data:", "javascript:")):
                    continue
                target = urlsplit(urljoin(urls[file], value))
                if target.netloc != urlsplit(SITE_URL).netloc:
                    continue
                assert target.path.startswith(prefix), f"Escapes project path: {value} in {file}"
                relative = unquote(target.path[len(prefix):])
                destination = SITE / relative
                if destination.is_dir():
                    destination /= "index.html"
                assert destination.is_file(), f"Broken local link: {value} in {file}"
                if target.fragment and destination.resolve() in documents:
                    fragment = unquote(target.fragment)
                    assert documents[destination.resolve()].find(id=fragment), (
                        f"Broken anchor: {value} in {file}"
                    )

    xml = ET.parse(SITE / "sitemap.xml")
    locations = {item.text for item in xml.findall(".//{*}loc")}
    assert locations == set(urls.values()), "Sitemap differs from published pages"
    search = json.loads((SITE / "search/search_index.json").read_text(encoding="utf-8"))
    assert search["docs"] and any("课表" in item["text"] for item in search["docs"])
    assert any("\u200b" in item["text"] for item in search["docs"]), "Chinese segmentation missing"
    indexed_pages = {item["location"].split("#")[0] for item in search["docs"]}
    assert "faq/" in indexed_pages and "overview.en/" in indexed_pages
    assert (SITE / "llms.txt").is_file()
    assert not any(SITE.rglob("*.py")), "Python source must not be in the site artifact"
    print(f"Validated {len(documents)} pages: links, anchors, SEO metadata, sitemap and search.")


if __name__ == "__main__":
    check_site()
