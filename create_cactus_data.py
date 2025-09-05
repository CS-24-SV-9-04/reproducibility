#!/usr/bin/python3
from argparse import ArgumentParser
from io import TextIOWrapper
from itertools import chain
from os import mkdir
from pathlib import Path
import sqlite3
import sys
from typing import List, Optional

from analysis_helper import Experiment, getExperimentId


parser = ArgumentParser(prog="Generates cactus graphs for all given experiments")
parser.add_argument("time_lower_threshold", type=float)
parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")
parser.add_argument("--category", help="limits the cactus plot to one category", default=None)
parser.add_argument("--memory", help="Uses memory instead of time", default=False, action="store_true")
args = parser.parse_args()

CATEGORY = args.category
USE_MEMORY = args.memory

con = sqlite3.connect("artifacts/results.db")

allExperimentIds = [getExperimentId(con, Experiment.fromFormat(experimentFormat)) for experimentFormat in args.experiments]
allExperiments: List[Experiment] = [Experiment.fromFormat(experimentFormat) for experimentFormat in args.experiments]

def getSkipCount(con: sqlite3.Connection, all_experiments: List[int], time_lower_threshold: float):
    cur = con.execute(f"""
        SELECT COUNT(*) FROM (
        SELECT 
            iqi.id
        FROM query_result iqr
            LEFT JOIN query_instance iqi ON iqi.id = iqr.query_instance_id
        WHERE iqr.experiment_id IN ({("?," * len(all_experiments))[:-1]})
        GROUP BY iqr.query_instance_id
        HAVING MAX(iqr.time) < ? AND COUNT(iqr.time) = COUNT(*))
    """, (*all_experiments, time_lower_threshold))
    return cur.fetchone()[0]

skipCount = getSkipCount(con, allExperimentIds, args.time_lower_threshold)

def getTimes(con: sqlite3.Connection, experiment: int, all_experiments: List[int], time_lower_threshold: float, category: Optional[str]):
    cur = con.execute(f"""
        SELECT qr.time FROM query_result qr
            LEFT JOIN query_instance qi ON qi.id = qr.query_instance_id
        WHERE qr.experiment_id = ? AND qr.status = "Answered" 
            AND qi.query_name != 'ReachabilityDeadlock'
            AND (qi.query_name = ? OR ? IS NULL)
            AND qr.query_instance_id NOT IN (
            SELECT 
                iqi.id
                FROM query_result iqr
                LEFT JOIN query_instance iqi ON iqi.id = iqr.query_instance_id
                WHERE iqr.experiment_id IN ({("?," * len(all_experiments))[:-1]})
                GROUP BY iqr.query_instance_id
                HAVING MAX(iqr.time) < ? AND COUNT(iqr.time) = COUNT(*)
            )
            ORDER BY qr.time
    """, (experiment, category, category, *all_experiments, time_lower_threshold))
    return [(skipCount + i, 0.0001 if time[0] == 0 else time[0]) for i, time in enumerate(cur.fetchall())]

def getMemory(con: sqlite3.Connection, experiment: int, all_experiments: List[int], memory_lower_threshold: float, category: Optional[str]):
    cur = con.execute(f"""
        SELECT qr.max_memory FROM query_result qr
            LEFT JOIN query_instance qi ON qi.id = qr.query_instance_id
        WHERE qr.experiment_id = ? AND qr.status = "Answered" 
            AND qi.query_name != 'ReachabilityDeadlock'
            AND (qi.query_name = ? OR ? IS NULL)
            AND qr.query_instance_id NOT IN (
            SELECT 
                iqi.id
                FROM query_result iqr
                LEFT JOIN query_instance iqi ON iqi.id = iqr.query_instance_id
                WHERE iqr.experiment_id IN ({("?," * len(all_experiments))[:-1]})
                GROUP BY iqr.query_instance_id
                HAVING MAX(iqr.max_memory) < ? AND COUNT(iqr.max_memory) = COUNT(*)
            )
            ORDER BY qr.max_memory
    """, (experiment, category, category, *all_experiments, memory_lower_threshold))
    return [(skipCount + i, 0.0001 if time[0] == 0 else time[0]) for i, time in enumerate(cur.fetchall())]

def createTab(out: TextIOWrapper, data: List[tuple[int, float]]):
    out.write(f"counter\t{"memory" if USE_MEMORY else "time"}\n")
    for dataPoint in data:
        i, time = dataPoint
        out.write(f"{i}\t{time}\n")

graphsDir = Path("document/graphs")
graphsDir.mkdir(exist_ok=True)
cactusDir = graphsDir / "cactus"
cactusDir.mkdir(exist_ok=True)

for experiment in allExperiments:
    id = getExperimentId(con, experiment)
    postfix = ""
    if (CATEGORY != None):
        postfix = f"_{CATEGORY}"
    with (graphsDir / f"cactus/{experiment.name}{postfix}{"-memory" if USE_MEMORY else ""}.tab").open("w") as f:
        if USE_MEMORY:
            createTab(f, getMemory(con, id, allExperimentIds, args.time_lower_threshold, CATEGORY))
        else:
            createTab(f, getTimes(con, id, allExperimentIds, args.time_lower_threshold, CATEGORY))
