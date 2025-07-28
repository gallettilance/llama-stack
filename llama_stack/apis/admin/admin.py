# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from typing import Any
from typing_extensions import Protocol, runtime_checkable

from llama_stack.schema_utils import webmethod
from pydantic import BaseModel


class CacheRefreshResponse(BaseModel):
    """Response for cache refresh operations."""
    
    status: str = "success"
    message: str = "Cache refreshed successfully"


@runtime_checkable
class Admin(Protocol):
    """Llama Stack Admin API for administrative operations."""

    @webmethod(route="/admin/cache/refresh", method="POST")
    async def refresh_jwks_cache(self) -> CacheRefreshResponse:
        """Refresh the JWKS cache from the auth server.
        
        This endpoint allows refreshing the cached JSON Web Key Set (JWKS) 
        without requiring a full server restart. This is useful when the 
        authentication server (e.g., Keycloak) rotates cryptographic keys.
        
        :returns: A CacheRefreshResponse indicating the result of the refresh operation.
        """
        ... 