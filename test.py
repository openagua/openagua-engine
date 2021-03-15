import unittest

test_kwargs = dict(
    guid='OA supplied string',
    name='My Model',
    network_id=77,
    scenario_ids=[1156, 1156],  # Merced River
    source_id=1,
    secret_key='model secret key',
    run_key=None,
    total_steps=60
)


class TestOpenAgua(unittest.TestCase):
    def test_app_import(self):
        """
        Test that it can be imported
        """
        from openagua import create_app

    def test_create_openagua(self):
        from openagua import OpenAguaEngine
        oa = OpenAguaEngine(**test_kwargs)

    def test_get_network(self):
        from openagua import OpenAguaEngine
        oa = OpenAguaEngine(**test_kwargs)
        resp = oa.get_network(oa.network_id)
        assert 'network' in resp


if __name__ == '__main__':
    unittest.main()
