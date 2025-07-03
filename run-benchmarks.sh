#!/usr/bin/bash
set -e

if [ ! -f target-models.txt ]; then
    echo "target-models.txt not found, will run on all models"
    echo "If you want to run on a specific set of models, create target-models.txt with one model name per line."
    read -p "Press enter to continue or Ctrl+C to exit"
    for model_name in artifacts/all-models/* ; do
        echo "$(basename $model_name)" >> target-models.txt
    done
fi

mkdir -p artifacts/packed-results

for bench_type in "ExplicitCPN" "Baseline" ; do
    if [ -f "artifacts/packed-results/$bench_type.tar" ]; then
        echo "Skipping $bench_type benchmark, already done."
        continue
    fi
    echo starting $bench_type benchmark
    if [ -d artifacts/current-benchmark ]; then
        rm -r artifacts/current-benchmark
    fi
    mkdir -p artifacts/current-benchmark
    for model_name in $(cat target-models.txt) ; do
        export CATEGORIES=$(cat << EOF
16:ReachabilityCardinality:0:$(realpath artifacts/all-models/$model_name/ReachabilityCardinality.xml)
16:ReachabilityFireability:0:$(realpath artifacts/all-models/$model_name/ReachabilityFireability.xml)
EOF
        )
        export MODEL_NAME=$model_name
        export MODEL_FILE_PATH="artifacts/all-models/$model_name/model.pnml"
        export VERIFYPN_PATH="artifacts/verifypn-linux64"
        export SEARCH_STRATEGY="RDFS"
        export SUCCESSOR_GENERATOR="even"
        export PER_QUERY_TIMEOUT=300
        if [[ "$bench_type" == "ExplicitCPN" ]]; then
            export REACHABILITY_OPTIONS="-n 1 -C -s RDFS"
        else
            export REACHABILITY_OPTIONS="-n 1"
        fi
        export OUT_FILE_PATH_PREFIX="artifacts/current-benchmark/${MODEL_NAME}_${bench_type}-1"
        echo "Running benchmark for model $MODEL_NAME using $bench_type"
        ./big_job_script.sh 2> $OUT_FILE_PATH_PREFIX.err 1> $OUT_FILE_PATH_PREFIX.out
    done
    echo "" > artifacts/current-benchmark/large
    cd artifacts/current-benchmark
    tar -cf artifacts/packed-results/$bench_type.tar .
    cd ../..
done
