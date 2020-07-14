@echo off
cd "%~dp0"

echo "USAGE: release-version ["fixup" | ""] [commit-message | ""]"
echo "Param 1 = release version, e.g. "0.1""
echo "Param 2 = "fixup" if you wanna amend the previous commit, or an empty string to create new commit"
echo "Param 3 = commit message or an empty string to edit commit message manually with editor"

if "%1" == "" (
	echo ">>>>>> ERROR: No version provided!"
	goto exitbat
)

echo ">>>>>> Switching to master..."
git checkout master
if %ERRORLEVEL% NEQ 0 goto exitbat

echo ">>>>>> Committing pending changes..."
git add --all
if "%2" == "fixup" (
	git commit -a --amend --no-edit
) else (
	if "%3" == "" (git commit -a) else (git commit -a -m "%3")
)
echo ">>>>>> Updating remote branch origin/master..."
git push -f

if %ERRORLEVEL% NEQ 0 goto exitbat

set prefix=release_
set br=%prefix%%1
set tagprefix=v
set tagname=%tagprefix%%1
echo ">>>>>> Switching to existing or new branch %br%..."
git checkout -B %br%

if %ERRORLEVEL% NEQ 0 goto exitbat
echo ">>>>>> Merging changes from master..."
git merge master

if %ERRORLEVEL% NEQ 0 goto exitbat

echo ">>>>>> Recreating tag latest..."
git tag -f %tagname%
git tag -f latest
echo ">>>>>> Pushing branch %tagname% and tag latest to remote repo..."
git push origin %br% -uf --tags
echo ">>>>>> Switching back to master..."
git checkout master

:exitbat
echo ">>>>>> DONE!"
set /p=Press ENTER...