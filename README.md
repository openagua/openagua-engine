# Overview

**openagua_engine** is a Python package to help connect a model engine to OpenAgua, so that it can be controlled from and communicate with OpenAgua. It includes
1. a task queue subscriber to process model tasks instantiated in the OpenAgua app
2. functions to report progress to the OpenAgua app 
3. functions to read from/write to the OpenAgua database

OpenAgua uses [RabbitMQ](www.rabbitmq.com) to manage model run tasks and, for the time being, [PubNub](www.pubnub.com) for realtime communication (for updating model progress in and stopping the model from OpenAgua). This package uses [Celery](docs.celeryproject.org) to listen for tasks in RabbitMQ queues. Access to the OpenAgua database is via the [OpenAgua API](www.openagua.org/api/v1)

# Installation

`pip install openagua_engine`

# Getting started

An app engine will generally consist of five major functions:
1. listen to a task queue to process model run requests,
2. read data from OpenAgua once a task is received,
3. run the model using the data,
4. publish model run progress and subscribe to user interventions, and
5. save data back to OpenAgua.

IMPORTANT: openagua_engine requires configuration keys to work.

Minimal requirements and a version of each of these is described, followed by an example that aggregates these.

## 1. Listen to a task queue

A basic model engine requires at the very least a file called 'tasks.py' that contains a function wrapped in a decorator "app", which is a Celery app created by openagua_engine. The general flow is:
1. Create an "app" to run:
```python
from openagua import create_app
app = create_app()
@app.task(name='model.run')
def run(**kwargs):
    # Do something great!
    return
```
The app above is a Celery app, such that the above script can be run with:
`celery -A tasks worker -l INFO`

**Windows users**: Celery does not officially support Windows. While there are several fixes, one that seems to work is to use the "solo" process when running this app:
`celery -A tasks worker -l INFO -P solo`

## 2. Read data from OpenAgua

Here is an example to instantiate the OpenAgua API and get a network:
```python
from openagua import API
api = API()
network = api.get_network(77)
```

## 3. Run the model

The sky is the limit here, especially considering parallel processing needs.

One easy way to parallel process is as follows. Among other arguments sent by OpenAgua to the task queue (the "kwargs" in the run function above) are the scenario ID combinations to be run. Because openagua_engine uses Celery, the app created with `create_app()` can be used to decorate a scenario-centric function, which can then be run in asynchronous mode, as follows:

## 4a. Publish progress

openagua_engine includes methods to report (publish) progress. First, import an OpenAgua class (`from openagua import OpenAgua`). Then, use it as follows:

```python
total_steps = 60  # This would normally be queried from a scenario     
guid = kwargs.get('guid')
run_name = kwargs.get('run_name')
network_id=kwargs.get('network_id')
oa = OpenAgua(guid, run_name, network_id, scen_ids, total_steps)

# Tell OpenAgua / the user that the model has started
oa.start()

for step in range(total_steps):
    my_model.step()  # Assume a model with method "step" to do some computation
    datetime = my_model.datetime
    oa.step(datetime)

# Tell OpenAgua / the user that the model has finished
oa.finish()
```

## 4b. Subscribe to user interventions
The OpenAgua class above also monitors for user interventions, namely pause and stop. These are set as boolean (True/False) attributes of the OpenAgua object. We can include this in the above script as:
```python
for i in range(total_steps):
    # Check if the user has paused or stopped the run
    # Note that pause is not currently implemented in the app
    if oa.paused:
        pause_start_time = dt.datetime.now()
        while oa.paused and (dt.datetime.now() - pause_start_time).seconds < 86400:
            sleep(0.5) # check every 1/2 second
            
    if oa.stopped:  # this should be after pause is checked, to stop during a pause
        oa.stop()  # This will report back to OA that the model has stopped
        break
```

## 5. Save data

[forthcoming]

## Summary

Here is a basic script that integrates the above major functions:

```python
import datetime as dt
from time import sleep
from openagua import create_app, OpenAgua

app = create_app()

@app.task(name='model.run')
def run(**kwargs):
    scenario_id_combinations = kwargs.pop('scenario_ids', [])

    # Here is a placeholder network; the actual network would be called using the OpenAgua API.
    network = {'name', 'Demo Model'}

    for scen_ids in scenario_id_combinations:
        # This is how to run a single scenario model asynchronously
        run_scenario.apply_async(args=(scen_ids, network,), kwargs=kwargs)


@app.task
def run_scenario(scen_ids, **kwargs):
    
    total_steps = 60  # This would normally be queried from a scenario 
    
    guid = kwargs.get('guid')
    run_name = kwargs.get('run_name')
    oa = OpenAgua(
        guid=guid,
        name=run_name,
        network_id=kwargs.get('network_id'),
        run_key=None,  # basic run
        scenario_ids=scen_ids,
        total_steps=total_steps
    )

    # Tell OA that the model is started
    oa.start()

    start = dt.date(1950, 10, 1)
    for i in range(total_steps):
        datetime = start + dt.timedelta(days=i)

        # Check if the user has paused or stopped the run
        # Note that pause is not currently implemented in the app
        if oa.paused:
            pause_start_time = dt.datetime.now()
            while oa.paused and (dt.datetime.now() - pause_start_time).seconds < 86400:
                sleep(0.5)
                
        if oa.stopped:  # this should be after pause is checked, to stop during a pause
            oa.stop()  # This will report back to OA that the model has stopped
            break
        
        # Do some very important modeling work here
        sleep(1)
        
        # Send a message to the app that the model has progressed by one step
        oa.step(datetime=datetime)

    # Send a message to the app that the model has finished
    oa.finish()


if __name__ == '__main__':
    # IMPORTANT: Celery does not support Windows. -P solo seems to work.
    app.start(['-A', 'tasks', 'worker', '-l', 'INFO', '-P' 'solo'])
```

## More examples

[forthcoming]