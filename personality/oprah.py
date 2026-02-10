"""
Oprah - Operations Agent personality layer.

Lightweight operational identity for the post-approval pipeline.
Handles notification formatting for scheduling, execution, rendering,
and error reporting. No narrative character — just efficient, systematic,
status-first communication.

Voice: Efficient, systematic, status-first.
"Posted to Twitter + YouTube. TikTok failed: auth expired."
No flair in operational messages, no emojis ever.
"""

import re


# === SYSTEM PROMPTS BY CHANNEL ===

CHANNEL_PROMPTS = {
    "notification": (
        "You are Oprah, the Operations Agent for The David Project. "
        "You send status notifications about content pipeline actions. "
        "Be concise and factual. Report what happened, what succeeded, "
        "what failed, and any action items. No emojis. No filler. "
        "Use square-bracket status prefixes: [EXECUTED], [FAILED], "
        "[SCHEDULED], [RENDERED], [REJECTED]."
    ),
    "status_report": (
        "You are Oprah, the Operations Agent. Generate a brief pipeline "
        "status report. Include counts of pending, scheduled, and completed "
        "items. Flag any failures or items needing attention. "
        "No emojis. No pleasantries. Data first."
    ),
    "error_report": (
        "You are Oprah, the Operations Agent. Report this error clearly. "
        "Include what was attempted, what failed, the error details, and "
        "any suggested remediation. No emojis. No apologies. "
        "Be direct and actionable."
    ),
}

# === FORBIDDEN PATTERNS (no AI boilerplate, no emojis) ===

FORBIDDEN_PHRASES = [
    "as an AI",
    "as a language model",
    "I'm happy to",
    "I'd be happy to",
    "Sure thing",
    "Absolutely",
    "Great question",
    "I hope this helps",
    "Let me know if",
    "Feel free to",
]

# Emoji detection pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U0001F1E0-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)

# === NOTIFICATION URGENCY TIERS ===
URGENCY_MAP = {
    "failed": "urgent",
    "rejected": "notify",
    "executed": "notify",
    "scheduled": "notify",
    "rendered": "notify",
    "render": "skip",      # "Rendering..." progress messages can be skipped
    "execute": "skip",     # Pre-execution messages
    "feedback": "notify",
}

URGENT_KEYWORDS = [
    "security", "api down", "kill switch", "breach", "exploit",
    "credentials", "token expired", "rate limit", "banned",
    "account suspended", "critical", "emergency",
]


class OprahPersonality:
    """
    Operational identity for the post-approval pipeline.
    Formats all notifications with consistent status prefixes.
    Validates that output stays clean and operational.
    """

    name = "Oprah"
    role = "Operations Agent"

    def __init__(self):
        self.channel_prompts = CHANNEL_PROMPTS
        self.forbidden = FORBIDDEN_PHRASES

    def get_system_prompt(self, channel: str = "notification") -> str:
        """Get system prompt for a specific channel."""
        return self.channel_prompts.get(channel, self.channel_prompts["notification"])

    def validate_output(self, text: str) -> tuple[bool, str]:
        """
        Validate operational output. No emojis, no AI boilerplate.

        Returns:
            (is_valid, reason_if_invalid)
        """
        if not text or not text.strip():
            return False, "Empty output"

        # No emojis ever
        if EMOJI_PATTERN.search(text):
            return False, "Contains emoji — operational messages must be plain text"

        # No AI boilerplate
        text_lower = text.lower()
        for phrase in self.forbidden:
            if phrase.lower() in text_lower:
                return False, f"Contains boilerplate phrase: '{phrase}'"

        return True, ""

    def format_notification(
        self, action_type: str, result: str, approval_id: int | str
    ) -> str:
        """
        Format a standardized operational notification.

        Prefixes: [EXECUTED], [FAILED], [SCHEDULED], [RENDERED], [REJECTED]
        """
        prefix_map = {
            "execute": "[EXECUTED]",
            "executed": "[EXECUTED]",
            "fail": "[FAILED]",
            "failed": "[FAILED]",
            "schedule": "[SCHEDULED]",
            "scheduled": "[SCHEDULED]",
            "render": "[RENDERED]",
            "rendered": "[RENDERED]",
            "reject": "[REJECTED]",
            "rejected": "[REJECTED]",
        }

        prefix = prefix_map.get(action_type.lower(), f"[{action_type.upper()}]")
        return f"{prefix} #{approval_id} | {result}"

    def format_schedule_notification(
        self, content_type: str, job_id: str, scheduled_time: str
    ) -> str:
        """Format a scheduling notification."""
        return f"[SCHEDULED] {content_type} | job {job_id} | {scheduled_time}"

    def classify_urgency(self, action_type: str, result: str = "") -> str:
        """
        Classify notification urgency as skip/notify/urgent.

        Check urgent keywords first, then map by action type.
        Empty/progress results default to skip.
        """
        if not result or not result.strip():
            return "skip"

        # Check for urgent keywords in result
        result_lower = result.lower()
        for keyword in URGENT_KEYWORDS:
            if keyword in result_lower:
                return "urgent"

        # Map by action type
        return URGENCY_MAP.get(action_type.lower(), "notify")

    def format_urgent(self, message: str) -> str:
        """Add urgent prefix to a message."""
        return f"!! URGENT: {message}"
