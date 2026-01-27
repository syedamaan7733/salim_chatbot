import os
import time
import json
import requests
import random
import jwt
import datetime
from datetime import timedelta, timezone
from utils.database import PostgreSQLConnector
from utils.access_token import get_token
from string import Template

import string

db = PostgreSQLConnector()

def get_previous_response_by_mobile(mobile):
    result = db.execute_query(f"SELECT response_id from whatsapp_conversation_history WHERE mobile = {mobile} ORDER BY created_on desc limit 1")
    return result[0]['response_id'] if result else 0

def get_response_details_details_by_response_id(response_id, user_message):
    results = db.execute_query(f"SELECT * from whatsapp_admin WHERE response_id = {response_id}")
    if not results:
        raise Exception("UnknownResponseID")
    if len(results) == 1:
        return results[0]
    map_result = None
    default_result = None
    for result in results:
        if result['map_user_message'] == user_message:
            map_result = result
        elif result['map_user_message'] is None:
            default_result = result
    if not map_result and not default_result:
        raise Exception("UnknownResponseID")        
    return map_result or default_result

def send_reply_to_user(respones_ids, data):
    if respones_ids and respones_ids!='None' and respones_ids!='null':
        for respones_id in respones_ids.split(','):
            result = db.execute_query(f"SELECT payload from whatsapp_request_collection WHERE id = {respones_id}")
            if not result:
                raise Exception("UnknownResponseID")
            if result[0]['payload']:
                payload = Template(json.dumps(result[0]['payload']))
                print(data)
                payload = json.loads(payload.substitute(**data))
                url = os.getenv('WHATSAPP_PUSH_URL')
                headers = {
                    "Authorization": f"Bearer {get_token()}",
                    "Content-Type": "application/json",
                    "User-Agent": "insomnia/2023.5.8"
                }
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    response_as_json = response.json()
                    create_message(data.get('mobile'), response_as_json.get('responseId'))
                print(response.text)
                if len(respones_ids) != 1:
                    time.sleep(0.5)
    
def record_user_conversation(mobile, user_message, response_id):
    if response_id!='None' and response_id!='null':
        data = {
            "mobile":mobile,
            "message":user_message,
            "response_id":response_id
        }
        db.insert('whatsapp_conversation_history', data)
    
def execute_queries(queries, data):
    for query in queries:
        results = db.execute_query(query.format(**data))
        if query[:6].strip().upper() == 'SELECT' and results:
            data.update(results[0])
    return data

def get_timestamps():
    current_time = datetime.datetime.now() 
    return current_time, current_time

def generate_message_id(length=50):
    characters = string.ascii_letters + string.digits
    message_id = ''.join(random.choice(characters) for _ in range(length))
    return message_id

def create_message(mobile, response_id):
    message_type = 'bot'
    original_message_id = generate_message_id()
    createdAt,updatedAt = get_timestamps()
    db.execute_query(f"""insert into messages (mobile,"responseId","messageType","originalMessageId","createdAt","updatedAt") values ('{mobile}','{response_id}','{message_type}','{original_message_id}','{createdAt}', '{updatedAt}')""")

def is_belstar_user(mobile, **kwargs):
    belstar_response = get_loan_details(mobile)
    response = belstar_response['Response'] if 'Response' in belstar_response and belstar_response['Response'] else []
    return type(response) is list and response and response[0] and 'Status' in response[0] and str(response[0]['Status']) == '1'

def get_employee_name(mobile,**kwargs):
    results = db.execute_query(f'select name from employees where employees."phoneNumber" = \'{mobile}\';')
    return {"employee_name": results[0]['name']}

def check_employee_or_user(mobile, **kwargs):
    results = db.execute_query(f'select id from employees where employees."phoneNumber" = \'{mobile}\';')
    if results:
        update_session_variables(mobile, {"employee_id": results[0]['id']})
        kitchen_availability = db.execute_query('select id from kitchen_timings where current_time between kitchen_timings."startTime" and kitchen_timings."endTime" and kitchen_timings."isActive" is true')
        if kitchen_availability:
            return 'Kitchen Open'
        else:
            return 'Kitchen Close'
    return fetch_loan_details(mobile, **kwargs)

