"""
checkpoint.py — Crash recovery for the simulation loop.

Crash-safety contract (Arch Issue 4 from DESIGN_DECISIONS.md):

  1. Before starting iteration N:
       backup_db(N-1, config)     ← snapshot SQLite BEFORE touching it

  2. After tracker.log() succeeds:
       write_checkpoint(N, config) ← ONLY written after CSV write succeeds

  3. On startup, if checkpoint.json exists:
       - Restore the SQLite backup for last_completed_iteration
       - Skip all iterations already recorded in the CSV
       - Rebuild current_stances from the CSV

This guarantees: the SQLite state exactly matches the CSV log at all times,
even after a crash mid-exchange.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import LikertStance, SimulationConfig
    from personas import AgentPersona


def write_checkpoint(iteration: int, config: "SimulationConfig") -> None:
    """Write checkpoint AFTER the CSV row has been successfully appended."""
    path = Path(config.output_dir) / "checkpoint.json"
    data = {
        "last_completed_iteration": iteration,
        "memory_condition":         config.memory_condition.value,
        "random_seed":              config.random_seed,
        "topic":                    config.topic,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_checkpoint(config: "SimulationConfig") -> int | None:
    """
    Return last_completed_iteration if a checkpoint exists, else None.
    None means this is a fresh run.
    """
    path = Path(config.output_dir) / "checkpoint.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["last_completed_iteration"]


def backup_db(iteration: int, config: "SimulationConfig") -> None:
    """
    Copy the SQLite database file before starting iteration N.
    The backup is named simulation_iter_{N}.db.bak.
    If no database file exists yet (fresh run), skip silently.
    """
    src = Path(config.db_path)
    if not src.exists():
        return
    dst = Path(config.output_dir) / f"simulation_iter_{iteration}.db.bak"
    shutil.copy2(src, dst)


def restore_db_backup(last_completed: int, config: "SimulationConfig") -> None:
    """
    Restore the SQLite database to the state at end of last_completed iteration.
    Called on resume after a crash.
    """
    backup = Path(config.output_dir) / f"simulation_iter_{last_completed}.db.bak"
    dst = Path(config.db_path)
    if backup.exists():
        shutil.copy2(backup, dst)
    elif dst.exists():
        # No backup but DB exists — safest to remove it and start KG fresh
        # (only the CSV-logged data is the source of truth for resume)
        dst.unlink()


def rebuild_stances(
    personas: list["AgentPersona"],
    csv_path: Path,
) -> dict[str, "LikertStance"]:
    """
    Rebuild the current_stances dict from the CSV log after a crash resume.

    Reads every row in the CSV and applies stance updates in order, so the
    returned dict reflects the last annotated stance for every agent.
    """
    import csv as _csv
    from config import LikertStance, parse_likert

    stances: dict[str, LikertStance] = {
        p.agent_id: p.initial_stance for p in personas
    }

    if not csv_path.exists():
        return stances

    with csv_path.open(encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            try:
                stances[row["agent_a_id"]] = parse_likert(row["agent_a_stance_after_label"])
                stances[row["agent_b_id"]] = parse_likert(row["agent_b_stance_after_label"])
            except (KeyError, Exception):
                # If a row is malformed, skip it; the next rows will overwrite anyway
                continue

    return stances
