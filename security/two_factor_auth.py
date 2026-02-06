"""
Two-Factor Authentication for Telegram Bot.

Uses TOTP (Time-based One-Time Password) compatible with:
- Google Authenticator
- Authy
- Microsoft Authenticator
- Any TOTP app

Session-based: Once authenticated, stays valid for configurable duration.
"""

import io
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import pyotp
import qrcode

logger = logging.getLogger(__name__)

# Session duration in minutes (default: 60 minutes = 1 hour)
DEFAULT_SESSION_DURATION = 60


class TwoFactorAuth:
    """Manages TOTP-based two-factor authentication."""

    def __init__(self, session_duration_minutes: int = DEFAULT_SESSION_DURATION):
        """
        Initialize 2FA manager.

        Args:
            session_duration_minutes: How long an authenticated session lasts
        """
        self.session_duration = timedelta(minutes=session_duration_minutes)
        self._secret = os.environ.get("TOTP_SECRET", "")
        self._authenticated_until: Optional[datetime] = None

        if not self._secret:
            logger.warning("TOTP_SECRET not set - 2FA disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if 2FA is enabled (secret is set)."""
        return bool(self._secret)

    @property
    def is_authenticated(self) -> bool:
        """Check if current session is authenticated."""
        if not self.is_enabled:
            return True  # If 2FA not enabled, always authenticated

        if self._authenticated_until is None:
            return False

        return datetime.now() < self._authenticated_until

    @property
    def session_expires_in(self) -> Optional[timedelta]:
        """Get time remaining in current session."""
        if not self.is_authenticated or self._authenticated_until is None:
            return None
        return self._authenticated_until - datetime.now()

    def verify_code(self, code: str) -> bool:
        """
        Verify a TOTP code.

        Args:
            code: 6-digit code from authenticator app

        Returns:
            True if code is valid
        """
        if not self.is_enabled:
            return True

        try:
            totp = pyotp.TOTP(self._secret)
            # valid_window=1 allows 30 seconds before/after for clock drift
            if totp.verify(code, valid_window=1):
                self._authenticated_until = datetime.now() + self.session_duration
                logger.info(f"2FA authenticated. Session valid until {self._authenticated_until}")
                return True
            else:
                logger.warning(f"Invalid 2FA code attempt")
                return False
        except Exception as e:
            logger.error(f"2FA verification error: {e}")
            return False

    def invalidate_session(self):
        """Force end the current authenticated session."""
        self._authenticated_until = None
        logger.info("2FA session invalidated")

    def extend_session(self, minutes: int = None):
        """Extend the current session."""
        if minutes is None:
            minutes = self.session_duration.total_seconds() / 60
        self._authenticated_until = datetime.now() + timedelta(minutes=minutes)

    @staticmethod
    def generate_new_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, account_name: str = "DavidFlip",
                            issuer: str = "Clawdbot") -> str:
        """
        Get the provisioning URI for QR code.

        Args:
            secret: The TOTP secret
            account_name: Display name in authenticator app
            issuer: Issuer name shown in app
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=account_name, issuer_name=issuer)

    @staticmethod
    def generate_qr_code(secret: str, account_name: str = "DavidFlip",
                        issuer: str = "Clawdbot") -> bytes:
        """
        Generate a QR code image for the TOTP secret.

        Args:
            secret: The TOTP secret
            account_name: Display name in authenticator app
            issuer: Issuer name shown in app

        Returns:
            PNG image bytes
        """
        uri = TwoFactorAuth.get_provisioning_uri(secret, account_name, issuer)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()

    def get_status(self) -> dict:
        """Get current 2FA status."""
        return {
            "enabled": self.is_enabled,
            "authenticated": self.is_authenticated,
            "expires_in_minutes": (
                int(self.session_expires_in.total_seconds() / 60)
                if self.session_expires_in else None
            ),
            "session_duration_minutes": int(self.session_duration.total_seconds() / 60),
        }