def menu_details(**kwargs):
    menu = ''
    # Define IST timezone offset (UTC+5:30)
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    # Get current date and time in IST
    ist_time = datetime.datetime.now(ist_offset)
    # Get the full date and time in IST
    current_day = ist_time.strftime('%A')
    menu_list = db.execute_query('SELECT id, menu_master."itemName", price, description FROM menu_master WHERE menu_master."isActive" IS TRUE')
    if menu_list:
        item = menu_list[0]["itemName"]

    daily_menu = db.execute_query(f"""SELECT dishes FROM daily_menu WHERE "dayOfWeek" ILIKE '{current_day}'""")
    if daily_menu:
        daily_menu = daily_menu[0]["dishes"]

    daily_menu_dict = {item: daily_menu}

    count = 1
    for item in menu_list:
        description = daily_menu_dict.get(item["itemName"], item["description"])
        menu += f"{count}. *{item['itemName']}*: \\n{description} - ₹{item['price']}\\n"
        count += 1
    return {"menu_details": menu}

def format_time(time_obj):
    """Convert datetime.time to 12-hour AM/PM format."""
    return time_obj.strftime("%I:%M %p")  # Format as HH:MM AM/PM

def show_kitchen_time(**kwargs):
    kitchen_time = db.execute_query(f"""
        SELECT 
            ("startTime" + INTERVAL '5 hours 30 minutes') AS startTime_IST,
            ("endTime" + INTERVAL '5 hours 30 minutes') AS endTime_IST
        FROM 
            kitchen_timings;
    """)

    if kitchen_time:
        start_time_ist = kitchen_time[0].get("starttime_ist")
        end_time_ist = kitchen_time[0].get("endtime_ist")

        start_time_formatted = start_time_ist.strftime("%I:%M %p")
        end_time_formatted = end_time_ist.strftime("%I:%M %p")

        open_time = f"{start_time_formatted} to {end_time_formatted}"

    return {"timings" : open_time}

def fetch_loan_details(mobile, **kwargs):
    if not is_belstar_user(mobile):
        return False
    belstar_response = get_loan_details(mobile)['Response']
    loan_details = []
    for i in belstar_response:
        loan_details.append(i)
    if not loan_details:
        return False
    if len(loan_details) == 1:
        return "Single Loan"
    else:
        return "Multiple Loans"
    
def update_session_variables(mobile,data):
    query = f"select session_variables from user_session where mobile = '{mobile}'"
    results = db.execute_query(query)
    if results:
        session_variables = results[0]['session_variables']
        session_variables.update(data)
        session_variables = json.dumps(session_variables).replace("'","''")
        query = f"""update user_session set session_variables = '{session_variables}' where mobile = {mobile}"""
    else:
        data= json.dumps(data).replace("'","''")
        query = f"""INSERT INTO "user_session"("mobile","session_variables") VALUES('{mobile}','{data}');"""
    db.execute_query(query)
    return True



def get_session_variables(mobile, key):
    query = f"select session_variables from user_session where mobile = '{mobile}'"
    results = db.execute_query(query)
    return results[0]['session_variables'][key]

    
def update_course(mobile,user_message, **kwargs):
    items = []
    if user_message == 'Main Course':
        items.append({
                "menuItemId": 1,
                "quantity": 1
            })
    elif user_message == 'Buttermilk':
        items.append({
                "menuItemId": 2,
                "quantity": 1
            })
    else:
        items.extend([{
                "menuItemId": 1,
                "quantity": 1
            },
            {
                "menuItemId": 2,
                "quantity": 1
            }])
    update_session_variables(mobile, {"items": items})
    return True

def update_order_for(user_message, mobile, **kwargs):
    if user_message == "Myself":
        user_message = "SELF"
    else:
        user_message = "OTHERS"
    update_session_variables(mobile, {"order_for": user_message})
    return True

def place_order(user_message, mobile, **kwargs):
    url = "https://chatbotapp.belstar.in/orders/food-order"
    order_for = get_session_variables(mobile, 'order_for')
    payload = {
        "employeeId": get_session_variables(mobile, 'employee_id'),
        "orderType": order_for,
        "items": get_session_variables(mobile, 'items'),
    }
    if order_for == 'OTHERS':
        payload.update({
            "orderedForName": user_message
        })
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "insomnia/10.0.0",
        "x-api-key": "2e3d5186-88d7-4236-b0df-62f55d7a4083",
        "x-secret-key": "558b8106-5851-414e-b069-cc5d8226d048",
        "Cookie": "cookiesession1=678A3E3FF3AF63A2F487ADDDADD89D54"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    print(response.text)
    return True


def update_butter_count(mobile, user_message, **kwargs):
    # Check user_message integer or not if it is not integer return False
    try:
        user_message = int(user_message)
        # Check user_messsage is greater than 0 if not return False
        if user_message < 1:
            return False
    except:
        return False
    update_session_variables(mobile, {"butter_count": user_message})
    return True

