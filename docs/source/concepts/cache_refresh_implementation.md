# Cache Refresh Implementation Guide

## Overview

This document provides a complete guide to the cache refresh feature implementation for Llama Stack. The feature allows refreshing JWKS (JSON Web Key Set) cache without server restart, solving the problem of stale cryptographic keys when authentication servers rotate keys.

## Architecture

### Components

1. **Admin API** (`llama_stack/apis/admin/admin.py`)
   - Defines the Admin protocol with cache refresh endpoint
   - Provides `CacheRefreshResponse` data structure

2. **Admin Implementation** (`llama_stack/distribution/admin.py`)
   - Implements the cache refresh logic
   - Integrates with OAuth2 auth provider
   - Handles error cases and logging

3. **Automatic JWKS Refresh** (`llama_stack/distribution/server/auth_providers.py`)
   - Automatically refreshes JWKS when "Unknown key ID" errors occur
   - Provides seamless recovery from key rotation
   - Eliminates the need for manual cache refresh in most cases

4. **Client-Side Handler** (`llama_stack/distribution/client_cache_refresh.py`)
   - Provides client-side cache refresh functionality
   - Implements automatic error detection and retry
   - Offers decorator pattern for easy integration

5. **Server Integration** (Multiple files)
   - Adds admin API to server routing
   - Integrates with OAuth2 scope validation
   - Includes admin API in stack construction

## Implementation Details

### 1. Admin API Protocol

```python
@runtime_checkable
class Admin(Protocol):
    @webmethod(route="/admin/cache/refresh", method="POST")
    async def refresh_jwks_cache(self) -> CacheRefreshResponse:
        """Refresh the JWKS cache from the auth server."""
        ...
```

**Key Features:**
- RESTful endpoint at `/v1/admin/cache/refresh`
- POST method for state-changing operation
- Returns structured response with status and message

### 2. Server-Side Implementation

```python
class DistributionAdminImpl(Admin):
    async def refresh_jwks_cache(self) -> CacheRefreshResponse:
        try:
            # Validate auth provider
            if not isinstance(self.auth_provider, OAuth2TokenAuthProvider):
                return CacheRefreshResponse(
                    status="error",
                    message="Cache refresh only available for OAuth2 token authentication"
                )
            
            # Clear cache and refresh
            self.auth_provider._jwks_at = 0.0
            self.auth_provider._jwks = {}
            await self.auth_provider._refresh_jwks()
            
            return CacheRefreshResponse(
                status="success",
                message="JWKS cache refreshed successfully"
            )
        except Exception as e:
            return CacheRefreshResponse(
                status="error",
                message=f"Failed to refresh JWKS cache: {str(e)}"
            )
```

**Key Features:**
- Validates auth provider type
- Clears existing cache completely
- Triggers fresh JWKS fetch
- Comprehensive error handling

### 3. Client-Side Implementation

#### JWKSCacheRefresher

```python
class JWKSCacheRefresher:
    async def refresh_server_cache(self) -> dict[str, Any]:
        url = f"{self.base_url}/v1/admin/cache/refresh"
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        
        response = await self._client.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
```

#### OAuth2ErrorHandler

```python
class OAuth2ErrorHandler:
    async def handle_jwks_error(self, error: Exception) -> bool:
        # Detect JWKS errors
        error_str = str(error).lower()
        jwks_indicators = ["unknown key id", "unknown key", "invalid key", "jwks", "key not found"]
        
        if not any(indicator in error_str for indicator in jwks_indicators):
            return False
        
        # Prevent infinite retry loops
        if self._refresh_attempted:
            return False
        
        # Attempt cache refresh
        try:
            async with JWKSCacheRefresher(self.base_url, self.auth_token) as refresher:
                await refresher.refresh_server_cache()
                return True
        except Exception:
            return False
```

#### Decorator Pattern

```python
def with_cache_refresh(base_url: str, auth_token: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            error_handler = OAuth2ErrorHandler(base_url, auth_token)
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if await error_handler.handle_jwks_error(e):
                    return await func(*args, **kwargs)  # Retry
                else:
                    raise e
        return wrapper
    return decorator
```

### 4. Server Integration

#### API Registration

```python
# Add to api_protocol_map in resolver.py
def api_protocol_map() -> dict[Api, Any]:
    return {
        # ... existing APIs
        Api.admin: Admin,
        # ... other APIs
    }
```

#### Stack Construction

