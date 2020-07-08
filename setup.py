import setuptools, os
from pycross.utils.globalvars import APP_NAME, APP_VERSION, APP_AUTHOR, APP_EMAIL, GIT_REPO

def walk_dir(root_path, abs_path=True, recurse=True, dir_process_function=None,
             file_process_function=None, file_types=None):
    if abs_path:
        root_path = os.path.abspath(root_path)
    if dir_process_function:
        dir_process_function(root_path)
    for (d, dirs, files) in os.walk(root_path):
        if dir_process_function:
            for d_ in dirs:
                dir_process_function(os.path.join(d, d_))
        if file_process_function:
            for f in files:
                ext = os.path.splitext(f)[1][1:].lower()
                if (not file_types) or (ext in file_types):
                    file_process_function(os.path.join(d, f))
        if not recurse: break

def get_all_files(root_dir):
    l = []
    def process_dir(dir_path):
        nonlocal l
        if not '__pycache__' in dir_path:
            l.append(dir_path.replace('\\', '/') + '/*')
    walk_dir(root_dir, False, True, process_dir)
    return l


with open("README.md", "r") as fh:
    long_description = fh.read()
    
with open("requirements.txt", "r") as reqs:
    pip_requirements = reqs.readlines()
    
includes = ['assets/dic/*', 'assets/icons/*', 
            'utils/*', 'plugins/*'] + \
           [f"../{d}" for d in get_all_files('pycross/doc')] + \
           [f"../{d}" for d in get_all_files('pycross/locale')] + \
           [f"../{d}" for d in get_all_files('pycross/presets')]

setuptools.setup(
    name=APP_NAME.lower(),
    version=APP_VERSION,
    scripts=['pycross/pycross.bat', 'pycross/pycross'],
    author=APP_AUTHOR,
    author_email=APP_EMAIL,
    description=f"{APP_NAME} - the Python Crossword Puzzle Generator and Editor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=GIT_REPO,
    packages=['pycross', 'pycross.utils', 'pycross.plugins'],
    package_data={'pycross': includes},
    install_requires=pip_requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)