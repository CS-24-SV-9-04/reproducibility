# Reproducibility package for Explicit Model Checking Engine for Reachability Analysis of Colored Petri Nets
This package, lets you reproduce the results from the paper "Explicit Model Checking Engine for Reachability Analysis of Colored Petri Nets" The procedure is mostly automatic and requires a linux machine with python 3.12 installed, 24+ GB memory and pdflatex or an online service like overleaf.

Running the full benchmark will in the worst case take 1450 hours and 40 minutes. Therefore, by default, only a subset of models will be run which takes ~5 hours. The subset of models that is used is specified in the `target-models.txt` file. It comes preloaded with 28 models that we know can be solved in a reasonable time frame. If the file is deleted, it will be recreated with all models from MCC24 and therefore a full benchmark will be run.

One can use a cluster computer to run the full benchmark with a few modifications to the `run-benchmarks.sh`, specifically by altering the call to `big_job_script.sh` to use sbatch in case of slurm or another form of scheduling.

To rerun the benchmark, firstly run the `reset.sh` script and then `./reproduce.sh` which will fetch all the neccessary files for the benchmark, run the benchmark, process the result and produce the figures. Afterwards the folder called `document` will be populated with the data for the graphs. Thereafter one can use pdflatex to compile the `main.tex` file or upload the folder to overleaf to render the graphs and tables.

The results from running all benchmarks come preloaded as if the `reproduce.sh` was run on all models from MCC24.
