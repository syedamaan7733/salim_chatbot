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

def fetch_categories(page=1, limit=10):
    CATEGORY_API_URL = os.getenv('CATEGORY_API_URL')
    """
    Fetches categories from the external API with pagination.
    Returns the full response object matching the new API structure:
    {
        "categories": [...],
        "meta": { "total": 20, "page": 1, "limit": 10, "totalPages": 2 }
    }
    """
    try:
        # Construct URL with query parameters
        # Assumes CATEGORY_API_URL does not already have query params
        url = f"{CATEGORY_API_URL}?page={page}&limit={limit}"
        print("Fetching URL:", url)
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # New structure detection
            # If the API returns the structure directly
            if "categories" in data and "meta" in data:
                return data
            
            # Fallback for old structure if needed (optional, keeping safe)
            if data.get("success"):
                return {"categories": data.get("data", []), "meta": {}}
                
    except Exception as e:
        print(f"Error fetching categories: {e}")
    
    return {"categories": [], "meta": {}}

def send_whatsapp_message(mobile, message_payload):
    """
    Sends a message to the WhatsApp user using the configured provider.
    """
    url = os.getenv('WHATSAPP_PUSH_URL')
    if not url:
        print("Error: WHATSAPP_PUSH_URL not set in .env")
        return

    headers = {
        "Authorization": "Bearer EAAQyxuMGj6oBQn6mZAuR8nzBIpDhW5xOwInSgw5BePeTgZCCP6xjXVPq0a5I9wCOGGDGfZALr6bQsil43cPauoybuAmGHOL2s4YPCn9MLWUgKyZBWvo7VjEhqwYgaWtlKwK1ZABiXS6SBXLJTUhTynWxaCHKaQkqrDKdGv1VBdY1o7rM2DIyokZB7bSDnHMPBSPQZDZD",
        "Content-Type": "application/json",
        "User-Agent": "insomnia/10.0.0"
    }
    
    # Construct the full payload required by Meta Cloud API
    # The payload must include 'messaging_product' and 'recipient_type'
    full_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": mobile,
    }
    
    # Merge the specific message content (e.g., {'type': 'text', 'text': {...}})
    full_payload.update(message_payload)
    
    try:
        response = requests.post(url, json=full_payload, headers=headers)
        print(f"Send Message Response Status: {response.status_code}")
        print(f"Send Message Response Body: {response.text}")
        return response
    except Exception as e:
        print(f"Error sending message: {e}")

def get_category_list_message(page=1):
    """
    Generates the WhatsApp Interactive List Message payload with pagination.
    """
    # We fetch 9 items to fit 9 categories + 1 'More' button = 10 rows (WhatsApp Limit).
    data = fetch_categories(page=page, limit=9)
    categories = data.get("categories", [])
    meta = data.get("meta", {})
    
    total_pages = meta.get("totalPages", 1)
    current_page = meta.get("page", 1)
    
    rows = []
    
    # Logic: If we are not on the last page, we need to reserve one slot for "More"
    has_next_page = current_page < total_pages
    
    # Determine categories to display (Max 9)
    display_categories = categories[:9]
    
    for cat in display_categories:
        # Adapt to key names in new API (name, imageUrl) vs old (category)
        cat_name = cat.get("name") or cat.get("category", "Unknown")
        
        # Title limit is 24 chars
        title = cat_name[:24]
        rows.append({
            "id": cat_name,       # We'll use the name as ID to identify selection
            "title": title,
            "description": ""     # description is optional
        })
    
    # Add 'More' button if needed
    if has_next_page:
        next_page = current_page + 1
        rows.append({
            "id": f"KEY3_p_{next_page}",
            "title": "More...",
            "description": f"Page {current_page}/{total_pages}"
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
            "text": "सलीम फुटवियर"
        },
        "body": {
            "text": f"स्वागत है! कृपया उत्पाद देखने के लिए एक श्रेणी चुनें (Page {current_page}/{total_pages}):"
        },
        "footer": {
            "text": "नीचे दी गई सूची से चुनें"
        },
        "action": {
            "button": "श्रेणियाँ देखें",
            "sections": [
                {
                    "title": "कलेक्शन",
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
    PRODUCTS_REDIRECT_BASE_URL = os.getenv('PRODUCTS_REDIRECT_BASE_URL')

    # Encode category safely
    encoded_category = requests.utils.quote(category_name)
    link = f"{PRODUCTS_REDIRECT_BASE_URL}?category={encoded_category}"

    print(link)

    return {
        "type": "text",
        "text": {
            "body": f"Click the link below to view *{category_name}* collection:\n\n{link}",
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
        
        if message_type == "interactive":
            interactive = message_data.get("interactive", {})
            selection_id = None
            
            if interactive.get("type") == "list_reply":
                selection_id = interactive.get("list_reply", {}).get("id")
            elif interactive.get("type") == "button_reply":
                 selection_id = interactive.get("button_reply", {}).get("id")
            
            if selection_id:
                # Check for Pagination Key
                if selection_id.startswith("KEY3_p_"):
                    try:
                        page_str = selection_id.split("_p_")[1]
                        page = int(page_str)
                        print(f"User requested page {page}")
                        response_payload = get_category_list_message(page=page)
                        send_whatsapp_message(mobile, response_payload)
                        return
                    except Exception as e:
                        print(f"Error parsing page number: {e}")
                        # Fallback to page 1 in error case
                        response_payload = get_category_list_message(page=1)
                        send_whatsapp_message(mobile, response_payload)
                        return
                    
                print(f"User {mobile} selected category: {selection_id}")
                response_payload = get_link_message(selection_id)
                send_whatsapp_message(mobile, response_payload)
                return

        # Default action: Send Category List (Page 1)
        # This covers "text", "image", etc. - basically "Hi" or any other trigger
        print(f"Received message from {mobile}, sending category list.")
        response_payload = get_category_list_message(page=1)
        print(response_payload)
        send_whatsapp_message(mobile, response_payload)
        
    except Exception as e:
        print(f"Error in process_incoming_message: {e}")
