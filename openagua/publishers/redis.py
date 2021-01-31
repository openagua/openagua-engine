from os import environ
import json
import redis


class RedisPublisher(object):

    def __init__(self, source_id, network_id, model_key=None, run_key=None):
        self.updater = None

        redis_host = environ.get('REDIS_HOST', 'localhost')
        self.redis = redis.Redis(host=redis_host, port=6379, db=0)

        self.channel = 'oa-{source_id}-{network_id}-{model_key}'.format(
            source_id=source_id,
            network_id=network_id,
            model_key=model_key or environ.get('OA_SECRET_KEY')
        )
        if run_key is not None:
            self.channel += '-{}'.format(run_key)

    # publish updates
    def publish(self, payload):
        self.redis.publish(self.channel, json.dumps(payload))
