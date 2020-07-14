@echo off
cd "%~dp0"

echo ">>>>>> Uploading to TestPyPi..."
python -m twine upload --repository testpypi -u s0mbre dist\*

echo ">>>>>> FINISHED!"
set /p=Press ENTER...