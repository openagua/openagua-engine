import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="openagua",
    version="0.9",
    author="David Rheinheimer",
    author_email="david.rheinheimer@tec.mx",
    description="Tools to connect a model engine to OpenAgua",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openagua/engine",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
