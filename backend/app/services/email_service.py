"""EmailService — sends transactional emails.

Dev mode (default): logs the message instead of sending, so the reset flow is
fully testable without an email provider or account. Swap the body of
`send_password_reset` for a real provider (Resend/Mailgun/SES) in production.
"""

from __future__ import annotations

from app.utils.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    def send_password_reset(self, email: str, reset_link: str) -> None:
        # DEV: print the link to the server log. In prod, call an email API here.
        logger.info("[DEV EMAIL] Password reset for %s -> %s", email, reset_link)
