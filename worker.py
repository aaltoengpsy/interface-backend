import os
import platform

import redis
from rq import Worker, SimpleWorker, Queue, Connection
from rq.timeouts import BaseDeathPenalty

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

class WindowsDeathPenalty(BaseDeathPenalty):
    def setup_death_penalty(self):
        pass
    def cancel_death_penalty(self):
        pass

if __name__ == '__main__':
    with Connection(conn):
        if platform.system() == 'Windows':
            worker = SimpleWorker(map(Queue, listen))
            worker.death_penalty_class = WindowsDeathPenalty
        else:
            worker = Worker(map(Queue, listen))
        worker.work()

