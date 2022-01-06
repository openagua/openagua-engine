from os import environ
import json
from ably import AblyRest

from openagua_engine import constants


class AblyPublisher(object):

    def __init__(self, source_id, network_id, model_key=None, run_key=None):
        self.api_key = environ.get(constants.ABLY_API_KEY)
        model_key = model_key or environ.get(constants.MODEL_KEY)
        self.channel_name = 'oa-{source_id}-{network_id}-{model_key}'.format(
            source_id=source_id,
            network_id=network_id,
            model_key=model_key
        )
        if run_key is not None:
            self.channel_name += '-{}'.format(run_key)

    # publish updates
    async def publish(self, payload):
        async with AblyRest('api:key') as client:
            channel = client.channels.get(self.channel_name)
            await channel.publish('event', json.dumps(payload))
