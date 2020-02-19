#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"
cd ../..

git fetch
retVal=$?
if [ $retVal -ne 0 ]; then
	echo "git fetch" failed with error code $retVal
fi

git reset --hard $1
retVal=$?
if [ $retVal -ne 0 ]; then
	echo "git reset --hard $1" failed with error code $retVal
fi

if [ $retVal -e 0 ]; then
	echo UPDATE SUCCEEDED
fi

cd pycross
python3 ./cwordg.py