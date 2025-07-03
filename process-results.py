#!/usr/bin/python3
from contextlib import closing
import csv
from itertools import islice
from pathlib import Path
import re
import sqlite3
from tarfile import TarFile, TarInfo
import tarfile
from typing import Iterator, Optional
from result_parser import QueryInstance, QueryResult, Result, Status
import xml.etree.ElementTree as ET

def create_tables(db: sqlite3.Connection):
    db.execute("""
    CREATE TABLE IF NOT EXISTS experiment (id INTEGER PRIMARY KEY, name, search_strategy);
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS query_instance (id INTEGER PRIMARY KEY, model_name, query_name, query_index, query_type, expected_answer)
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS query_result (
        id INTEGER PRIMARY KEY,
        experiment_id,
        query_instance_id,
        time,
        status,
        result,
        max_memory,
        states,
        color_reduction_time,
        verification_time,
        FOREIGN KEY(experiment_id) REFERENCES experiment(id),
        FOREIGN KEY(query_instance_id) REFERENCES query_instance(id)
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS extended_result (
        id INTEGER PRIMARY KEY,
        query_result_id,
        stdout,
        stderr,
        FOREIGN KEY(query_result_id) REFERENCES query_result(id)
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS processed_files (
        id INTEGER PRIMARY KEY,
        file_name
    );
    """)

class ConsensusAnswer:
    def __init__(self, model_name: str, category: str, index: int, consensus: Optional[QueryResult]):
        self.model_name = model_name
        self.category = category
        self.index = index + 1
        self.consensus = consensus


def read_consensus_answers(answerPath: Path) -> Iterator[ConsensusAnswer]:
    with answerPath.open("r", newline='') as csvFile:
        csvReader = csv.reader(csvFile)
        for row in csvReader:
            yield ConsensusAnswer(row[0], row[1], int(row[2]),
                QueryResult.Satisfied if row[3] == "T"
                    else (QueryResult.Unsatisfied if row[3] == "F" else None))

