import requests
import re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "ColabWikiSearch/1.0 (educational use)"}

def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)                          # remove [1], [2] citation marks
    text = re.sub(r"\[[a-zA-Z ]+\]", "", text)                   # remove [citation needed] etc.
    text = re.sub(r"\(/[^)]*\)", "", text)                        # remove IPA pronunciation
    text = re.sub(r"\([^)]*listen[^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)                              # collapse whitespace
    return text.strip()


def split_into_points(text, max_points=8):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    points = [s.strip() for s in sentences if len(s.strip()) > 25]
    return points[:max_points]

def get_top_title(query):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": 1,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    results = r.json().get("query", {}).get("search", [])
    return results[0]["title"] if results else None

def get_page_summary(title):
    safe_title = title.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    return {
        "title": data.get("title", title),
        "extract": data.get("extract", ""),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{safe_title}"),
    }

def get_infobox(title):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "redirects": 1,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return {}, None
    data = r.json()
    html = data.get("parse", {}).get("text", {}).get("*", "")
    if not html:
        return {}, None

    soup = BeautifulSoup(html, "html.parser")
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return {}, None

    image_url = None

    for row in infobox.find_all("tr"):
        full_cell = row.find("td", class_="infobox-full-data")
        if full_cell and full_cell.find("div", style=lambda s: s and "font-weight:bold" in s):
            img_tag = full_cell.find("img")
            if img_tag and img_tag.get("src"):
                src = img_tag["src"]
                image_url = "https:" + src if src.startswith("//") else src
            break

    if not image_url:
        image_cell = infobox.find("td", class_="infobox-image")
        if image_cell:
            img_tag = image_cell.find("img")
            if img_tag and img_tag.get("src"):
                src = img_tag["src"]
                image_url = "https:" + src if src.startswith("//") else src

    if not image_url:
        img_tag = infobox.find("img")
        if img_tag and img_tag.get("src"):
            src = img_tag["src"]
            image_url = "https:" + src if src.startswith("//") else src

    facts = {}
    for row in infobox.find_all("tr"):
        for sup in row.find_all("sup"):
            sup.decompose()

        label_cell = row.find("th", class_="infobox-label")
        value_cell = row.find("td", class_="infobox-data")

        if label_cell and value_cell:
            label = clean_text(label_cell.get_text(" ", strip=True))
            value = clean_text(value_cell.get_text(" | ", strip=True))
            if label and value:
                facts[label] = value
            continue

        full_cell = row.find("td", class_="infobox-full-data")
        if full_cell:
            bold_div = full_cell.find("div", style=lambda s: s and "font-weight:bold" in s)
            if bold_div:
                bold_text = clean_text(bold_div.get_text(" ", strip=True))
                full_text = clean_text(full_cell.get_text(" ", strip=True))
                words = bold_text.split(" ", 1)
                if len(words) == 2:
                    label, name = words
                    remainder = full_text.replace(bold_text, "", 1).strip()
                    value = f"{name} ({remainder})" if remainder else name
                    facts[label] = value
            continue

        plain_cells = row.find_all("td", recursive=False)
        if len(plain_cells) == 2:
            label = clean_text(plain_cells[0].get_text(" ", strip=True)).rstrip(":")
            value = clean_text(plain_cells[1].get_text(" | ", strip=True))
            if label and value and len(label) < 30:  # avoid picking up stray long rows
                facts[label] = value

    return facts, image_url

def wikipedia_search(query: str, num_points: int = 6) -> dict:
    """
    Search Wikipedia and return a structured dictionary with title, url, image_url, facts, and points.
    """
    try:
        title = get_top_title(query)
        if not title:
            return {"error": "No results found."}

        page = get_page_summary(title)
        if not page or not page["extract"]:
            return {"error": "Could not retrieve a summary for this page."}

        facts, image_url = get_infobox(title)

        cleaned = clean_text(page["extract"])
        points = split_into_points(cleaned, max_points=num_points)

        return {
            "title": page["title"],
            "url": page["url"],
            "image_url": image_url,
            "facts": facts,
            "points": points if points else [cleaned],
            "query": query
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}"}
    except Exception as e:
        return {"error": f"Error: {e}"}

class WikipediaSearchTool:
    """
    A class wrapper to expose the search function as a tool.
    """
    def __init__(self):
        self.name = "wikipedia_search"
        self.description = "Search Wikipedia for general static factual information."
    
    def execute(self, query: str, num_points: int = 6):
        return wikipedia_search(query, num_points)
