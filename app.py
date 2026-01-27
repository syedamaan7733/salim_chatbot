from dotenv import load_dotenv
from flask import Flask
from flask_caching import Cache

load_dotenv()

config = {
    "CACHE_TYPE": "SimpleCache"
}
# initating app 
app = Flask(__name__)

cache = Cache(app, config=config)