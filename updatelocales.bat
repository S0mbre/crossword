@echo off
set pybabel="%PYPATH%\Scripts\pybabel.exe"
%pybabel% extract --sort-by-file -o pycross\locale\base.pot pycross
%pybabel% update --no-fuzzy-matching -D base -i pycross\locale\base.pot -d pycross\locale
%pybabel% compile -D base -d pycross\locale
set /p=HIT ENTER...