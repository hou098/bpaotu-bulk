#!/usr/bin/env/python
from setuptools import setup

setup(
    name="bpaotu_bulk",
    version="1.0",
    description="",
    license="GPL3",
    packages=["bpaotu_bulk"],
    zip_safe=False,
    include_package_data=True,
    package_dir={"bpaotu_bulk": "bpaotu_bulk"},
    package_data={
        "bpaotu_bulk": [
            "*.json",
            "templates/*.html",
            "templates/*/*.html",
            "templates/*/*/*.html",
            "static/*.css",
            "static/*.png",
            "static/*.jpg",
            "static/*.css",
            "static/*.ico",
        ]
    },
)
