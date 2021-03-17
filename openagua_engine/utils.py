from os import environ
from openagua_engine import constants


def get_broker_url(model_key, protocol='amqp'):
    broker_url = '{protocol}://{username}:{password}@{hostname}:5672/{vhost}'.format(
        protocol=protocol,
        username=model_key,
        password='password',
        hostname=environ.get(constants.RABBITMQ_HOST, 'localhost'),
        vhost='model-{}'.format(model_key),
    )

    return broker_url
