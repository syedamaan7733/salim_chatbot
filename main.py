import os

from app import app
from apscheduler.schedulers.background import BackgroundScheduler
from routers.whatsapp import bp_whatsapp
from utils.access_token import set_token


scheduler = BackgroundScheduler()
scheduler.add_job(func=set_token, trigger="interval", hours=8)
scheduler.start()

app.register_blueprint(bp_whatsapp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)