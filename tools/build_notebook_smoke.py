# ARCHITECTURE SMOKE TEST ONLY (not the project notebook builder). Usage: python tools/build_notebook_smoke.py . smoke.ipynb
# Writes a notebook whose cells %%writefile the crew modules, then imports them from the notebook folder.
import nbformat as nbf, sys, os
kit, out = sys.argv[1], sys.argv[2]
nb = nbf.v4.new_notebook(); C = []
C.append(nbf.v4.new_markdown_cell("# Smoke test of the notebook architecture (not the project notebook)"))
C.append(nbf.v4.new_code_cell(
"import os, sys, importlib\n"
"HERE = os.path.abspath(os.getcwd())\n"
"os.makedirs('crew', exist_ok=True)\n"
"if HERE not in sys.path: sys.path.insert(0, HERE)\n"
"for f in ['instances/proto/P0_example8.json']:\n"
"    assert os.path.exists(f), f'missing data file: {f} (unzip the submission next to the notebook)'"))
for mod in ['__init__.py','config.py','instance.py','checker.py','sysinfo.py']:
    # encoding="utf-8": the crew files contain non-English characters (e.g. the section sign in config.py).
    # Without it, Windows reads them as cp1252 and the notebook shows garbage such as "Â§".
    with open(os.path.join(kit, 'crew', mod), encoding='utf-8') as fh:
        src = fh.read()
    C.append(nbf.v4.new_code_cell(f"%%writefile crew/{mod}\n"+src))
# crew/instance.py validates every file against instance.schema.json (rule V1), which it looks for one folder
# above crew/. The notebook writes it too, so the loader works next to the notebook without extra files.
with open(os.path.join(kit, 'instance.schema.json'), encoding='utf-8') as fh:
    C.append(nbf.v4.new_code_cell("%%writefile instance.schema.json\n" + fh.read()))
C.append(nbf.v4.new_code_cell(
"importlib.invalidate_caches()\n"
"import crew, crew.config as config, crew.instance, crew.checker\n"
"for m in (crew, config, crew.instance, crew.checker): importlib.reload(m)\n"
"assert os.path.dirname(os.path.abspath(crew.__file__)) == os.path.join(HERE, 'crew'), crew.__file__\n"
"from crew.instance import load_instance\n"
"from crew.checker import check_schedule\n"
"inst = load_instance('instances/proto/P0_example8.json')   # validates V1-V10, opens the file as UTF-8\n"
"res = check_schedule(inst, inst.reference['schedule'], inst.reference['cost'])\n"
"assert res.ok and res.cost == 945.0, res\n"
"print('crew loaded from', crew.__file__); print(inst.name, len(inst.trips), 'trips, reference cost recomputed by the checker:', res.cost)"))
nb['cells'] = C
nbf.write(nb, out)   # nbformat always writes UTF-8
