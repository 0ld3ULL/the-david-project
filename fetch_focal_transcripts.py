"""
Fetch Focal ML tutorial transcripts via Supadata API.
Saves each transcript with metadata (title, channel, date) for Pixel's knowledge base.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPADATA_KEY = os.environ.get("SUPADATA_API_KEY", "sd_d826ccdab9a7a682d5716084f28d4d73")
SUPADATA_URL = "https://api.supadata.ai/v1/transcript"
OUTPUT_DIR = Path("data/pixel_transcripts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Top Focal ML tutorials — prioritized by comprehensiveness
VIDEOS = [
    # Official
    {"id": "lk_EuoqBE5I", "title": "Focal Tutorial (Official)", "channel": "Focal", "duration": "9:25", "est_date": "2025-03"},
    # Winston Wee 3-part series (~73 min total)
    {"id": "aIiK5R1F2o4", "title": "Focal ML Review Complete Tutorial Part 1", "channel": "Winston Wee", "duration": "29:11", "est_date": "2025-03"},
    {"id": "lNRSYba_nv8", "title": "Focal ML Review Complete Tutorial Part 2", "channel": "Winston Wee", "duration": "18:47", "est_date": "2025-03"},
    {"id": "XOxYkZMS_V4", "title": "Focal ML Review Complete Tutorial Part 3 (Advanced)", "channel": "Winston Wee", "duration": "25:37", "est_date": "2025-03"},
    # Comprehensive step-by-step tutorials
    {"id": "_sxuYZJ7pkQ", "title": "FOCAL AI: Create EPIC Cinematic MOVIES — Step-By-Step Tutorial", "channel": "Prompt Revolution", "duration": "12:15", "est_date": "2025-03"},
    {"id": "hcH_9cmfrLE", "title": "Create Full AI-Generated Movies with FocalML (Free Guide)", "channel": "AI Artistry Lab", "duration": "9:26", "est_date": "2025-03"},
    {"id": "A2gjoL159m8", "title": "Create Cinematic Videos With AI — FocalML Tutorial", "channel": "Tutorialboxx", "duration": "14:41", "est_date": "2025-03"},
    {"id": "qEs3B235FhA", "title": "Create Cinematic Movies with FocalML AI - Free and Easy!", "channel": "Epic AI", "duration": "15:15", "est_date": "2025-03"},
    {"id": "RZnnTjzNNKI", "title": "STOP Using Multiple AI Tools! FocalML — Minimax, Flux, Runway in One Place", "channel": "WealthWise", "duration": "11:10", "est_date": "2025-03"},
    # Specific features
    {"id": "aiu3WmTLT0A", "title": "How to Use FOCAL AI Video Generator", "channel": "More Tutorials", "duration": "5:15", "est_date": "2025-03"},
    {"id": "4-IKrWLCOiI", "title": "Create AI ANIMATION with Focal (Image to Video)", "channel": "More Tutorials", "duration": "12:34", "est_date": "2025-03"},
    {"id": "he9MymAdNBs", "title": "Best AI Tool To Generate Faceless Videos? FOCAL AI Full Guide", "channel": "Nina Scott", "duration": "8:59", "est_date": "2025-03"},
    {"id": "nIyiXJ77w-w", "title": "Focal ML — Create Cinematic Videos Like a PRO", "channel": "IdeaPlex", "duration": "8:20", "est_date": "2025-03"},
    {"id": "WteYD9wjdo0", "title": "Make AMAZING Videos with Focalml AI in Minutes", "channel": "Tech Riser", "duration": "12:15", "est_date": "2025-03"},
    {"id": "gs_HzDOAiYA", "title": "Easy AI Movie generation for everyone with FocalML", "channel": "Eigi and AI", "duration": "10:30", "est_date": "2025-03"},
    {"id": "81uX3_gjjAs", "title": "Focal Tutorial - Create Amazing Videos with Ai Software", "channel": "How to Hermione", "duration": "10:38", "est_date": "2025-03"},
    # Specific use cases
    {"id": "4wBFslxFPUY", "title": "How I Made a Hollywood-Style Movie Using Free FocalML", "channel": "Artificicy", "duration": "7:05", "est_date": "2025-03"},
    {"id": "O3uzsgVEcJI", "title": "How to Make Viral AI History Shorts - FocalML Tutorial", "channel": "Artificicy", "duration": "6:19", "est_date": "2025-03"},
    {"id": "O7gHTTyANvo", "title": "MIND-BLOWING Movies Made with JUST ONE AI Tool", "channel": "AI Upskill", "duration": "11:50", "est_date": "2025-03"},
    # Pricing / overview
    {"id": "J4u7OBhWuUA", "title": "FOCAL AI PLANS AND PRICING", "channel": "1ClickTutorialen", "duration": "1:27", "est_date": "2025-03"},
    {"id": "2BEP5Z99Kkg", "title": "AI Video Creation Workflow Explained — Focal ML Tutorial", "channel": "AiMinds", "duration": "6:07", "est_date": "2025-03"},
]


async def fetch_transcript(client: httpx.AsyncClient, video: dict) -> dict:
    """Fetch a single transcript from Supadata."""
    url = f"https://www.youtube.com/watch?v={video['id']}"
    try:
        resp = await client.get(
            SUPADATA_URL,
            params={"url": url, "text": "true"},
            headers={"x-api-key": SUPADATA_KEY},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            transcript_text = data.get("content", "") or data.get("text", "") or str(data)
            print(f"  OK  {video['id']} — {video['title'][:50]}... ({len(transcript_text)} chars)")
            return {
                "video_id": video["id"],
                "title": video["title"],
                "channel": video["channel"],
                "duration": video["duration"],
                "est_date": video["est_date"],
                "fetched_at": datetime.now().isoformat(),
                "transcript": transcript_text,
                "char_count": len(transcript_text),
            }
        else:
            print(f"  FAIL {video['id']} — HTTP {resp.status_code}: {resp.text[:100]}")
            return {
                "video_id": video["id"],
                "title": video["title"],
                "channel": video["channel"],
                "error": f"HTTP {resp.status_code}",
            }
    except Exception as e:
        print(f"  ERR  {video['id']} — {e}")
        return {
            "video_id": video["id"],
            "title": video["title"],
            "channel": video["channel"],
            "error": str(e),
        }


async def main():
    print(f"Fetching {len(VIDEOS)} Focal ML tutorial transcripts...")
    print(f"Output: {OUTPUT_DIR}\n")

    results = []
    success = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        # One at a time with delay to avoid rate limits
        for v in VIDEOS:
            # Skip if already fetched
            existing = OUTPUT_DIR / f"{v['id']}.json"
            if existing.exists():
                with open(existing, "r", encoding="utf-8") as f:
                    r = json.load(f)
                if "transcript" in r:
                    print(f"  SKIP {v['id']} — already fetched ({r.get('char_count', 0)} chars)")
                    results.append(r)
                    success += 1
                    continue

            r = await fetch_transcript(client, v)
            results.append(r)
            if "error" not in r:
                success += 1
            else:
                failed += 1
            await asyncio.sleep(2)  # 2 seconds between requests

    # Save individual transcripts
    for r in results:
        if "transcript" in r:
            filepath = OUTPUT_DIR / f"{r['video_id']}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(r, f, indent=2, ensure_ascii=False)

    # Save manifest
    manifest = {
        "fetched_at": datetime.now().isoformat(),
        "total_videos": len(VIDEOS),
        "success": success,
        "failed": failed,
        "videos": [
            {
                "id": r["video_id"],
                "title": r.get("title"),
                "channel": r.get("channel"),
                "duration": r.get("duration"),
                "est_date": r.get("est_date"),
                "chars": r.get("char_count", 0),
                "error": r.get("error"),
            }
            for r in results
        ],
    }
    with open(OUTPUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone: {success} transcripts fetched, {failed} failed")
    print(f"Saved to: {OUTPUT_DIR}")

    # Show total content
    total_chars = sum(r.get("char_count", 0) for r in results)
    print(f"Total transcript content: {total_chars:,} characters")


if __name__ == "__main__":
    asyncio.run(main())
