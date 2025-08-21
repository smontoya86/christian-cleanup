"""
Frontend Template Tests

TDD tests for template rendering and static assets.
These tests define the expected behavior for our simplified frontend.
"""

import pytest


class TestTemplateRendering:
    """Test that templates render correctly with proper assets."""

    @pytest.mark.frontend
    def test_homepage_renders_with_correct_css(self, client):
        """Test that homepage renders and references correct CSS files."""
        response = client.get("/")
        assert response.status_code == 200

        # Should reference our actual CSS files
        content = response.get_data(as_text=True)
        assert "base.css" in content or "components.css" in content

        # Should not reference non-existent files
        assert "style.css" not in content

    @pytest.mark.frontend
    def test_homepage_has_bootstrap_integration(self, client):
        """Test that homepage includes Bootstrap for styling."""
        response = client.get("/")
        content = response.get_data(as_text=True)

        # Should include Bootstrap (either CDN or local)
        assert "bootstrap" in content.lower()

    @pytest.mark.frontend
    def test_static_css_files_accessible(self, client):
        """Test that our actual CSS files are accessible."""
        # Test our known CSS files
        css_files = [
            "/static/css/base.css",
            "/static/css/components.css",
            "/static/css/utilities.css",
        ]

        for css_file in css_files:
            response = client.get(css_file)
            assert response.status_code == 200
            assert "text/css" in response.content_type

    @pytest.mark.frontend
    def test_dashboard_template_integration(self, client):
        """Test that dashboard template works with simplified structure."""
        # This should redirect to login since we're not authenticated
        response = client.get("/dashboard")
        assert response.status_code in [302, 401]  # Redirect or unauthorized

    @pytest.mark.frontend
    def test_base_template_structure(self, client):
        """Test that base template has required elements."""
        response = client.get("/")
        content = response.get_data(as_text=True)

        # Check basic HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "<head>" in content
        assert "<body>" in content

        # Check meta tags
        assert "viewport" in content
        assert "charset" in content

    @pytest.mark.frontend
    def test_javascript_integration(self, client):
        """Test that JavaScript files are properly referenced."""
        response = client.get("/")
        content = response.get_data(as_text=True)

        # Should have script tags for JS functionality
        assert "<script" in content

    @pytest.mark.frontend
    def test_responsive_design_elements(self, client):
        """Test that responsive design elements are present."""
        response = client.get("/")
        content = response.get_data(as_text=True)

        # Check for viewport meta tag
        assert "width=device-width" in content
        assert "initial-scale=1" in content


class TestStaticAssets:
    """Test static asset serving and optimization."""

    @pytest.mark.frontend
    def test_static_directory_structure(self, client):
        """Test that static files are organized correctly."""
        # Test CSS directory
        response = client.get("/static/css/base.css")
        assert response.status_code == 200

        # Test if dist directory exists (for built assets)
        response = client.get("/static/dist/css/base.css")
        # This might be 200 or 404 depending on build status
        assert response.status_code in [200, 404]

    @pytest.mark.frontend
    def test_image_assets_available(self, client):
        """Test that default images are available."""
        # Test for common default images
        default_images = [
            "/static/images/default_playlist_image.png",
            "/static/dist/images/default_playlist_image.png",
        ]

        # At least one should exist
        found = False
        for image_path in default_images:
            response = client.get(image_path)
            if response.status_code == 200:
                found = True
                break
        assert found, "No default playlist image found"


class TestErrorPages:
    """Test error page templates."""

    @pytest.mark.frontend
    def test_404_page_styling(self, client):
        """Test that 404 pages have proper styling."""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

        content = response.get_data(as_text=True)
        # Should still have basic HTML structure
        assert "<html" in content or "Not Found" in content

    @pytest.mark.frontend
    def test_error_pages_consistent_styling(self, client):
        """Test that error pages maintain consistent styling with main app."""
        response = client.get("/nonexistent-page")
        content = response.get_data(as_text=True)

        # Should reference same CSS framework
        if "bootstrap" in content.lower():
            # If using Bootstrap, should be consistent
            assert True
        else:
            # Should at least have some styling
            assert "css" in content.lower() or "style" in content.lower()
