"""
Correlation ID utilities for tracing requests across logs and responses.
"""

import uuid

from flask import g, request

HEADER_NAME = "X-Request-ID"


def get_request_id() -> str:
    rid = getattr(g, "request_id", None)
    if rid:
        return rid
    rid = request.headers.get(HEADER_NAME) or str(uuid.uuid4())
    g.request_id = rid
    return rid
