from os import environ
from dotenv import load_dotenv


def get_broker_url(protocol='amqp'):
    load_dotenv()

    model_key = environ.get('OA_SECRET_KEY')

    broker_url = '{protocol}://{username}:{password}@{hostname}:5672/{vhost}'.format(
        protocol=protocol,
        username=model_key,
        password='password',
        hostname=environ.get('RABBITMQ_HOST', 'localhost'),
        vhost='model-{}'.format(model_key),
    )

    return broker_url
