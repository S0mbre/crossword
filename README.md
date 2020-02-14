# pyCross - the Python Crossword Puzzle Generator and Editor
*pyCross* is a pure-Python implementation of a crossword puzzle generator and editor.


## Features:
* full-fledged [Qt 5](https://doc.qt.io/qt-5/index.html) based GUI
* cross-platform implementation
* multilingual interface (currently only English and Russian, more to come)
* install using pip (see [dist/](https://github.com/S0mbre/crossword/tree/master/dist)) or clone from Github
* open, save, restore, export, and import crossword puzzles
* powerful word sources: SQLite database / CSV (plaintext) / raw python list
* crossword generation (from word sources)
* supports common puzzle file formats: [XPF](https://www.xwordinfo.com/XPF/), [IPUZ](http://www.ipuz.org/) and raw text grid 
* easily load, edit and save word clues
* flexible GUI settings: colors, grid settings, clues table look & feel, etc. (can load and save settings)
* auto app updating / new release checking from Github
* lookup word definition in an online dictionary and Google
* suggest individual words from word sources
* comfortable navigation in GUI (hotkeys, keystrokes, mouse)
* context menus
* printing to PDF or printer with customizable page / element layout
* export crossword to image (jpg, png, tiff) / PDF / SVG with customizable resolution etc.
* comprehensive Doxygen-generated API reference

## Installation

### Requirements
You must have the following applications / packages installed in your system:

* Python 3.6+ (the app was written and tested with Python 3.7.4 and 3.8.0)
* Python packages: 
	- PyQt5>=5.14
	- PyQtWebEngine>=5.14
	- requests
	- numpy
	- pandas
	- altair
* Git (should be pre-installed on most modern Linux and Mac systems, alternatively install from the [git website](https://git-scm.com/downloads))

Git is not actually required if you opt for the pip installation variant as described below.

### Installation options

*1. Clone repo*

  To get the latest (non-stable) version, run:
  ```bash
  git clone https://github.com/S0mbre/crossword.git .
  ```
  
  This will checkout to the *master* branch which tracks all recent changes, some of which may not be yet merged into a release version.
  
  To get the latest stable version, run:
  ```bash
  git clone https://github.com/S0mbre/crossword.git .
  git reset --hard latest
  ```
  
  This will checkout to the branch pointed at by the *latest* tag which will always be the latest stable release.
  
*2. Install the required packages*

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
  cd crossword
  pip install -r requirements.txt
  ```
  
  If you're using a virtual environment, you can deactivate it after closing the app with `deactivate`.

## Usage
Run `pycross.sh` on Linux/Mac (remember to do `chmod +x pycross.sh` first) or `pycross.bat` on Windows to launch the pyCross UI app.

Alternativaly, you can register the pycross file associations at initial run (go to *Settings* > *Common* > *Register file associations*). After that, you can launch the app by double-clicking crossword files (like *.xpf or *.ipuz) or settings files (*.pxjson)

See docs for detailed usage guide.

## Roadmap

See [roadmap.txt](https://github.com/S0mbre/crossword/blob/master/roadmap.txt) for future plans!