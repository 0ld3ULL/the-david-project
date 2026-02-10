"""
Git Guard - TOTP-protected git push for Claude D.

Prevents unauthorized pushes even if the laptop is compromised.
Requires TOTP code from operator's phone before any push can execute.

Flow:
1. Claude D calls request_push() with repo details
2. Git Guard sends Telegram notification with push summary
3. Operator approves with /authpush <code>
4. Push executes within 5-minute approval window
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import pyotp

logger = logging.getLogger(__name__)

# Short approval window - must push within 5 minutes of approval
PUSH_APPROVAL_WINDOW = timedelta(minutes=5)

# Pending push requests file
PENDING_PUSH_FILE = Path("data/pending_push.json")


class GitGuard:
    """Guards git push operations with TOTP verification."""

    def __init__(self, telegram_bot=None):
        """
        Initialize GitGuard.

        Args:
            telegram_bot: TelegramBot instance for sending notifications
        """
        self.telegram_bot = telegram_bot
        self._secret = os.environ.get("TOTP_SECRET", "")
        self._push_approved_until: Optional[datetime] = None
        self._pending_push: Optional[Dict] = None

        # Ensure data directory exists
        PENDING_PUSH_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not self._secret:
            logger.warning("TOTP_SECRET not set - GitGuard disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if GitGuard is enabled."""
        return bool(self._secret)

    @property
    def has_pending_push(self) -> bool:
        """Check if there's a pending push awaiting approval."""
        return self._pending_push is not None

    @property
    def is_push_approved(self) -> bool:
        """Check if push is currently approved."""
        if self._push_approved_until is None:
            return False
        return datetime.now() < self._push_approved_until

    def get_push_summary(self, repo_path: str) -> Dict:
        """
        Get a summary of what would be pushed.

        Args:
            repo_path: Path to the git repository

        Returns:
            Dict with commit info, file changes, etc.
        """
        try:
            # Get unpushed commits
            result = subprocess.run(
                ["git", "log", "@{u}..HEAD", "--oneline"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            commits = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # Get changed files summary
            result = subprocess.run(
                ["git", "diff", "--stat", "@{u}..HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            diff_stat = result.stdout.strip()

            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            branch = result.stdout.strip()

            # Get remote
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            remote_url = result.stdout.strip()
            # Extract repo name from URL
            repo_name = remote_url.split('/')[-1].replace('.git', '')

            return {
                "repo_name": repo_name,
                "branch": branch,
                "commits": commits,
                "commit_count": len(commits),
                "diff_stat": diff_stat,
                "repo_path": repo_path,
                "remote_url": remote_url
            }

        except Exception as e:
            logger.error(f"Error getting push summary: {e}")
            return {
                "repo_name": "unknown",
                "branch": "unknown",
                "commits": [],
                "commit_count": 0,
                "diff_stat": str(e),
                "repo_path": repo_path,
                "remote_url": ""
            }

    def format_push_notification(self, summary: Dict) -> str:
        """Format the push summary as a Telegram message."""
        msg = f"🔐 **Push Requested**\n\n"
        msg += f"**Repo:** {summary['repo_name']}\n"
        msg += f"**Branch:** {summary['branch']}\n"
        msg += f"**Commits:** {summary['commit_count']}\n\n"

        if summary['commits']:
            msg += "**Changes:**\n"
            for commit in summary['commits'][:5]:  # Show max 5 commits
                msg += f"  • {commit}\n"
            if len(summary['commits']) > 5:
                msg += f"  ... and {len(summary['commits']) - 5} more\n"

        msg += f"\n**Files:**\n```\n{summary['diff_stat'][:500]}\n```\n"
        msg += f"\nReply `/authpush <code>` to approve\n"
        msg += f"Or `/diffpush` to see full diff first"

        return msg

    async def request_push(self, repo_path: str, branch: str = "main") -> Tuple[bool, str]:
        """
        Request approval for a git push.

        Args:
            repo_path: Path to the git repository
            branch: Branch to push

        Returns:
            Tuple of (success, message)
        """
        if not self.is_enabled:
            # GitGuard disabled - push directly
            return await self._execute_push(repo_path, branch)

        # Get push summary
        summary = self.get_push_summary(repo_path)
        summary['branch'] = branch

        if summary['commit_count'] == 0:
            return False, "Nothing to push - no unpushed commits"

        # Store pending push
        self._pending_push = {
            "repo_path": repo_path,
            "branch": branch,
            "summary": summary,
            "requested_at": datetime.now().isoformat()
        }

        # Save to file (survives restarts)
        self._save_pending_push()

        # Send Telegram notification
        if self.telegram_bot:
            notification = self.format_push_notification(summary)
            await self.telegram_bot.send_message(notification, parse_mode="Markdown")

        return True, f"Push requested. Waiting for TOTP approval. {summary['commit_count']} commits ready."

    def verify_and_approve(self, code: str) -> Tuple[bool, str]:
        """
        Verify TOTP code and approve pending push.

        Args:
            code: 6-digit TOTP code

        Returns:
            Tuple of (success, message)
        """
        if not self.is_enabled:
            return False, "GitGuard is not enabled"

        if not self._pending_push:
            # Try to load from file
            self._load_pending_push()
            if not self._pending_push:
                return False, "No pending push request"

        try:
            totp = pyotp.TOTP(self._secret)
            if totp.verify(code, valid_window=1):
                self._push_approved_until = datetime.now() + PUSH_APPROVAL_WINDOW
                logger.info(f"Push approved until {self._push_approved_until}")
                return True, f"Push approved! Window open for 5 minutes."
            else:
                logger.warning("Invalid push approval code")
                return False, "Invalid code. Try again."
        except Exception as e:
            logger.error(f"Push approval error: {e}")
            return False, f"Error: {e}"

    async def execute_approved_push(self) -> Tuple[bool, str]:
        """
        Execute the push if approved.

        Returns:
            Tuple of (success, message)
        """
        if not self.is_push_approved:
            return False, "Push not approved or approval expired"

        if not self._pending_push:
            self._load_pending_push()
            if not self._pending_push:
                return False, "No pending push to execute"

        repo_path = self._pending_push['repo_path']
        branch = self._pending_push['branch']

        result = await self._execute_push(repo_path, branch)

        # Clear pending push
        self._pending_push = None
        self._push_approved_until = None
        self._clear_pending_push_file()

        return result

    async def _execute_push(self, repo_path: str, branch: str) -> Tuple[bool, str]:
        """Actually execute the git push."""
        try:
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for large pushes
            )

            if result.returncode == 0:
                output = result.stdout or result.stderr or "Push successful"
                logger.info(f"Push successful: {output}")
                return True, f"✅ Push successful!\n```\n{output[:500]}\n```"
            else:
                error = result.stderr or result.stdout or "Unknown error"
                logger.error(f"Push failed: {error}")
                return False, f"❌ Push failed:\n```\n{error[:500]}\n```"

        except subprocess.TimeoutExpired:
            return False, "❌ Push timed out after 2 minutes"
        except Exception as e:
            logger.error(f"Push error: {e}")
            return False, f"❌ Push error: {e}"

    def get_pending_diff(self, max_lines: int = 100) -> str:
        """Get the diff for pending push."""
        if not self._pending_push:
            self._load_pending_push()
            if not self._pending_push:
                return "No pending push"

        try:
            result = subprocess.run(
                ["git", "diff", "@{u}..HEAD"],
                cwd=self._pending_push['repo_path'],
                capture_output=True,
                text=True
            )

            diff = result.stdout
            lines = diff.split('\n')

            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f"\n\n... ({len(lines) - max_lines} more lines)"
            return diff

        except Exception as e:
            return f"Error getting diff: {e}"

    def cancel_pending_push(self) -> str:
        """Cancel the pending push request."""
        self._pending_push = None
        self._push_approved_until = None
        self._clear_pending_push_file()
        return "Pending push cancelled"

    def _save_pending_push(self):
        """Save pending push to file."""
        if self._pending_push:
            with open(PENDING_PUSH_FILE, 'w') as f:
                json.dump(self._pending_push, f)

    def _load_pending_push(self):
        """Load pending push from file."""
        if PENDING_PUSH_FILE.exists():
            try:
                with open(PENDING_PUSH_FILE, 'r') as f:
                    self._pending_push = json.load(f)
            except Exception as e:
                logger.error(f"Error loading pending push: {e}")

    def _clear_pending_push_file(self):
        """Remove pending push file."""
        if PENDING_PUSH_FILE.exists():
            PENDING_PUSH_FILE.unlink()

    def get_status(self) -> Dict:
        """Get current GitGuard status."""
        return {
            "enabled": self.is_enabled,
            "has_pending_push": self.has_pending_push,
            "is_push_approved": self.is_push_approved,
            "pending_push": self._pending_push,
            "approval_expires_in_seconds": (
                int((self._push_approved_until - datetime.now()).total_seconds())
                if self.is_push_approved and self._push_approved_until else None
            )
        }
