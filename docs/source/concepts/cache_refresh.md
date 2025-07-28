# Cache Refresh Feature

## Overview

The cache refresh feature allows Llama Stack server to refresh its JWKS (JSON Web Key Set) cache without requiring a full server restart. This is particularly useful when authentication servers (like Keycloak) rotate cryptographic keys, which can cause "Unknown key ID" errors.

**Important Security Note**: The cache refresh endpoint accepts any valid authentication token (not just admin tokens). This is intentional because when JWKS keys are stale, **all authentication fails** - including admin authentication. This creates a chicken-and-egg problem where you need admin access to refresh the cache, but you can't authenticate as admin because the cache is stale. Therefore, any authenticated user can refresh the cache to recover from key rotation issues.

**Automatic JWKS Refresh**: The system now automatically refreshes the JWKS cache when it encounters an "Unknown key ID" error during JWT validation. This provides seamless recovery from key rotation without requiring manual intervention.

**Token Validation**: The system now allows tokens that are valid but don't necessarily have Llama Stack scopes. This is important for emergency operations like cache refresh when the authentication server has rotated keys.

## Problem

When authentication servers rotate cryptographic keys, the Llama Stack server's cached JWKS becomes stale, causing authentication failures with errors like:

```
ValueError: Unknown key ID: <key_id>
```

Previously, the only solution was to restart the server:

```bash
pkill -f "llama-stack"
llama-stack run
```

## Solution

The cache refresh feature provides:

1. **Server-side endpoint** to refresh JWKS cache
2. **Client-side error handling** to automatically detect and handle JWKS errors
3. **Automatic retry logic** to recover from key rotation issues

## Server-Side Implementation

### Admin API Endpoint

The cache refresh functionality is exposed through the Admin API:

```
POST /v1/admin/cache/refresh
```

**Authentication:** Requires any valid authentication token (not admin-only)

**Response:**
```json
{
  "status": "success",
  "message": "JWKS cache refreshed successfully"
}
```

**Error Response:**
```json
{
  "status": "error", 
  "message": "Failed to refresh JWKS cache: <error_details>"
}
```

### How It Works

1. **Clears existing cache** - Resets the JWKS cache timestamp and clears stored keys
2. **Fetches fresh keys** - Makes a new request to the JWKS URI to get updated keys
3. **Updates cache** - Stores the new keys for future token validation

## Client-Side Implementation

### Manual Cache Refresh

```python
from llama_stack.distribution.client_cache_refresh import JWKSCacheRefresher

async def refresh_cache():
    # Any valid authentication token can be used (not just admin tokens)
    async with JWKSCacheRefresher("http://localhost:8321", auth_token="your-token") as refresher:
        result = await refresher.refresh_server_cache()
        print(f"Cache refresh result: {result}")
```

### Automatic Error Handling

```python
from llama_stack.distribution.client_cache_refresh import OAuth2ErrorHandler

async def handle_auth_errors():
    # Any valid authentication token can be used (not just admin tokens)
    error_handler = OAuth2ErrorHandler("http://localhost:8321", auth_token="your-token")
    
    try:
        # Your API call that might fail due to stale JWKS
        response = await client.models.list()
        return response
    except Exception as e:
        # Automatically handle JWKS errors
        if await error_handler.handle_jwks_error(e):
            # Retry the operation after cache refresh
            return await client.models.list()
        else:
            # Not a JWKS error, re-raise
            raise e
```

### Decorator Pattern

```python
from llama_stack.distribution.client_cache_refresh import with_cache_refresh

# Any valid authentication token can be used (not just admin tokens)
@with_cache_refresh("http://localhost:8321", auth_token="your-token")
async def my_api_call():
    return await client.models.list()

# The decorator automatically handles JWKS errors and retries
result = await my_api_call()
```

## Usage Examples

### Basic Usage

```python
import asyncio
from llama_stack.distribution.client_cache_refresh import JWKSCacheRefresher

async def main():
    # Manual cache refresh
    async with JWKSCacheRefresher("http://localhost:8321") as refresher:
        try:
            result = await refresher.refresh_server_cache()
            print(f"✅ Cache refreshed: {result}")
        except Exception as e:
            print(f"❌ Cache refresh failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Integration with Existing Code

```python
from llama_stack.distribution.client_cache_refresh import OAuth2ErrorHandler

class LlamaStackClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.auth_token = auth_token
        self.error_handler = OAuth2ErrorHandler(base_url, auth_token)
    
    async def call_api(self, api_method):
        try:
            return await api_method()
        except Exception as e:
            # Handle JWKS errors automatically
            if await self.error_handler.handle_jwks_error(e):
                # Retry after cache refresh
                return await api_method()
            else:
                raise e
    
    async def list_models(self):
        return await self.call_api(self._list_models_impl)
    
    async def _list_models_impl(self):
        # Actual API call implementation
        pass
```

### Error Detection

The client automatically detects JWKS-related errors by looking for these indicators in error messages:

- "unknown key id"
- "unknown key" 
- "invalid key"
- "jwks"
- "key not found"

## Configuration

### Server Configuration

The admin API is automatically enabled when authentication is configured. No additional configuration is required.

### Client Configuration

```python
# Basic configuration
error_handler = OAuth2ErrorHandler(
    base_url="http://localhost:8321",
    auth_token="your-admin-token"
)

# With custom timeout
async with JWKSCacheRefresher(
    base_url="http://localhost:8321",
    auth_token="your-admin-token"
) as refresher:
    result = await refresher.refresh_server_cache()
```

## Security Considerations

### Authentication Requirements

- **Any Authenticated User**: The cache refresh endpoint accepts any valid authentication token
- **No Admin Scope Required**: This is intentional since stale JWKS affects all authentication
- **Security Rationale**: When JWKS keys are stale, all authentication fails including admin authentication
- **Emergency Recovery**: Allows any authenticated user to recover from key rotation issues

### Error Handling

- The client prevents infinite retry loops
- Failed refresh attempts are logged but don't crash the application
- Original errors are preserved when refresh fails

### Logging

All cache refresh operations are logged with appropriate levels:

- **INFO**: Successful cache refresh
- **WARNING**: Cache refresh failures
- **ERROR**: Unexpected errors during refresh

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```
   Cache refresh failed: 403
   ```
   **Solution:** Ensure your token is valid and properly authenticated

2. **Server Unreachable**
   ```
   Cache refresh request failed: Connection error
   ```
   **Solution:** Check server URL and network connectivity

3. **JWKS URI Issues**
   ```
   Failed to refresh JWKS cache: JWKS URI not accessible
   ```
   **Solution:** Verify JWKS URI configuration and network access

### Debug Mode

Enable debug logging to see detailed cache refresh operations:

```python
import logging
logging.getLogger("llama_stack.distribution.client_cache_refresh").setLevel(logging.DEBUG)
```

## Migration Guide

### From Manual Server Restart

**Before:**
```bash
# When JWKS errors occur
pkill -f "llama-stack"
llama-stack run
```

**After:**
```python
# Automatic handling
@with_cache_refresh("http://localhost:8321", auth_token="your-token")
async def my_api_call():
    return await client.models.list()
```

### Integration with Existing Error Handling

```python
# Existing error handling
try:
    result = await client.models.list()
except Exception as e:
    if "Unknown key ID" in str(e):
        # Old manual approach
        print("JWKS error detected, please restart server")
    else:
        raise e

# New automatic approach
@with_cache_refresh("http://localhost:8321", auth_token="your-token")
async def robust_api_call():
    return await client.models.list()

# No manual error handling needed
result = await robust_api_call()
```

## Best Practices

1. **Use the decorator pattern** for automatic error handling
2. **Provide valid authentication tokens** for cache refresh operations
3. **Monitor logs** for cache refresh activities
4. **Test with key rotation** in your authentication server
5. **Implement fallback strategies** for when cache refresh fails

## API Reference

### JWKSCacheRefresher

```python
class JWKSCacheRefresher:
    def __init__(self, base_url: str, auth_token: Optional[str] = None)
    async def refresh_server_cache() -> dict[str, Any]
```

### OAuth2ErrorHandler

```python
class OAuth2ErrorHandler:
    def __init__(self, base_url: str, auth_token: Optional[str] = None)
    async def handle_jwks_error(error: Exception) -> bool
    def reset_refresh_attempt()
```

### Decorator

```python
def with_cache_refresh(base_url: str, auth_token: Optional[str] = None)
``` 