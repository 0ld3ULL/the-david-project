"""Quick test for the transcript scraper components."""
import asyncio
import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_youtube_transcript():
    """Test fetching a transcript from a known video."""
    print("=" * 60)
    print("TEST 1: YouTube Transcript API")
    print("=" * 60)

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        test_video_id = "dQw4w9WgXcQ"
        print(f"Fetching transcript for video: {test_video_id}")

        api = YouTubeTranscriptApi()
        transcript = api.fetch(test_video_id, languages=["en"])

        full_text = " ".join(snippet.text for snippet in transcript)
        print(f"SUCCESS! Got {len(full_text)} chars of transcript")
        safe_text = full_text[:200].encode('ascii', 'replace').decode('ascii')
        print(f"Preview: {safe_text}...")
        print()
        return True

    except ImportError as e:
        print(f"IMPORT ERROR: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


async def test_channel_resolution():
    """Test resolving YouTube @handles using the actual scraper."""
    print("=" * 60)
    print("TEST 2: Channel Handle Resolution (via TranscriptScraper)")
    print("=" * 60)

    try:
        from agents.research_agent.scrapers.transcript_scraper import TranscriptScraper
        scraper = TranscriptScraper()

        handles_to_test = ["GodaGo", "matthew_berman"]
        all_passed = True

        for handle in handles_to_test:
            channel_id = await scraper._resolve_channel_id(handle)
            if channel_id:
                print(f"  @{handle} -> {channel_id}")
            else:
                print(f"  @{handle} -> FAILED TO RESOLVE")
                all_passed = False

        await scraper.close()
        print()
        return all_passed

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rss_feed():
    """Test fetching RSS feed for a resolved channel."""
    print("=" * 60)
    print("TEST 3: YouTube RSS Feed")
    print("=" * 60)

    try:
        from agents.research_agent.scrapers.transcript_scraper import TranscriptScraper
        scraper = TranscriptScraper()

        # Resolve a channel first
        handle = "matthew_berman"
        channel_id = await scraper._resolve_channel_id(handle)
        if not channel_id:
            print(f"Could not resolve @{handle}")
            await scraper.close()
            return False

        print(f"Resolved @{handle} -> {channel_id}")

        # Get videos via RSS
        videos = await scraper._get_channel_videos_via_rss(channel_id, handle)
        print(f"Found {len(videos)} recent videos")

        for vid_id, title, published in videos[:3]:
            safe_title = title.encode('ascii', 'replace').decode('ascii') if title else "?"
            pub_str = published.strftime('%Y-%m-%d') if published else "?"
            print(f"  - [{vid_id}] {safe_title} ({pub_str})")

        await scraper.close()
        print()
        return len(videos) > 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_scrape_single():
    """Test scraping transcript from one video found via RSS."""
    print("=" * 60)
    print("TEST 4: Full Pipeline (RSS -> Transcript)")
    print("=" * 60)

    try:
        from agents.research_agent.scrapers.transcript_scraper import TranscriptScraper
        scraper = TranscriptScraper()

        # Resolve channel
        handle = "matthew_berman"
        channel_id = await scraper._resolve_channel_id(handle)
        if not channel_id:
            print(f"Could not resolve @{handle}")
            await scraper.close()
            return False

        # Get videos
        videos = await scraper._get_channel_videos_via_rss(channel_id, handle)
        if not videos:
            print("No recent videos found")
            await scraper.close()
            return False

        # Try to get transcript for the first video
        vid_id, title, _ = videos[0]
        safe_title = title.encode('ascii', 'replace').decode('ascii') if title else "?"
        print(f"Fetching transcript for: {safe_title}")
        print(f"Video ID: {vid_id}")

        transcript = await scraper._fetch_youtube_transcript(vid_id)
        if transcript:
            print(f"SUCCESS! Got {len(transcript)} chars of transcript")
            safe_preview = transcript[:300].encode('ascii', 'replace').decode('ascii')
            print(f"Preview: {safe_preview}...")
        else:
            print("No transcript available (video may not have captions)")
            # This is OK - not all videos have transcripts
            print("(This is expected for some videos)")

        await scraper.close()
        print()
        return True  # Pass even if no transcript (API worked)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_scraper_config():
    """Test that the TranscriptScraper loads config correctly."""
    print("=" * 60)
    print("TEST 5: TranscriptScraper Config")
    print("=" * 60)

    try:
        from agents.research_agent.scrapers.transcript_scraper import TranscriptScraper
        scraper = TranscriptScraper()
        print(f"Name: {scraper.name}")
        channels = scraper.config.get('youtube_channels', [])
        print(f"YouTube channels: {len(channels)}")
        for ch in channels:
            print(f"  - {ch}")
        print(f"Max transcript length: {scraper.max_length}")
        print(f"Fetch delay: {scraper.delay}s")
        print(f"Supadata (TikTok): {'Enabled' if scraper.supadata_key else 'Disabled'}")
        await scraper.close()
        print()
        return len(channels) > 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\nTranscript Scraper Test Suite")
    print("=" * 60)
    print()

    results = []
    results.append(("YouTube Transcript API", await test_youtube_transcript()))
    results.append(("Channel Handle Resolution", await test_channel_resolution()))
    results.append(("YouTube RSS Feed", await test_rss_feed()))
    results.append(("Full Pipeline (RSS -> Transcript)", await test_full_scrape_single()))
    results.append(("TranscriptScraper Config", await test_scraper_config()))

    # Summary
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    all_passed = all(r[1] for r in results)
    print(f"\n{'ALL TESTS PASSED!' if all_passed else 'SOME TESTS FAILED'}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
