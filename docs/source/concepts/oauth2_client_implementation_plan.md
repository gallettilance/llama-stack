# OAuth2 Token Exchange Implementation Plan for llama-stack-client-python

## Overview

This document outlines a comprehensive implementation plan for adding OAuth2 token exchange capabilities to the `llama-stack-client-python` SDK. The goal is to enable dynamic scope elevation and token management without breaking existing workflows or losing agent session state.

## Table of Contents

- [Current Architecture Analysis](#current-architecture-analysis)
- [Proposed Enhanced Architecture](#proposed-enhanced-architecture)
- [Implementation Details](#implementation-details)
- [Usage Examples](#usage-examples)
- [Migration Path & Backward Compatibility](#migration-path--backward-compatibility)
- [Error Handling & Diagnostics](#error-handling--diagnostics)
- [Testing Strategy](#testing-strategy)
- [Performance Considerations](#performance-considerations)

## Current Architecture Analysis

### Current Authentication Flow

```python
# Current: Static API key authentication
client = LlamaStackClient(api_key="static_token")
# auth_headers property: {"Authorization": f"Bearer {api_key}"}
```

### Current Limitations

- ❌ Single static token for entire session
- ❌ No scope elevation capabilities  
- ❌ Agent sessions lost when token changes
- ❌ No OAuth2 compliance
- ❌ Cannot handle dynamic permission requirements

### Current File Structure

```
llama-stack-client-python/
├── src/llama_stack_client/
│   ├── _client.py              # LlamaStackClient class
│   ├── _base_client.py         # Base authentication logic
│   ├── _exceptions.py          # Error handling
│   └── types/                  # Type definitions
```

## Proposed Enhanced Architecture

### Enhanced File Structure

```
llama-stack-client-python/
├── src/llama_stack_client/
│   ├── _client.py                    # Enhanced with OAuth2 support
│   ├── _base_client.py              # Enhanced auth headers logic
│   ├── _auth/                       # ✨ New auth module
│   │   ├── __init__.py
│   │   ├── oauth2_manager.py        # OAuth2 token exchange logic
│   │   ├── token_cache.py           # Token caching and management
│   │   ├── scopes.py               # Client-side scope definitions
│   │   └── decorators.py           # Method decoration for scopes
│   ├── _exceptions.py               # Enhanced with auth exceptions
│   └── types/
│       └── auth_types.py            # ✨ OAuth2 configuration types
```

### Architecture Principles

1. **Backward Compatibility**: Existing code continues to work unchanged
2. **Opt-in OAuth2**: OAuth2 features are optional, enabled via configuration
3. **Standards Compliance**: Implements RFC 8693 OAuth2 Token Exchange
4. **Session Preservation**: Agent sessions survive token changes
5. **Performance**: Intelligent token caching and minimal exchange requests

## Implementation Details

### 1. OAuth2 Configuration Types

Create type definitions for OAuth2 configuration and token metadata:

```python
# src/llama_stack_client/types/auth_types.py
from typing import Optional, Set, Dict, Any
from pydantic import BaseModel
from enum import Enum

class ScopeElevationStrategy(str, Enum):
    """Strategies for handling insufficient scopes."""
    AUTO_EXCHANGE = "auto_exchange"      # Automatically exchange for required scopes
    PROMPT_USER = "prompt_user"          # Ask user for consent
    FAIL_FAST = "fail_fast"             # Fail immediately if scopes insufficient

class OAuth2Config(BaseModel):
    """OAuth2 configuration for token exchange and management."""
    
    # OAuth2 Provider Configuration
    token_endpoint: str                  # OAuth2 token endpoint URL
    client_id: str                      # OAuth2 client ID
    client_secret: Optional[str] = None  # OAuth2 client secret (for confidential clients)
    
    # Token Exchange Configuration
    enable_token_exchange: bool = True   # Enable RFC 8693 token exchange
    scope_elevation_strategy: ScopeElevationStrategy = ScopeElevationStrategy.AUTO_EXCHANGE
    
    # Cache Configuration
    cache_tokens: bool = True           # Cache tokens by scope combination
    token_cache_ttl: int = 300          # Cache TTL in seconds (5 minutes default)
    
    # Retry Configuration  
    max_exchange_retries: int = 3       # Max retries for token exchange
    exchange_timeout: int = 10          # Timeout for token exchange requests
    
    # Security Configuration
    validate_scopes: bool = True        # Validate scopes against Llama Stack standards
    require_https: bool = True          # Require HTTPS for token endpoints

class TokenMetadata(BaseModel):
    """Metadata about an OAuth2 token."""
    
    access_token: str                   # The actual access token
    scopes: Set[str]                   # Scopes granted to this token
    expires_at: Optional[float] = None  # Token expiration timestamp
    refresh_token: Optional[str] = None # Refresh token (if available)
    token_type: str = "Bearer"         # Token type (usually Bearer)
```

### 2. OAuth2 Scope Definitions (Client-Side)

Mirror the server-side OAuth2 scopes for client-side scope detection:

```python
# src/llama_stack_client/_auth/scopes.py
"""
Client-side OAuth2 scope definitions that mirror the server-side scopes.
Used for automatic scope detection and validation.
"""

from typing import Set, Dict

# Standard Llama Stack OAuth2 scopes (mirrors server-side)
STANDARD_SCOPES = {
    "llama:inference": "Access to inference APIs (chat completion, embeddings)",
    "llama:models:read": "Read access to models (list, get model details)",
    "llama:models:write": "Write access to models (register, unregister)",
    "llama:agents:read": "Read access to agents (list sessions, get agent details)", 
    "llama:agents:write": "Write access to agents (create sessions, send messages)",
    "llama:tools": "Access to tool runtime and execution",
    "llama:vector_dbs:read": "Read access to vector databases",
    "llama:vector_dbs:write": "Write access to vector databases",
    "llama:safety": "Access to safety shields and content filtering",
    "llama:eval": "Access to evaluation and benchmarking",
    "llama:admin": "Full administrative access to all APIs",
}

# Map client methods to required scopes
METHOD_SCOPE_MAP: Dict[str, Set[str]] = {
    # Inference operations
    "inference.chat_completion": {"llama:inference"},
    "inference.completion": {"llama:inference"},
    "inference.embeddings": {"llama:inference"},
    
    # Model operations
    "models.list": {"llama:models:read"},
    "models.retrieve": {"llama:models:read"},
    "models.register": {"llama:models:write"},
    "models.unregister": {"llama:models:write"},
    
    # Agent operations
    "agents.create": {"llama:agents:write"},
    "agents.delete": {"llama:agents:write"},
    "agents.session.create": {"llama:agents:write"},
    "agents.turn.create": {"llama:agents:write"},
    "agents.list": {"llama:agents:read"},
    "agents.session.retrieve": {"llama:agents:read"},
    
    # Tool operations
    "tools.list": {"llama:tools"},
    "tools.get": {"llama:tools"},
    "tool_runtime.invoke_tool": {"llama:tools"},
    
    # Vector DB operations
    "vector_dbs.create": {"llama:vector_dbs:write"},
    "vector_dbs.delete": {"llama:vector_dbs:write"},
    "vector_dbs.list": {"llama:vector_dbs:read"},
    "vector_dbs.retrieve": {"llama:vector_dbs:read"},
    
    # File operations
    "files.create": {"llama:files:write"},
    "files.delete": {"llama:files:write"},
    "files.list": {"llama:files:read"},
    
    # Safety operations
    "safety.run_shield": {"llama:safety"},
    
    # Eval operations
    "eval.run_eval": {"llama:eval"},
    "benchmarks.run": {"llama:eval"},
    
    # Admin operations
    "providers.list": {"llama:admin"},
    "inspect.health": {"llama:admin"},
}

def get_required_scopes(method_name: str) -> Set[str]:
    """Get required scopes for a client method."""
    base_scopes = METHOD_SCOPE_MAP.get(method_name, {"llama:admin"})
    # Always include admin as it grants universal access
    return base_scopes | {"llama:admin"}

def validate_scopes(scopes: Set[str]) -> Set[str]:
    """Validate scopes against standard Llama Stack scopes."""
    valid_scopes = scopes.intersection(STANDARD_SCOPES.keys())
    if not valid_scopes:
        raise ValueError("No valid Llama Stack scopes found in token")
    return valid_scopes
```

### 3. Token Cache Implementation

Implement thread-safe token caching organized by scope combinations:

```python
# src/llama_stack_client/_auth/token_cache.py
import time
import threading
from typing import Dict, Optional, Set
from ..types.auth_types import TokenMetadata

class TokenCache:
    """Thread-safe cache for OAuth2 tokens organized by scope combinations."""
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._cache: Dict[str, TokenMetadata] = {}
        self._lock = threading.RLock()
    
    def _scope_key(self, scopes: Set[str]) -> str:
        """Generate a cache key for a set of scopes."""
        return "|".join(sorted(scopes))
    
    def get(self, scopes: Set[str]) -> Optional[TokenMetadata]:
        """Get a cached token for the given scopes."""
        with self._lock:
            key = self._scope_key(scopes)
            token_meta = self._cache.get(key)
            
            if token_meta is None:
                return None
            
            # Check if token is expired
            if token_meta.expires_at and time.time() >= token_meta.expires_at:
                del self._cache[key]
                return None
            
            return token_meta
    
    def put(self, token_meta: TokenMetadata) -> None:
        """Cache a token for its scopes."""
        with self._lock:
            key = self._scope_key(token_meta.scopes)
            self._cache[key] = token_meta
    
    def find_compatible(self, required_scopes: Set[str]) -> Optional[TokenMetadata]:
        """Find a cached token that includes all required scopes."""
        with self._lock:
            for token_meta in self._cache.values():
                # Check expiration
                if token_meta.expires_at and time.time() >= token_meta.expires_at:
                    continue
                
                # Check if token has all required scopes
                if required_scopes.issubset(token_meta.scopes):
                    return token_meta
            
            return None
    
    def clear(self) -> None:
        """Clear all cached tokens."""
        with self._lock:
            self._cache.clear()
```

### 4. OAuth2 Token Manager

Core OAuth2 token exchange logic implementing RFC 8693:

```python
# src/llama_stack_client/_auth/oauth2_manager.py
import asyncio
import time
import httpx
from typing import Set, Optional
from .token_cache import TokenCache
from .scopes import validate_scopes, STANDARD_SCOPES
from ..types.auth_types import OAuth2Config, TokenMetadata, ScopeElevationStrategy
from .._exceptions import AuthenticationError, InsufficientScopesError

class OAuth2TokenManager:
    """Manages OAuth2 tokens with automatic exchange and scope elevation."""
    
    def __init__(self, config: OAuth2Config, initial_token: str):
        self.config = config
        self.initial_token = initial_token
        self.cache = TokenCache(config.token_cache_ttl) if config.cache_tokens else None
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(timeout=self.config.exchange_timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client:
            await self._http_client.aclose()
    
    async def get_token_for_scopes(self, required_scopes: Set[str]) -> str:
        """Get a token with the required scopes, performing exchange if necessary."""
        
        # Validate scopes if configured
        if self.config.validate_scopes:
            required_scopes = validate_scopes(required_scopes)
        
        # Try cache first
        if self.cache:
            cached_token = self.cache.find_compatible(required_scopes)
            if cached_token:
                return cached_token.access_token
        
        # No suitable cached token - perform exchange
        return await self._exchange_token(required_scopes)
    
    async def _exchange_token(self, required_scopes: Set[str]) -> str:
        """Exchange current token for one with required scopes using RFC 8693."""
        
        if not self.config.enable_token_exchange:
            # Token exchange disabled - return initial token
            return self.initial_token
        
        # Handle different elevation strategies
        if self.config.scope_elevation_strategy == ScopeElevationStrategy.FAIL_FAST:
            raise InsufficientScopesError(f"Token exchange disabled. Required scopes: {required_scopes}")
        
        if self.config.scope_elevation_strategy == ScopeElevationStrategy.PROMPT_USER:
            if not await self._prompt_user_consent(required_scopes):
                raise InsufficientScopesError("User denied scope elevation")
        
        # Perform RFC 8693 token exchange
        for attempt in range(self.config.max_exchange_retries):
            try:
                return await self._perform_token_exchange(required_scopes)
            except Exception as e:
                if attempt == self.config.max_exchange_retries - 1:
                    raise AuthenticationError(f"Token exchange failed after {self.config.max_exchange_retries} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _perform_token_exchange(self, required_scopes: Set[str]) -> str:
        """Perform the actual RFC 8693 token exchange."""
        
        if not self._http_client:
            raise RuntimeError("OAuth2TokenManager must be used as async context manager")
        
        # Prepare token exchange request (RFC 8693)
        exchange_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": self.config.client_id,
            "subject_token": self.initial_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "scope": " ".join(required_scopes),
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token"
        }
        
        if self.config.client_secret:
            exchange_data["client_secret"] = self.config.client_secret
        
        # Make token exchange request
        response = await self._http_client.post(
            self.config.token_endpoint,
            data=exchange_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise AuthenticationError(f"Token exchange failed: {response.status_code} {response.text}")
        
        token_data = response.json()
        access_token = token_data["access_token"]
        
        # Cache the new token
        if self.cache:
            token_meta = TokenMetadata(
                access_token=access_token,
                scopes=set(token_data.get("scope", "").split()),
                expires_at=time.time() + token_data.get("expires_in", 3600),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer")
            )
            self.cache.put(token_meta)
        
        return access_token
    
    async def _prompt_user_consent(self, required_scopes: Set[str]) -> bool:
        """Prompt user for consent to additional scopes."""
        # In a real implementation, this might show a GUI dialog or CLI prompt
        print(f"Additional permissions required: {', '.join(required_scopes)}")
        response = input("Grant additional scopes? (y/n): ")
        return response.lower() in ('y', 'yes')
```

### 5. Enhanced Client Implementation

Modify the existing LlamaStackClient to support OAuth2:

```python
# src/llama_stack_client/_client.py (enhanced sections)
import asyncio
import inspect
from typing import Optional, Dict, Any, Set
from ._auth.oauth2_manager import OAuth2TokenManager
from ._auth.scopes import get_required_scopes
from .types.auth_types import OAuth2Config
from ._exceptions import AuthenticationError

class LlamaStackClient(SyncAPIClient):
    """Enhanced LlamaStackClient with OAuth2 token exchange support."""
    
    # ... existing properties ...
    
    # OAuth2 properties
    oauth2_config: Optional[OAuth2Config]
    _oauth2_manager: Optional[OAuth2TokenManager]
    _method_call_depth: int = 0  # Track recursive calls to prevent loops
    
    def __init__(
        self,
        *,
        api_key: str | None = None,
        oauth2_config: Optional[OAuth2Config] = None,
        # ... existing parameters ...
        **kwargs
    ) -> None:
        """Enhanced constructor with OAuth2 support."""
        
        # Initialize OAuth2 if configured
        self.oauth2_config = oauth2_config
        self._oauth2_manager = None
        
        if oauth2_config and api_key:
            # Initialize OAuth2 manager with the provided token
            self._oauth2_manager = OAuth2TokenManager(oauth2_config, api_key)
        
        # Call parent constructor
        super().__init__(api_key=api_key, **kwargs)
    
    @property
    @override
    def auth_headers(self) -> dict[str, str]:
        """Enhanced auth headers with dynamic token resolution."""
        
        # For OAuth2-enabled clients, token resolution happens per-request
        # This property returns the current token or empty dict
        if self._oauth2_manager:
            # Return current token if available, otherwise empty
            # The actual token resolution happens in _resolve_token_for_operation
            api_key = self.api_key
            if api_key:
                return {"Authorization": f"Bearer {api_key}"}
            return {}
        
        # Fallback to original behavior
        api_key = self.api_key
        if api_key is None:
            return {}
        return {"Authorization": f"Bearer {api_key}"}
    
    async def _resolve_token_for_operation(self, method_name: str) -> str:
        """Resolve the appropriate token for a specific operation."""
        
        if not self._oauth2_manager:
            # No OAuth2 configured - use static token
            if not self.api_key:
                raise AuthenticationError("No API key or OAuth2 configuration provided")
            return self.api_key
        
        # Prevent infinite recursion
        if self._method_call_depth > 3:
            raise AuthenticationError("Token resolution recursion detected")
        
        try:
            self._method_call_depth += 1
            
            # Get required scopes for this operation
            required_scopes = get_required_scopes(method_name)
            
            # Use OAuth2 manager to get appropriate token
            async with self._oauth2_manager as manager:
                token = await manager.get_token_for_scopes(required_scopes)
                
            return token
            
        finally:
            self._method_call_depth -= 1
    
    def _make_request_with_oauth2(self, method_name: str, original_method):
        """Wrapper to inject OAuth2 token resolution into requests."""
        
        if not self._oauth2_manager:
            # No OAuth2 - use original method
            return original_method()
        
        # For sync client, we need to handle async token resolution
        try:
            # Get event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't call async method directly
                # This is a limitation - sync client with OAuth2 in async context
                raise AuthenticationError(
                    "OAuth2 token exchange requires AsyncLlamaStackClient when called from async context"
                )
            else:
                # Run token resolution in event loop
                token = loop.run_until_complete(self._resolve_token_for_operation(method_name))
        except RuntimeError:
            # No event loop - create one
            token = asyncio.run(self._resolve_token_for_operation(method_name))
        
        # Update the api_key for this request
        original_api_key = self.api_key
        try:
            self.api_key = token
            return original_method()
        finally:
            # Restore original api_key
            self.api_key = original_api_key

# Enhanced AsyncLlamaStackClient with better OAuth2 support
class AsyncLlamaStackClient(AsyncAPIClient):
    """Enhanced AsyncLlamaStackClient with OAuth2 token exchange support."""
    
    # ... similar enhancements as sync client ...
    
    async def _make_request_with_oauth2(self, method_name: str, original_method):
        """Async wrapper to inject OAuth2 token resolution into requests."""
        
        if not self._oauth2_manager:
            # No OAuth2 - use original method
            return await original_method()
        
        # Resolve token for this operation
        token = await self._resolve_token_for_operation(method_name)
        
        # Update the api_key for this request
        original_api_key = self.api_key
        try:
            self.api_key = token
            return await original_method()
        finally:
            # Restore original api_key
            self.api_key = original_api_key
```

### 6. Method Decoration for Automatic Scope Resolution

Implement decorators to automatically handle OAuth2 scope resolution:

```python
# src/llama_stack_client/_auth/decorators.py
import functools
from typing import Callable, Any

def with_oauth2_scopes(method_name: str):
    """Decorator to automatically handle OAuth2 scope resolution for client methods."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            if hasattr(self, '_make_request_with_oauth2'):
                return self._make_request_with_oauth2(method_name, lambda: func(self, *args, **kwargs))
            return func(self, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            if hasattr(self, '_make_request_with_oauth2'):
                return await self._make_request_with_oauth2(method_name, lambda: func(self, *args, **kwargs))
            return await func(self, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Example usage in resource classes:
# src/llama_stack_client/resources/agents/agents.py
from .._auth.decorators import with_oauth2_scopes

class AgentsResource(SyncAPIResource):
    
    @with_oauth2_scopes("agents.create")
    def create(self, **params) -> AgentCreateResponse:
        # ... existing implementation ...
        pass
    
    @with_oauth2_scopes("agents.list")  
    def list(self, **params) -> AgentListResponse:
        # ... existing implementation ...
        pass
```

## Usage Examples

### Basic OAuth2 Configuration

```python
from llama_stack_client import LlamaStackClient
from llama_stack_client.types import OAuth2Config, ScopeElevationStrategy

# Configure OAuth2 with automatic token exchange
oauth2_config = OAuth2Config(
    token_endpoint="https://auth.example.com/oauth2/token",
    client_id="your-client-id",
    client_secret="your-client-secret",
    enable_token_exchange=True,
    scope_elevation_strategy=ScopeElevationStrategy.AUTO_EXCHANGE
)

# Create client with OAuth2 support
client = LlamaStackClient(
    base_url="http://localhost:5000",
    api_key="initial_token_with_basic_scopes",
    oauth2_config=oauth2_config
)

# All operations work seamlessly with automatic scope elevation
agent = client.agents.create(agent_config={...})        # Auto-exchanges for agent:write
response = client.inference.chat_completion(...)        # Uses inference scopes  
file = client.files.create(...)                         # Auto-exchanges for files:write

# Agent is preserved! No client recreation needed
agents = client.agents.list()  # Original agent still exists
```

### Different Elevation Strategies

```python
# Prompt user for consent
oauth2_config = OAuth2Config(
    token_endpoint="https://auth.example.com/oauth2/token",
    client_id="your-client-id", 
    scope_elevation_strategy=ScopeElevationStrategy.PROMPT_USER
)

# Fail fast on insufficient scopes
oauth2_config = OAuth2Config(
    token_endpoint="https://auth.example.com/oauth2/token",
    client_id="your-client-id",
    scope_elevation_strategy=ScopeElevationStrategy.FAIL_FAST
)
```

### Async Client Usage

```python
import asyncio
from llama_stack_client import AsyncLlamaStackClient

async def main():
    async with AsyncLlamaStackClient(
        base_url="http://localhost:5000",
        api_key="initial_token",
        oauth2_config=oauth2_config
    ) as client:
        # Seamless async OAuth2 token management
        agent = await client.agents.create(...)
        response = await client.inference.chat_completion(...)
        
        # Agent preserved across token exchanges
        agents = await client.agents.list()

asyncio.run(main())
```

### Configuration Examples

#### Auth0 Configuration

```python
oauth2_config = OAuth2Config(
    token_endpoint="https://your-tenant.auth0.com/oauth/token",
    client_id="your-auth0-client-id",
    client_secret="your-auth0-client-secret",
    enable_token_exchange=True
)
```

#### Keycloak Configuration

```python
oauth2_config = OAuth2Config(
    token_endpoint="https://keycloak.example.com/auth/realms/your-realm/protocol/openid-connect/token",
    client_id="llama-stack-client",
    client_secret="your-keycloak-secret",
    enable_token_exchange=True
)
```

#### Azure AD Configuration

```python
oauth2_config = OAuth2Config(
    token_endpoint="https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token",
    client_id="your-azure-client-id",
    client_secret="your-azure-client-secret",
    enable_token_exchange=True
)
```

## Migration Path & Backward Compatibility

### Backward Compatibility Guarantees

- ✅ **Existing code continues to work unchanged**
- ✅ `api_key` parameter still works for static tokens
- ✅ No breaking changes to existing API surface
- ✅ OAuth2 features are opt-in
- ✅ All existing method signatures preserved

### Migration Strategy

#### Phase 1: Add OAuth2 Support (Non-Breaking)

- Implement OAuth2 features as optional functionality
- Add new parameters to client constructors with default values
- Ensure existing tests continue to pass

#### Phase 2: Documentation & Examples

- Update documentation with OAuth2 configuration examples
- Create migration guides for common OAuth2 providers
- Add OAuth2 examples to getting started guides

#### Phase 3: Encourage Adoption

- Promote OAuth2 usage for new applications
- Provide tooling to help migrate existing applications
- Create best practices documentation

#### Phase 4: Long-term Evolution

- Gather feedback and iterate on OAuth2 implementation
- Consider making OAuth2 the default in future major version
- Potentially deprecate static API keys in distant future

### Incremental Migration Example

```python
# Before (continues to work):
client = LlamaStackClient(api_key="static_token")

# After (enhanced capabilities):
client = LlamaStackClient(
    api_key="initial_token",
    oauth2_config=oauth2_config  # Optional enhancement
)
```

## Error Handling & Diagnostics

### Enhanced Exception Types

```python
# src/llama_stack_client/_exceptions.py
class InsufficientScopesError(LlamaStackClientError):
    """Raised when token lacks required OAuth2 scopes."""
    
    def __init__(self, message: str, required_scopes: Set[str] = None, user_scopes: Set[str] = None):
        super().__init__(message)
        self.required_scopes = required_scopes or set()
        self.user_scopes = user_scopes or set()

class TokenExchangeError(AuthenticationError):
    """Raised when OAuth2 token exchange fails."""
    
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

class OAuth2ConfigurationError(LlamaStackClientError):
    """Raised when OAuth2 configuration is invalid."""
    pass
```

### Error Scenarios & Handling

#### Insufficient Scopes

```python
try:
    client.agents.create(...)
except InsufficientScopesError as e:
    print(f"Missing scopes: {e.required_scopes - e.user_scopes}")
    print("Please request additional permissions from your administrator")
```

#### Token Exchange Failure

```python
try:
    client.files.create(...)
except TokenExchangeError as e:
    print(f"OAuth2 token exchange failed: {e}")
    print(f"Status code: {e.status_code}")
    # Potentially retry with exponential backoff
```

#### Configuration Errors

```python
try:
    client = LlamaStackClient(oauth2_config=invalid_config)
except OAuth2ConfigurationError as e:
    print(f"OAuth2 configuration error: {e}")
    # Guide user to fix configuration
```

### Debugging Support

#### Debug Logging

```python
import logging

# Enable OAuth2 debug logging
logging.getLogger('llama_stack_client.oauth2').setLevel(logging.DEBUG)

client = LlamaStackClient(
    api_key="token",
    oauth2_config=oauth2_config
)

# Logs will show:
# DEBUG: Resolving scopes for agents.create: {'llama:agents:write', 'llama:admin'}
# DEBUG: Cache miss for scopes: llama:agents:write
# DEBUG: Performing token exchange for scopes: llama:agents:write
# DEBUG: Token exchange successful (expires: 2024-01-15 10:30:00)
# DEBUG: Cached token for scopes: llama:agents:write
```

#### Diagnostic Methods

```python
# Add diagnostic methods to client
class LlamaStackClient:
    def get_oauth2_status(self) -> Dict[str, Any]:
        """Get OAuth2 configuration and token cache status."""
        if not self._oauth2_manager:
            return {"oauth2_enabled": False}
        
        return {
            "oauth2_enabled": True,
            "token_endpoint": self.oauth2_config.token_endpoint,
            "client_id": self.oauth2_config.client_id,
            "cache_enabled": self.oauth2_config.cache_tokens,
            "cached_tokens": len(self._oauth2_manager.cache._cache) if self._oauth2_manager.cache else 0,
            "elevation_strategy": self.oauth2_config.scope_elevation_strategy.value
        }
    
    def clear_token_cache(self) -> None:
        """Clear the OAuth2 token cache."""
        if self._oauth2_manager and self._oauth2_manager.cache:
            self._oauth2_manager.cache.clear()
```

## Testing Strategy

### Unit Testing

#### Test Structure

```
tests/
├── unit/
│   ├── auth/
│   │   ├── test_oauth2_manager.py
│   │   ├── test_token_cache.py
│   │   ├── test_scopes.py
│   │   └── test_decorators.py
│   ├── test_client_oauth2.py
│   └── test_exceptions.py
├── integration/
│   ├── test_oauth2_flow.py
│   ├── test_scope_elevation.py
│   └── test_provider_compatibility.py
└── fixtures/
    ├── mock_oauth2_server.py
    └── test_tokens.py
```

#### Key Test Cases

**OAuth2 Manager Tests:**
```python
# test_oauth2_manager.py
class TestOAuth2Manager:
    async def test_token_exchange_success(self):
        # Test successful RFC 8693 token exchange
        pass
    
    async def test_token_exchange_failure(self):
        # Test handling of exchange failures
        pass
    
    async def test_scope_validation(self):
        # Test scope validation logic
        pass
    
    async def test_cache_behavior(self):
        # Test token caching and retrieval
        pass
```

**Client Integration Tests:**
```python
# test_client_oauth2.py
class TestClientOAuth2Integration:
    def test_backward_compatibility(self):
        # Ensure existing code still works
        client = LlamaStackClient(api_key="static_token")
        # ... test existing functionality
    
    async def test_oauth2_enabled_client(self):
        # Test OAuth2-enabled client functionality
        pass
    
    async def test_scope_elevation_flow(self):
        # Test automatic scope elevation
        pass
```

### Integration Testing

#### Mock OAuth2 Server

```python
# tests/fixtures/mock_oauth2_server.py
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

class MockOAuth2Server:
    """Mock OAuth2 server implementing RFC 8693 for testing."""
    
    def __init__(self):
        self.app = FastAPI()
        self._setup_routes()
        self.client = TestClient(self.app)
    
    def _setup_routes(self):
        @self.app.post("/oauth/token")
        async def token_exchange(request):
            # Mock RFC 8693 token exchange implementation
            pass
    
    def get_token_endpoint(self) -> str:
        return "http://testserver/oauth/token"
```

#### Provider Compatibility Tests

Test with real OAuth2 providers:

```python
# test_provider_compatibility.py
@pytest.mark.integration
class TestProviderCompatibility:
    
    @pytest.mark.parametrize("provider", ["auth0", "keycloak", "azure_ad"])
    async def test_real_provider_integration(self, provider):
        # Test against real OAuth2 providers (requires credentials)
        config = get_provider_config(provider)
        # ... test integration
```

### Performance Testing

#### Token Cache Performance

```python
# test_performance.py
class TestPerformance:
    def test_cache_performance(self):
        cache = TokenCache()
        # Test cache performance with many tokens
        pass
    
    async def test_concurrent_token_requests(self):
        # Test thread safety and performance under load
        pass
```

## Performance Considerations

### Token Caching Strategy

- **Scope-based Caching**: Cache tokens by exact scope combinations
- **Compatible Token Reuse**: Use tokens with broader scopes for narrower requests
- **TTL Management**: Respect token expiration times
- **Memory Efficiency**: Limit cache size and implement LRU eviction

### Network Optimization

- **Connection Pooling**: Reuse HTTP connections for token exchange
- **Retry Logic**: Exponential backoff for failed exchanges
- **Timeout Configuration**: Configurable timeouts for token operations
- **Async Implementation**: Non-blocking token exchange for async clients

### Performance Metrics

Expected performance characteristics:

| Operation | Without OAuth2 | With OAuth2 (Cache Hit) | With OAuth2 (Cache Miss) |
|-----------|----------------|-------------------------|---------------------------|
| API Call  | ~10ms          | ~12ms                   | ~150ms                    |
| Token Lookup | N/A          | ~1ms                    | ~100ms                    |
| Cache Size | N/A           | ~1KB per cached token   | N/A                       |

### Optimization Strategies

1. **Eager Token Exchange**: Pre-exchange tokens for known scope requirements
2. **Batch Operations**: Group operations requiring same scopes
3. **Smart Caching**: Cache tokens with broader scopes more aggressively
4. **Background Refresh**: Refresh tokens before expiration in background

## Security Considerations

### Token Storage

- **Memory Only**: Tokens stored only in memory, never persisted to disk
- **Process Isolation**: Tokens isolated per client instance
- **Secure Disposal**: Clear tokens from memory when no longer needed

### HTTPS Requirements

- **Default HTTPS**: Require HTTPS for token endpoints by default
- **Certificate Validation**: Validate SSL certificates by default
- **Configurable**: Allow disabling for development/testing only

### Scope Validation

- **Server-side Validation**: Primary validation happens on Llama Stack server
- **Client-side Hints**: Client-side validation provides early feedback
- **Standard Scopes**: Only allow standard Llama Stack scopes

### Error Information

- **Limited Disclosure**: Don't expose sensitive token information in errors
- **Audit Logging**: Log security-relevant events for monitoring
- **Rate Limiting**: Respect OAuth2 provider rate limits

## Implementation Timeline

### Phase 1: Foundation (2-3 weeks)
- [ ] Implement OAuth2 type definitions
- [ ] Create token cache implementation
- [ ] Implement basic OAuth2 manager
- [ ] Add unit tests for core components

### Phase 2: Client Integration (2-3 weeks)
- [ ] Enhance LlamaStackClient with OAuth2 support
- [ ] Implement method decorators for scope resolution
- [ ] Add async client support
- [ ] Ensure backward compatibility

### Phase 3: Testing & Validation (2-3 weeks)
- [ ] Implement comprehensive test suite
- [ ] Create mock OAuth2 server for testing
- [ ] Test with real OAuth2 providers
- [ ] Performance testing and optimization

### Phase 4: Documentation & Release (1-2 weeks)
- [ ] Write comprehensive documentation
- [ ] Create migration guides
- [ ] Prepare release notes
- [ ] Submit pull request for review

## Conclusion

This implementation plan provides a comprehensive roadmap for adding OAuth2 token exchange capabilities to `llama-stack-client-python`. The design prioritizes backward compatibility, standards compliance, and user experience while solving the core problem of dynamic scope elevation without losing agent session state.

Key benefits of this approach:

- ✅ **Preserves existing functionality** - No breaking changes
- ✅ **Standards compliant** - Implements RFC 8693 OAuth2 Token Exchange
- ✅ **Performance optimized** - Intelligent caching and minimal exchange requests
- ✅ **Security focused** - Secure token handling and validation
- ✅ **Developer friendly** - Simple configuration and automatic scope management

The implementation enables seamless OAuth2 integration while maintaining the simplicity and reliability that developers expect from the Llama Stack client SDK. 