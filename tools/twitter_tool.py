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
        self._read_client = None  # Bearer token client for read operations
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

        # v2 client for posting (OAuth 1.0a User Context)
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

    def _ensure_read_client(self):
        """Initialize bearer token client for read operations (search, etc)."""
        if self._read_client is not None:
            return

        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN", "")
        if not bearer_token:
            raise RuntimeError("TWITTER_BEARER_TOKEN not configured in .env")

        # Bearer token client for read-only operations
        self._read_client = tweepy.Client(bearer_token=bearer_token)

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
        """
        Get recent mentions using search (workaround for API tier limits).

        The mentions endpoint requires Basic tier ($100+/month).
        Search with bearer token works on pay-per-use tier.
        """
        self._ensure_client()
        self._ensure_read_client()
        try:
            # Get our username
            me = self._client.get_me()
            username = me.data.username

            # Search for tweets mentioning us (last 7 days)
            # Use bearer token client for search
            results = self._read_client.search_recent_tweets(
                query=f"@{username} -is:retweet",
                max_results=min(count, 100),
                tweet_fields=["created_at", "author_id", "text", "conversation_id", "in_reply_to_user_id"],
                expansions=["author_id"],
                user_fields=["username", "name"],
            )

            if not results.data:
                return []

            # Build author lookup
            authors = {}
            if results.includes and "users" in results.includes:
                for user in results.includes["users"]:
                    authors[str(user.id)] = {
                        "username": user.username,
                        "name": user.name,
                    }

            mentions = []
            for t in results.data:
                author_id = str(t.author_id)
                author_info = authors.get(author_id, {})
                mentions.append({
                    "id": str(t.id),
                    "text": t.text,
                    "author_id": author_id,
                    "author_username": author_info.get("username", ""),
                    "author_name": author_info.get("name", ""),
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                    "conversation_id": str(t.conversation_id) if t.conversation_id else "",
                    "is_reply": t.in_reply_to_user_id is not None,
                })

            return mentions

        except Exception as e:
            logger.error(f"Failed to get mentions: {e}")
            return []

    def get_replies_to_tweet(self, tweet_id: str, count: int = 20) -> list[dict]:
        """Get replies to a specific tweet (for monitoring comments on David's posts)."""
        self._ensure_read_client()
        try:
            # Search for replies to a specific conversation (using bearer token)
            results = self._read_client.search_recent_tweets(
                query=f"conversation_id:{tweet_id} -is:retweet",
                max_results=min(count, 100),
                tweet_fields=["created_at", "author_id", "text", "in_reply_to_user_id"],
                expansions=["author_id"],
                user_fields=["username", "name"],
            )

            if not results.data:
                return []

            # Build author lookup
            authors = {}
            if results.includes and "users" in results.includes:
                for user in results.includes["users"]:
                    authors[str(user.id)] = {
                        "username": user.username,
                        "name": user.name,
                    }

            replies = []
            for t in results.data:
                # Skip the original tweet
                if str(t.id) == tweet_id:
                    continue

                author_id = str(t.author_id)
                author_info = authors.get(author_id, {})
                replies.append({
                    "id": str(t.id),
                    "text": t.text,
                    "author_id": author_id,
                    "author_username": author_info.get("username", ""),
                    "author_name": author_info.get("name", ""),
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                })

            return replies

        except Exception as e:
            logger.error(f"Failed to get replies: {e}")
            return []

    def get_my_recent_tweets(self, count: int = 10) -> list[dict]:
        """Get David's recent tweets (to monitor for replies)."""
        self._ensure_client()
        self._ensure_read_client()
        try:
            me = self._client.get_me()
            user_id = me.data.id

            # Use bearer token for read operations
            tweets = self._read_client.get_users_tweets(
                id=user_id,
                max_results=min(count, 100),
                tweet_fields=["created_at", "public_metrics", "conversation_id"],
            )

            if not tweets.data:
                return []

            return [
                {
                    "id": str(t.id),
                    "text": t.text,
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                    "reply_count": t.public_metrics.get("reply_count", 0) if t.public_metrics else 0,
                    "like_count": t.public_metrics.get("like_count", 0) if t.public_metrics else 0,
                    "conversation_id": str(t.conversation_id) if t.conversation_id else str(t.id),
                }
                for t in tweets.data
            ]

        except Exception as e:
            logger.error(f"Failed to get my tweets: {e}")
            return []
