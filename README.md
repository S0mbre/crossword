# pyCross - the Python Crossword Puzzle Generator and Editor
*pyCross* is a pure-Python implementation of a crossword puzzle generator and editor.


## Features:
* full-fledged [Qt 5](https://doc.qt.io/qt-5/index.html) based GUI
* cross-platform implementation
* install using pip (see [dist/](https://github.com/S0mbre/crossword/tree/master/dist)) or clone from Github
* open, save, restore, export, and import crossword puzzles
* powerful word sources: SQLite database / CSV (plaintext) / raw python list
* crossword generation (from word sources) using 2 methods: recursive and iterative
* supports common puzzle file formats: [XPF](https://www.xwordinfo.com/XPF/), [IPUZ](http://www.ipuz.org/) and raw text grid 
* easily load, edit and save word clues
* flexible GUI settings: colors, grid settings, clues table look & feel, etc.
* auto app updating / new release checking from Github
* lookup word definition in online dictionary and Google
* suggest words from word sources
* comfortable navigation in GUI (hotkeys, keystrokes, mouse)
* context menus
* printing to PDF or printer with customizable page / element layout
* export crossword to image (jpg, png, tiff) / PDF / SVG with customizable resolution etc.

## Installation

### Requirements
You must have the following applications / packages installed in your system:

* Python 3.6+ (the app was written and tested with Python 3.7.4 and 3.8.0)
* Python packages: *PyQt5*, *numpy*, and *requests* 
* Git (should be pre-installed on most modern Linux and Mac systems, alternatively install from the [git website](https://git-scm.com/downloads))

### Installation options

#### 1 - Clone from Github (for full 'developer' mode)

**1. Install the required packages**

  I recommend (as many do) installing packages into python's virtual environment using *virtualenv* or the inbuilt *venv*:
  
  Create a new virtual environment:
  **Linux / Mac**
  ```bash
  cd myprojects
  virtualenv pycross
  cd pycross
  . ./bin/activate
  ```
  
  **Windows**
  ```bash
  cd myprojects
  virtualenv pycross
  cd pycross
  Scripts\activate.bat
  ```
  
  This step is, of course, optional. You can skip it if you don't want to use virtual environments for some reason or other. 
  
  Then just run:
  ```bash
  pip install --upgrade PyQt5 numpy requests
  ```
  
**2. Clone repo**

  To get the latest (non-stable) version, run:
  ```bash
  git clone https://github.com/S0mbre/crossword
  ```
  
  This will checkout to the *master* branch which tracks all recent changes, some of which may not be yet merged into a release version.
  
  To get the latest stable version, run:
  ```bash
  git clone -b latest https://github.com/S0mbre/crossword
  ```
  
  This will checkout to the branch pointed at by the *latest* tag which will always be the latest stable release.
  
#### 2 - Install with pip (specific version)

**1. Create your project directory and Python virtual environment [optional]**

  Follow the described procedure to create your project dir and Python virtual environment (recommended but optional).
  
**2. Install the Python wheel**

  Use *pip* to install the Python wheel (distro):
  
  ```bash
  pip install --upgrade https://github.com/S0mbre/crossword/raw/master/dist/pyCross-VERSION-py3-none-any.whl
  ```
  
  Replace here *VERSION* with the version of *pyCross* you'd like to install (e.g. *0.1*).
  
## Usage
Run `pycross.sh` on Linux/Mac (remember to do `chmod +x pycross.sh` first) or `pycross.bat` on Windows to launch the pyCross UI app.

See docs for detailed usage guide.

## Roadmap

See [roadmap.txt](https://github.com/S0mbre/crossword/blob/master/roadmap.txt) for future plans!