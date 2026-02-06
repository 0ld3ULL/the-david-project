"""
YouTube video upload tool.

Uses YouTube Data API v3 for uploading videos as Shorts or regular videos.
Requires OAuth2 credentials (client_secrets.json) and token storage.
"""

import logging
import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Data directory for token storage
DATA_DIR = Path(os.environ.get("CLAWDBOT_DATA_DIR", "data"))


class YouTubeTool:
    """YouTube video upload tool."""

    def __init__(self):
        self._youtube = None
        self._credentials_path = DATA_DIR / "youtube_credentials.json"
        self._token_path = DATA_DIR / "youtube_token.pickle"

    def _ensure_client(self):
        """Initialize YouTube API client with OAuth2."""
        if self._youtube is not None:
            return

        creds = None

        # Load existing token
        if self._token_path.exists():
            with open(self._token_path, "rb") as token:
                creds = pickle.load(token)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Check for client secrets file
                client_secrets = os.environ.get(
                    "YOUTUBE_CLIENT_SECRETS",
                    str(DATA_DIR / "client_secrets.json")
                )
                if not Path(client_secrets).exists():
                    raise RuntimeError(
                        f"YouTube client secrets not found at {client_secrets}. "
                        "Download from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._token_path, "wb") as token:
                pickle.dump(creds, token)

        self._youtube = build("youtube", "v3", credentials=creds)

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category_id: str = "22",  # People & Blogs
        privacy_status: str = "public",
        is_short: bool = True,
    ) -> dict:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category (22 = People & Blogs)
            privacy_status: public, private, or unlisted
            is_short: If True, adds #Shorts to title/description

        Returns:
            dict with video_id, url, etc.
        """
        self._ensure_client()

        if not Path(video_path).exists():
            return {"error": f"Video file not found: {video_path}"}

        # Format for YouTube Shorts
        if is_short:
            if "#Shorts" not in title:
                title = f"{title} #Shorts"
            if "#Shorts" not in description:
                description = f"{description}\n\n#Shorts"
            if tags is None:
                tags = []
            if "Shorts" not in tags:
                tags.append("Shorts")

        # Default tags for David Flip content
        default_tags = [
            "FLIPT", "decentralization", "crypto", "freedom",
            "permissionless", "Web3", "AI"
        ]
        if tags:
            tags = list(set(tags + default_tags))
        else:
            tags = default_tags

        body = {
            "snippet": {
                "title": title[:100],  # YouTube title limit
                "description": description[:5000],  # Description limit
                "tags": tags[:500],  # Tag limit
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
        )

        try:
            request = self._youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")

            video_id = response["id"]
            logger.info(f"Video uploaded: {video_id}")

            return {
                "video_id": video_id,
                "url": f"https://youtube.com/watch?v={video_id}",
                "shorts_url": f"https://youtube.com/shorts/{video_id}" if is_short else None,
                "title": title,
            }

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return {"error": str(e)}

    async def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
    ) -> dict:
        """Convenience method for uploading Shorts."""
        return await self.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            is_short=True,
        )

    def get_channel_info(self) -> dict:
        """Get info about the authenticated channel."""
        self._ensure_client()

        try:
            request = self._youtube.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()

            if not response.get("items"):
                return {"error": "No channel found"}

            channel = response["items"][0]
            return {
                "channel_id": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"].get("description", ""),
                "subscriber_count": channel["statistics"].get("subscriberCount", "0"),
                "video_count": channel["statistics"].get("videoCount", "0"),
                "view_count": channel["statistics"].get("viewCount", "0"),
            }

        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return {"error": str(e)}
