@echo off

cd "%~dp0"
cd ..\..

git fetch
if %ERRORLEVEL% NEQ 0 (
	echo "git fetch" failed with error code %ERRORLEVEL%
	goto lrestart
)

git reset --hard %1
if %ERRORLEVEL% NEQ 0 (
	echo "git reset --hard %1" failed with error code %ERRORLEVEL%
	goto lrestart
)
:success
echo UPDATE SUCCEEDED

:lrestart
cd pycross\
python cwordg.py