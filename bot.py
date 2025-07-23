import pywikibot
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import mwparserfromhell
from pywikibot.exceptions import OtherPageSaveError

# =========================
# Config
# =========================

# Set to False later
TEST_MODE = True
TEST_PAGES = ["User:AsteraBot/sandbox"]  

# =========================
# Utility Functions
# =========================

def fetch_title(url):
    try:
        headers = {'User-Agent': 'TestWikiBot/1.0'}
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.title.string.strip() if soup.title else "No title"
    except Exception as e:
        print(f"Could not fetch title for {url}: {e}")
        return "No title"

def detect_cite_template(url):
    """Return 'cite news' if the domain looks newsy, otherwise 'cite web'."""
    news_domains = ["nytimes", "bbc", "cnn", "reuters", "apnews", "nbcnews", "washingtonpost", "foxnews", "theguardian"]
    for domain in news_domains:
        if domain in url:
            return "cite news"
    return "cite web"

def replace_bare_urls(text):
    updated = text
    seen = set()

    pattern = re.compile(r'(<ref[^>]*>)?\s*(https?://[^\s\[\]<>"]+)\s*(</ref>)?', re.IGNORECASE)

    def replacer(match):
        pre = match.group(1) or ''
        url = match.group(2)
        post = match.group(3) or ''

        if url in seen:
            return match.group(0)
        seen.add(url)

        title = fetch_title(url)
        template = detect_cite_template(url)
        cite = f"{{{{{template} |url={url} |title={title} |access-date={datetime.utcnow().date()}}}}}"
        return f"{pre}{cite}{post}"

    updated = re.sub(pattern, replacer, updated)
    return updated

def remove_cleanup_templates(text):
    return re.sub(r'\{\{\s*Cleanup bare URLs[^}]*\}\}', '', text, flags=re.IGNORECASE)

def log_edit(title):
    site = pywikibot.Site()
    log_page = pywikibot.Page(site, "User:AsteraBot/log")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    log_entry = f"* [[{title}]] – replaced bare URLs – {timestamp}\n"

    try:
        current_text = log_page.text
    except pywikibot.NoPage:
        current_text = ""

    log_page.text = current_text + log_entry
    log_page.save(summary=f"Bot log: added entry for [[{title}]]")

# =========================
# Page Processing
# =========================

def process_page(title):
    site = pywikibot.Site()
    page = pywikibot.Page(site, title)

    if not page.exists():
        print(f"❌ Page {title} does not exist.")
        return

    original_text = page.text
    updated_text = replace_bare_urls(original_text)
    updated_text = remove_cleanup_templates(updated_text)

    if original_text != updated_text:
        page.text = updated_text
        try:
            page.save(summary="Bot: Replaced bare URLs with citation templates and removed cleanup template")
            print(f"✅ Edited page: {title}")
            log_edit(title)
        except OtherPageSaveError as e:
            print(f"⚠️ Skipped page '{title}' – bot not allowed to edit ({{nobots}}, {{in use}}, etc.):\n{e}")
    else:
        print(f"ℹ️ No changes made to: {title}")

# =========================
# Main Bot Runner
# =========================

def main():
    if TEST_MODE:
        print("Running in TEST MODE with hardcoded pages...")
        for title in TEST_PAGES:
            process_page(title)
    else:
        category = "Category:All articles with bare URLs for citations"
        site = pywikibot.Site()
        cat = pywikibot.Category(site, category)
        pages = list(cat.articles(namespaces=[0]))
        for page in pages:
            process_page(page.title())

if __name__ == "__main__":
    main()
