from os import environ

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

from openagua_engine import constants


def on_publish(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        raise Exception("Failed to report progress.")
        # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];


class PubNubPublisher(object):

    def __init__(self, source_id, network_id, model_key=None, run_key=None):

        publish_key = environ.get(constants.PUBNUB_PUBLISH_KEY)
        subscribe_key = environ.get(constants.PUBNUB_SUBSCRIBE_KEY)
        model_key = model_key or environ.get(constants.MODEL_KEY)

        if publish_key and subscribe_key:
            pnconfig = PNConfiguration()
            pnconfig.subscribe_key = subscribe_key
            pnconfig.publish_key = publish_key
            pnconfig.uuid = model_key
            pnconfig.ssl = False
            self.pubnub = PubNub(pnconfig)
            self.channel = 'oa-{source_id}-{network_id}-{model_key}'.format(
                source_id=source_id,
                network_id=network_id,
                model_key=model_key
            )
            if run_key is not None:
                self.channel += '-{}'.format(run_key)
        else:
            self.pubnub = None
            self.channel = None

    # publish updates
    def publish(self, payload):
        self.pubnub.publish().channel(self.channel).message(payload).pn_async(on_publish)
