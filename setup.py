from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="pymashov",
    version="0.0.2",
    description="Unofficial async Python API wrapper for Mashov",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Tomer Klein",
    author_email="tomer.klein@gmail.com",
    url="https://github.com/t0mer/pymashov",
    download_url="https://pypi.org/project/pymashov/",
    packages=find_packages(exclude=("tests",)),
    keywords=[
        "mashov",
        "education",
        "api",
        "async",
        "httpx",
        "israel",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.25,<1.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: AsyncIO",
        "Operating System :: OS Independent",
    ],
)
