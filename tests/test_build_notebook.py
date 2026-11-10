"""Tests for the notebook builder (task A10). Executing the notebook is the clean-computer test (B11, Q18)."""
import glob
import importlib.util
import os
import sys

import nbformat
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_notebook", os.path.join(ROOT, "tools", "build_notebook.py"))
bn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bn)


def test_every_crew_module_is_written_in_full():
    nb = bn.build_notebook()
    written = {c.source.splitlines()[0].split("crew/")[1]: c.source.split("\n", 1)[1]
               for c in nb.cells if c.cell_type == "code" and c.source.startswith("%%writefile crew/")}
    for path in glob.glob(os.path.join(ROOT, "crew", "*.py")):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            assert written.get(name) == fh.read(), f"{name} missing or changed in the notebook"


def test_no_personal_paths_and_valid_notebook():
    nb = bn.build_notebook()
    bn.check_no_personal_paths(nb)
    nbformat.validate(nb)


def test_personal_path_is_caught():
    nb = bn.build_notebook()
    nb.cells.append(nbformat.v4.new_code_cell('load(r"C:\\\\Users\\\\me\\\\file.json")'))
    with pytest.raises(SystemExit):
        bn.check_no_personal_paths(nb)


def test_build_writes_notebook_and_data(tmp_path):
    bn.main(["--out", str(tmp_path)])
    assert (tmp_path / bn.NB_NAME).exists()
    assert (tmp_path / "instances" / "proto" / "P0_example8.json").exists()
    assert (tmp_path / "instance.schema.json").exists() and (tmp_path / "README.txt").exists()
