@echo off

cd "%~dp0"

git fetch -q > nul
if %ERRORLEVEL% neq 0 goto finished
git describe --abbrev=0

:finished
rem set /p=Press ENTER...