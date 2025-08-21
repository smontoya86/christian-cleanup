"""
Request validation utilities for API endpoints.

Provides marshmallow schemas and decorators to validate JSON bodies and
query parameters. Supports a non-breaking "log-only" mode by default,
controlled via the API_VALIDATION_ENFORCE environment variable.
"""

import logging
import os
from functools import wraps
from typing import Optional, Type

from flask import jsonify, request
from marshmallow import Schema, ValidationError, fields, validate

logger = logging.getLogger(__name__)


def _is_enforced(explicit: Optional[bool] = None) -> bool:
    if explicit is not None:
        return explicit
    return os.environ.get("API_VALIDATION_ENFORCE", "0") in ("1", "true", "True")


def validate_json(schema_cls: Type[Schema], enforce: Optional[bool] = None):
    """Decorator to validate request JSON using the given marshmallow Schema class.

    When enforce=False (default via env), validation errors are logged and the
    endpoint continues with the original handler to avoid breaking existing clients.
    When enforce=True, a 400 is returned with error details.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                payload = request.get_json(silent=True) or {}
                schema = schema_cls()
                schema.load(payload)
                return fn(*args, **kwargs)
            except ValidationError as ve:
                logger.warning("JSON validation failed: %s", ve.messages)
                if _is_enforced(enforce):
                    return jsonify(
                        {"success": False, "error": "validation_error", "details": ve.messages}
                    ), 400
                # Log-only mode: continue without blocking
                return fn(*args, **kwargs)

        return wrapper

    return decorator


def validate_query(schema_cls: Type[Schema], enforce: Optional[bool] = None):
    """Decorator to validate request.args against a marshmallow Schema class."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                params = request.args.to_dict(flat=True)
                schema = schema_cls()
                schema.load(params)
                return fn(*args, **kwargs)
            except ValidationError as ve:
                logger.warning("Query validation failed: %s", ve.messages)
                if _is_enforced(enforce):
                    return jsonify(
                        {"success": False, "error": "validation_error", "details": ve.messages}
                    ), 400
                return fn(*args, **kwargs)

        return wrapper

    return decorator


# Schemas


class WhitelistAddSchema(Schema):
    spotify_id = fields.String(required=True, validate=validate.Length(min=1, max=255))
    item_type = fields.String(
        required=True, validate=validate.OneOf(["song", "artist", "playlist"])
    )
    name = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    reason = fields.String(required=False, allow_none=True, validate=validate.Length(max=2048))


class WhitelistQuerySchema(Schema):
    item_type = fields.String(
        required=False, validate=validate.OneOf(["song", "artist", "playlist"])
    )


class GA4CompletedSchema(Schema):
    completed_songs = fields.Integer(required=True, validate=validate.Range(min=0))
    total_songs = fields.Integer(required=True, validate=validate.Range(min=0))


class TestSemanticDetectionSchema(Schema):
    title = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    artist = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    lyrics = fields.String(required=True, validate=validate.Length(min=1))
