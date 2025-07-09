#!/usr/bin/python3
from argparse import ArgumentParser
from itertools import islice
import sqlite3

from analysis_helper import Experiment, getExperimentId


prettyNames = {
    "Baseline": "Unfolding",
    "ExplicitCPN": "Explicit",
}

def main():
    parser = ArgumentParser(prog="Generates cactus graphs for all given experiments")
    parser.add_argument("experiments", nargs='+', help="all experiments included in the matrix in <name>-<strategy> format")    
    args = parser.parse_args()
    db = sqlite3.connect("artifacts/results.db")

    experimentIds = map(lambda e: getExperimentId(db, Experiment.fromFormat(e)), args.experiments)

    cur = db.execute(f"""
        SELECT
            e.name,
            COUNT(*) AS all_total,
            COUNT(*) FILTER (WHERE (qi.query_type = "ef" AND qr.result = "Satisfied") OR (qi.query_type = "ag" AND qr.result = "Unsatisfied")) AS all_positive_answers,
            COUNT(*) FILTER (WHERE (qi.query_type = "ag" AND qr.result = "Satisfied") OR (qi.query_type = "ef" AND qr.result = "Unsatisfied")) AS all_negative_answers,
            COUNT(*) FILTER (WHERE qi.query_name = 'ReachabilityCardinality' OR qi.query_name = 'LTLCardinality') AS cardinality_total,
            COUNT(*) FILTER (WHERE ((qi.query_type = "ef" AND qr.result = "Satisfied") OR (qi.query_type = "ag" AND qr.result = "Unsatisfied")) and (qi.query_name = 'ReachabilityCardinality' OR qi.query_name = 'LTLCardinality')) AS cardinality_positive_answers,
            COUNT(*) FILTER (WHERE ((qi.query_type = "ag" AND qr.result = "Satisfied") OR (qi.query_type = "ef" AND qr.result = "Unsatisfied")) and (qi.query_name = 'ReachabilityCardinality' OR qi.query_name = 'LTLCardinality')) AS cardinality_negative_answers,
            COUNT(*) FILTER (WHERE qi.query_name = 'ReachabilityFireability' OR qi.query_name = 'LTLFireability') AS fireability_total,
            COUNT(*) FILTER (WHERE ((qi.query_type = "ef" AND qr.result = "Satisfied") OR (qi.query_type = "ag" AND qr.result = "Unsatisfied")) and (qi.query_name = 'ReachabilityFireability' OR qi.query_name = 'LTLFireability')) AS fireability_positive_answers,
            COUNT(*) FILTER (WHERE ((qi.query_type = "ag" AND qr.result = "Satisfied") OR (qi.query_type = "ef" AND qr.result = "Unsatisfied")) and (qi.query_name = 'ReachabilityFireability' OR qi.query_name = 'LTLFireability')) AS fireability_negative_answers
        FROM query_result qr
            LEFT JOIN query_instance qi ON qi.id = qr.query_instance_id
            LEFT JOIN experiment e ON e.id = qr.experiment_id
        WHERE e.id IN ({",".join(map(lambda x: str(x), experimentIds))}) AND qi.query_name != 'ReachabilityDeadlock' AND qr.status = "Answered"
        GROUP BY qr.experiment_id
        ORDER BY all_total DESC
    """)
    print(r"\multirow{2}{*}{Engine}&\multicolumn{3}{c|}{All}&\multicolumn{3}{c|}{Cardinality}&\multicolumn{3}{c|}{Fireability}")
    print(r"\\\cline{2-10}")
    print(r"&$\ast$&+&-&$\ast$&+&-&$\ast$&+&-")
    print(r"\\\hline")
    for data in cur.fetchall():
        print(f"{prettyNames[data[0]]}&{"&".join(islice(map(lambda x: str(x), data), 1, None))}\n\\\\")
        print(r"\hline")

if __name__ == "__main__":
    main()