"""
Setup configuration for the Process Builder package.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="processbuilder",
    version="0.1.0",
    author="Your Name",
    author_email="greg@gregmeyer.com",
    description="A tool for building structured process definitions through interactive interviews",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gregmeyer/processbuilder-example",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "processbuilder=processbuilder.cli:main",
        ],
    },
) 