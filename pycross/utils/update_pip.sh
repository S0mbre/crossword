#!/bin/bash

python -m pip install --upgrade pycrossword

retVal=$?
if [ $retVal -ne 0 ]; then
	echo "python -m pip install --upgrade pycrossword" failed with error code $retVal
fi

if [ $retVal -e 0 ]; then
	echo UPDATE SUCCEEDED
fi

pycross