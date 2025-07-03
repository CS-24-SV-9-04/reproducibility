#!/usr/bin/bash
set -e

mkdir -p artifacts

./get-verifypn.sh
./get_all_answers.py
./retrieve_models.sh
./run-benchmarks.sh
./process-results.py
./create-plots.sh