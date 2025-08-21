"""
Lightweight GA4 Measurement Protocol sender with safe fallbacks.

Use:
    send_event_async(app, 'login_success', { 'method': 'spotify' }, user_id='123')
"""

import logging
import os
import threading
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def _get_ga4_config(app) -> Optional[Dict[str, Any]]:
    try:
        measurement_id = app.config.get("GA4_MEASUREMENT_ID") or os.getenv("GA4_MEASUREMENT_ID")
        api_secret = app.config.get("GA4_API_SECRET") or os.getenv("GA4_API_SECRET")
        if not measurement_id or not api_secret:
            return None
        return {"measurement_id": measurement_id, "api_secret": api_secret}
    except Exception:
        return None


def send_event(
    app,
    name: str,
    params: Dict[str, Any],
    *,
    user_id: Optional[str] = None,
    client_id: Optional[str] = None,
) -> None:
    cfg = _get_ga4_config(app)
    if not cfg:
        return

    try:
        payload: Dict[str, Any] = {"events": [{"name": name, "params": params or {}}]}

        # One of client_id or user_id is required
        if user_id:
            payload["user_id"] = str(user_id)
        if client_id:
            payload["client_id"] = str(client_id)
        if ("client_id" not in payload) and ("user_id" not in payload):
            # Fallback: anonymous synthetic client id
            payload["client_id"] = "server." + os.urandom(6).hex()

        endpoint = f"https://www.google-analytics.com/mp/collect?measurement_id={cfg['measurement_id']}&api_secret={cfg['api_secret']}"
        # Short timeout, best effort, no raise
        requests.post(endpoint, json=payload, timeout=2)
    except Exception as e:
        # Never break app flow
        logger.debug(f"GA4 send_event error (ignored): {e}")


def send_event_async(
    app,
    name: str,
    params: Dict[str, Any],
    *,
    user_id: Optional[str] = None,
    client_id: Optional[str] = None,
) -> None:
    try:
        app_obj = app._get_current_object()
        threading.Thread(
            target=send_event,
            args=(app_obj, name, params),
            kwargs={"user_id": user_id, "client_id": client_id},
            daemon=True,
        ).start()
    except Exception:
        # Synchronous fallback if threading fails
        send_event(app, name, params, user_id=user_id, client_id=client_id)
