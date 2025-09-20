# infrastructure/redis_client.py

from redis import Redis
from app.config import config

redis_client = Redis.from_url(config.REDIS_URL)
