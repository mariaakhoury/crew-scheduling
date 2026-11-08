"""Instance data contract (schema 1.0). Owner: Member A.

Loads, validates (rules V1-V10 of data_dictionary.md) and saves timetable files.
Times are integer minutes; money is dollars; trip ids are 0..n-1 and equal the list position.
make_instance (the rotation generator, task A4) is still to be written.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import NamedTuple, Optional

import jsonschema

from crew import config

Schedule = list[list[int]]          # each duty = trip ids in increasing start time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "instance.schema.json")
FIELD_ORDER = ["schema_version", "name", "generator", "seed", "params", "units",
               "L", "W", "tau", "F", "c_per_min", "terminals", "trips", "reference"]


class Trip(NamedTuple):
    id: int          # 0..n-1, equals position in Instance.trips
    start: int       # minutes after 00:00 of the service day (may exceed 1440)
    end: int         # minutes, end > start
    origin: int      # index into Instance.terminals
    dest: int        # index into Instance.terminals, dest != origin
    label: str = ""  # display name only (e.g. "T1"); never used in logic


@dataclass
class Instance:
    name: str
    generator: str                  # "hand" | "timetable" | "planted" | "routes"
    seed: Optional[int]
    params: dict
    L: int                          # max spread, minutes
    W: int                          # max driving, minutes
    tau: int                        # turnaround, minutes (must equal config.TAU)
    F: float                        # $ per duty (must equal config.F)
    c_per_min: float                # $ per minute (must equal config.C_PER_MIN)
    terminals: list[str]
    trips: list[Trip]
    reference: Optional[dict] = None   # {"schedule": Schedule, "cost": float, "kind": str, "verified_by": str}
    schema_version: str = "1.0"
    units: dict = field(default_factory=lambda: {"time": "minutes", "money": "USD"})


# ---------------------------------------------------------------- conversions

def _from_dict(raw: dict) -> Instance:
    """Build an Instance from a raw JSON dict (no validation)."""
    trips = [Trip(t["id"], t["start"], t["end"], t["origin"], t["dest"], t.get("label", ""))
             for t in raw["trips"]]
    return Instance(name=raw["name"], generator=raw["generator"], seed=raw["seed"], params=raw["params"],
                    L=raw["L"], W=raw["W"], tau=raw["tau"], F=raw["F"], c_per_min=raw["c_per_min"],
                    terminals=list(raw["terminals"]), trips=trips, reference=raw.get("reference"),
                    schema_version=raw["schema_version"], units=raw["units"])


def _to_dict(inst: Instance) -> dict:
    """Instance -> JSON dict in the documented field order."""
    trips = []
    for t in inst.trips:
        d = {"id": t.id}
        if t.label:
            d["label"] = t.label
        d.update(start=t.start, end=t.end, origin=t.origin, dest=t.dest)
        trips.append(d)
    raw = {"schema_version": inst.schema_version, "name": inst.name, "generator": inst.generator,
           "seed": inst.seed, "params": inst.params, "units": inst.units, "L": inst.L, "W": inst.W,
           "tau": inst.tau, "F": inst.F, "c_per_min": inst.c_per_min, "terminals": inst.terminals,
           "trips": trips}
    if inst.reference is not None:
        raw["reference"] = inst.reference
    return {k: raw[k] for k in FIELD_ORDER if k in raw}


# ---------------------------------------------------------------- validation rules

def _rule_errors(raw: dict, file_stem: Optional[str]) -> list[str]:
    """Rules V2-V10 on a raw dict. V7 is checked only when the file name is known."""
    errors: list[str] = []
    trips = raw.get("trips")
    if not isinstance(trips, list) or not all(isinstance(t, dict) for t in trips):
        return ["V2: trips is missing or not a list of objects"]
    n = len(trips)

    # V2: ids are exactly 0..n-1 in list order
    ids = [t.get("id") for t in trips]
    if ids != list(range(n)):
        errors.append(f"V2: trip ids are not 0..{n - 1} in list order")

    # V3: integer times (a float such as 360.0 is invalid) and 0 <= start < end
    for pos, t in enumerate(trips):
        s, e = t.get("start"), t.get("end")
        if type(s) is not int or type(e) is not int:
            errors.append(f"V3: trip at position {pos} has non-integer times ({s!r}, {e!r})")
        elif not 0 <= s < e:
            errors.append(f"V3: trip at position {pos} has start {s} not before end {e}")

    # V4: valid terminal indices and origin != dest
    m = len(raw.get("terminals") or [])
    for pos, t in enumerate(trips):
        o, d = t.get("origin"), t.get("dest")
        if not (isinstance(o, int) and isinstance(d, int) and 0 <= o < m and 0 <= d < m):
            errors.append(f"V4: trip at position {pos} uses a terminal index outside 0..{m - 1}")
        elif o == d:
            errors.append(f"V4: trip at position {pos} has origin == dest ({o})")

    # V5: W <= L and every trip lasts at most W (so one driver per trip is always legal)
    L, W = raw.get("L"), raw.get("W")
    if isinstance(L, int) and isinstance(W, int):
        if W > L:
            errors.append(f"V5: W = {W} > L = {L}")
        for pos, t in enumerate(trips):
            s, e = t.get("start"), t.get("end")
            if type(s) is int and type(e) is int and e - s > W:
                errors.append(f"V5: trip at position {pos} lasts {e - s} min > W = {W}")

    # V6: cost constants and turnaround equal config.py
    if raw.get("tau") != config.TAU:
        errors.append(f"V6: tau = {raw.get('tau')} but config.TAU = {config.TAU}")
    if raw.get("F") != config.F:
        errors.append(f"V6: F = {raw.get('F')} but config.F = {config.F}")
    if raw.get("c_per_min") != config.C_PER_MIN:
        errors.append(f"V6: c_per_min = {raw.get('c_per_min')} but config.C_PER_MIN = {config.C_PER_MIN}")

    # V7: name equals the file name
    if file_stem is not None and raw.get("name") != file_stem:
        errors.append(f"V7: name {raw.get('name')!r} differs from file name {file_stem!r}")

    # V8: labels, if present, are unique
    labels = [t["label"] for t in trips if t.get("label")]
    if len(labels) != len(set(labels)):
        errors.append("V8: trip labels are not unique")

    # V9: the reference schedule passes the checker and its cost matches.
    # Checked only when the trips themselves are valid (V2-V6), because the checker reads them.
    # A wrong file name (V7) or duplicate labels (V8) do not stop it, so a second problem is still reported.
    ref = raw.get("reference")
    trips_broken = any(e.startswith(("V2:", "V3:", "V4:", "V5:", "V6:")) for e in errors)
    if ref and not trips_broken:
        from crew.checker import check_schedule   # imported here to avoid a circular import
        try:
            result = check_schedule(_from_dict(raw), ref.get("schedule", []), ref.get("cost"))
            if not result.ok:
                errors.extend(f"V9: reference schedule rejected - {msg}" for msg in result.errors)
        except (KeyError, TypeError, IndexError) as exc:
            errors.append(f"V9: reference could not be checked ({exc!r})")

    # V10: generated files record n equal to the number of trips
    if raw.get("generator") != "hand":
        params = raw.get("params") or {}
        if params.get("n") != n:
            errors.append(f"V10: params.n = {params.get('n')} but the file has {n} trips")
    return errors


def validate_instance(inst: Instance) -> list[str]:
    """Rules V1-V10 for an Instance object (V7 needs a file name, so it is checked only on load).
    Every message starts with its rule code and a colon, e.g. "V5: W = 500 > L = 420"."""
    raw = _to_dict(inst)
    errors = [f"V1: {e.message}" for e in jsonschema.Draft202012Validator(_schema()).iter_errors(raw)]
    return errors + _rule_errors(raw, file_stem=None)


def load_instance_raw_errors(path: str) -> list[str]:
    """Validate a JSON file WITHOUT building an Instance first, so broken files can be tested.
    Runs JSON Schema (V1), then V2-V10 on the raw dict. Returns [] if the file is valid."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        return ["V1: the file does not contain a JSON object"]
    errors = [f"V1: {e.message}" for e in jsonschema.Draft202012Validator(_schema()).iter_errors(raw)]
    stem = os.path.splitext(os.path.basename(path))[0]
    return errors + _rule_errors(raw, file_stem=stem)