def update_main_course_count(mobile, user_message, **kwargs):
    # Check user_message integer or not if it is not integer return False
    try:
        user_message = int(user_message)
        if user_message < 1:
            return False
    except:
        return False
    update_session_variables(mobile, {"main_course": user_message})
    return True
        
def summarize_order(mobile, **kwargs):
    course = get_session_variables(mobile, 'course')
    if course == 'Both':
        main_course_total = get_session_variables(mobile, 'main_course')
        butter_total = get_session_variables(mobile, 'butter_count')
        return {
            "order": f"Main Course - {main_course_total}\\nButter Milk- {butter_total}",
            "total": main_course_total * 120 + butter_total * 40
        }
    elif course == 'Main Course':
        main_course_total = get_session_variables(mobile, 'main_course')
        return {
            "order": f"Main Course - {main_course_total}",
            "total": main_course_total * 120
        }
    else:
        butter_total = get_session_variables(mobile, 'butter_count')
        return {
            "order": f"Butter Milk- {butter_total}",
            "total": butter_total * 40
        }
        

def construct_loan_details(mobile, **kwargs):
    if not is_belstar_user(mobile):
        return False
    belstar_response = get_loan_details(mobile)['Response']
    user_name = belstar_response[0]['Name']
    loan_details = []
    for index,i in enumerate(belstar_response):
        loan_details.append(f"{index+1}. Loan Number: {i['AccountID']} | Outstanding Amount: ₹{i['TotalODAmt']}")
    return {"user_name":user_name, "loan_details":"\n".join(loan_details).replace("\n","\\n")}

def extract_loan_details(mobile,user_message, **kwargs):
    belstar_response = get_loan_details(mobile)['Response']
    invalid_payload = {"messages": [{"sender": os.getenv('WHATSAPP_BOT_NUMBER'), "to": mobile, "type": "text", "channel": "wa", "text": {"content": f"The option you selected is not valid. Please choose a serial number from the list {'(1 - ' + str(len(belstar_response)) +')' if len(belstar_response)>1 else ''} to proceed."}}]}
    try:
        user_message = int(user_message)
        if user_message > len(belstar_response):
            send_custom_message(mobile, invalid_payload)
            return False   
    except:
        send_custom_message(mobile, invalid_payload)
        return False
    user_name = belstar_response[int(user_message)-1]['Name']
    due_amount = belstar_response[int(user_message)-1]['TotalODAmt']
    account_id = belstar_response[int(user_message)-1]['AccountID']
    due_date = format_user_readable_date(belstar_response[int(user_message)-1]['DueDate'])
    variables = json.dumps({"account_id":account_id, "user_name": user_name,"due_amount":due_amount,"due_date":due_date,"token_data":{
            "recipient": mobile,
            "messageId": kwargs.get('message_id'),
            "collectionType": "bot", 
            "campaignId": None ,
            "accountId": account_id,
            "amount":due_amount,
            "clientName": user_name
            }}).replace("'","''")
    db.execute_query(f"update user_session set session_variables = '{variables}' where mobile = '{mobile}'")
    return {"serial_number": user_message, "due_amount": due_amount, "due_date": due_date, "account_id": account_id}

def get_loan_details(mobile, **kwargs):
    if str(mobile) in ['918778784990', '8778784990', '919965048100', '9965048100']:
        return {
            'Response': [
                {
                    'TotalODAmt': 1,
                    'Name': 'Mohanaprasath',
                    'DueDate' : '2024-09-18T12:54:45',
                    'Status': 1,
                    'AccountID': 23193934
                },
                {
                    'TotalODAmt': 10,
                    'Name': 'Mohanaprasath',
                    'DueDate' : '2024-09-25T12:54:45',
                    'Status': 1,
                    'AccountID': 23193979
                }
            ]
        }
    url = "https://belstar.brnetsaas.com/BELSTARBRConClientAPI/V1/BrNetConnect"
    mobile = str(mobile)
    payload = {
            "Method": "GetCustDetailMob",
            "MobileNumber": mobile[2:] if len(mobile) == 12 else mobile
        }
    headers = {
            "Authorization": "BELSTAR 311e7dfcfc10450aa283be45d722f41a:dpdhWQWOyhX+scTOoLZ7CSLDVJaMnII7F6d7RGAl4ho=:027a071be3354827b97269912c42326f:1704356249:8.3",
            "Content-Type": "application/json"
        }
    response = requests.get(url=url,
                            json=payload,
                            headers=headers)
    response.raise_for_status()
    return response.json()

