#!/usr/bin/env python3
"""Setup script for IriusRisk CLI tool."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="iriusrisk-cli",
    version="0.1.0",
    author="IriusRisk",
    description="A command line interface for IriusRisk API v2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "python-dotenv>=0.19.0",
        "tabulate>=0.8.0",
        "mcp>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "iriusrisk=iriusrisk_cli.main:cli",
        ],
    },
)
