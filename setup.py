#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup


def read(fname):
    return open(fname).read()


setup(
    name="terra_layer",
    version="0.1",
    author="Makina Corpus",
    author_email="terralego-pypi@makina-corpus.com",
    description="Terra Layer",
    url="https://github.com/Terralego/terra-layer",
    packages=find_packages(
        exclude=["*.tests", ]
    ),
    include_package_data=True,
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development",
        "OSI Approved :: MIT License",
    ],
    install_requires=[
        "Django>=2.1,<2.2",
        "djangorestframework>=3.8,<3.9",
        "django_geosource",
        "terra-common>=0.3"
    ],
)
