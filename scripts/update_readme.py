"""Refresh the 'Open source contributions' section of README.md.

Lists pull requests I opened in other people's repos that are merged
or still open, newest first. Runs daily from GitHub Actions.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime

USER = os.environ.get("GH_USER", "AnmolSrivastavaaaa")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
MAX_ITEMS = 15
START, END = "<!-- OSS:START -->", "<!-- OSS:END -->"

# Shown until the first PR is merged or opened.
EMPTY = (
    "Just getting started. Currently working with "
    "[@justadityaraj](https://github.com/justadityaraj) on a Windows version of "
    "[Switchboard](https://github.com/justadityaraj/switchboard-browser-picker) and on "
    "[amazon-in-mcp](https://github.com/justadityaraj/amazon-in-mcp)."
)


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fmt_stars(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def fmt_date(iso):
    return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %d, %Y")


def build(items, stars):
    prs = []
    for x in items:
        merged = (x.get("pull_request") or {}).get("merged_at")
        if not merged and x.get("state") != "open":
            continue  # skip closed-without-merge
        repo = x["repository_url"].split("/repos/")[1]
        prs.append({
            "repo": repo, "num": x["number"], "title": x["title"].replace("|", "\\|"),
            "url": x["html_url"], "merged": merged, "date": merged or x["created_at"],
        })
    if not prs:
        return EMPTY
    prs.sort(key=lambda p: p["date"], reverse=True)
    merged_count = sum(1 for p in prs if p["merged"])
    open_count = len(prs) - merged_count
    summary = f"**{merged_count} merged**" + (f", {open_count} in review" if open_count else "")
    lines = [summary, "", "| Project | Pull request | Status |", "|---|---|---|"]
    for p in prs[:MAX_ITEMS]:
        s = stars.get(p["repo"])
        star = f" ★ {fmt_stars(s)}" if s else ""
        status = f"✅ Merged {fmt_date(p['date'])}" if p["merged"] else f"🟡 In review since {fmt_date(p['date'])}"
        lines.append(
            f"| [{p['repo']}](https://github.com/{p['repo']}){star} "
            f"| [#{p['num']} {p['title']}]({p['url']}) | {status} |"
        )
    if len(prs) > MAX_ITEMS:
        q = urllib.parse.quote(f"is:pr author:{USER} -user:{USER}")
        lines += ["", f"[See all {len(prs)} pull requests](https://github.com/pulls?q={q})"]
    return "\n".join(lines)


def main():
    q = urllib.parse.quote(f"type:pr author:{USER} -user:{USER}")
    data = get(f"https://api.github.com/search/issues?q={q}&sort=created&order=desc&per_page=100")
    items = data.get("items", [])
    stars = {}
    for repo in {x["repository_url"].split("/repos/")[1] for x in items}:
        try:
            stars[repo] = get(f"https://api.github.com/repos/{repo}").get("stargazers_count", 0)
        except Exception:
            pass
    section = build(items, stars)

    with open(README, encoding="utf-8") as f:
        text = f.read()
    if START not in text or END not in text:
        sys.exit("OSS markers missing from README")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: f"{START}\n{section}\n{END}", text, flags=re.S)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
