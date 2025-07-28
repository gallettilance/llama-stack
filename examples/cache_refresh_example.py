#!/usr/bin/env python3
"""
Cache Refresh Example

This example demonstrates how to use the cache refresh functionality
to handle JWKS (JSON Web Key Set) cache issues without restarting the server.

Usage:
    python cache_refresh_example.py

Requirements:
    - Llama Stack server running with OAuth2 authentication
    - Any valid authentication token (not just admin tokens)
"""

import asyncio
import logging
from typing import Optional

from llama_stack.distribution.client_cache_refresh import (
    JWKSCacheRefresher,
    OAuth2ErrorHandler,
    with_cache_refresh,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LlamaStackClient:
    """Example client that demonstrates cache refresh functionality."""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.error_handler = OAuth2ErrorHandler(base_url, auth_token)
    
    async def call_api_with_retry(self, api_method, *args, **kwargs):
        """
        Call an API method with automatic JWKS error handling and retry.
        
        Args:
            api_method: The API method to call
            *args, **kwargs: Arguments to pass to the API method
            
        Returns:
            The result of the API call
            
        Raises:
            Exception: If the API call fails and is not a JWKS error
        """
        try:
            return await api_method(*args, **kwargs)
        except Exception as e:
            logger.info(f"API call failed: {e}")
            
            # Try to handle JWKS errors automatically
            if await self.error_handler.handle_jwks_error(e):
                logger.info("🔄 JWKS error detected, retrying after cache refresh...")
                # Retry the operation after cache refresh
                return await api_method(*args, **kwargs)
            else:
                logger.error(f"❌ Non-JWKS error, re-raising: {e}")
                raise e
    
    async def list_models(self):
        """Example API call that might fail due to stale JWKS."""
        # Simulate an API call that could fail with JWKS error
        logger.info("📋 Listing models...")
        
        # Simulate a JWKS error (in real usage, this would be an actual API call)
        import random
        if random.random() < 0.3:  # 30% chance of JWKS error for demo
            raise ValueError("Unknown key ID: abc123")
        
        return {"models": ["model1", "model2", "model3"]}
    
    async def manual_refresh_cache(self):
        """Manually refresh the server's JWKS cache."""
        logger.info("🔄 Manually refreshing server cache...")
        
        try:
            async with JWKSCacheRefresher(self.base_url, self.auth_token) as refresher:
                result = await refresher.refresh_server_cache()
                logger.info(f"✅ Cache refresh result: {result}")
                return result
        except Exception as e:
            logger.error(f"❌ Manual cache refresh failed: {e}")
            raise


@with_cache_refresh("http://localhost:8321", auth_token="your-token")
async def robust_api_call():
    """
    Example of using the decorator pattern for automatic cache refresh.
    
    This function will automatically handle JWKS errors and retry
    the operation after refreshing the cache.
    """
    logger.info("🚀 Making robust API call with automatic cache refresh...")
    
    # Simulate an API call that might fail
    import random
    if random.random() < 0.4:  # 40% chance of JWKS error for demo
        raise ValueError("Unknown key ID: xyz789")
    
    return {"status": "success", "data": "API call completed"}


async def main():
    """Main example function."""
    logger.info("🔧 Llama Stack Cache Refresh Example")
    logger.info("=" * 50)
    
    # Configuration
    base_url = "http://localhost:8321"
    auth_token = "your-token"  # Replace with any valid authentication token
    
    # Create client
    client = LlamaStackClient(base_url, auth_token)
    
    # Example 1: Manual cache refresh
    logger.info("\n📝 Example 1: Manual Cache Refresh")
    logger.info("-" * 30)
    try:
        await client.manual_refresh_cache()
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
    
    # Example 2: API call with automatic retry
    logger.info("\n📝 Example 2: API Call with Automatic Retry")
    logger.info("-" * 30)
    try:
        result = await client.call_api_with_retry(client.list_models)
        logger.info(f"✅ API call successful: {result}")
    except Exception as e:
        logger.error(f"❌ API call failed: {e}")
    
    # Example 3: Decorator pattern
    logger.info("\n📝 Example 3: Decorator Pattern")
    logger.info("-" * 30)
    try:
        result = await robust_api_call()
        logger.info(f"✅ Decorator API call successful: {result}")
    except Exception as e:
        logger.error(f"❌ Decorator API call failed: {e}")
    
    # Example 4: Multiple API calls with error handling
    logger.info("\n📝 Example 4: Multiple API Calls")
    logger.info("-" * 30)
    
    for i in range(3):
        logger.info(f"Making API call {i + 1}/3...")
        try:
            result = await client.call_api_with_retry(client.list_models)
            logger.info(f"✅ Call {i + 1} successful: {result}")
        except Exception as e:
            logger.error(f"❌ Call {i + 1} failed: {e}")
    
    logger.info("\n🎉 Example completed!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 