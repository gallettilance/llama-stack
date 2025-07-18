# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llama_stack.distribution.admin import DistributionAdminImpl
from llama_stack.distribution.datatypes import DistributionAdminConfig
from llama_stack.distribution.server.auth_providers import OAuth2TokenAuthProvider


class TestCacheRefresh:
    """Test cache refresh functionality."""

    @pytest.fixture
    def mock_auth_provider(self):
        """Create a mock OAuth2 auth provider."""
        provider = MagicMock(spec=OAuth2TokenAuthProvider)
        provider._jwks_at = 1000.0
        provider._jwks = {"old-key": "old-value"}
        provider._refresh_jwks = AsyncMock()
        return provider

    @pytest.fixture
    def admin_impl(self, mock_auth_provider):
        """Create admin implementation with mock auth provider."""
        config = DistributionAdminConfig()
        deps = {"auth_provider": mock_auth_provider}
        return DistributionAdminImpl(config, deps)

    @pytest.mark.asyncio
    async def test_refresh_jwks_cache_success(self, admin_impl, mock_auth_provider):
        """Test successful JWKS cache refresh."""
        result = await admin_impl.refresh_jwks_cache()
        
        assert result.status == "success"
        assert "JWKS cache refreshed successfully" in result.message
        
        # Verify cache was cleared and refreshed
        assert mock_auth_provider._jwks_at == 0.0
        assert mock_auth_provider._jwks == {}
        mock_auth_provider._refresh_jwks.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_jwks_cache_no_auth_provider(self):
        """Test cache refresh when no auth provider is available."""
        config = DistributionAdminConfig()
        deps = {"auth_provider": None}
        admin_impl = DistributionAdminImpl(config, deps)
        
        result = await admin_impl.refresh_jwks_cache()
        
        assert result.status == "error"
        assert "No authentication provider available" in result.message

    @pytest.mark.asyncio
    async def test_refresh_jwks_cache_wrong_provider_type(self):
        """Test cache refresh with non-OAuth2 auth provider."""
        config = DistributionAdminConfig()
        wrong_provider = MagicMock()  # Not OAuth2TokenAuthProvider
        deps = {"auth_provider": wrong_provider}
        admin_impl = DistributionAdminImpl(config, deps)
        
        result = await admin_impl.refresh_jwks_cache()
        
        assert result.status == "error"
        assert "only available for OAuth2 token authentication" in result.message

    @pytest.mark.asyncio
    async def test_refresh_jwks_cache_refresh_error(self, admin_impl, mock_auth_provider):
        """Test cache refresh when JWKS refresh fails."""
        mock_auth_provider._refresh_jwks.side_effect = Exception("JWKS refresh failed")
        
        result = await admin_impl.refresh_jwks_cache()
        
        assert result.status == "error"
        assert "Failed to refresh JWKS cache" in result.message
        assert "JWKS refresh failed" in result.message

    @pytest.mark.asyncio
    async def test_cache_clear_behavior(self, admin_impl, mock_auth_provider):
        """Test that cache is properly cleared before refresh."""
        # Set initial cache state
        mock_auth_provider._jwks_at = 1234.0
        mock_auth_provider._jwks = {"key1": "value1", "key2": "value2"}
        
        await admin_impl.refresh_jwks_cache()
        
        # Verify cache was cleared
        assert mock_auth_provider._jwks_at == 0.0
        assert mock_auth_provider._jwks == {}
        
        # Verify refresh was called
        mock_auth_provider._refresh_jwks.assert_called_once()


class TestClientCacheRefresh:
    """Test client-side cache refresh functionality."""

    @pytest.mark.asyncio
    async def test_jwks_cache_refresher_success(self):
        """Test successful cache refresh from client."""
        from llama_stack.distribution.client_cache_refresh import JWKSCacheRefresher
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "success", "message": "Cache refreshed"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            async with JWKSCacheRefresher("http://localhost:8321", "test-token") as refresher:
                result = await refresher.refresh_server_cache()
                
                assert result["status"] == "success"
                assert result["message"] == "Cache refreshed"
                
                # Verify correct request was made
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "http://localhost:8321/v1/admin/cache/refresh"
                assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_oauth2_error_handler_detection(self):
        """Test JWKS error detection in OAuth2 error handler."""
        from llama_stack.distribution.client_cache_refresh import OAuth2ErrorHandler
        
        handler = OAuth2ErrorHandler("http://localhost:8321", "test-token")
        
        # Test JWKS error detection
        jwks_error = ValueError("Unknown key ID: abc123")
        assert await handler.handle_jwks_error(jwks_error) is True
        
        # Test non-JWKS error
        other_error = ValueError("Some other error")
        assert await handler.handle_jwks_error(other_error) is False

    @pytest.mark.asyncio
    async def test_error_handler_prevent_infinite_retry(self):
        """Test that error handler prevents infinite retry loops."""
        from llama_stack.distribution.client_cache_refresh import OAuth2ErrorHandler
        
        handler = OAuth2ErrorHandler("http://localhost:8321", "test-token")
        
        # First attempt should work
        jwks_error = ValueError("Unknown key ID: abc123")
        assert await handler.handle_jwks_error(jwks_error) is True
        
        # Second attempt should be skipped
        assert await handler.handle_jwks_error(jwks_error) is False
        
        # Reset should allow another attempt
        handler.reset_refresh_attempt()
        assert await handler.handle_jwks_error(jwks_error) is True 