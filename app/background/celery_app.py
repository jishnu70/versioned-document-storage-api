# background/celery_app.py

from celery import Celery
from app.background.OtpService import OtpSendError, get_otp_service
from app.config import config

celery_app = Celery(
    "background_worker",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_BACKEND_URL
)

@celery_app.task(name="otp.send_email")
def send_otp_email(to_email:str):
    otp_service = get_otp_service()
    try:
        otp_service.send_otp(to_email)
        return {"status": "success"}
    except OtpSendError as e:
        return {"status": "failed", "error": str(e)}
