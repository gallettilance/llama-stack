# OAuth2 Scope-Based Authentication

## Overview

Starting with this version, Llama Stack implements **OAuth2 scope-based authorization** for fine-grained access control to API endpoints. This is a **breaking change** that requires JWT tokens to include valid OAuth2 scopes.

## ⚠️ Breaking Changes

### What Changed

- **JWT tokens now REQUIRE OAuth2 scopes** in the `scope` claim
- **Tokens without valid scopes will be rejected** (deny-by-default security)
- **API access is now controlled by specific scope requirements**
- **Admin access requires explicit `llama:admin` scope**

### Before vs After

**Before (Legacy):**
```json
{
  "sub": "user123",
  "iss": "your-issuer",
  "aud": "llama-stack",
  "roles": ["admin"]
}
```
✅ **Result:** Full access based on roles/attributes

**After (OAuth2 Scopes Required):**
```json
{
  "sub": "user123", 
  "iss": "your-issuer",
  "aud": "llama-stack",
  "scope": "llama:inference llama:models:read"
}
```
✅ **Result:** Access only to inference and model reading

**Invalid Token (No Scopes):**
```json
{
  "sub": "user123",
  "iss": "your-issuer", 
  "aud": "llama-stack"
  // Missing scope claim
}
```
❌ **Result:** `401 Unauthorized - Token lacks required OAuth2 scopes`

## Standard OAuth2 Scopes

### API-Specific Scopes

| Scope | Description | API Access |
|-------|-------------|-------------|
| `llama:inference` | Access to inference APIs | `/v1/inference/*`, `/v1/openai/*` |
| `llama:models:read` | Read access to models | `GET /v1/models/*` |
| `llama:models:write` | Write access to models | `POST/PUT/DELETE /v1/models/*` |
| `llama:agents:read` | Read access to agents | `GET /v1/agents/*` |
| `llama:agents:write` | Write access to agents | `POST/PUT/DELETE /v1/agents/*` |
| `llama:tools` | Access to tool runtime | `/v1/tools/*` |
| `llama:toolgroups:read` | Read access to tool groups | `GET /v1/toolgroups/*` |
| `llama:toolgroups:write` | Write access to tool groups | `POST/PUT/DELETE /v1/toolgroups/*` |
| `llama:vector_dbs:read` | Read access to vector DBs | `GET /v1/vector_dbs/*` |
| `llama:vector_dbs:write` | Write access to vector DBs | `POST/PUT/DELETE /v1/vector_dbs/*` |
| `llama:safety` | Access to safety shields | `/v1/safety/*` |
| `llama:eval` | Access to evaluation APIs | `/v1/eval/*`, `/v1/benchmarks/*` |

### Administrative Scope

| Scope | Description | Access |
|-------|-------------|--------|
| `llama:admin` | **Full administrative access** | **All APIs and operations** |

> **Note:** The `llama:admin` scope grants access to all APIs, overriding individual scope requirements.

## Scope Requirements by API

### Inference APIs
- **Required Scopes:** `llama:inference` OR `llama:admin`
- **Endpoints:** 
  - `POST /v1/inference/chat-completion`
  - `POST /v1/inference/completion`
  - `POST /v1/inference/embeddings`
  - `POST /v1/openai/v1/chat/completions` (OpenAI compatibility)

### Models API
- **Read Operations:** `llama:models:read` OR `llama:admin`
  - `GET /v1/models`
  - `GET /v1/models/{model_id}`
- **Write Operations:** `llama:models:write` OR `llama:admin`
  - `POST /v1/models` (register)
  - `DELETE /v1/models/{model_id}` (unregister)

### Agents API  
- **Read Operations:** `llama:agents:read` OR `llama:admin`
  - `GET /v1/agents/sessions`
  - `GET /v1/agents/sessions/{session_id}`
- **Write Operations:** `llama:agents:write` OR `llama:admin`
  - `POST /v1/agents/sessions` (create)
  - `POST /v1/agents/sessions/{session_id}/messages` (send message)

## Migration Guide

### Step 1: Update Your OAuth2 Provider

Configure your OAuth2/OIDC provider to include Llama Stack scopes in JWT tokens:

