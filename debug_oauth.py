#!/usr/bin/env python3
"""Debug script to inspect OAuth authentication flow.

Run this to capture and analyze what headers Claude is actually sending.
"""

import sys
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
import json


async def debug_endpoint(request):
    """Debug endpoint that logs all request details."""
    print("\n" + "="*80)
    print("INCOMING MCP REQUEST")
    print("="*80)
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Path: {request.url.path}")
    print()
    
    print("HEADERS:")
    for key, value in request.headers.items():
        # Mask sensitive values but show presence
        if 'key' in key.lower() or 'secret' in key.lower():
            display_value = value[:20] + "..." if len(value) > 20 else value
        elif 'authorization' in key.lower():
            if value.startswith("Bearer "):
                display_value = f"Bearer {value[7:30]}..."
            else:
                display_value = value[:30] + "..."
        else:
            display_value = value
        print(f"  {key}: {display_value}")
    print()
    
    # Check for OAuth
    auth_header = request.headers.get("authorization", "")
    has_oauth = auth_header.startswith("Bearer ")
    has_api_key = "x-iriusrisk-api-key" in [k.lower() for k in request.headers.keys()]
    
    print("AUTHENTICATION DETECTION:")
    print(f"  Authorization header present: {bool(auth_header)}")
    print(f"  OAuth Bearer token: {has_oauth}")
    print(f"  X-IriusRisk-API-Key header: {has_api_key}")
    print()
    
    if has_oauth:
        print("✅ OAuth mode would be used")
        token = auth_header[7:]
        print(f"   Token length: {len(token)}")
        print(f"   Token preview: {token[:50]}...")
    elif has_api_key:
        print("✅ Direct API key mode would be used")
    else:
        print("❌ NO AUTHENTICATION DETECTED")
        print("   Claude might not be sending auth headers!")
    print()
    
    # Body
    if request.method == "POST":
        body = await request.body()
        body_str = body.decode()[:500]
        print(f"BODY (first 500 chars):")
        try:
            body_json = json.loads(body.decode())
            print(json.dumps(body_json, indent=2)[:500])
        except:
            print(body_str)
    
    print("="*80)
    print()
    
    # Return a dummy response
    return JSONResponse({
        "status": "debug",
        "has_oauth": has_oauth,
        "has_api_key": has_api_key,
        "auth_detected": has_oauth or has_api_key
    })


app = Starlette(
    routes=[
        Route("/mcp", debug_endpoint, methods=["GET", "POST"]),
        Route("/{path:path}", debug_endpoint, methods=["GET", "POST", "OPTIONS"]),
    ]
)


if __name__ == "__main__":
    print("="*80)
    print("OAUTH DEBUG SERVER")
    print("="*80)
    print()
    print("This server logs all incoming requests to help debug OAuth authentication.")
    print()
    print("Server: http://localhost:8080/mcp")
    print()
    print("Point Claude to this URL (or via nginx proxy) to see what headers it's sending.")
    print()
    print("Press Ctrl+C to stop")
    print("="*80)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


