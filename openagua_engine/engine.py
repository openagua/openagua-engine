from os import environ
import datetime as dt
from loguru import logger

import requests

from openagua_engine import constants
from openagua_engine.publishers.pubnub import PubNubPublisher
from openagua_engine.subscribers.pubnub import subscribe_pubnub

from openagua_client import Client

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
    api_headers = None
    api_endpoint = None

    def __init__(self, name, network_id, scenario_ids, guid=None, source_id=1, request_host=None,
                 api_endpoint=None, api_key=None, secret_key=None, run_key=None, total_steps=None):

        # set up api

        if api_endpoint is None:
            if request_host:
                if request_host[-1] == '/':
                    api_endpoint = request_host + 'api/v1'
                else:
                    api_endpoint = request_host + '/api/v1'
            else:
                api_endpoint = 'https://www.openagua.org/api/v1'
        self.api_endpoint = api_endpoint

        self.api_key = api_key or environ.get(constants.API_KEY)
        if not self.api_key:
            logger.warning(
                'No OpenAgua API key supplied. You will not be able to read from OpenAgua or report lifecycle progress.')
        else:
            self.api_headers = {'X-API-KEY': self.api_key}

        self.Client = Client(request_host=request_host, api_endpoint=api_endpoint, api_key=api_key)

        self.network_id = network_id

        scen_ids_set = list(set(scenario_ids))

        if guid is not None:
            run_id = '{guid}-{scen_ids}'.format(
                guid=guid,
                scen_ids='-'.join(str(s) for s in scen_ids_set)
            )
        else:
            run_id = None

        self.run_id = run_id
        self.model_key = secret_key or environ.get(constants.MODEL_KEY)
        self.total_steps = total_steps
        if not self.model_key:
            raise Exception('No model key supplied. This probably won''t work.')

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
        if self.model_key:
            channel = 'model-{model_key}-{run_id}'.format(model_key=self.model_key, run_id=self.run_id)
            subscribe_key = environ.get(constants.PUBNUB_SUBSCRIBE_KEY)
            subscribe_pubnub(subscribe_key=subscribe_key, uuid=self.model_key, channel=channel,
                             handle_message=self.handle_message_received)

    def __getattr__(self, name):
        def method(*args, **kwargs):
            if name in statuses:
                return self.publish_status(name, **kwargs)
            else:
                return getattr(self, name)(*args, **kwargs)

        return method

    def prepare_payload(self, action, **kwargs):
        payload = self.payload.copy()

        datetime = kwargs.get('datetime')
        if isinstance(datetime, dt.datetime) or isinstance(datetime, dt.date):
            datetime = datetime.isoformat()

        if self.total_steps:
            progress = int(round(self._step / self.total_steps * 100))
        else:
            progress = 0.0

        payload.update(
            action=action,
            status=statuses.get(action, 'unknown'),
            datetime=datetime,
            progress=progress
        )

        if action == 'done':
            payload.update(
                saved=100
            )

        return payload

    def report(self, action, payload):
        if not self.run_id or not self.api_endpoint:
            logger.info(action)
            return

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

        if action == 'error':
            self.has_error = True
        if action == 'finish' and self.has_error:
            return  # don't do anything

        # publish to a pubsub service for realtime updates
        self.publisher.publish(payload)

        # and also report life stage events to the OpenAgua server
        if action != 'step':
            self.report(action, payload)

        return

    def handle_message_received(self, message):
        if message:
            state = message.get('state')
            self.stopped = state == 'stopped'
            self.paused = state == 'paused'
