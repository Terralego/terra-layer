#!/usr/bin/env python

import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(HERE, "README.md")).read()
CHANGES = open(os.path.join(HERE, "CHANGES.md")).read()

tests_require = [
    "factory-boy",
    "flake8",
    "coverage",
]

setup(
    name="terra-layer",
    version=open(os.path.join(HERE, "terra_layer", "VERSION.md")).read().strip(),
    include_package_data=True,
    author="Makina Corpus",
    author_email="terralego-pypi@makina-corpus.com",
    description="Geographic data visualizer backend for terra-visu",
    long_description=README + "\n\n" + CHANGES,
    description_content_type="text/markdown",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url="https://github.com/Terralego/terra-layer.git",
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        "Django>=2.2",
        "djangorestframework",
        "django-geosource>=0.4.10",
        "django-geostore>=0.5.4",
        "django-terra-accounts>=1.0.1",
        "jsonschema",
        "django-mapbox-baselayer>=0.0.3",
        "django-terra-settings>=1.0",
    ],
    extras_require={"dev": tests_require},
)
