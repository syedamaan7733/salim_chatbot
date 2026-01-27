import os
import requests
from app import cache

def set_token():
    print("setting token")
    url = os.getenv("LOGIN_URL")
    if not url:
        print("LOGIN_URL not set, using dummy token for local testing")
        token = "dummy_token_for_local_testing"
        cache.set('api_token', token)
        return token
        
    payload = f"grant_type=password&client_id=ipmessaging-client&username={os.getenv('LOGIN_USERNAME')}&password={os.getenv('LOGIN_PASSWORD')}"
    headers = {
        "cache-control": "no-cache",
        "content-type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.request("POST", url, data=payload, headers=headers).json()
        token = response.get('access_token')
    except Exception as e:
        print(f"Error fetching token: {e}")
        token = "dummy_token_error"

    cache.set('api_token', token)
    return token
    
    
def get_token():
    print("getting token")
    token = cache.get('api_token')
    return token if token else set_token()