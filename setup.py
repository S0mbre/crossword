import setuptools
from pycross.utils.globalvars import APP_NAME, APP_VERSION, APP_AUTHOR, APP_EMAIL, GIT_REPO
#from pycross.utils.utils import walk_dir

"""
def get_all_files(root_dir):
    l = []
    def process_dir(dir_path):
        nonlocal l
        l.append(dir_path.replace('\\', '/') + '/*')
    walk_dir(root_dir, False, True, process_dir)
    print(l)
    return l
"""

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=APP_NAME,
    version=APP_VERSION,
    scripts=[],
    author=APP_AUTHOR,
    author_email=APP_EMAIL,
    description=f"{APP_NAME} - the Python Crossword Puzzle Generator and Editor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=GIT_REPO,
    packages=['pycross', 'pycross.utils'],
    package_data={'pycross': ['assets/*', 'assets/dic/*', 'assets/icons/*', 
                              'utils/*', '*.bat', '*.json', '*.sh']},
    #package_data={'pycross': ['assets/*', 'assets/dic/*', 'assets/icons/*', 
    #                          'utils/*', '*.bat', '*.json', '*.sh', '../.gitignore'] + \
    #                          [f"../{d}" for d in get_all_files('.git')]},    
    install_requires=['requests', 'numpy', 'PyQt5'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)