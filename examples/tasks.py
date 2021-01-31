from openagua import app
from examples.demo_model import run_demo_model


@app.task(name='model.run')
def run(**kwargs):
    scenario_id_combinations = kwargs.pop('scenario_ids', [])
    for scen_ids in scenario_id_combinations:
        run_scenario.apply_async(args=(scen_ids,), kwargs=kwargs)


@app.task
def run_scenario(scen_ids, **kwargs):
    run_demo_model(scen_ids, **kwargs)


if __name__ == '__main__':
    # IMPORTANT: Celery does not support Windows. -P solo seems to work.
    app.start(['-A', 'tasks', 'worker', '-l', 'INFO', '-P' 'solo'])
