# Overview

**openagua-engine** is a Python package to help connect a model engine to OpenAgua, so that it can be controlled from and communicate with OpenAgua. It includes
1. a task queue subscriber to process model tasks instantiated in the OpenAgua app
2. functions to report progress to the OpenAgua app 
3. functions to read from/write to the OpenAgua database

OpenAgua uses [RabbitMQ](www.rabbitmq.com) to manage model run tasks and, for the time being, [PubNub](www.pubnub.com) for realtime communication (for updating model progress in and stopping the model from OpenAgua). This package uses [Celery](docs.celeryproject.org) to listen for tasks in RabbitMQ queues. Access to the OpenAgua database is via the [OpenAgua API](www.openagua.org/api/v1)

# Installation

## From pip

This package is availabe via PyPI (see [project page](https://pypi.org/project/openagua-engine/)):

`pip install openagua-engine`

## From source

`python setup.py install` should do the trick.

# Getting started

The following should help you get going. In addition, see examples of OpenAgua Engine in action at https://github.com/openagua/engine-examples

## Configuration

OpenAgua Engine requires several configuration keys to work. These may be provided directly as arguments to classes/functions, and/or as system environment variables. The possible configuration keys are as follows, listed by their recognized environment variable and respective argument name:

* `OA_API_KEY` (`api_key`) - This is used to access the OpenAgua API. Get this from your account settings in OpenAgua. 
* `OA_MODEL_KEY` (`model_key`) - This is used to route model runs started in OpenAgua to the model engine you want to set up. Get this from the model configuration page in OpenAgua.
* `OA_RUN_KEY` (`run_key`) (OPTIONAL) - This is a key associated with a particular run configuration that can isolate an engine instance from other engines connected to the same model. If this is omitted, the engine will accept any run associated with the model key (if no run key is assigned in the run configuration). Get this from the run configuration.
* `OA_RABBITMQ_HOST` (variable only) - The RabbitMQ server IP address.

These may be provided in a number of ways. One common and easy way is to use a file called `.env` with your keys (and maybe some others as needed for your application):

```dotenv
OA_API_KEY=SECRETKEY123
OA_SECRET_KEY=SECRETKEY123
OA_MODEL_KEY=MODELKEY456
OA_RABBITMQ_HOST=1.2.3.4
```
This can be loaded into your main *tasks.py* script as:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Usage

An app engine will generally consist of five major steps/functions:
1. listen to a task queue to process model run requests,
2. read data from OpenAgua once a task is received,
3. run the model using the data,
4. publish model run progress and subscribe to user interventions, and
5. save data back to OpenAgua.

These are described along with code snippets below. See the [examples](https://github.com/openagua/engine-examples) for more complete script examples.

### 1. Listen to a task queue

A basic model engine requires a file called *tasks.py* that contains an entry function wrapped in a decorator "app", which is a Celery app created by openagua-engine. This app is then run in one of two ways.

#### 1a. Create the entry function

```python
from openagua_engine import create_app

app = create_app()

@app.task(name='model.run')
def run(**kwargs):
    # Do something great!
    return
```
**IMPORTANT**: The `name='model.run'` bit above is critical. When a model is run in OpenAgua, the `model.run` function is called.

#### 1b. Start the app
The app above is a Celery app, and can be run as:
`celery -A tasks worker -l INFO`

Alternatively, the app may be called from within the script, for example by appending *tasks.py* with:
```python
if __name__=='__main__':
    app.start(['-A', 'tasks', 'worker', '-l', 'INFO'])
```

**Windows users**: Celery does not officially support Windows. While there are several fixes, one that seems to work is to use the "solo" process when running this app:
`celery -A tasks worker -l INFO -P solo`

### 2. Read data from OpenAgua

Here is an example to instantiate the OpenAgua API and get a network:
```python
from openagua_engine import OpenAguaEngine as OA
oa = OA()
api = oa.Client
network = api.get_network(77)
```

### 3. Run the model

The sky is the limit here, especially considering parallel processing needs.

One easy way to parallel process is as follows. Among other arguments sent by OpenAgua to the task queue (the "kwargs" in the run function above) are the scenario ID combinations to be run. Because openagua-engine uses Celery, the app created with `create_app()` can be used to decorate a scenario-centric function, which can then be run in asynchronous mode, as follows:

```python
@app.task(name='model.run')
def run(**kwargs):
    network = oa.get_network(123)
    
    scenario_id_combinations = kwargs.pop('scenario_ids', [])
    for scen_ids in scenario_id_combinations:
        
        # Run a single scenario model asynchronously
        run_scenario.apply_async(args=(scen_ids, network,), kwargs=kwargs)

@app.task
def run_scenario(scen_ids, **kwargs):
    # Run model here...
    return
```

### 4a. Publish progress

openagua-engine includes methods to report (publish) progress. First, import an OpenAgua class (`from openagua-engine import OpenAgua`). Then, use it as follows:

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

### 4b. Subscribe to user interactions
The OpenAgua class above also monitors for user interactions, namely pause and stop. These are set as boolean (True/False) attributes of the OpenAgua object. We can include this in the above script as:
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

### 5. Save data

[forthcoming]