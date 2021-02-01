rmdir /Q /S build dist openagua_engine.egg-info
python setup.py sdist --formats=gztar,zip bdist_wheel
twine upload dist/*