# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Any

from llama_stack.apis.admin.admin import Admin, CacheRefreshResponse
from llama_stack.distribution.datatypes import DistributionAdminConfig
from llama_stack.distribution.server.auth_providers import OAuth2TokenAuthProvider
from llama_stack.log import get_logger

logger = get_logger(name=__name__, category="admin")


class DistributionAdminImpl(Admin):
    """Implementation of the Admin API for Llama Stack distributions."""

    def __init__(self, config: DistributionAdminConfig, deps: dict[str, Any]):
        self.config = config
        self.deps = deps
        # Get the auth provider from dependencies if available
        self.auth_provider = deps.get("auth_provider")

    async def initialize(self) -> None:
        """Initialize the admin implementation."""
        pass

    async def refresh_jwks_cache(self) -> CacheRefreshResponse:
        """Refresh the JWKS cache from the auth server.
        
        This method clears the current JWKS cache and fetches fresh keys
        from the authentication server. This is useful when the auth server
        rotates cryptographic keys and the cached keys become stale.
        
        Returns:
            CacheRefreshResponse: Success or error status with message
        """
        try:
            if not self.auth_provider:
                return CacheRefreshResponse(
                    status="error",
                    message="No authentication provider available for cache refresh"
                )
            
            if not isinstance(self.auth_provider, OAuth2TokenAuthProvider):
                return CacheRefreshResponse(
                    status="error", 
                    message="Cache refresh only available for OAuth2 token authentication"
                )
            
            # Clear the current JWKS cache by resetting the timestamp
            # This will force a refresh on the next token validation
            self.auth_provider._jwks_at = 0.0
            self.auth_provider._jwks = {}
            
            # Trigger a fresh JWKS fetch
            await self.auth_provider._refresh_jwks()
            
            logger.info("JWKS cache refreshed successfully")
            return CacheRefreshResponse(
                status="success",
                message="JWKS cache refreshed successfully"
            )
            
        except Exception as e:
            logger.exception("Failed to refresh JWKS cache")
            return CacheRefreshResponse(
                status="error",
                message=f"Failed to refresh JWKS cache: {str(e)}"
            ) 