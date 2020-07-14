@echo off
cd "%~dp0"

echo ">>>>>> Clearing packages..."
start cleardist.bat

echo ">>>>>> Building packages..."
python setup.py sdist bdist_wheel

echo ">>>>>> FINISHED!"
set /p=Press ENTER...