def _schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- load / save

def load_instance(path: str) -> Instance:
    """Read a JSON file, validate it (V1-V10) and return an Instance. Raises ValueError listing every problem."""
    errors = load_instance_raw_errors(path)
    if errors:
        raise ValueError(f"{path} is not a valid instance:\n  " + "\n  ".join(errors))
    with open(path, encoding="utf-8") as fh:
        return _from_dict(json.load(fh))


def save_instance(inst: Instance, path: str) -> None:
    """Write JSON in schema 1.0 (indent=1, documented field order). Round-trips with load_instance."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_to_dict(inst), fh, indent=1)
        fh.write("\n")


# ---------------------------------------------------------------- generator and features

def make_instance(name: str, n: int, m: int, L: int, W: int, seed: int, **gen_params) -> Instance:
    """Rotation generator (task A4, still to be written). Must guarantee d_i <= W <= L for every trip
    and reach a median of at least 3 trips per duty; stores a checked reference schedule."""
    raise NotImplementedError("A4: rotation generator not written yet")


def instance_features(inst: Instance) -> dict:
    """Simple size and density features used to explain difficulty (H8)."""
    trips = inst.trips
    n = len(trips)
    arcs = sum(1 for a in trips for b in trips
               if a.dest == b.origin and a.end + inst.tau <= b.start)
    first, last = min(t.start for t in trips), max(t.end for t in trips)
    hours = max((last - first) / 60, 1e-9)
    return {"n": n, "m": len(inst.terminals), "L": inst.L, "W": inst.W, "arcs": arcs,
            "arcs_per_trip": arcs / n, "mean_duration": sum(t.end - t.start for t in trips) / n,
            "trips_per_hour": n / hours}
