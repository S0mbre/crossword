import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyCross",
    version="0.1",
    scripts=['pycross-cli.bat', 'pycross-gui.bat', 'pycross-cli.sh', 'pycross-gui.sh'],
    author="Iskander Shafikov (s0mbre)",
    author_email="s00mbre@gmail.com",
    description="pyCross - the Python Crossword Puzzle Generator and Editor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/S0mbre/crossword",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)