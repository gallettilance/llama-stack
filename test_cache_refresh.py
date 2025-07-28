#!/usr/bin/env python3
"""
Simple test script to check cache refresh functionality.
"""

import asyncio
import httpx
import json

async def test_cache_refresh():
    """Test the cache refresh endpoint."""
    
    # Configuration
    base_url = "http://localhost:8321"
    auth_token = "your-token-here"  # Replace with your actual token
    
    print(f"Testing cache refresh at {base_url}")
    
    # Test 1: Check if admin API is accessible
    try:
        async with httpx.AsyncClient() as client:
            # Try to access the cache refresh endpoint
            url = f"{base_url}/v1/admin/cache/refresh"
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            
            print(f"Making POST request to {url}")
            response = await client.post(url, headers=headers)
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                print("✅ Cache refresh endpoint is accessible!")
            else:
                print(f"❌ Cache refresh failed with status {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error testing cache refresh: {e}")

if __name__ == "__main__":
    asyncio.run(test_cache_refresh()) 