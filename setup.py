#!/usr/bin/env python3
"""Setup script for IriusRisk CLI tool."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="iriusrisk-cli",
    version="0.5.0",
    author="IriusRisk",
    author_email="support@iriusrisk.com",
    description="AI-powered threat modeling integration for IriusRisk. Command line interface and MCP server for security analysis.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iriusrisk/iriusrisk_cli",
    project_urls={
        "Bug Reports": "https://github.com/iriusrisk/iriusrisk_cli/issues",
        "Documentation": "https://github.com/iriusrisk/iriusrisk_cli#readme",
        "Source": "https://github.com/iriusrisk/iriusrisk_cli",
        "Changelog": "https://github.com/iriusrisk/iriusrisk_cli/blob/main/CHANGELOG.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "iriusrisk_cli": ["prompts/*.md"],
    },
    include_package_data=True,
    keywords=[
        "security",
        "threat-modeling",
        "iriusrisk",
        "cli",
        "mcp",
        "ai",
        "threat-analysis",
        "security-testing",
        "compliance",
        "cybersecurity",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Environment :: Console",
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
