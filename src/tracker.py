"""
tracker.py — Append-only logging for simulation results.

Two output files per run:
  results.csv    — one row per completed iteration (stance trajectory data)
  exchanges.jsonl — one JSON object per iteration (full conversation transcripts)

Both files are opened and closed atomically on every write so a crash never
leaves a partially-written row. The CSV header is written once on first call.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import LikertStance, SimulationConfig
    from exchange import ExchangeTurn
    from personas import AgentPersona


CSV_COLUMNS = [
    "iteration",
    "run_id",
    "memory_condition",
    "topic",
    "agent_a_id",
    "agent_a_name",
    "agent_a_leaning",
    "agent_a_stance_before_label",
    "agent_a_stance_before_score",
    "agent_a_stance_after_label",
    "agent_a_stance_after_score",
    "agent_b_id",
    "agent_b_name",
    "agent_b_leaning",
    "agent_b_stance_before_label",
    "agent_b_stance_before_score",
    "agent_b_stance_after_label",
    "agent_b_stance_after_score",
    "n_turns",
    "sim_clock",
]


class SimulationTracker:
    def __init__(self, config: "SimulationConfig", run_id: str) -> None:
        self._output_dir = Path(config.output_dir)
        self._config = config
        self._run_id = run_id
        self._csv_path = self._output_dir / "results.csv"
        self._jsonl_path = self._output_dir / "exchanges.jsonl"
        self._csv_initialised = self._csv_path.exists()

    def log(
        self,
        iteration: int,
        agent_a: "AgentPersona",
        agent_b: "AgentPersona",
        stance_a_before: "LikertStance",
        stance_a_after: "LikertStance",
        stance_b_before: "LikertStance",
        stance_b_after: "LikertStance",
        exchange_log: list["ExchangeTurn"],
        sim_clock: str,
    ) -> None:
        self._write_csv_row(
            iteration, agent_a, agent_b,
            stance_a_before, stance_a_after,
            stance_b_before, stance_b_after,
            len(exchange_log), sim_clock,
        )
        self._write_jsonl_record(
            iteration, agent_a, agent_b,
            stance_a_before, stance_a_after,
            stance_b_before, stance_b_after,
            exchange_log, sim_clock,
        )

    def _write_csv_row(
        self,
        iteration: int,
        agent_a: "AgentPersona",
        agent_b: "AgentPersona",
        stance_a_before: "LikertStance",
        stance_a_after: "LikertStance",
        stance_b_before: "LikertStance",
        stance_b_after: "LikertStance",
        n_turns: int,
        sim_clock: str,
    ) -> None:
        row = {
            "iteration":                  iteration,
            "run_id":                     self._run_id,
            "memory_condition":           self._config.memory_condition.value,
            "topic":                      self._config.topic,
            "agent_a_id":                 agent_a.agent_id,
            "agent_a_name":               agent_a.name,
            "agent_a_leaning":            agent_a.leaning.value,
            "agent_a_stance_before_label": stance_a_before.label,
            "agent_a_stance_before_score": stance_a_before.score,
            "agent_a_stance_after_label":  stance_a_after.label,
            "agent_a_stance_after_score":  stance_a_after.score,
            "agent_b_id":                 agent_b.agent_id,
            "agent_b_name":               agent_b.name,
            "agent_b_leaning":            agent_b.leaning.value,
            "agent_b_stance_before_label": stance_b_before.label,
            "agent_b_stance_before_score": stance_b_before.score,
            "agent_b_stance_after_label":  stance_b_after.label,
            "agent_b_stance_after_score":  stance_b_after.score,
            "n_turns":                    n_turns,
            "sim_clock":                  sim_clock,
        }

        write_header = not self._csv_initialised
        with self._csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if write_header:
                writer.writeheader()
                self._csv_initialised = True
            writer.writerow(row)

    def _write_jsonl_record(
        self,
        iteration: int,
        agent_a: "AgentPersona",
        agent_b: "AgentPersona",
        stance_a_before: "LikertStance",
        stance_a_after: "LikertStance",
        stance_b_before: "LikertStance",
        stance_b_after: "LikertStance",
        exchange_log: list["ExchangeTurn"],
        sim_clock: str,
    ) -> None:
        record = {
            "iteration":      iteration,
            "run_id":         self._run_id,
            "memory_condition": self._config.memory_condition.value,
            "topic":          self._config.topic,
            "agent_a": {
                "id":      agent_a.agent_id,
                "name":    agent_a.name,
                "leaning": agent_a.leaning.value,
            },
            "agent_b": {
                "id":      agent_b.agent_id,
                "name":    agent_b.name,
                "leaning": agent_b.leaning.value,
            },
            "agent_a_stance_before": stance_a_before.label,
            "agent_a_stance_after":  stance_a_after.label,
            "agent_b_stance_before": stance_b_before.label,
            "agent_b_stance_after":  stance_b_after.label,
            "n_turns":    len(exchange_log),
            "sim_clock":  sim_clock,
            "turns": [
                {
                    "turn":         t.turn,
                    "speaker_id":   t.speaker_id,
                    "speaker_name": t.speaker_name,
                    "listener_id":  t.listener_id,
                    "utterance":    t.utterance,
                }
                for t in exchange_log
            ],
        }

        with self._jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
