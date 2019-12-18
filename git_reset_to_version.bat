@echo off

cd "%~dp0"

git checkout stable
git reset --hard %1 > gitlog.log

:finished
python cwordg.py
rem set /p=Press ENTER...