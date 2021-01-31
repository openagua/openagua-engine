from os import environ
from celery import Celery
from dotenv import load_dotenv
from openagua.utils import get_broker_url

load_dotenv()

run_key = environ.get('OA_RUN_KEY')
model_key = environ.get('OA_SECRET_KEY')

broker_url = get_broker_url()

redis_host = environ.get('REDIS_HOST', 'localhost')

# test redis
# redis.set('test', 1)

# environ['FORKED_BY_MULTIPROCESSING'] = '1'

app = Celery(
    'openagua',
    broker=broker_url,
    include=['tasks'],
)

task_queue_name = 'model-{}'.format(model_key)
if run_key:
    task_queue_name += '-{}'.format(run_key)

app.conf.update(
    task_default_queue=task_queue_name,
    task_default_exchange='tasks',
    broker_heartbeat=10,
    accept_content=['json', 'pickle'],
    result_expires=3600
)
