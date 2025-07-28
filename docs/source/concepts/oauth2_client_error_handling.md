# OAuth2 Client-Side Error Handling and Scope Elevation

## Overview

This guide explains how to handle OAuth2 scope-based authentication errors in client-side applications and implement scope elevation to request additional permissions when needed.

## Understanding Scope-Based Authentication

Llama Stack uses OAuth2 scopes to control access to different API endpoints. When your client application receives a `401 Unauthorized` error with insufficient scopes, you need to handle this gracefully and potentially request additional permissions.

### Common Error Scenarios

1. **Missing Scopes**: Token has no valid Llama Stack scopes
2. **Insufficient Scopes**: Token has some scopes but not the ones required for the requested operation
3. **Expired Token**: Token is valid but has expired
4. **Invalid Token**: Token format is invalid or from wrong issuer

## Error Response Format

When scope validation fails, Llama Stack returns a `401 Unauthorized` response with detailed error information:

```json
{
  "error": {
    "message": "Insufficient OAuth2 scopes for models API. Required: llama:models:write, llama:admin"
  }
}
```

## Client-Side Error Handling Strategies

### Strategy 1: Graceful Degradation

Handle scope errors by disabling features that require missing permissions:

```javascript
// React/JavaScript Example
class LlamaStackClient {
  constructor(apiKey, oauth2Config) {
    this.apiKey = apiKey;
    this.oauth2Config = oauth2Config;
    this.userScopes = new Set();
  }

  async makeRequest(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      if (response.status === 401) {
        const errorData = await response.json();
        
        // Check if it's a scope error
        if (errorData.error?.message?.includes('Insufficient OAuth2 scopes')) {
          const requiredScopes = this.extractRequiredScopes(errorData.error.message);
          const missingScopes = this.getMissingScopes(requiredScopes);
          
          // Handle scope error gracefully
          return this.handleScopeError(missingScopes, endpoint);
        }
        
        // Handle other auth errors
        throw new Error('Authentication failed');
      }

      return response;
    } catch (error) {
      throw error;
    }
  }

  extractRequiredScopes(errorMessage) {
    // Extract scopes from error message like "Required: llama:models:write, llama:admin"
    const match = errorMessage.match(/Required: (.+)$/);
    if (match) {
      return match[1].split(', ').map(scope => scope.trim());
    }
    return [];
  }

  getMissingScopes(requiredScopes) {
    return requiredScopes.filter(scope => !this.userScopes.has(scope));
  }

  handleScopeError(missingScopes, endpoint) {
    // Option 1: Show user-friendly error
    console.warn(`Missing scopes for ${endpoint}: ${missingScopes.join(', ')}`);
    
    // Option 2: Trigger scope elevation flow
    return this.requestScopeElevation(missingScopes);
  }
}
```

### Strategy 2: Automatic Scope Elevation

Implement automatic token exchange to request additional scopes:

```javascript
class OAuth2ScopeManager {
  constructor(oauth2Config) {
    this.tokenEndpoint = oauth2Config.tokenEndpoint;
    this.clientId = oauth2Config.clientId;
    this.clientSecret = oauth2Config.clientSecret;
  }

  async requestScopeElevation(currentToken, requiredScopes) {
    try {
      const response = await fetch(this.tokenEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
          grant_type: 'urn:ietf:params:oauth:grant-type:token-exchange',
          client_id: this.clientId,
          client_secret: this.clientSecret,
          subject_token: currentToken,
          subject_token_type: 'urn:ietf:params:oauth:token-type:access_token',
          scope: requiredScopes.join(' '),
          requested_token_type: 'urn:ietf:params:oauth:token-type:access_token'
        })
      });

      if (response.ok) {
        const tokenData = await response.json();
        return tokenData.access_token;
      } else {
        throw new Error(`Token exchange failed: ${response.status}`);
      }
    } catch (error) {
      console.error('Scope elevation failed:', error);
      throw error;
    }
  }
}
```

### Strategy 3: User Consent Flow

Prompt the user for consent before requesting additional scopes:

