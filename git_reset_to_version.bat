@echo off

cd "%~dp0"

rem git reset --mixed %1 > gitlog.log
rem if %ERRORLEVEL% neq 0 goto restore
git checkout %1 > gitlog.log
goto finished

:restore
rem git reset --hard %2

:finished
python cwordg.py
rem set /p=Press ENTER...