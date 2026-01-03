#!/usr/bin/env python3
import requests
import json

# Get a free HTTPS tunnel URL
try:
    # Use localtunnel API to get a tunnel
    response = requests.post('https://api.localtunnel.me/tunnels', json={'port': 8000})
    if response.status_code == 200:
        data = response.json()
        https_url = data.get('url', '')
        if https_url:
            print(f"HTTPS URL: {https_url}")
            print(f"Facebook redirect URI should be: {https_url}/facebook/callback")
        else:
            print("Failed to get HTTPS URL from localtunnel")
    else:
        print("Failed to create tunnel")
except Exception as e:
    print(f"Error: {e}")
    print("Manual approach: Use https://ngrok.com or https://serveo.net")