```javascript
class UserConsentManager {
  async promptForScopeConsent(missingScopes) {
    const scopeDescriptions = {
      'llama:inference': 'Access to run AI models and generate responses',
      'llama:models:read': 'View available AI models',
      'llama:models:write': 'Register and manage AI models',
      'llama:agents:read': 'View agent sessions and history',
      'llama:agents:write': 'Create and manage agent sessions',
      'llama:tools': 'Execute tools and workflows',
      'llama:safety': 'Apply content safety filters',
      'llama:eval': 'Run model evaluations and benchmarks',
      'llama:admin': 'Full administrative access'
    };

    const scopeList = missingScopes.map(scope => 
      `• ${scope}: ${scopeDescriptions[scope] || 'Additional permissions'}`
    ).join('\n');

    const message = `This action requires additional permissions:\n\n${scopeList}\n\nDo you want to grant these permissions?`;
    
    return new Promise((resolve) => {
      const confirmed = window.confirm(message);
      resolve(confirmed);
    });
  }
}
```

## Implementation Examples

### React Hook for Scope-Aware API Calls

```javascript
import { useState, useCallback } from 'react';

export function useLlamaStackAPI() {
  const [userScopes, setUserScopes] = useState(new Set());
  const [isElevatingScopes, setIsElevatingScopes] = useState(false);

  const makeAuthenticatedRequest = useCallback(async (endpoint, options = {}) => {
    try {
      const response = await fetch(`/api${endpoint}`, {
        ...options,
        headers: {
          'Authorization': `Bearer ${getStoredToken()}`,
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      if (response.status === 401) {
        const errorData = await response.json();
        
        if (errorData.error?.message?.includes('Insufficient OAuth2 scopes')) {
          return await handleScopeError(errorData, endpoint, options);
        }
      }

      return response;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }, []);

  const handleScopeError = async (errorData, originalEndpoint, originalOptions) => {
    const requiredScopes = extractRequiredScopes(errorData.error.message);
    const missingScopes = requiredScopes.filter(scope => !userScopes.has(scope));

    if (missingScopes.length === 0) {
      throw new Error('Unexpected scope error');
    }

    // Try automatic scope elevation
    try {
      setIsElevatingScopes(true);
      const newToken = await requestScopeElevation(missingScopes);
      
      // Update stored token
      storeToken(newToken);
      
      // Update user scopes
      setUserScopes(prev => new Set([...prev, ...missingScopes]));
      
      // Retry original request with new token
      return await makeAuthenticatedRequest(originalEndpoint, originalOptions);
    } catch (elevationError) {
      // Fallback to user consent
      const userConsented = await promptForScopeConsent(missingScopes);
      
      if (userConsented) {
        // Retry with user consent
        return await handleScopeError(errorData, originalEndpoint, originalOptions);
      } else {
        throw new Error('User denied additional permissions');
      }
    } finally {
      setIsElevatingScopes(false);
    }
  };

  return {
    makeAuthenticatedRequest,
    isElevatingScopes,
    userScopes
  };
}
```

### Python Client with Scope Handling

