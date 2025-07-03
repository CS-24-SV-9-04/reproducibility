#!/usr/bin/bash
mkdir -p artifacts
if [ ! -f artifacts/verifypn-linux64 ]; then
    if [ ! -f artifacts/verifypn-linux64.zip ]; then
        echo "Downloading verifyPN..."
        wget https://nightly.link/TAPAAL/verifypn/actions/runs/15775790484/verifypn-linux64.zip -O artifacts/verifypn-linux64.zip
    fi
    unzip -o artifacts/verifypn-linux64.zip -d artifacts/
fi