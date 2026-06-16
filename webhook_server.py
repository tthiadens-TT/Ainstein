"""Flask webhook server for receiving Jamie (and future tool) callbacks.

Runs as a daemon thread alongside the Slack SocketModeHandler.
Only starts if JAMIE_WEBHOOK_SECRET is set in the environment.
"""

import json
import logging
import os
import threading

from flask import Flask, Response, request

from jamie import parse_jamie_payload, verify_jamie_signature
from models import TranscriptEvent

logger = logging.getLogger(__name__)

_processed_meetings: set[str] = set()
_meetings_lock = threading.Lock()


def _is_duplicate(meeting_id: str) -> bool:
    """Return True and register if already seen; False if new."""
    with _meetings_lock:
        if meeting_id in _processed_meetings:
            return True
        _processed_meetings.add(meeting_id)
        return False


def create_webhook_app(slack_client, anthropic_client) -> Flask:
    """Create and return the Flask app. Clients are injected to avoid circular imports."""
    from transcript_processor import process_transcript

    app = Flask(__name__)
    webhook_secret = os.environ.get("JAMIE_WEBHOOK_SECRET", "")
    transcript_channel = os.environ.get("AINSTEIN_TRANSCRIPT_CHANNEL", "")

    def _post_raw_to_slack(raw: bytes, reason: str) -> None:
        if not transcript_channel:
            logger.warning("AINSTEIN_TRANSCRIPT_CHANNEL not set — cannot post parse error")
            return
        try:
            text = raw.decode("utf-8", errors="replace")[:3000]
            slack_client.chat_postMessage(
                channel=transcript_channel,
                text=(
                    f":warning: *Jamie-webhook ontvangen maar niet verwerkt*\n"
                    f"Reden: {reason}\n\n"
                    f"```{text}```"
                ),
                mrkdwn=True,
            )
        except Exception as exc:
            logger.error("Failed to post parse error to Slack: %s", exc)

    @app.route("/webhooks/jamie", methods=["POST"])
    def jamie_webhook() -> Response:
        raw_body = request.get_data()

        # 1. HMAC verification
        if webhook_secret:
            sig_header = request.headers.get("X-Jamie-Signature", "")
            if not verify_jamie_signature(raw_body, sig_header, webhook_secret):
                logger.warning("Jamie webhook: invalid signature")
                return Response("Forbidden", status=403)

        # 2. Parse JSON
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            logger.warning("Jamie webhook: invalid JSON: %s", exc)
            _post_raw_to_slack(raw_body, f"Ongeldige JSON: {exc}")
            return Response("OK", status=200)

        # 3. Deduplication check
        meeting_id = str(body.get("id") or body.get("meetingId") or "")
        if not meeting_id:
            logger.warning("Jamie webhook: no meeting ID in payload")
            _post_raw_to_slack(raw_body, "Geen meeting ID gevonden in payload (veld 'id' of 'meetingId').")
            return Response("OK", status=200)

        if _is_duplicate(meeting_id):
            logger.info("Jamie webhook: duplicate meeting_id=%s, skipping", meeting_id)
            return Response("OK", status=200)

        # 4. Parse payload
        event: TranscriptEvent | None = parse_jamie_payload(body)
        if event is None:
            _post_raw_to_slack(
                raw_body,
                "Kon payload niet parsen. Controleer de veldnamen in jamie.py.",
            )
            return Response("OK", status=200)

        # 5. Return 200 immediately, then process in background
        t = threading.Thread(
            target=process_transcript,
            args=(event, slack_client, anthropic_client),
            daemon=True,
        )
        t.start()
        return Response("OK", status=200)

    @app.route("/health", methods=["GET"])
    def health() -> Response:
        return Response(
            json.dumps({
                "status": "ok",
                "jamie_configured": bool(webhook_secret),
                "version": "1.0",
            }),
            status=200,
            mimetype="application/json",
        )

    return app


def start_webhook_server(port: int, slack_client, anthropic_client) -> None:
    """Start the Flask server. Designed to run as a daemon thread."""
    flask_app = create_webhook_app(slack_client, anthropic_client)
    # Disable Flask's default werkzeug banner and reloader (not needed in daemon mode)
    import logging as _logging
    _logging.getLogger("werkzeug").setLevel(_logging.WARNING)
    flask_app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