```python
import requests
import jwt
from typing import Set, Optional

class LlamaStackClient:
    def __init__(self, api_key: str, oauth2_config: Optional[dict] = None):
        self.api_key = api_key
        self.oauth2_config = oauth2_config
        self.user_scopes = self._extract_scopes_from_token(api_key)
    
    def _extract_scopes_from_token(self, token: str) -> Set[str]:
        """Extract scopes from JWT token without validation."""
        try:
            # Decode without verification to extract claims
            decoded = jwt.decode(token, options={"verify_signature": False})
            scope_string = decoded.get("scope", "")
            return set(scope_string.split()) if scope_string else set()
        except:
            return set()
    
    def make_request(self, method: str, endpoint: str, **kwargs):
        """Make authenticated request with scope error handling."""
        try:
            response = requests.request(
                method,
                f"{self.base_url}{endpoint}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                **kwargs
            )
            
            if response.status_code == 401:
                error_data = response.json()
                if "Insufficient OAuth2 scopes" in error_data.get("error", {}).get("message", ""):
                    return self._handle_scope_error(error_data, method, endpoint, **kwargs)
            
            return response
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
    
    def _handle_scope_error(self, error_data: dict, method: str, endpoint: str, **kwargs):
        """Handle scope errors by attempting token exchange."""
        error_message = error_data["error"]["message"]
        required_scopes = self._extract_required_scopes(error_message)
        missing_scopes = required_scopes - self.user_scopes
        
        if not missing_scopes:
            raise Exception("Unexpected scope error")
        
        # Try automatic scope elevation
        try:
            new_token = self._request_scope_elevation(missing_scopes)
            self.api_key = new_token
            self.user_scopes = self._extract_scopes_from_token(new_token)
            
            # Retry original request
            return self.make_request(method, endpoint, **kwargs)
            
        except Exception as elevation_error:
            # Fallback to user prompt
            if self._prompt_user_consent(missing_scopes):
                return self._handle_scope_error(error_data, method, endpoint, **kwargs)
            else:
                raise Exception("User denied additional permissions")
    
    def _extract_required_scopes(self, error_message: str) -> Set[str]:
        """Extract required scopes from error message."""
        import re
        match = re.search(r"Required: (.+)$", error_message)
        if match:
            return set(scope.strip() for scope in match.group(1).split(", "))
        return set()
    
    def _request_scope_elevation(self, missing_scopes: Set[str]) -> str:
        """Request token exchange for additional scopes."""
        if not self.oauth2_config:
            raise Exception("OAuth2 configuration required for scope elevation")
        
        response = requests.post(
            self.oauth2_config["token_endpoint"],
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": self.oauth2_config["client_id"],
                "client_secret": self.oauth2_config["client_secret"],
                "subject_token": self.api_key,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "scope": " ".join(missing_scopes),
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code}")
        
        token_data = response.json()
        return token_data["access_token"]
    
    def _prompt_user_consent(self, missing_scopes: Set[str]) -> bool:
        """Prompt user for consent to additional scopes."""
        scope_descriptions = {
            "llama:inference": "Run AI models and generate responses",
            "llama:models:read": "View available AI models",
            "llama:models:write": "Register and manage AI models",
            "llama:agents:read": "View agent sessions and history",
            "llama:agents:write": "Create and manage agent sessions",
            "llama:tools": "Execute tools and workflows",
            "llama:safety": "Apply content safety filters",
            "llama:eval": "Run model evaluations and benchmarks",
            "llama:admin": "Full administrative access"
        }
        
        scope_list = "\n".join(f"• {scope}: {scope_descriptions.get(scope, 'Additional permissions')}" 
                              for scope in missing_scopes)
        
        message = f"This action requires additional permissions:\n\n{scope_list}\n\nGrant these permissions? (y/n): "
        
        # In a real application, this would show a GUI dialog
        response = input(message)
        return response.lower() in ('y', 'yes')
```

## Best Practices

### 1. Graceful Error Handling

Always handle scope errors gracefully to avoid breaking user experience:

```javascript
// Good: Graceful handling
try {
  const result = await client.models.register(modelData);
  return result;
} catch (error) {
  if (isScopeError(error)) {
    // Show user-friendly message
    showNotification('This action requires additional permissions. Please contact your administrator.');
    return null;
  }
  throw error;
}

// Bad: Letting scope errors crash the app
const result = await client.models.register(modelData); // May throw scope error
```

### 2. Progressive Enhancement

Design your UI to work with limited scopes:

```javascript
function ModelManagementUI() {
  const { userScopes } = useLlamaStackAPI();
  
  return (
    <div>
      <h2>Model Management</h2>
      
      {/* Always show read access if available */}
      {userScopes.has('llama:models:read') && (
        <ModelList />
      )}
      
      {/* Only show write controls if user has write scope */}
      {userScopes.has('llama:models:write') && (
        <ModelRegistrationForm />
      )}
      
      {/* Show upgrade prompt if user lacks write scope */}
      {!userScopes.has('llama:models:write') && (
        <UpgradePermissionsPrompt />
      )}
    </div>
  );
}
```

### 3. Caching and State Management

Cache scope information to avoid repeated requests:

