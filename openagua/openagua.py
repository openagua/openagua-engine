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


class OpenAguaEngine:
    datetime = None
    _step = 0
    paused = False
    stopped = False

    def __init__(self, guid, name, network_id, scenario_ids, source_id=1, request_host=None,
                 api_endpoint=None, api_key=None, secret_key=None, run_key=None, total_steps=None):

        if api_endpoint is None:
            if request_host:
                api_endpoint = request_host + 'api/v1'
            else:
                api_endpoint = 'https://www.openagua.org/api/v1'

        # set up api
        self.api_key = api_key or environ.get(constants.API_KEY)
        self.api_endpoint = api_endpoint
        self.api_headers = {'X-API-KEY': self.api_key}

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
            elif name[:4] == 'add_':
                return self.request_post(name, **kwargs)
            elif name[:4] == 'get_':
                return self.request_get(name, *args, **kwargs)
            elif name[:7] == 'update_':
                return self.request_put(name, *args, **kwargs)
            else:
                return getattr(self, name)(*args, **kwargs)

        return method

    def request_post(self, fn, **kwargs):
        resource = fn[4:]  # add_
        url = '{}/{}'.format(self.api_endpoint, resource + 's')
        resp = requests.post(url, headers=self.api_headers, json=kwargs)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {'status_code': resp.status_code}

    def request_get(self, fn, *args, **kwargs):
        resource = fn[4:]  # get_
        resource_id = args[0]
        url = '{}/{}/{}'.format(self.api_endpoint, resource + 's', resource_id)
        resp = requests.get(url, headers=self.api_headers, params=kwargs)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {'status_code': resp.status_code}

    def request_put(self, fn, *args, **kwargs):
        resource = fn[7:]  # update_
        resource_id = args[0]
        url = '{}/{}/{}'.format(self.api_endpoint, resource + 's', resource_id)
        resp = requests.get(url, headers=self.api_headers, params=kwargs)
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

    def report(self, action, payload):
        url = '{api_endpoint}/models/runs/{sid}/actions/{action}'.format(
            api_endpoint=self.api_endpoint,
            sid=self.run_id,
            action=action
        )
        resp = requests.post(url, headers=self.api_headers, json=payload)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {'status_code': resp.status_code}

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
            self.report(action, payload)

        return

    def handle_message_received(self, message):
        if message:
            state = message.get('state')
            self.stopped = state == 'stopped'
            self.paused = state == 'paused'
