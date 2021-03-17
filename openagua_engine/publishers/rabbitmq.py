from os import environ
import json
from kombu import Connection, Exchange, Queue
from openagua_engine.utils import get_broker_url
from openagua_engine import constants


class RabbitMQPublisher(object):

    def __init__(self, source_id, network_id, model_key=None, run_key=None):
        broker_url = get_broker_url(model_key)
        self.conn = Connection(broker_url)
        self.conn.connect()

        self.channel = 'oa-{source_id}-{network_id}-{model_key}'.format(
            source_id=source_id,
            network_id=network_id,
            model_key=model_key or environ.get(constants.MODEL_KEY)
        )
        if run_key is not None:
            self.channel += '-{}'.format(run_key)

        self.producer = self.conn.Producer(serializer='json')

        # set up the Exchange, Queue, and Producer
        media_exchange = Exchange('media', 'direct', durable=True)
        video_queue = Queue('video', exchange=media_exchange, routing_key='video')


    # publish updates
    def publish(self, payload):
        self.producer.publish(self.channel, json.dumps(payload))

    def close(self):
        self.conn.release()
