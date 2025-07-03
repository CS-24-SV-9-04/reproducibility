#!/usr/bin/bash
if [ ! -d artifacts/all-models ]; then
    if [ ! -f artifacts/INPUTS-2024.tar.gz ]; then
        wget -O artifacts/INPUTS-2024.tar.gz https://mcc.lip6.fr/2024/archives/INPUTS-2024.tar.gz
    fi
    tar -xzf artifacts/INPUTS-2024.tar.gz -C artifacts
    mv artifacts/INPUTS artifacts/all-models
    rm artifacts/all-models/*-PT-*.tgz
    rm artifacts/all-models/.DS_Store
    for file in artifacts/all-models/*.tgz; do
        tar -xzf "$file" -C artifacts/all-models
        rm $file 
    done
else
    echo "artifacts/all-models already exists, skipping retrieval"
fi
