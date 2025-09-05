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
parser.add_argument("experiment_a", help="The first experiment <name>-<strategy> format")
parser.add_argument("experiment_b", help="The second experiment <name>-<strategy> format")
parser.add_argument("--category", help="limits the cactus plot to one category", default=None)
parser.add_argument("--memory", help="Uses memory instead of time", default=False, action="store_true")
args = parser.parse_args()

CATEGORY = args.category
EXPERIMENT_A = args.experiment_a
EXPERIMENT_B = args.experiment_b
USE_MEMORY = args.memory

con = sqlite3.connect("artifacts/results.db")

aParsed = Experiment.fromFormat(EXPERIMENT_A)
bParsed = Experiment.fromFormat(EXPERIMENT_B)

aId = getExperimentId(con, aParsed)
bId = getExperimentId(con, bParsed)


def getTimes(con: sqlite3.Connection, experimenta: int, experimentb: int, category: Optional[str]):
    cur = con.execute(f"""
        SELECT
            CASE WHEN qra.result IS NULL AND qrb.result IS NULL THEN 0
                WHEN qra.result IS NULL AND qrb.result IS NOT NULL THEN 1000000000000
                WHEN qra.result IS NULL AND qrb.result IS NULL THEN 1
                ELSE qra.time/qrb.time END AS ratio
        FROM query_instance qi
            LEFT JOIN query_result qra ON qra.query_instance_id = qi.id
            LEFT JOIN query_result qrb ON qrb.query_instance_id = qi.id
        WHERE 
            qra.experiment_id = ?
            AND qrb.experiment_id = ?
            AND (qi.query_name = ? OR ? IS NULL)
        ORDER BY ratio
    """, (experimenta, experimentb, category, category))
    rows: List[tuple[float]] = cur.fetchall()
    max_value = max(map(lambda x: x[0] if x[0] < 1000000000000 else -1, rows))
    min_value = min(map(lambda x: x[0] if x[0] > 0 else 1000000000000, rows))
    return [(i, min_value if time[0] == 0 else (time[0] if time[0] < 1000000000000 else max_value)) for i, time in enumerate(rows)]

def getMemory(con: sqlite3.Connection, experimenta: int, experimentb: int, category: Optional[str]):
    cur = con.execute(f"""
        SELECT
            CASE WHEN qra.result IS NULL AND qrb.result IS NULL THEN 0
                WHEN qra.result IS NULL AND qrb.result IS NOT NULL THEN 1000000000000
                WHEN qra.result IS NULL AND qrb.result IS NULL THEN 1
                ELSE qra.max_memory/qrb.max_memory END AS ratio
        FROM query_instance qi
            LEFT JOIN query_result qra ON qra.query_instance_id = qi.id
            LEFT JOIN query_result qrb ON qrb.query_instance_id = qi.id
        WHERE 
            qra.experiment_id = ?
            AND qrb.experiment_id = ?
            AND (qi.query_name = ? OR ? IS NULL)
        ORDER BY ratio
    """, (experimenta, experimentb, category, category))
    rows: List[tuple[float]] = cur.fetchall()
    max_value = max(map(lambda x: x[0] if x[0] < 1000000000000 else -1, rows))
    min_value = min(map(lambda x: x[0] if x[0] > 0 else 1000000000000, rows))
    return [(i, min_value if time[0] == 0 else (time[0] if time[0] < 1000000000000 else max_value)) for i, time in enumerate(rows)]

def createTab(out: TextIOWrapper, data: List[tuple[int, float]]):
    out.write(f"counter\t{"memory" if USE_MEMORY else "time"}\n")
    for dataPoint in data:
        i, time = dataPoint
        out.write(f"{i}\t{time:f}\n")

postfix = ""
if (CATEGORY != None):
    postfix = f"_{CATEGORY}"

output_directory = Path("document/graphs/ratio")
output_directory.mkdir(parents=True, exist_ok=True)

with (output_directory / f"{aParsed.name}_{bParsed.name}{postfix}{"-memory" if USE_MEMORY else ""}.tab").open("w") as f:
    if USE_MEMORY:
        createTab(f, getMemory(con, aId, bId, CATEGORY))
    else:
        createTab(f, getTimes(con, aId, bId, CATEGORY))
