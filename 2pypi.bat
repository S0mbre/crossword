@echo off
cd "%~dp0"

echo ">>>>>> Uploading to PyPi..."
python -m twine upload --verbose -u s0mbre dist\*

echo ">>>>>> FINISHED!"
set /p=Press ENTER...