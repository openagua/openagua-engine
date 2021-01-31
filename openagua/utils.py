from os import environ


def get_broker_url(model_key, protocol='amqp'):

    broker_url = '{protocol}://{username}:{password}@{hostname}:5672/{vhost}'.format(
        protocol=protocol,
        username=model_key,
        password='password',
        hostname=environ.get('RABBITMQ_HOST', 'localhost'),
        vhost='model-{}'.format(model_key),
    )

    return broker_url
