@echo off
cd "%~dp0"

echo ">>>>>> Building packages..."
python setup.py sdist bdist_wheel

echo ">>>>>> Uploading to PyPi..."
python -m twine upload --verbose -u __token__ -p pypi-AgEIcHlwaS5vcmcCJGE3NTBhZTgyLWJmYWYtNDZhNS05MDk2LTczZWE1ZGFjZGE3MAACJXsicGVybWlzc2lvbnMiOiAidXNlciIsICJ2ZXJzaW9uIjogMX0AAAYgN_NSesWV44ptEPqyUFL7a7S2cdTnNScZHy5zVlfhT4E dist\*

echo ">>>>>> FINISHED!"
set /p=Press ENTER...