def generate_token(data):
    secret = os.getenv('PAY_NOW_BUTTON_JWT_SECRET_KEY')
    # Create the token, similar to the JavaScript version, and set expiration to 24 hours
    token = jwt.encode(
        {**data, 'exp': datetime.datetime.now() + datetime.timedelta(hours=24)}, 
        secret, 
        algorithm="HS256"
    )
    return token

def format_user_readable_date(date_str):
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    return date_obj.strftime("%d-%m-%Y")

    
def generate_pay_now_messages(mobile, **kwargs):
    session_variable = db.execute_query(f"select session_variables from user_session where mobile = '{mobile}'")[0]['session_variables']
    token = generate_token(session_variable['token_data'])
    payload = {
            "messages": [
                {
                "sender": os.getenv('WHATSAPP_BOT_NUMBER'),
                "to": mobile,
                "channel": "wa",
                "type": "template",
                "template": {
                    "body": [
                    {
                        "type": "text",
                        "text": str(session_variable['due_amount']),
                    },
                    {
                        "type": "text",
                        "text": str(session_variable['account_id']),
                    },
                    ],
                    "buttons": [
                    {
                        "index": "0",
                        "subType": "callToAction",
                        "parameters": {
                        "type": "text",
                        "text": f"messages/paynow?amt={session_variable['due_amount']}&tkn={token}",
                        },
                    },
                    ],
                    "templateId": "bot_paymet_message",
                    "langCode": "en",
                },
                },
            ],
            "responseType": "json",
            }
    send_custom_message(mobile, payload)
    return True
            
    
    
def get_due_amount(mobile, **kwargs):
    session_variable = db.execute_query(f"select session_variables from user_session where mobile = '{mobile}'")[0]['session_variables']
    return session_variable

def send_custom_message(mobile, payload):
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "User-Agent": "insomnia/10.0.0"}
    response = requests.request("POST", os.getenv('WHATSAPP_PUSH_URL'), json=payload, headers=headers)
    if response.status_code == 200:
        response_as_json = response.json()
        create_message(mobile, response_as_json.get('responseId'))
        
def single_loan_update_session_variables(mobile, **kwargs):
    belstar_response = get_loan_details(mobile)['Response'][0]
    user_name = belstar_response['Name']
    due_amount = belstar_response['TotalODAmt']
    account_id = belstar_response['AccountID']
    due_date = format_user_readable_date(belstar_response['DueDate'])
    variables = json.dumps({"account_id":account_id, "user_name": user_name,"due_amount":due_amount,"due_date":due_date,"token_data":{
            "recipient": mobile,
            "messageId": kwargs.get('message_id'),
            "collectionType": "bot", 
            "campaignId": None ,
            "accountId": account_id,
            "amount":due_amount,
            "clientName": user_name
            }}).replace("'","''")
    db.execute_query(f"update user_session set session_variables = '{variables}' where mobile = '{mobile}'")
    return True

def validate_user_amount(mobile, user_message, **kwargs):
    session_variable = db.execute_query(f"select session_variables from user_session where mobile = '{mobile}'")[0]['session_variables']
    due_amount = session_variable['due_amount']
    invalid_payload = {"messages": [{"sender": os.getenv('WHATSAPP_BOT_NUMBER'), "to": mobile, "type": "text", "channel": "wa", "text": {"content": f"It looks like you've either entered invalid characters or an amount that exceeds ₹{due_amount}. Please enter only the amount (numbers only) within the allowed limit."}}]}
    try:
        user_message = int(user_message)
    except:        
        send_custom_message(mobile, invalid_payload)
        return False
    if user_message < 1 or int(due_amount) < user_message:
        send_custom_message(mobile, invalid_payload)
        return False
    session_variable['due_amount'] = user_message
    session_variable['token_data']['amount'] = user_message
    session_variable = json.dumps(session_variable).replace("'","''")
    db.execute_query(f"update user_session set session_variables = '{session_variable}' where mobile = '{mobile}'")
    # generate_pay_now_messages(mobile, **kwargs)
    return True

def pay_now(mobile, **kwargs):
    session_variables = db.execute_query(f"select session_variables from user_session where mobile = '{mobile}'")[0]['session_variables']    
    return {
        "amount": session_variables['due_amount'],
        "account_id": session_variables['account_id'],
        "token": generate_token(session_variables['token_data'])}