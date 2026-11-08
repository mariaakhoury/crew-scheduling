"""Encoding tests (v1.5): every file is read and written as UTF-8, so Windows gives the same result as Mac/Linux.
    pytest -q tests/test_encoding.py
"""
import glob, os, re, subprocess, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_FILES = sorted(glob.glob(os.path.join(ROOT, "crew", "*.py")) + glob.glob(os.path.join(ROOT, "tools", "*.py"))
                  + glob.glob(os.path.join(ROOT, "tests", "*.py")))


def test_every_open_names_utf8():
    # Windows reads files as cp1252 unless told otherwise; "§" then becomes "Â§".
    bad = []
    for f in PY_FILES:
        with open(f, encoding="utf-8") as fh:
            for k, line in enumerate(fh, 1):
                if re.search(r"(?<![\w.])open\(", line) and "encoding" not in line:
                    bad.append(f"{os.path.relpath(f, ROOT)}:{k}: {line.strip()}")
    assert not bad, "open() without encoding='utf-8':\n" + "\n".join(bad)


def test_smoke_notebook_copies_crew_files_exactly():
    nbformat = pytest.importorskip("nbformat")
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "smoke.ipynb")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_notebook_smoke.py"), ROOT, out], check=True)
        nb = nbformat.read(out, as_version=4)
    cells = {c.source.split("\n", 1)[0]: c.source.split("\n", 1)[1] for c in nb.cells
             if c.cell_type == "code" and c.source.startswith("%%writefile")}
    for mod in ["__init__.py", "config.py", "instance.py", "checker.py", "sysinfo.py"]:
        with open(os.path.join(ROOT, "crew", mod), encoding="utf-8") as fh:
            assert cells[f"%%writefile crew/{mod}"] == fh.read(), mod      # no "Â§" or other garbage


def test_smoke_notebook_writes_the_schema_exactly():
    nbformat = pytest.importorskip("nbformat")
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "smoke.ipynb")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_notebook_smoke.py"), ROOT, out], check=True)
        nb = nbformat.read(out, as_version=4)
    cell = next(c.source for c in nb.cells if c.source.startswith("%%writefile instance.schema.json"))
    with open(os.path.join(ROOT, "instance.schema.json"), encoding="utf-8") as fh:
        assert cell.split("\n", 1)[1] == fh.read()