**Example: Auth0 Configuration**
```javascript
// Add custom claim in Auth0 Action
exports.onExecutePostLogin = async (event, api) => {
  const scopes = [];
  
  // Map user roles to Llama Stack scopes
  if (event.user.app_metadata?.roles?.includes('admin')) {
    scopes.push('llama:admin');
  } else {
    // Grant specific scopes based on user type
    if (event.user.app_metadata?.type === 'data_scientist') {
      scopes.push('llama:inference', 'llama:models:read', 'llama:eval');
    } else if (event.user.app_metadata?.type === 'ml_engineer') {
      scopes.push('llama:inference', 'llama:models:read', 'llama:models:write');
    } else if (event.user.app_metadata?.type === 'app_developer') {
      scopes.push('llama:inference', 'llama:agents:read', 'llama:agents:write');
    }
  }
  
  api.accessToken.setCustomClaim('scope', scopes.join(' '));
};
```

**Example: Keycloak Configuration**
```yaml
# Client Scope Mapping
client_scopes:
  llama-stack-inference:
    name: "llama:inference"
    description: "Access to Llama Stack inference APIs"
  llama-stack-admin:
    name: "llama:admin" 
    description: "Full administrative access to Llama Stack"
```

### Step 2: Update Client Applications

Modify your client applications to request appropriate scopes:

**Example: Python Client**
```python
import requests
from requests.auth import HTTPBasicAuth

# Request token with required scopes
token_response = requests.post(
    "https://your-oauth-provider.com/oauth/token",
    data={
        "grant_type": "client_credentials",
        "scope": "llama:inference llama:models:read"  # Request specific scopes
    },
    auth=HTTPBasicAuth(client_id, client_secret)
)

token = token_response.json()["access_token"]

# Use token with Llama Stack
llama_response = requests.post(
    "https://your-llama-stack.com/v1/inference/chat-completion",
    headers={"Authorization": f"Bearer {token}"},
    json={"model": "llama-3", "messages": [...]}
)
```

**Example: JavaScript Client**
```javascript
// Request token with scopes
const tokenResponse = await fetch('https://your-oauth-provider.com/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code: authCode,
    scope: 'llama:inference llama:agents:write'
  })
});

const { access_token } = await tokenResponse.json();

// Use with Llama Stack
const llamaResponse = await fetch('https://your-llama-stack.com/v1/agents/sessions', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ agent_id: 'my-agent' })
});
```

### Step 3: Test Migration

Use these example tokens to verify your migration:

**Data Scientist Token:**
```json
{
  "sub": "data_scientist_user", 
  "scope": "llama:inference llama:models:read llama:eval llama:safety",
  "iss": "your-issuer",
  "aud": "llama-stack",
  "exp": 1234567890
}
```

**ML Engineer Token:**
```json
{
  "sub": "ml_engineer_user",
  "scope": "llama:inference llama:models:read llama:models:write llama:agents:read llama:agents:write llama:tools llama:eval",
  "iss": "your-issuer", 
  "aud": "llama-stack",
  "exp": 1234567890
}
```

**Admin Token:**
```json
{
  "sub": "admin_user",
  "scope": "llama:admin",
  "iss": "your-issuer",
  "aud": "llama-stack", 
  "exp": 1234567890
}
```

## User Role Examples

### Data Scientist
**Scopes:** `llama:inference llama:models:read llama:eval llama:safety`

**Can:**
- ✅ Run inference requests
- ✅ List and inspect available models
- ✅ Run evaluations and benchmarks
- ✅ Use safety shields

**Cannot:**
- ❌ Register or delete models
- ❌ Create agent sessions
- ❌ Execute tools
- ❌ Manage vector databases

### ML Engineer  
**Scopes:** `llama:inference llama:models:read llama:models:write llama:agents:read llama:agents:write llama:tools llama:eval`

**Can:**
- ✅ Everything a Data Scientist can do, plus:
- ✅ Register and manage models
- ✅ Create and manage agent sessions
- ✅ Execute tools and workflows

**Cannot:**
- ❌ Manage vector databases (unless explicitly granted)

### Application Developer
**Scopes:** `llama:inference llama:agents:read llama:agents:write llama:tools llama:safety`

**Can:**
- ✅ Build applications using inference
- ✅ Create interactive agent experiences  
- ✅ Execute tools for app functionality
- ✅ Apply safety measures

**Cannot:**
- ❌ Manage models (focused on app development, not model management)
- ❌ Run evaluations
- ❌ Access vector databases

### Administrator
**Scopes:** `llama:admin`

**Can:**
- ✅ **Everything** - full access to all APIs

## Backward Compatibility Options

