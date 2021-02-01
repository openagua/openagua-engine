from os import environ
import datetime as dt

import requests

from openagua import constants
from openagua.publishers.pubnub import PubNubPublisher
from openagua.subscribers.pubnub import subscribe_pubnub

statuses = {
    'start': 'started',
    'finish': 'finished',
    'error': 'error',
    'pause': 'paused',
    'resume': 'resuming',
    'stop': 'stopped',
    'step': 'running',
    'save': 'saving'
}


class OpenAgua:
    reporter = None
    datetime = None
    _step = 0
    paused = False
    stopped = False

    def __init__(self, guid, name, network_id, scenario_ids, source_id=1,
                 api_endpoint='https://www.openagua.org/api/v1', api_key=None,
                 secret_key=None, run_key=None, total_steps=None):

        self.api_key = api_key or environ.get(constants.API_KEY)
        self.api_endpoint = api_endpoint
        self.network_id = network_id

        scen_ids_set = list(set(scenario_ids))

        run_id = '{guid}-{scen_ids}'.format(
            guid=guid,
            scen_ids='-'.join(str(s) for s in scen_ids_set)
        )

        self.run_id = run_id
        self.key = secret_key or environ.get(constants.MODEL_KEY)
        self.total_steps = total_steps
        if not self.key:
            raise Exception('No OpenAgua key supplied.')

        self.payload = {
            'sid': run_id,
            'name': name,
            'source_id': source_id,
            'network_id': network_id,
            'scids': scen_ids_set,
            'status': 'unknown'
        }

        # PUBLISH
        self.publisher = PubNubPublisher(source_id=source_id, network_id=network_id, run_key=run_key)

        # SUBSCRIBE
        channel = 'model-{model_key}-{run_id}'.format(model_key=self.key, run_id=self.run_id)
        subscribe_key = environ.get(constants.PUBNUB_SUBSCRIBE_KEY)
        subscribe_pubnub(subscribe_key=subscribe_key, uuid=self.key, channel=channel,
                         handle_message=self.handle_message_received)

    def __getattr__(self, name):
        def method(*args, **kwargs):
            if name in statuses:
                return self.publish_status(name, **kwargs)
            elif name[:4] == 'get_':
                return self.get_request(name, *args, **kwargs)
            else:
                return getattr(self, name)(*args, **kwargs)

        return method

    def get_request(self, fn, *args, **kwargs):
        resource = fn[4:]
        resource_id = args[0]
        endpoint = '{api_endpoint}/{resource}/{resource_id}'.format(
            api_endpoint=self.api_endpoint,
            resource=resource + 's',
            resource_id=resource_id
        )
        resp = requests.get(endpoint, headers={'X-Api-Key': self.api_key}, params=kwargs)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {'status_code': resp.status_code}

    def prepare_payload(self, action, **kwargs):
        payload = self.payload.copy()

        datetime = kwargs.get('datetime')
        if isinstance(datetime, dt.datetime) or isinstance(datetime, dt.date):
            datetime = datetime.isoformat()

        payload.update(
            action=action,
            status=statuses.get(action, 'unknown'),
            datetime=datetime,
            progress=int(round(self._step / self.total_steps * 100))
        )

        if action == 'done':
            payload.update(
                saved=100
            )

        return payload

    def publish_status(self, action, **kwargs):

        if action == 'step':
            step = kwargs.get('step')
            if step is not None:
                self._step = step
            else:
                self._step += 1

        payload = self.prepare_payload(action, **kwargs)

        if action in ['step', 'save']:
            # publish to a pubsub service for realtime updates
            self.publisher.publish(payload)

        if action != 'step':
            # report key events to the OpenAgua server
            if self.reporter:
                self.reporter.post(action, payload)

        return

    def handle_message_received(self, message):
        if message:
            state = message.get('state')
            self.stopped = state == 'stopped'
            self.paused = state == 'paused'
