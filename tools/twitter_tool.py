"""
Twitter/X posting tool.

All methods return draft data for the approval queue.
Nothing is posted directly - everything goes through human review.
"""

import logging
import os

import tweepy

logger = logging.getLogger(__name__)


class TwitterTool:

    def __init__(self):
        self._client = None
        self._api = None  # v1.1 API for media upload

    def _ensure_client(self):
        """Lazy initialization of Twitter clients."""
        if self._client is not None:
            return

        consumer_key = os.environ.get("TWITTER_API_KEY", "")
        consumer_secret = os.environ.get("TWITTER_API_SECRET", "")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
        access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

        if not all([consumer_key, consumer_secret, access_token, access_secret]):
            raise RuntimeError("Twitter API credentials not configured in .env")

        # v2 client for posting
        self._client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        # v1.1 API for media uploads
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_secret,
        )
        self._api = tweepy.API(auth)

    # --- Draft methods (for approval queue) ---

    def draft_tweet(self, text: str, media_path: str | None = None) -> dict:
        """Create a draft tweet for the approval queue."""
        return {
            "action": "tweet",
            "text": text,
            "media_path": media_path,
        }

    def draft_thread(self, tweets: list[str]) -> dict:
        """Create a draft thread for the approval queue."""
        return {
            "action": "thread",
            "tweets": tweets,
        }

    def draft_reply(self, tweet_id: str, text: str) -> dict:
        """Create a draft reply for the approval queue."""
        return {
            "action": "reply",
            "tweet_id": tweet_id,
            "text": text,
        }

    # --- Execution methods (called AFTER approval) ---

    async def execute(self, action_data: dict) -> dict:
        """Execute an approved Twitter action."""
        self._ensure_client()
        action = action_data.get("action")

        if action == "tweet":
            return await self._post_tweet(action_data)
        elif action == "thread":
            return await self._post_thread(action_data)
        elif action == "reply":
            return await self._post_reply(action_data)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _post_tweet(self, data: dict) -> dict:
        """Post a single tweet."""
        text = data["text"]
        media_path = data.get("media_path")
        media_ids = None

        if media_path:
            try:
                media = self._api.media_upload(media_path)
                media_ids = [media.media_id]
            except Exception as e:
                logger.error(f"Media upload failed: {e}")
                return {"error": f"Media upload failed: {e}"}

        try:
            result = self._client.create_tweet(
                text=text,
                media_ids=media_ids,
            )
            tweet_id = result.data["id"]
            logger.info(f"Tweet posted: {tweet_id}")
            return {"tweet_id": tweet_id, "url": f"https://x.com/i/status/{tweet_id}"}
        except Exception as e:
            logger.error(f"Tweet failed: {e}")
            return {"error": str(e)}

    async def _post_thread(self, data: dict) -> dict:
        """Post a thread of tweets."""
        tweets = data["tweets"]
        tweet_ids = []
        reply_to = None

        for i, tweet_text in enumerate(tweets):
            try:
                result = self._client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=reply_to,
                )
                tweet_id = result.data["id"]
                tweet_ids.append(tweet_id)
                reply_to = tweet_id
                logger.info(f"Thread tweet {i+1}/{len(tweets)} posted: {tweet_id}")
            except Exception as e:
                logger.error(f"Thread tweet {i+1} failed: {e}")
                return {
                    "error": str(e),
                    "posted": tweet_ids,
                    "failed_at": i,
                }

        return {
            "thread_ids": tweet_ids,
            "url": f"https://x.com/i/status/{tweet_ids[0]}",
        }

    async def _post_reply(self, data: dict) -> dict:
        """Reply to a tweet."""
        try:
            result = self._client.create_tweet(
                text=data["text"],
                in_reply_to_tweet_id=data["tweet_id"],
            )
            tweet_id = result.data["id"]
            logger.info(f"Reply posted: {tweet_id}")
            return {"tweet_id": tweet_id, "url": f"https://x.com/i/status/{tweet_id}"}
        except Exception as e:
            logger.error(f"Reply failed: {e}")
            return {"error": str(e)}

    # --- Video posting ---

    async def post_video(self, text: str, video_path: str) -> dict:
        """Post a tweet with video attachment using chunked upload."""
        self._ensure_client()

        try:
            # Chunked upload for video
            media = self._api.chunked_upload(
                video_path,
                media_category="tweet_video",
                wait_for_async_finalize=True,
            )
            logger.info(f"Video uploaded: media_id={media.media_id}")

            # Post tweet with video
            result = self._client.create_tweet(
                text=text,
                media_ids=[media.media_id],
            )
            tweet_id = result.data["id"]
            logger.info(f"Video tweet posted: {tweet_id}")
            return {
                "tweet_id": tweet_id,
                "url": f"https://x.com/i/status/{tweet_id}",
                "media_id": media.media_id,
            }

        except Exception as e:
            logger.error(f"Video post failed: {e}")
            return {"error": str(e)}

    # --- Read methods (no approval needed) ---

    def get_mentions(self, count: int = 20) -> list[dict]:
        """Get recent mentions (read-only, no approval needed)."""
        self._ensure_client()
        try:
            # Get authenticated user ID
            me = self._client.get_me()
            user_id = me.data.id

            mentions = self._client.get_users_mentions(
                id=user_id,
                max_results=min(count, 100),
                tweet_fields=["created_at", "author_id", "text"],
            )
            if not mentions.data:
                return []

            return [
                {
                    "id": str(t.id),
                    "text": t.text,
                    "author_id": str(t.author_id),
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                }
                for t in mentions.data
            ]
        except Exception as e:
            logger.error(f"Failed to get mentions: {e}")
            return []
