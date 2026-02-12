"""
Comic Pipeline — AI-driven comic parable generation.

One generation run → four content formats:
1. Individual panel images (social posts / NFT)
2. Assembled comic pages (PNG)
3. Multi-page PDF (download / print)
4. Motion comic video (MP4 with narration + music)

Usage:
    from comic_pipeline import ComicParablePipeline

    pipeline = ComicParablePipeline()
    project = await pipeline.generate(
        theme="The Fisherman's Free Net — A fisherman was given a free net...",
    )
"""

from comic_pipeline.comic_generator import ComicParablePipeline
from comic_pipeline.models import ComicProject, Panel, ComicPage

__all__ = [
    "ComicParablePipeline",
    "ComicProject",
    "Panel",
    "ComicPage",
]