### Legacy Token Support (Temporary)

If you need time to migrate, you can temporarily configure legacy token support by modifying the authentication provider to grant default scopes:

> **⚠️ Warning:** This reduces security and should only be used temporarily during migration.

```python
# In your OAuth2 provider configuration
# This is NOT recommended for production
default_migration_scopes = ["llama:admin"]  # Grants full access to legacy tokens
```

### Gradual Migration Strategy

1. **Phase 1:** Add scope claims to new tokens while maintaining legacy support
2. **Phase 2:** Monitor token usage and identify clients that need updating  
3. **Phase 3:** Remove legacy support and enforce OAuth2 scopes

## Error Messages

### Common Errors and Solutions

**Error:** `401 Unauthorized - Token lacks required OAuth2 scopes for Llama Stack access`
- **Cause:** JWT token missing `scope` claim or no valid scopes
- **Solution:** Update OAuth2 provider to include Llama Stack scopes

**Error:** `401 Unauthorized - Insufficient OAuth2 scopes for models API. Required: llama:models:write, llama:admin`
- **Cause:** Token has scopes but not the right ones for the requested operation
- **Solution:** Request token with appropriate scopes for your use case

**Example Error Response:**
```json
{
  "error": {
    "message": "Insufficient OAuth2 scopes for models API. Required: llama:models:write, llama:admin"
  }
}
```

## Security Benefits

### Enhanced Security Posture

1. **Principle of Least Privilege:** Users only get access to APIs they need
2. **Granular Control:** Separate read/write permissions for sensitive operations  
3. **Audit Trail:** OAuth2 scopes provide clear audit trail of permissions
4. **Deny by Default:** No access without explicit scope grants
5. **Standard Compliance:** Follows OAuth2.0 RFC specifications

### Access Control Matrix

| User Type | Inference | Models Read | Models Write | Agents | Tools | Safety | Eval | Admin |
|-----------|-----------|-------------|--------------|--------|-------|--------|------|-------|
| **Data Scientist** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **ML Engineer** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |  
| **App Developer** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Administrator** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Troubleshooting

### Debug Token Scopes

Use this script to debug your JWT token scopes:

```python
import jwt
import json

def debug_token_scopes(token):
    """Debug OAuth2 scopes in JWT token"""
    try:
        # Decode without verification for debugging (don't use in production)
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print("Token Claims:")
        print(json.dumps(decoded, indent=2))
        
        scope_claim = decoded.get('scope', '')
        scopes = scope_claim.split() if scope_claim else []
        
        print(f"\nExtracted Scopes: {scopes}")
        
        # Check against Llama Stack standard scopes
        valid_scopes = [
            'llama:inference', 'llama:models:read', 'llama:models:write',
            'llama:agents:read', 'llama:agents:write', 'llama:tools',
            'llama:vector_dbs:read', 'llama:vector_dbs:write', 
            'llama:safety', 'llama:eval', 'llama:admin'
        ]
        
        recognized = [s for s in scopes if s in valid_scopes]
        unrecognized = [s for s in scopes if s not in valid_scopes]
        
        print(f"Recognized Llama Stack scopes: {recognized}")
        if unrecognized:
            print(f"Unrecognized scopes: {unrecognized}")
            
        if not recognized:
            print("❌ No valid Llama Stack scopes found!")
        else:
            print("✅ Valid scopes found")
            
    except Exception as e:
        print(f"Error decoding token: {e}")

# Usage
debug_token_scopes("your.jwt.token.here")
```

### Validate Scope Requirements

Test what scopes are needed for specific API calls:

```python
from llama_stack.distribution.server.oauth2_scopes import get_required_scopes_for_api

# Check what scopes are needed
print("Inference API:", get_required_scopes_for_api("inference", "POST"))
print("Models Read:", get_required_scopes_for_api("models", "GET")) 
print("Models Write:", get_required_scopes_for_api("models", "POST"))
print("Agents Write:", get_required_scopes_for_api("agents", "POST"))
```

## Support

If you need help migrating to OAuth2 scopes:

1. **Check your OAuth2 provider documentation** for scope configuration
2. **Review the error messages** - they specify exactly which scopes are required
3. **Use the debug tools** provided above to inspect your tokens
4. **Start with `llama:admin` scope** for initial testing, then narrow down to specific scopes

The OAuth2 scope system provides much better security and auditability while following industry standards. The migration effort is worth the enhanced security posture! 