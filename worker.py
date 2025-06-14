import os
from rq import Worker, Queue
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    worker = Worker([Queue()], connection=redis_conn)
    worker.work() 