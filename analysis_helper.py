import sqlite3
from typing import Self

class Experiment:
    def __init__(self, name: str, strategy: str):
        self.name = name
        self.strategy = strategy
        if self.name.startswith('V2baseline'):
            self.type = 'baseline'
        elif self.strategy.lower() == "default":
            self.type = "baseline"
        elif self.strategy.lower().startswith("e"):
            self.type = "even"
        else:
            self.type = "fixed"

    def __repr__(self):
        return f"<Experiment {self.name} {self.strategy}>"
    
    @staticmethod
    def fromFormat(format: str) -> Self:
        name, strategy = format.split("-")
        return Experiment(name, strategy)
    
    def getFullStrategyName(self) -> str:
        if (self.type == "even"):
            return f"EVEN-{self.getStrategyWithoutSuccessorGen()}"
        elif (self.type == "fixed"):
            return f"FIX-{self.getStrategyWithoutSuccessorGen()}"
        else:
            return "baseline"
    def getStrategyWithoutSuccessorGen(self) -> str:
        return self.strategy.split("_")[1]

def getExperimentId(con: sqlite3.Connection, experiment: Experiment):
    res = con.execute("SELECT id FROM experiment WHERE name=? AND search_strategy=?", (experiment.name, experiment.strategy))
    return res.fetchone()[0]