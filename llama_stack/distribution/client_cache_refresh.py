# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import asyncio
import logging
from typing import Any, Callable, Optional

import httpx

from llama_stack.log import get_logger

logger = get_logger(name=__name__, category="client")


class CacheRefreshError(Exception):
    """Exception raised when cache refresh operations fail."""
    pass


class JWKSCacheRefresher:
    """Client-side JWKS cache refresh handler for Llama Stack."""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        Initialize the JWKS cache refresher.
        
        Args:
            base_url: Base URL of the Llama Stack server
            auth_token: Optional authentication token for admin operations
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self._client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            
    async def refresh_server_cache(self) -> dict[str, Any]:
        """
        Refresh the server's JWKS cache.
        
        Returns:
            Response from the cache refresh endpoint
            
        Raises:
            CacheRefreshError: If the cache refresh fails
        """
        if not self._client:
            raise CacheRefreshError("Client not initialized. Use async context manager.")
            
        url = f"{self.base_url}/v1/admin/cache/refresh"
        headers = {}
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        try:
            response = await self._client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Cache refresh failed with status {e.response.status_code}: {e.response.text}")
            raise CacheRefreshError(f"Cache refresh failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Cache refresh request failed: {e}")
            raise CacheRefreshError(f"Cache refresh request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during cache refresh: {e}")
            raise CacheRefreshError(f"Unexpected error: {e}")


class OAuth2ErrorHandler:
    """OAuth2 error handler with automatic JWKS cache refresh."""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        Initialize the OAuth2 error handler.
        
        Args:
            base_url: Base URL of the Llama Stack server
            auth_token: Optional authentication token for admin operations
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self._refresh_attempted = False
        
    async def handle_jwks_error(self, error: Exception) -> bool:
        """
        Handle JWKS-related errors by attempting to refresh the server cache.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if cache refresh was successful, False otherwise
        """
        # Check if this is a JWKS-related error
        error_str = str(error).lower()
        jwks_indicators = [
            "unknown key id",
            "unknown key",
            "invalid key",
            "jwks",
            "key not found"
        ]
        
        if not any(indicator in error_str for indicator in jwks_indicators):
            return False
            
        # Prevent infinite retry loops
        if self._refresh_attempted:
            logger.warning("JWKS cache refresh already attempted, skipping")
            return False
            
        logger.info("🔄 JWKS cache error detected, refreshing server cache...")
        self._refresh_attempted = True
        
        try:
            async with JWKSCacheRefresher(self.base_url, self.auth_token) as refresher:
                result = await refresher.refresh_server_cache()
                logger.info(f"✅ Server cache refreshed: {result}")
                return True
        except CacheRefreshError as e:
            logger.warning(f"⚠️ Cache refresh failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during cache refresh: {e}")
            return False
            
    def reset_refresh_attempt(self):
        """Reset the refresh attempt flag to allow future refresh attempts."""
        self._refresh_attempted = False


def with_cache_refresh(base_url: str, auth_token: Optional[str] = None):
    """
    Decorator that automatically handles JWKS cache refresh on errors.
    
    Args:
        base_url: Base URL of the Llama Stack server
        auth_token: Optional authentication token for admin operations
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            error_handler = OAuth2ErrorHandler(base_url, auth_token)
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Try to handle JWKS errors
                if await error_handler.handle_jwks_error(e):
                    # Retry the original operation once after cache refresh
                    try:
                        return await func(*args, **kwargs)
                    except Exception as retry_error:
                        logger.error(f"Operation failed after cache refresh: {retry_error}")
                        raise retry_error
                else:
                    # Not a JWKS error or refresh failed, re-raise
                    raise e
                    
        return wrapper
    return decorator 