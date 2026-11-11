#!/usr/bin/env python3
"""Radar snapshot: Douyin hot-search board via the Evil0ctal v4 crawler.

Usage: ./venv/bin/python radar_hot.py [top_n]
Writes a JSON snapshot to ../radar-snapshots/douyin-hot-<timestamp>.json
and prints the top topics. TikTok per-video endpoints need a fresh
user cookie (see ORCHESTRATION.md); the Douyin board works as-is.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from crawlers.douyin.web.web_crawler import DouyinWebCrawler  # noqa: E402


async def main(top_n: int) -> None:
    crawler = DouyinWebCrawler()
    result = await crawler.fetch_hot_search_result()
    word_list = result.get("data", {}).get("word_list", [])
    topics = [
        {
            "rank": i + 1,
            "word": w.get("word"),
            "hot_value": w.get("hot_value"),
            "label": w.get("label"),
        }
        for i, w in enumerate(word_list)
    ]
    out_dir = Path(__file__).parent.parent / "radar-snapshots"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"douyin-hot-{stamp}.json"
    path.write_text(
        json.dumps(
            {"source": "douyin_hot_search", "fetched_at": stamp, "topics": topics},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"snapshot: {path} ({len(topics)} topics)")
    for t in topics[:top_n]:
        print(f"{t['rank']:>2}. {t['word']}  (hot {t['hot_value']})")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 15))
