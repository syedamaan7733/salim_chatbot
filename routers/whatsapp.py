from flask import Blueprint, request
from utils.response import make_response
from routers_helper import salim_helper

bp_whatsapp = Blueprint('whatsapp', __name__)

@bp_whatsapp.route('/webhook/inbound-message', methods=['GET'])
def verify_webhook():
    """
    Webhook verification endpoint for WhatsApp providers (Meta Cloud API).
    
    When setting up the webhook in your provider's dashboard, they will send a GET request
    with query parameters: hub.mode, hub.verify_token, and hub.challenge.
    
    You should set a VERIFY_TOKEN in your .env file and match it here.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Get the verify token from environment (you should set this in .env)
    import os
    verify_token = os.getenv('WEBHOOK_VERIFY_TOKEN', 'salim_footwear_verify_token_123')
    
    # Check if mode and token are correct
    if mode == 'subscribe' and token == verify_token:
        # Respond with the challenge to verify the webhook
        return challenge, 200
    else:
        # Forbidden if verification fails
        return 'Verification failed', 403

@bp_whatsapp.route('/webhook/inbound-message', methods=['POST'])
def whatsapp_bot():
    """
    Webhook entry point for incoming WhatsApp messages.
    Routes processing to salim_helper.
    """
    data = request.get_json()
    salim_helper.process_incoming_message(data)
    return make_response(message="Success")

@bp_whatsapp.route('/delivery-report', methods=['POST'])
def whatsapp_delivery_report():
    """
    Webhook entry point for delivery reports.
    Currently just acknowledges receipt.
    """
    # data = request.get_json()
    # Logic to handle delivery reports can be added here if needed
    return make_response(message="Success")