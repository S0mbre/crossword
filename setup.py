import setuptools
from pycross.utils.globalvars import APP_NAME, APP_VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=APP_NAME,
    version=APP_VERSION,
    scripts=[],
    author="Iskander Shafikov (s0mbre)",
    author_email="s00mbre@gmail.com",
    description="pyCross - the Python Crossword Puzzle Generator and Editor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/S0mbre/crossword",
    packages=['pycross', 'pycross.utils'],
    package_data={'pycross': ['assets/*', 'assets/dic/*', 'assets/icons/*', '*.bat', '*.json']},
    install_requires=['requests', 'numpy', 'PyQt5'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)