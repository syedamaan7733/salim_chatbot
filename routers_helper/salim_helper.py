import os
import requests
import json
from dotenv import load_dotenv
from utils.access_token import get_token

load_dotenv()
# API Endpoint
# Redirect Base URL (Generic placeholder, can be updated)
# Redirect Base URL (Generic placeholder, can be updated)
PRODUCTS_REDIRECT_BASE_URL = os.getenv('PRODUCTS_REDIRECT_BASE_URL')

def fetch_categories():
    CATEGORY_API_URL = os.getenv('CATEGORY_API_URL')
    """
    Fetches categories from the external API.
    Returns a list of category objects.
    """
    try:
        print("CATEGORY_API_URL",CATEGORY_API_URL)
        response = requests.get(CATEGORY_API_URL)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("data", [])
    except Exception as e:
        print(f"Error fetching categories: {e}")
    return []

def send_whatsapp_message(mobile, message_payload):
    """
    Sends a message to the WhatsApp user using the configured provider.
    """
    url = os.getenv('WHATSAPP_PUSH_URL')
    if not url:
        print("Error: WHATSAPP_PUSH_URL not set in .env")
        return

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "User-Agent": "insomnia/10.0.0"
    }
    
    # Construct the full payload required by the provider/API
    full_payload = {
        "messages": [
            {
                "sender": os.getenv('WHATSAPP_BOT_NUMBER'),
                "to": mobile,
                "channel": "wa", 
                # Merge the specific message content
                **message_payload 
            }
        ],
        "responseType": "json"
    }
    
    try:
        response = requests.post(url, json=full_payload, headers=headers)
        print(f"Send Message Response Status: {response.status_code}")
        print(f"Send Message Response Body: {response.text}")
        return response
    except Exception as e:
        print(f"Error sending message: {e}")

def get_category_list_message():
    """
    Generates the WhatsApp Interactive List Message payload.
    """
    categories = fetch_categories()
    
    # WhatsApp Limit: Max 10 rows in a section
    valid_categories = categories[:10]
    
    rows = []
    for cat in valid_categories:
        cat_name = cat.get("category", "Unknown")
        # Title limit is 24 chars
        title = cat_name[:24]
        rows.append({
            "id": cat_name,       # We'll use the name as ID to identify selection
            "title": title,
            "description": ""     # description is optional
        })
        
    if not rows:
        return {
            "type": "text",
            "text": {"content": "Sorry, no categories available right now."}
        }

    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Salim Footwear"
            },
            "body": {
                "text": "Welcome! Please select a category to view products:"
            },
            "footer": {
                "text": "Select from the list below"
            },
            "action": {
                "button": "View Categories",
                "sections": [
                    {
                        "title": "Collections",
                        "rows": rows
                    }
                ]
            }
        }
    }

def get_link_message(category_name):
    """
    Generates the Text Message payload with the redirect link.
    """
    # Construct redirect link
    PRODUCTS_REDIRECT_BASE_URL = os.getenv('PRODUCTS_REDIRECT_BASE_URL')
    # Using quote to handle spaces and special chars in category name
    encoded_category = requests.utils.quote(category_name)
    link = f"{PRODUCTS_REDIRECT_BASE_URL}?category={encoded_category}"
    
    return {
        "type": "text",
        "text": {
            "content": f"Click the link below to view *{category_name}* collection:\n\n{link}",
            "preview_url": True
        }
    }

def process_incoming_message(data):
    """
    Main logic handler.
    If 'interactive' (selection) -> Send Link.
    Otherwise (any text) -> Send Category List.
    """
    try:
        print(f"Received Payload: {data}")
        
        message_data = None
        
        # Path 1: Standard Meta/WhatsApp Cloud API
        if "entry" in data and isinstance(data["entry"], list) and len(data["entry"]) > 0:
            entry = data["entry"][0]
            changes = entry.get("changes", [])
            if len(changes) > 0:
                value = changes[0].get("value", {})
                messages = value.get("messages", [])
                if len(messages) > 0:
                    message_data = messages[0]

        # Path 2: Direct Change Object (User's log content)
        elif "value" in data and "messages" in data["value"]:
             messages = data["value"].get("messages", [])
             if len(messages) > 0:
                 message_data = messages[0]

        # Path 3: Legacy/Simplified
        elif "message" in data:
            message_data = data["message"]

        if not message_data:
            print("Could not extract message from payload")
            return

        mobile = message_data.get("from")
        
        if not mobile:
            print("No mobile number found")
            return

        message_type = message_data.get("type")
        
        # Check if it's an interactive reply (User selected a list option or button)
        if message_type == "interactive":
            interactive = message_data.get("interactive", {})
            selection_id = None
            
            if interactive.get("type") == "list_reply":
                selection_id = interactive.get("list_reply", {}).get("id")
            elif interactive.get("type") == "button_reply":
                 selection_id = interactive.get("button_reply", {}).get("id")
            
            if selection_id:
                print(f"User {mobile} selected category: {selection_id}")
                response_payload = get_link_message(selection_id)
                send_whatsapp_message(mobile, response_payload)
                return

        # Default action: Send Category List
        # This covers "text", "image", etc. - basically "Hi" or any other trigger
        print(f"Received message from {mobile}, sending category list.")
        response_payload = get_category_list_message()
        print(response_payload)
        send_whatsapp_message(mobile, response_payload)
        
    except Exception as e:
        print(f"Error in process_incoming_message: {e}")
