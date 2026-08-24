import json
from pathlib import Path

d = Path(r"C:\Users\satta\Downloads\koreanguy\traderlog\output\playwright\evidence-desk")
posts = json.load(open(d / "manas_year_posts.json", encoding="utf-8"))
replies = json.load(open(d / "manas_year_replies.json", encoding="utf-8"))
merged: dict = {}
for src in (posts, replies):
    for h, recs in src.items():
        merged.setdefault(h, {})
        for pid, rec in recs.items():
            merged[h][pid] = rec
out = d / "manas_year_combined.json"
json.dump(merged, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("combined:", {h: len(v) for h, v in merged.items()})
media_posts = sum(1 for recs in merged.values() for r in recs.values() if r.get("media_urls"))
print("posts with media:", media_posts)