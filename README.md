# pycrossword - the Python Crossword Puzzle Generator and Editor
*pycrossword* is a pure-Python implementation of a crossword puzzle generator and editor.

## Download
*pycrossword* source code and documentation are hosted on [Github](https://github.com/S0mbre/crossword)

The python package is available from [PyPi](https://pypi.org/project/pycrossword/)

## Features:
* full-fledged [Qt 5](https://doc.qt.io/qt-5/index.html) based GUI
* cross-platform implementation
* multilingual interface (currently only English and Russian, more to come)
* install from Github or PyPi
* open, save, restore, export, and import crossword puzzles
* powerful word sources: SQLite database / CSV (plaintext) / raw python list
* crossword generation (from word sources)
* supports common puzzle file formats: [XPF](https://www.xwordinfo.com/XPF/), [IPUZ](http://www.ipuz.org/) and raw text grid 
* easily load, edit and save word clues
* flexible GUI settings: colors, grid settings, clues table look & feel, etc. (can load and save settings)
* auto app updating / new release checking from Github
* lookup word definition in an online dictionary and Google
* manual editing of individual words and suggestions from word sources
* comfortable navigation in GUI (hotkeys, keystrokes, mouse)
* context menus
* hi-res printing to PDF or printer with customizable page / element layout
* export crossword to image (jpg, png, tiff) / PDF / SVG with customizable resolution etc.
* store crosswords in cloud and share them social networks
* view user-friendly stats on current crossword in chart
* inbuilt browser
* comprehensive Doxygen-generated API reference

## Installation

### Requirements
You must have the following applications / packages installed in your system:

* Python 3.7+ (the app was written and tested with Python 3.7.4 and 3.8.0)
* Python packages: 
	- PyQt5>=5.14
	- PyQtWebEngine>=5.14
	- QScintilla>=2.11
	- requests
	- numpy
	- pandas
	- altair
* Git (should be pre-installed on most modern Linux and Mac systems, alternatively install from the [git website](https://git-scm.com/downloads))

The latter two (packages and Git) are not actually required if you opt for the PyPi (pip) installation variant as described below.

### Installation options
Choose one of the two installation options.

#### *1. Clone repo* - copy entire source code with version control history

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
  
#### Install the required packages

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
  scripts\activate.bat
  ```
  
  This step is, of course, optional. You can skip it if you don't want to use virtual environments for some reason or other. 
  
  Then just run:
  ```bash
  cd crossword
  python -m pip install -r requirements.txt
  ```
  
  If you're using a virtual environment, you can deactivate it after closing the app with `deactivate`.
  
#### *2. Install from PyPi*

  Create your virtual environment as described above (which is again optional). Then use *pip* to download and install *pycrossword* (together with the required additional packages):
  ```
  pip install --upgrade pycrossword
  ```

## Usage
Run `pycross.sh` on Linux/Mac (remember to do `chmod +x pycross.sh` first) or `pycross.bat` on Windows to launch the pycrossword UI app.

Alternativaly, you can register the pycrossword file associations at initial run (go to *Settings* > *Common* > *Register file associations*). After that, you can launch the app by double-clicking crossword files (like \*.xpf or \*.ipuz) or settings files (\*.pxjson)

See docs for detailed usage guide.

## Roadmap

See [roadmap.txt](https://github.com/S0mbre/crossword/blob/master/roadmap.txt) for future plans!