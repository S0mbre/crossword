@echo off
set pybabel="c:\_PROG_\WPy64-3800\python-3.8.0.amd64\Scripts\pybabel.exe"
%pybabel% extract --sort-by-file -o pycross\locale\base.pot pycross
%pybabel% update -D base -i pycross\locale\base.pot -d pycross\locale
%pybabel% compile -D base -d pycross\locale
set /p=HIT ENTER...