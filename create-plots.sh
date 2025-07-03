#!/usr/bin/bash
set -e
for c in "" "ReachabilityCardinality" "ReachabilityFireability"; do
    category_arg="--category $c"
    if [ -z "$c" ]; then
        category_arg=""
    fi
    echo "Creating cactus data with category $c"
    ./create_cactus_data.py -1 $category_arg ExplicitCPN-even_RDFS Baseline-even_RDFS
    for a in "ExplicitCPN-even_RDFS" "Baseline-even_RDFS"; do
        for b in "ExplicitCPN-even_RDFS" "Baseline-even_RDFS"; do
            if [ "$a" = "$b" ]; then
                continue
            fi
            echo "Creating ratio plot for $a vs $b with category $c"
            ./create_ratio_plot.py $category_arg $a $b
        done
    done
done