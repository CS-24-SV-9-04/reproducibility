#!/usr/bin/bash
set -e
for c in "" "ReachabilityCardinality" "ReachabilityFireability"; do
    category_arg="--category $c"
    if [ -z "$c" ]; then
        category_arg=""
    fi
    echo "Creating cactus data with category $c"
    for enable_memory in " " "--memory"; do
        echo "Creating ratio and cactus with flag '$enable_memory'"
        ./create_cactus_data.py -1 $category_arg ExplicitCPN-even_RDFS Baseline-even_RDFS $enable_memory
        for a in "ExplicitCPN-even_RDFS" "Baseline-even_RDFS"; do
            for b in "ExplicitCPN-even_RDFS" "Baseline-even_RDFS"; do
                if [ "$a" = "$b" ]; then
                    continue
                fi
                echo "Creating ratio plot for $a vs $b with category $c"
                ./create_ratio_plot.py $category_arg $a $b $enable_memory
            done
        done
    done
done
cat << EOF > document/comparison-table.tex
\begin{table}[htbp]
\centering
\begin{tabular}{|l|c|c|c|c|c|c|c|c|c|}
\hline
EOF
./create-comparison-table.py Baseline-even_RDFS ExplicitCPN-even_RDFS >> document/comparison-table.tex
cat << EOF >> document/comparison-table.tex
\end{tabular}
\caption{Comparison of Explicit and Unfolding where + means positive answers, - means negative answers and $\ast$ means both}
\label{tab:comparison-table}
\end{table}
EOF