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
        "Django>=2.0,<2.1.0",
        "djangorestframework>=3.7,<3.8",
        "django_geosource",
        "terra-common"
    ],
)
