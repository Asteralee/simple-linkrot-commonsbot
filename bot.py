import pywikibot
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import mwparserfromhell

# ====================
# Utility Functions
# ====================

def fetch_title(url):
    """Get the <title> from the webpage at the given URL."""
    try:
        headers = {'User-Agent': 'TestWikiBot/1.0 (https://test.wikipedia.org)'}
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.title.string.strip() if soup.title else "No title"
    except Exception as e:
        print(f"Could not fetch title for {url}: {e}")
        return "No title"

def replace_bare_urls(text):
    """Replace bare URLs (including in <ref>) with cite web templates."""
    updated = text
    seen = set()

    # Match bare URLs, possibly inside <ref>...</ref>
    pattern = re.compile(r'(<ref[^>]*>)?\s*(https?://[^\s\[\]<>"]+)\s*(</ref>)?', re.IGNORECASE)

    def replacer(match):
        pre = match.group(1) or ''
        url = match.group(2)
        post = match.group(3) or ''

        if url in seen:
            return match.group(0)
        seen.add(url)

        title = fetch_title(url)
        cite = f"{{{{cite web |url={url} |title={title} |access-date={datetime.utcnow().date()}}}}}"
        return f"{pre}{cite}{post}"

    updated = re.sub(pattern, replacer, updated)
    return updated

def remove_cleanup_templates(text):
    """Remove {{Cleanup bare URLs}} template (and similar)."""
    return re.sub(r'\{\{\s*Cleanup bare URLs[^}]*\}\}', '', text, flags=re.IGNORECASE)

def log_edit(title):
    """Append a log entry to the user's bot log subpage."""
    site = pywikibot.Site()
    log_page = pywikibot.Page(site, "User:Chi/Bot log")  # Update if using a different name
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    log_entry = f"* [[{title}]] – replaced bare URLs – {timestamp}\n"

    try:
        current_text = log_page.text
    except pywikibot.NoPage:
        current_text = ""

    log_page.text = current_text + log_entry
    log_page.save(summary=f"Bot log: added entry for [[{title}]]")

# ====================
# Main Processing Logic
# ====================

def process_page(title):
    """Fix one page if it exists and has bare URLs."""
    site = pywikibot.Site()
    page = pywikibot.Page(site, title)

    if not page.exists():
        print(f"Page {title} does not exist.")
        return

    original_text = page.text
    updated_text = replace_bare_urls(original_text)
    updated_text = remove_cleanup_templates(updated_text)

    if original_text != updated_text:
        page.text = updated_text
        page.save(summary="Bot: Replaced bare URLs with cite web templates and removed cleanup template")
        print(f"✅ Edited page: {title}")
        log_edit(title)
    else:
        print(f"ℹ️ No changes made to: {title}")

def get_pages_from_category(cat_title):
    """Get all pages in a given category."""
    site = pywikibot.Site()
    category = pywikibot.Category(site, cat_title)
    return list(category.articles(namespaces=[0]))  # Mainspace only

# ====================
# Run the Bot
# ====================

if __name__ == "__main__":
    category_name = "Category:All articles with bare URLs for citations"
    pages = get_pages_from_category(category_name)

    if not pages:
        print("No pages found in the category.")
    else:
        for page in pages:
            process_page(page.title())