def parse_query_and_type(property: ET.Element) -> tuple[str, int, Optional[str]]:
    name = property.find("./{http://mcc.lip6.fr/}id").text
    m = re.match(r".+\-([^-0-9]+)\-([0-9]+\-)?([0-9]+)$", name)
    query_name = m.group(1)
    index = int(m.group(3)) + 1

    if property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}all-paths") is not None:
        return query_name, index, "ag"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}exists-path") is not None:
        return query_name, index, "ef"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}negation/{http://mcc.lip6.fr/}all-paths") is not None:
        return query_name, index, "ef"
    elif property.find("./{http://mcc.lip6.fr/}formula/{http://mcc.lip6.fr/}negation/{http://mcc.lip6.fr/}exists-path") is not None:
        return query_name, index, "ag"
    else:
        return query_name, index, None

NON_DYNAMIC_QUERY_CATEGORIES = ["ReachabilityDeadlock", "OneSafe", "Liveness", "StableMarking", "QuasiLiveness"]
DYNAMIC_QUERY_CATEGORIES = ["ReachabilityCardinality", "ReachabilityFireability", "LTLCardinality", "LTLFireability", "CTLCardinality", "CTLFireability"]
def create_query_instances(db: sqlite3.Connection, consensus_answers_path: Path, all_models_path: Path):
    with closing(db.execute("SELECT COUNT(*) FROM query_instance")) as cur:
        if cur.fetchone()[0] > 0:
            print("Query instances already exist, skipping creation")
            return
    known_models: set[str] = set()
    consensus_answers = read_consensus_answers(consensus_answers_path)
    queries_to_insert: list[tuple] = []
    for consensus_answer in filter(lambda x : 'COL' in x.model_name, consensus_answers):
        known_models.add(consensus_answer.model_name)
        expected_answer = None if consensus_answer.consensus == None else consensus_answer.consensus.name
        query_type = None
        if consensus_answer.category in DYNAMIC_QUERY_CATEGORIES:
            parsed = ET.parse(str(Path(all_models_path) / consensus_answer.model_name / (consensus_answer.category + ".xml")))
            for queryElement in islice(parsed.iterfind(".//{http://mcc.lip6.fr/}property"), consensus_answer.index - 1, consensus_answer.index):
                _, _, query_type = parse_query_and_type(queryElement)
        if (consensus_answer.category == "ReachabilityDeadlock"):
            query_type = "ef"
        queries_to_insert.append((consensus_answer.model_name, consensus_answer.category, consensus_answer.index, query_type, expected_answer))
    for modelDirectoryPath in Path(all_models_path).glob("*"):
        model_name = modelDirectoryPath.name 
        if (modelDirectoryPath.name not in known_models):
            for queryCategory in DYNAMIC_QUERY_CATEGORIES:
                parsed = ET.parse(str(modelDirectoryPath / (queryCategory + ".xml")))
                for queryElement in parsed.iterfind(".//{http://mcc.lip6.fr/}property"):
                    _, index, query_type = parse_query_and_type(queryElement)
                    queries_to_insert.append((model_name, queryCategory, index, query_type, None))
            for queryCategory in NON_DYNAMIC_QUERY_CATEGORIES:
                query_type = None if queryCategory != "ReachabilityDeadlock" else "ef"
                queries_to_insert.append((model_name, queryCategory, 1, query_type, None))
    with closing(db.cursor()) as cur:
        cur.executemany("""
            INSERT INTO query_instance (model_name, query_name, query_index, query_type, expected_answer)
            VALUES (?, ?, ?, ?, ?)
        """, queries_to_insert)

def read_or_fail(tarFile: TarFile, tarFileInfo: TarInfo):
    f = tarFile.extractfile(tarFileInfo)
    if f == None:
        raise Exception("Could not find specific file in tar file")
    with f as fi:
        return fi.read().decode()

def process_tar(tarFile: TarFile) -> Iterator[Result]:
    is_large_job = any(map(lambda x: x.endswith('large'), tarFile.getnames()))
    for outInfo in tarFile.getmembers():
        if not outInfo.path.endswith(".out"):
            continue
        try:
            outContent = read_or_fail(tarFile, outInfo)
            errContent = read_or_fail(tarFile, tarFile.getmember(outInfo.path.removesuffix(".out") + ".err"))
            results = Result.fromOutErr(outContent, errContent, is_large_job)
            for result in results:
                yield result
        except KeyError:
            pass


def process_directory(already_processed_files: set[str], directory: Path) -> Iterator[tuple[str, Result] | str]:
    for filePath in directory.glob("*.tar"):
        bench_name = filePath.name.split(".")[0]
        if (bench_name in already_processed_files):
            print(f"Skipping already processed file {filePath.name}")
            continue
        with tarfile.open(str(filePath), "r") as tarFile:
            print(f"adding file {filePath.name} to database")
            for result in process_tar(tarFile):
                yield (bench_name, result)
            yield bench_name

def process_and_insert(db: sqlite3.Connection, directory: Path):
    experiment_id_map: dict[str, int] = {}
    query_instance_id_map: dict[str, int] = {}

    with closing(db.execute("SELECT id, name, search_strategy FROM experiment")) as cur:
        for row in cur.fetchall():
            experiment_id_map[f"{row[1]}#{row[2]}"] = row[0]

    with closing(db.execute("SELECT id, model_name, query_name, query_index, query_type FROM query_instance")) as cur:
        for row in cur.fetchall():
            query_instance_id_map[f"{row[1]}#{row[2]}#{row[3]}"] = row[0]

    cur = db.execute("SELECT file_name FROM processed_files")
    already_processed_files = set(map(lambda x: x[0], cur.fetchall()))
    cur.close()
    rows_to_insert: list[tuple] = []

    for item in process_directory(already_processed_files, directory):
        if type(item) is str:
            with closing(db.execute("INSERT INTO processed_files (file_name) VALUES (?)", (item,))):
                pass
            continue
        else:
            experiment_name: str = item[0]
            result: Result = item[1]
            experiment_id_key = f"{experiment_name}-{result.strategy}"
            if (experiment_id_key not in experiment_id_map):
                cur = db.execute("INSERT INTO experiment (name, search_strategy) VALUES (?, ?) RETURNING id", (experiment_name, result.strategy))
                id = cur.fetchone()
                cur.close()
                experiment_id_map[experiment_id_key] = id[0]

            rows_to_insert.append((
                experiment_id_map[experiment_id_key],
                query_instance_id_map[f"{result.query_instance.model_name}#{result.query_instance.query_name}#{result.query_instance.query_index}"],
                result.time,
                result.status.name,
                None if result.result == None else result.result.name,
                result.maxMemory,
                result.states,
                result.colorReductionTime,
                result.verificationTime
            ))
    with closing(db.cursor()) as cur:
        cur.executemany("""
            INSERT INTO query_result
                (
                    experiment_id,
                    query_instance_id,
                    time,
                    status,
                    result,
                    max_memory,
                    states,
                    color_reduction_time,
                    verification_time
                )
            VALUES
                (?,?,?,?,?,?,?,?,?)
        """, rows_to_insert)

def main():
    artifacts_path = Path("artifacts")
    artifacts_path.mkdir(exist_ok=True)

    db = sqlite3.connect(str(artifacts_path / "results.db"))
    create_tables(db)
    print("Creating query instances...")
    create_query_instances(db, artifacts_path / "consensus-answers.csv", artifacts_path / "all-models")
    print("Processing results...")
    process_and_insert(db, artifacts_path / "packed-results")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()