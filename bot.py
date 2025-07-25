import pywikibot
from pywikibot import pagegenerators
import hashlib
import re
import time
import datetime
import requests
from bs4 import BeautifulSoup

def log_to_userpage(site, title, summary, diff_id):
    log_page = pywikibot.Page(site, "User:AsteraBot/log")
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    entry = f"* {timestamp} – [[{title}]] – {summary} – [[Special:Diff/{diff_id}|diff]]\n"
    try:
        txt = log_page.get()
    except pywikibot.NoPage:
        txt = "== Log ==\n"
    log_page.text = txt + entry
    log_page.save(summary=f"Logging edit to {title}")

def rename_duplicate_refs(text):
    pattern = r"<ref>(.*?)</ref>"
    refs = re.findall(pattern, flags=re.DOTALL, string=text)
    changes = False
    used = {}

    for content in set(refs):
        count = refs.count(content)
        if count > 1:
            h = hashlib.md5(content.strip().encode()).hexdigest()[:6]
            used[content] = h

    if not used:
        return text, False

    for old, h in used.items():
        first = f'<ref name="ref{h}">{old}</ref>'
        replacement = f'<ref name="ref{h}" />'
        text = text.replace(f"<ref>{old}</ref>", first, 1)
        text = text.replace(f"<ref>{old}</ref>", replacement)
        changes = True

    return text, changes

def cite_web_from_url(url):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "SimpleJanitorBot"})
        resp.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(resp.text, 'html.parser')
    title = soup.title.string.strip() if soup.title else url
    domain = requests.utils.urlparse(url).hostname or ''
    access_date = datetime.datetime.utcnow().strftime("%B %d, %Y")
    citation = f'{{{{cite web|url={url}|title={title}|work={domain}|access-date={access_date}}}}}'
    return citation

def replace_bare_refs(text):
    changed = False
    pattern = r"<ref>(https?://[^\s<]+)</ref>"
    matches = re.findall(pattern, text)
    for url in matches:
        cite = cite_web_from_url(url)
        if cite:
            text = text.replace(f"<ref>{url}</ref>", f"<ref>{cite}</ref>")
            changed = True
            time.sleep(5)
    return text, changed

def process_page(page, site):
    original = page.text
    text = original
    refs_renamed = False
    bare_fixed = False

    if page.title() != "User:AsteraBot/sandbox":
        return

    text, refs_renamed = rename_duplicate_refs(text)
    text, bare_fixed = replace_bare_refs(text)

    if text != original:
        actions = []
        if refs_renamed:
            actions.append("named duplicate references")
        if bare_fixed:
            actions.append("converted bare refs to cite web")
        summary = "Bot: " + "; ".join(actions)
        page.text = text
        page.save(summary=summary)
        diff = page.latest_revision_id
        log_to_userpage(site, page.title(), summary, diff)
        print(f"Processed {page.title()}: {summary}")

def main():
    site = pywikibot.Site('test', 'wikipedia')
    sandbox = pywikibot.Page(site, "User:AsteraBot/sandbox")
    process_page(sandbox, site)

if __name__ == "__main__":
    main()
