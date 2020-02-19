@echo off

python -m pip install --upgrade pycrossword

if %ERRORLEVEL% NEQ 0 (
	echo "python -m pip install --upgrade pycrossword" failed with error code %ERRORLEVEL%
	goto lrestart
)
:success
echo UPDATE SUCCEEDED

:lrestart
cd pycross\
pythonw cwordg.py