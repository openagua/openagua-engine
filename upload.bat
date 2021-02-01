rmdir /Q /S build dist openagua_engine.egg-info
python setup.py sdist bdist_wheel
twine upload dist/*