```python
# Add to add_internal_implementations in stack.py
def add_internal_implementations(impls: dict[Api, Any], run_config: StackRunConfig) -> None:
    # ... existing implementations
    
    # Add admin implementation
    admin_impl = DistributionAdminImpl(
        DistributionAdminConfig(),
        deps={"auth_provider": auth_provider}
    )
    impls[Api.admin] = admin_impl
```

#### OAuth2 Scope Integration

```python
# Add to get_required_scopes_for_api in oauth2_scopes.py
def get_required_scopes_for_api(api_name: str, method: str = "GET") -> Set[str]:
    # ... existing scope logic
    elif api_name == "admin":
        required_scopes.add("llama:admin")  # Admin API requires admin scope
```

## Usage Patterns

### 1. Manual Cache Refresh

```python
async with JWKSCacheRefresher("http://localhost:8321", auth_token) as refresher:
    result = await refresher.refresh_server_cache()
    print(f"Cache refresh result: {result}")
```

### 2. Automatic Error Handling

```python
error_handler = OAuth2ErrorHandler("http://localhost:8321", auth_token)

try:
    result = await client.models.list()
except Exception as e:
    if await error_handler.handle_jwks_error(e):
        result = await client.models.list()  # Retry
    else:
        raise e
```

### 3. Decorator Pattern

```python
@with_cache_refresh("http://localhost:8321", auth_token)
async def my_api_call():
    return await client.models.list()

# Automatic JWKS error handling and retry
result = await my_api_call()
```

## Security Considerations

### Authentication Requirements

- **Any Authenticated User**: Any user with a valid authentication token can refresh cache
- **No Admin Scope Required**: This is intentional since stale JWKS affects all authentication
- **Security Rationale**: When JWKS keys are stale, all authentication fails including admin authentication
- **Emergency Recovery**: Allows any authenticated user to recover from key rotation issues
- **Token Validation**: All tokens are validated before cache refresh, including tokens without Llama Stack scopes
- **Basic Authentication**: The system allows tokens that are valid but don't have specific Llama Stack scopes
- **Error Isolation**: Cache refresh failures don't expose sensitive information

### Error Handling

- **Infinite Loop Prevention**: Client prevents multiple refresh attempts
- **Graceful Degradation**: Failed refreshes don't crash applications
- **Comprehensive Logging**: All operations are logged for audit trails

## Testing

### Unit Tests

```python
class TestCacheRefresh:
    @pytest.mark.asyncio
    async def test_refresh_jwks_cache_success(self, admin_impl, mock_auth_provider):
        result = await admin_impl.refresh_jwks_cache()
        assert result.status == "success"
        assert mock_auth_provider._jwks_at == 0.0
        assert mock_auth_provider._jwks == {}
```

### Integration Tests

```python
class TestClientCacheRefresh:
    @pytest.mark.asyncio
    async def test_jwks_cache_refresher_success(self):
        with patch("httpx.AsyncClient.post") as mock_post:
            # Test successful cache refresh
            result = await refresher.refresh_server_cache()
            assert result["status"] == "success"
```

## Configuration

### Server Configuration

The admin API is automatically enabled when authentication is configured. No additional configuration required.

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
@with_cache_refresh("http://localhost:8321", auth_token="your-token")
async def my_api_call():
    return await client.models.list()

# Automatic handling
result = await my_api_call()
```

## Benefits

1. **No Server Restart**: Refresh cache without downtime
2. **Automatic Recovery**: Client handles JWKS errors automatically
3. **Better UX**: Users don't need to restart servers manually
4. **Production Ready**: Works in high-availability environments
5. **Security**: Proper authentication and authorization controls

## Future Enhancements

1. **Metrics**: Add cache refresh metrics and monitoring
2. **Notifications**: Alert administrators of cache refresh events
3. **Scheduled Refresh**: Automatically refresh cache on schedule
4. **Multi-Server**: Support cache refresh across multiple server instances
5. **Health Checks**: Include cache freshness in health check endpoints

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Ensure token has `llama:admin` scope
2. **Connection Errors**: Check server URL and network connectivity
3. **JWKS URI Issues**: Verify JWKS URI configuration and access

### Debug Mode

```python
import logging
logging.getLogger("llama_stack.distribution.client_cache_refresh").setLevel(logging.DEBUG)
```

## Conclusion

The cache refresh feature provides a robust solution for handling JWKS cache issues in Llama Stack. It eliminates the need for server restarts while maintaining security and providing excellent user experience through automatic error handling and retry logic. 