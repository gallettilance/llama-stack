#!/usr/bin/env python3
"""
Debug script to check JWKS refresh and key validation.
"""

import asyncio
import httpx
import json
import jwt
from datetime import datetime

async def debug_jwks():
    """Debug JWKS refresh and key validation."""
    
    # Configuration - replace with your actual values
    jwks_uri = "https://your-auth-server/.well-known/jwks.json"  # Replace with your JWKS URI
    token = "your-jwt-token-here"  # Replace with your actual JWT token
    
    print(f"Debugging JWKS refresh and key validation")
    print(f"JWKS URI: {jwks_uri}")
    print(f"Token: {token[:20]}..." if len(token) > 20 else "Token: [empty]")
    print()
    
    try:
        # Step 1: Decode token header to get key ID
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "RS256")
        
        print(f"Token header:")
        print(f"  Key ID (kid): {kid}")
        print(f"  Algorithm: {alg}")
        print()
        
        # Step 2: Fetch current JWKS
        print("Fetching JWKS from server...")
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri, timeout=10)
            response.raise_for_status()
            jwks_data = response.json()
            
            keys = jwks_data.get("keys", [])
            print(f"JWKS response: {len(keys)} keys available")
            
            # Extract key IDs
            key_ids = [key.get("kid") for key in keys if key.get("kid")]
            print(f"Available key IDs: {key_ids}")
            print()
            
            # Check if our token's key ID is in the JWKS
            if kid in key_ids:
                print(f"✅ Key ID {kid} found in JWKS!")
                
                # Find the matching key
                matching_key = next((key for key in keys if key.get("kid") == kid), None)
                if matching_key:
                    print(f"Key details:")
                    print(f"  Algorithm: {matching_key.get('alg')}")
                    print(f"  Key type: {matching_key.get('kty')}")
                    print(f"  Use: {matching_key.get('use')}")
            else:
                print(f"❌ Key ID {kid} NOT found in JWKS!")
                print(f"This means your token was signed with a key that's no longer available.")
                print(f"Possible causes:")
                print(f"  1. Key rotation occurred and your token is using an old key")
                print(f"  2. JWKS endpoint is not returning the correct keys")
                print(f"  3. Token is malformed or from a different issuer")
                
    except Exception as e:
        print(f"❌ Error during JWKS debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_jwks()) 