```javascript
class ScopeManager {
  constructor() {
    this.scopeCache = new Map();
    this.tokenCache = new Map();
  }
  
  async getTokenForScopes(requiredScopes) {
    const cacheKey = requiredScopes.sort().join(' ');
    
    // Check cache first
    if (this.tokenCache.has(cacheKey)) {
      const cached = this.tokenCache.get(cacheKey);
      if (Date.now() < cached.expiresAt) {
        return cached.token;
      }
    }
    
    // Request new token
    const newToken = await this.requestScopeElevation(requiredScopes);
    
    // Cache for 5 minutes
    this.tokenCache.set(cacheKey, {
      token: newToken,
      expiresAt: Date.now() + 5 * 60 * 1000
    });
    
    return newToken;
  }
}
```

### 4. User Experience Considerations

- **Clear Messaging**: Explain what permissions are needed and why
- **Progressive Disclosure**: Only request permissions when needed
- **Fallback Options**: Provide alternative workflows when permissions are denied
- **Loading States**: Show appropriate loading indicators during scope elevation

## Testing Scope Error Handling

### Unit Tests

```javascript
describe('Scope Error Handling', () => {
  it('should handle insufficient scopes gracefully', async () => {
    const mockResponse = {
      status: 401,
      json: () => Promise.resolve({
        error: {
          message: 'Insufficient OAuth2 scopes for models API. Required: llama:models:write, llama:admin'
        }
      })
    };
    
    const client = new LlamaStackClient('token');
    const result = await client.handleScopeError(mockResponse);
    
    expect(result.missingScopes).toContain('llama:models:write');
  });
  
  it('should retry request after scope elevation', async () => {
    // Test that original request is retried after successful scope elevation
  });
});
```

### Integration Tests

```python
def test_scope_elevation_flow():
    """Test complete scope elevation flow."""
    client = LlamaStackClient("initial_token", oauth2_config)
    
    # Mock initial request that fails with scope error
    with patch('requests.request') as mock_request:
        mock_request.return_value.status_code = 401
        mock_request.return_value.json.return_value = {
            "error": {
                "message": "Insufficient OAuth2 scopes for models API. Required: llama:models:write"
            }
        }
        
        # Mock successful token exchange
        with patch.object(client, '_request_scope_elevation') as mock_elevation:
            mock_elevation.return_value = "new_token"
            
            # Mock successful retry
            mock_request.return_value.status_code = 200
            mock_request.return_value.json.return_value = {"success": True}
            
            result = client.make_request("POST", "/v1/models", json={})
            
            assert result.status_code == 200
            assert client.api_key == "new_token"
```

## Troubleshooting

### Common Issues

1. **Token Exchange Fails**
   - Verify OAuth2 provider supports RFC 8693 token exchange
   - Check client credentials and endpoint configuration
   - Ensure current token is valid

2. **Scope Elevation Not Working**
   - Verify required scopes are available to the user
   - Check OAuth2 provider configuration
   - Review token exchange logs

3. **User Consent Denied**
   - Implement fallback workflows
   - Provide clear explanation of why permissions are needed
   - Offer alternative approaches

### Debug Information

Enable debug logging to troubleshoot scope issues:

```javascript
// Enable debug logging
localStorage.setItem('debug', 'llama-stack:scope');

// Check token scopes
const token = getStoredToken();
const decoded = jwt_decode(token);
console.log('Current scopes:', decoded.scope);
```

## Security Considerations

1. **Token Storage**: Store tokens securely (use secure storage, not localStorage for sensitive apps)
2. **Scope Validation**: Always validate scopes on both client and server
3. **User Consent**: Always get explicit user consent before requesting additional scopes
4. **Token Expiration**: Handle token expiration gracefully
5. **Error Logging**: Log scope errors for debugging but avoid logging sensitive token information

## Migration from Legacy Authentication

If migrating from legacy authentication:

1. **Phase 1**: Add scope validation while maintaining backward compatibility
2. **Phase 2**: Update client applications to handle scope errors
3. **Phase 3**: Remove legacy authentication support

```javascript
// Migration helper
class MigrationHelper {
  static isLegacyToken(token) {
    try {
      const decoded = jwt_decode(token);
      return !decoded.scope; // Legacy tokens don't have scope claim
    } catch {
      return true;
    }
  }
  
  static async migrateToScopedToken(legacyToken) {
    // Implementation depends on your OAuth2 provider
    // This might involve redirecting to authorization endpoint
  }
}
```

This comprehensive guide should help you implement robust client-side error handling for OAuth2 scope-based authentication in your Llama Stack applications. 