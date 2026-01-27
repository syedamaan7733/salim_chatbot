from app import app
from apscheduler.schedulers.background import BackgroundScheduler
from routers.whatsapp import bp_whatsapp
from utils.access_token import set_token



scheduler = BackgroundScheduler()
scheduler.add_job(func=set_token, trigger="interval", hours=8)
scheduler.start()

app.register_blueprint(bp_whatsapp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)