"""Setup file for wiki_music."""

import logging
from pathlib import Path
from setuptools import setup, find_packages

log = logging.getLogger(__name__)

# The directory containing this file
PKG_ROOT = Path(__file__).parent

# Read package constants
README = (PKG_ROOT / "README.md").read_text()
REQUIREMENTS = (PKG_ROOT / "requirements.txt").read_text().split("\n")


# This call to setup() does all the work
setup(
    name="simulation-progress",
    version="0.0.1",
    description="web app to display any simulation progress",
    long_description=README,
    long_description_content_type="text/markdown",
    url="",
    author="Marián Rynik",
    keywords="ssh MD DEPMD MetaD",
    author_email="marian.rynik@outlook.sk",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Environment :: Console",
        "Environment :: MacOS X",
        "Environment :: X11 Applications :: Qt",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Typing :: Typed"
    ],
    packages=find_packages(exclude=("setup", "tests")),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    extras_require={"test": ["unittest"] + REQUIREMENTS},
    python_requires=">=3.6",
)
