#!/bin/bash
#SBATCH --mem=16G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2

let "m=1024*1024*15"
ulimit -v $m

CATEGORY_REGEX="^([^:]+):([^:]+):([^:]+):(.+)$"

for CATEGORY in $CATEGORIES
do
    [[ $CATEGORY =~ $CATEGORY_REGEX ]]
    if [[ $? != 0 ]]; then
        echo $CATEGORY
        echo "INVALID CATEGORY DESCRIPTION"
        exit 1
    fi
    QUERY_COUNT=${BASH_REMATCH[1]}
    QUERY_CATEGORY_NAME=${BASH_REMATCH[2]}
    QUERY_IS_LTL=${BASH_REMATCH[3]}
    QUERY_FILE_PATH=${BASH_REMATCH[4]}
    for QUERY_INDEX in $(seq $QUERY_COUNT) ;
    do
        line="\n###### RUNNING $MODEL_NAME X $SUCCESSOR_GENERATOR-$SEARCH_STRATEGY X $QUERY_CATEGORY_NAME X $QUERY_INDEX ######"
        echo -e $line
        echo -e "$line" >&2
        if [ $QUERY_IS_LTL = '1' ]; then
            time /usr/bin/time --format="MAX_MEMORY: %MkB" timeout $PER_QUERY_TIMEOUT $VERIFYPN_PATH -x $QUERY_INDEX $MODEL_FILE_PATH $QUERY_FILE_PATH $LTL_OPTIONS
        else
            time /usr/bin/time --format="MAX_MEMORY: %MkB" timeout $PER_QUERY_TIMEOUT $VERIFYPN_PATH -x $QUERY_INDEX $MODEL_FILE_PATH $QUERY_FILE_PATH $REACHABILITY_OPTIONS
        fi
        EXECUTION_RESULT=$?
        if [ $EXECUTION_RESULT = 124 ]; then
            echo "TIMEOUT"
        elif [ $EXECUTION_RESULT = 130 ]; then
            exit 130
        elif [ "$EXECUTION_RESULT" -gt "2" ]; then
            echo "ERROR"
        fi
    done
done
