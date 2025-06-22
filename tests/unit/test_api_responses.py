"""
Unit tests for standardized API response utilities.

This module tests the API response functions in app.utils.api_responses,
ensuring consistent error response formatting and proper metadata inclusion.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from flask import Flask, request, jsonify

from app.utils.api_responses import (
    success_response,
    error_response,
    validation_error,
    not_found_error,
    unauthorized_error,
    forbidden_error,
    rate_limit_error,
    server_error,
    external_service_error,
    timeout_error,
    conflict_error,
    create_success_response,
    create_error_response,
    create_paginated_response,
    format_song_for_ui,
    format_analysis_status
)


class TestSuccessResponse:
    """Test success response generation."""
    
    def test_basic_success_response(self, app):
        """Test basic success response structure."""
        with app.app_context():
            response, status_code = success_response(
                data={"user_id": 123},
                message="User created successfully"
            )
            
            assert status_code == 200
            
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert data["message"] == "User created successfully"
            assert data["data"] == {"user_id": 123}
            assert "timestamp" in data
            assert datetime.fromisoformat(data["timestamp"])
    
    def test_success_response_with_meta(self, app):
        """Test success response with metadata."""
        with app.app_context():
            meta = {"total": 50, "page": 1, "per_page": 10}
            response, status_code = success_response(
                data={"users": []},
                meta=meta
            )
            
            data = json.loads(response.data)
            assert data["meta"] == meta
    
    def test_success_response_custom_status_code(self, app):
        """Test success response with custom status code."""
        with app.app_context():
            response, status_code = success_response(
                data={"id": 123},
                message="Resource created",
                status_code=201
            )
            
            assert status_code == 201


class TestErrorResponse:
    """Test error response generation."""
    
    def test_basic_error_response(self, app):
        """Test basic error response structure."""
        with app.app_context():
            response, status_code = error_response(
                400,
                "Invalid input provided",
                "ValidationError"
            )
            
            assert status_code == 400
            
            data = json.loads(response.data)
            assert data["status"] == "error"
            assert data["error"]["code"] == 400
            assert data["error"]["type"] == "ValidationError"
            assert data["error"]["message"] == "Invalid input provided"
            assert "id" in data["error"]
            assert "request_id" in data["error"]
            assert "timestamp" in data["error"]
    
    def test_error_response_with_details_in_debug(self, app):
        """Test error response includes details in debug mode."""
        app.config["DEBUG"] = True
        
        with app.app_context():
            details = {"field": "email", "reason": "invalid format"}
            response, status_code = error_response(
                400,
                "Validation failed",
                details=details
            )
            
            data = json.loads(response.data)
            assert data["error"]["details"] == details
    
    def test_error_response_no_details_in_production(self, app):
        """Test error response excludes details in production mode."""
        # Save original config values
        original_debug = app.config.get("DEBUG")
        original_testing = app.config.get("TESTING")
        
        try:
            # Set production mode configuration
            app.config["DEBUG"] = False
            app.config["TESTING"] = False
            
            with app.app_context():
                details = {"internal": "error details"}
                response, status_code = error_response(
                    500,
                    "Internal error",
                    details=details
                )
                
                data = json.loads(response.data)
                assert "details" not in data["error"]
        finally:
            # Restore original configuration
            app.config["DEBUG"] = original_debug
            app.config["TESTING"] = original_testing
    
    def test_error_response_with_custom_ids(self, app):
        """Test error response with custom error and request IDs."""
        with app.app_context():
            error_id = str(uuid.uuid4())
            request_id = str(uuid.uuid4())
            
            response, status_code = error_response(
                404,
                "Not found",
                error_id=error_id,
                request_id=request_id
            )
            
            data = json.loads(response.data)
            assert data["error"]["id"] == error_id
            assert data["error"]["request_id"] == request_id


class TestValidationError:
    """Test validation error responses."""
    
    def test_validation_error_with_string_errors(self, app):
        """Test validation error with string error message."""
        with app.app_context():
            response, status_code = validation_error(
                "Email is required",
                field="email"
            )
            
            assert status_code == 400
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "ValidationError"
            assert data["error"]["details"]["validation_errors"] == "Email is required"
            assert data["error"]["details"]["field"] == "email"
    
    def test_validation_error_with_dict_errors(self, app):
        """Test validation error with dictionary of errors."""
        with app.app_context():
            errors = {
                "email": ["Email is required", "Email format is invalid"],
                "password": ["Password is too short"]
            }
            
            response, status_code = validation_error(errors)
            
            data = json.loads(response.data)
            assert data["error"]["details"]["validation_errors"] == errors
    
    def test_validation_error_with_list_errors(self, app):
        """Test validation error with list of errors."""
        with app.app_context():
            errors = ["Field A is invalid", "Field B is missing"]
            
            response, status_code = validation_error(errors)
            
            data = json.loads(response.data)
            assert data["error"]["details"]["validation_errors"] == errors


class TestNotFoundError:
    """Test not found error responses."""
    
    def test_not_found_error_basic(self, app):
        """Test basic not found error."""
        with app.app_context():
            response, status_code = not_found_error("User", 123)
            
            assert status_code == 404
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "ResourceNotFound"
            assert "User with ID '123' not found" in data["error"]["message"]
            assert data["error"]["details"]["resource_type"] == "User"
            assert data["error"]["details"]["resource_id"] == "123"
    
    def test_not_found_error_custom_message(self, app):
        """Test not found error with custom message."""
        with app.app_context():
            custom_message = "The playlist you're looking for doesn't exist"
            response, status_code = not_found_error(
                "Playlist", 
                "abc123", 
                message=custom_message
            )
            
            data = json.loads(response.data)
            assert data["error"]["message"] == custom_message


class TestUnauthorizedError:
    """Test unauthorized error responses."""
    
    def test_unauthorized_error_default(self, app):
        """Test default unauthorized error."""
        with app.app_context():
            response, status_code = unauthorized_error()
            
            assert status_code == 401
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "AuthenticationError"
            assert "Authentication required" in data["error"]["message"]
            assert data["error"]["details"]["auth_type"] == "bearer"
    
    def test_unauthorized_error_custom(self, app):
        """Test unauthorized error with custom message and auth type."""
        with app.app_context():
            response, status_code = unauthorized_error(
                message="Valid API key required",
                auth_type="api_key"
            )
            
            data = json.loads(response.data)
            assert data["error"]["message"] == "Valid API key required"
            assert data["error"]["details"]["auth_type"] == "api_key"


class TestForbiddenError:
    """Test forbidden error responses."""
    
    def test_forbidden_error_default(self, app):
        """Test default forbidden error."""
        with app.app_context():
            response, status_code = forbidden_error()
            
            assert status_code == 403
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "AuthorizationError"
            assert "Access denied" in data["error"]["message"]
    
    def test_forbidden_error_with_permission(self, app):
        """Test forbidden error with required permission."""
        with app.app_context():
            response, status_code = forbidden_error(
                message="Admin access required",
                required_permission="admin.read"
            )
            
            data = json.loads(response.data)
            assert data["error"]["message"] == "Admin access required"
            assert data["error"]["details"]["required_permission"] == "admin.read"


class TestRateLimitError:
    """Test rate limit error responses."""
    
    def test_rate_limit_error_basic(self, app):
        """Test basic rate limit error."""
        with app.app_context():
            response, status_code = rate_limit_error()
            
            assert status_code == 429
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "RateLimitError"
            assert "Rate limit exceeded" in data["error"]["message"]
    
    def test_rate_limit_error_with_details(self, app):
        """Test rate limit error with retry and limit details."""
        with app.app_context():
            response, status_code = rate_limit_error(
                message="Too many API calls",
                retry_after=60,
                limit=100,
                remaining=0
            )
            
            data = json.loads(response.data)
            assert data["error"]["message"] == "Too many API calls"
            assert data["error"]["details"]["retry_after"] == 60
            assert data["error"]["details"]["limit"] == 100
            assert data["error"]["details"]["remaining"] == 0


class TestServerError:
    """Test server error responses."""
    
    def test_server_error_basic(self, app):
        """Test basic server error."""
        with app.app_context():
            exception = ValueError("Something went wrong")
            
            with patch('app.utils.api_responses.logger') as mock_logger:
                response, status_code = server_error(exception)
            
            assert status_code == 500
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "ServerError"
            assert "An unexpected error occurred" in data["error"]["message"]
            assert "id" in data["error"]
            
            # Verify logging occurred
            mock_logger.error.assert_called_once()
    
    def test_server_error_with_traceback_in_debug(self, app):
        """Test server error includes traceback in debug mode."""
        app.config["DEBUG"] = True
        
        with app.app_context():
            exception = ValueError("Debug error")
            
            with patch('app.utils.api_responses.logger'):
                response, status_code = server_error(
                    exception, 
                    include_traceback=True
                )
            
            data = json.loads(response.data)
            assert "details" in data["error"]
            assert data["error"]["details"]["exception_type"] == "ValueError"
            assert data["error"]["details"]["exception_message"] == "Debug error"
            assert "traceback" in data["error"]["details"]
    
    def test_server_error_no_traceback_in_production(self, app):
        """Test server error excludes traceback in production."""
        app.config["DEBUG"] = False
        app.config["TESTING"] = False
        
        with app.app_context():
            exception = ValueError("Production error")
            
            with patch('app.utils.api_responses.logger'):
                response, status_code = server_error(exception)
            
            data = json.loads(response.data)
            assert "details" not in data["error"]


class TestExternalServiceError:
    """Test external service error responses."""
    
    def test_external_service_error_basic(self, app):
        """Test basic external service error."""
        with app.app_context():
            response, status_code = external_service_error("Spotify")
            
            assert status_code == 502
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "ExternalServiceError"
            assert "Error communicating with Spotify" in data["error"]["message"]
            assert data["error"]["details"]["service_name"] == "Spotify"
            assert data["error"]["details"]["retry_possible"] is True
    
    def test_external_service_error_no_retry(self, app):
        """Test external service error with retry not recommended."""
        with app.app_context():
            response, status_code = external_service_error(
                "Payment API",
                error_details="Invalid payment method",
                status_code=400,
                retry_possible=False
            )
            
            data = json.loads(response.data)
            assert "(retry not recommended)" in data["error"]["message"]
            assert data["error"]["details"]["retry_possible"] is False
            assert data["error"]["details"]["error_details"] == "Invalid payment method"


class TestTimeoutError:
    """Test timeout error responses."""
    
    def test_timeout_error_basic(self, app):
        """Test basic timeout error."""
        with app.app_context():
            response, status_code = timeout_error("database query", 30.0)
            
            assert status_code == 408
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "TimeoutError"
            assert "database query" in data["error"]["message"]
            assert "30.0s" in data["error"]["message"]
            assert data["error"]["details"]["operation"] == "database query"
            assert data["error"]["details"]["timeout_duration"] == 30.0
    
    def test_timeout_error_custom_message(self, app):
        """Test timeout error with custom message."""
        with app.app_context():
            response, status_code = timeout_error(
                "API call",
                15.0,
                message="The request took too long to complete"
            )
            
            data = json.loads(response.data)
            assert data["error"]["message"] == "The request took too long to complete"


class TestConflictError:
    """Test conflict error responses."""
    
    def test_conflict_error_basic(self, app):
        """Test basic conflict error."""
        with app.app_context():
            response, status_code = conflict_error()
            
            assert status_code == 409
            
            data = json.loads(response.data)
            assert data["error"]["type"] == "ConflictError"
            assert "Resource conflict" in data["error"]["message"]
    
    def test_conflict_error_with_details(self, app):
        """Test conflict error with conflict details."""
        with app.app_context():
            response, status_code = conflict_error(
                message="Username already exists",
                conflicting_resource="user:john_doe",
                conflict_reason="duplicate username"
            )
            
            data = json.loads(response.data)
            assert data["error"]["message"] == "Username already exists"
            assert data["error"]["details"]["conflicting_resource"] == "user:john_doe"
            assert data["error"]["details"]["conflict_reason"] == "duplicate username"


class TestResponseConsistency:
    """Test consistency across different error response types."""
    
    def test_all_error_responses_have_required_fields(self, app):
        """Test that all error responses have consistent required fields."""
        with app.app_context():
            error_functions = [
                lambda: validation_error("test"),
                lambda: not_found_error("Test", 123),
                lambda: unauthorized_error(),
                lambda: forbidden_error(),
                lambda: rate_limit_error(),
                lambda: server_error(Exception("test")),
                lambda: external_service_error("Test"),
                lambda: timeout_error("test", 10.0),
                lambda: conflict_error(),
            ]
            
            for error_func in error_functions:
                with patch('app.utils.api_responses.logger'):
                    response, status_code = error_func()
                
                data = json.loads(response.data)
                
                # Check top-level structure
                assert data["status"] == "error"
                assert "error" in data
                
                # Check error object structure
                error = data["error"]
                assert "code" in error
                assert "type" in error
                assert "message" in error
                assert "id" in error
                assert "request_id" in error
                assert "timestamp" in error
                
                # Verify types
                assert isinstance(error["code"], int)
                assert isinstance(error["type"], str)
                assert isinstance(error["message"], str)
                assert isinstance(error["id"], str)
                assert isinstance(error["request_id"], str)
                assert isinstance(error["timestamp"], str)
                
                # Verify timestamp format
                datetime.fromisoformat(error["timestamp"])
    
    def test_error_ids_are_unique(self, app):
        """Test that error IDs are unique across multiple calls."""
        with app.app_context():
            with patch('app.utils.api_responses.logger'):
                response1, _ = server_error(Exception("test1"))
                response2, _ = server_error(Exception("test2"))
            
            data1 = json.loads(response1.data)
            data2 = json.loads(response2.data)
            
            assert data1["error"]["id"] != data2["error"]["id"]
    
    def test_request_context_integration(self, app):
        """Test error responses include request context when available."""
        with app.test_request_context('/api/test', method='POST'):
            with patch('app.utils.api_responses.logger'):
                response, status_code = server_error(Exception("test"))
            
            # The error should be generated successfully even with request context
            assert status_code == 500
            data = json.loads(response.data)
            assert "error" in data


class TestApiResponses:
    """Test API response utilities."""
    
    def test_create_success_response(self):
        """Test success response creation."""
        data = {'test': 'value'}
        response = create_success_response(data, 'Success message')
        
        assert response['success'] is True
        assert response['message'] == 'Success message'
        assert response['data'] == data
    
    def test_create_error_response(self):
        """Test error response creation."""
        response = create_error_response('Error message', 400)
        
        assert response['success'] is False
        assert response['message'] == 'Error message'
        assert response['status_code'] == 400
    
    def test_create_paginated_response(self):
        """Test paginated response creation."""
        items = [{'id': 1}, {'id': 2}]
        response = create_paginated_response(items, 1, 2, 10)
        
        assert response['success'] is True
        assert response['data'] == items
        assert response['pagination']['page'] == 1
        assert response['pagination']['per_page'] == 2
        assert response['pagination']['total'] == 10

    def test_format_song_for_ui_with_analysis_status(self):
        """Test song formatting with enhanced analysis status indicators."""
        from app.models.models import Song, AnalysisResult
        from datetime import datetime, timezone
        
        # Create mock song
        song = Mock(spec=Song)
        song.id = 1
        song.title = 'Test Song'
        song.artist = 'Test Artist'
        song.album = 'Test Album'
        song.duration_ms = 180000
        song.explicit = False
        song.spotify_id = 'test_spotify_id'
        
        # Create mock analysis with 'completed' status
        analysis = Mock(spec=AnalysisResult)
        analysis.status = 'completed'
        analysis.score = 85
        analysis.concern_level = 'low'
        analysis.created_at = datetime.now(timezone.utc)
        
        song.analysis_results = [analysis]
        
        result = format_song_for_ui(song)
        
        # Verify basic song data
        assert result['id'] == 1
        assert result['title'] == 'Test Song'
        assert result['artist'] == 'Test Artist'
        
        # Verify enhanced analysis status
        assert result['analysis_status'] == 'completed'
        assert result['analysis_score'] == 85
        assert result['concern_level'] == 'low'
        assert result['can_reanalyze'] is True
        assert 'analysis_date' in result

    def test_format_song_for_ui_pending_analysis(self):
        """Test song formatting with pending analysis status."""
        from app.models.models import Song, AnalysisResult
        
        # Create mock song with pending analysis
        song = Mock(spec=Song)
        song.id = 2
        song.title = 'Pending Song'
        song.artist = 'Test Artist'
        song.album = 'Test Album'
        song.duration_ms = 200000
        song.explicit = False
        song.spotify_id = 'test_spotify_id_2'
        
        # Mock pending analysis
        analysis = Mock(spec=AnalysisResult)
        analysis.status = 'pending'
        analysis.score = None
        analysis.concern_level = None
        analysis.created_at = datetime.now(timezone.utc)
        
        song.analysis_results = [analysis]
        
        result = format_song_for_ui(song)
        
        # Verify pending status indicators
        assert result['analysis_status'] == 'pending'
        assert result['analysis_score'] is None
        assert result['concern_level'] is None
        assert result['can_reanalyze'] is False  # Can't reanalyze while pending
        assert result['status_display'] == 'Analysis pending...'

    def test_format_song_for_ui_no_analysis(self):
        """Test song formatting with no analysis."""
        from app.models.models import Song
        
        # Create mock song with no analysis
        song = Mock(spec=Song)
        song.id = 3
        song.title = 'Unanalyzed Song'
        song.artist = 'Test Artist'
        song.album = 'Test Album'
        song.duration_ms = 150000
        song.explicit = True
        song.spotify_id = 'test_spotify_id_3'
        song.analysis_results = []
        
        result = format_song_for_ui(song)
        
        # Verify no analysis indicators
        assert result['analysis_status'] == 'not_analyzed'
        assert result['analysis_score'] is None
        assert result['concern_level'] is None
        assert result['can_reanalyze'] is True  # Can start analysis
        assert result['status_display'] == 'Not analyzed'

    def test_format_analysis_status_utility(self):
        """Test the analysis status formatting utility function."""
        from app.models.models import AnalysisResult
        
        # Test completed analysis
        analysis = Mock(spec=AnalysisResult)
        analysis.status = 'completed'
        analysis.score = 92
        analysis.concern_level = 'low'
        
        status = format_analysis_status(analysis)
        assert status['status'] == 'completed'
        assert status['display'] == '✅ Completed (Score: 92)'
        assert status['badge_class'] == 'badge-success'
        
        # Test pending analysis
        analysis.status = 'pending'
        analysis.score = None
        
        status = format_analysis_status(analysis)
        assert status['status'] == 'pending'
        assert status['display'] == '⏳ Analysis pending...'
        assert status['badge_class'] == 'badge-warning'
        
        # Test failed analysis
        analysis.status = 'failed'
        analysis.score = None
        
        status = format_analysis_status(analysis)
        assert status['status'] == 'failed'
        assert status['display'] == '❌ Analysis failed'
        assert status['badge_class'] == 'badge-danger'

    def test_format_analysis_status_no_analysis(self):
        """Test analysis status formatting when no analysis exists."""
        status = format_analysis_status(None)
        assert status['status'] == 'not_analyzed'
        assert status['display'] == '⚪ Not analyzed'
        assert status['badge_class'] == 'badge-secondary'
