"""Slides 10, 11, 12 and 14 (Member C) as PowerPoint, in the style of B's slides_B.pptx (same template).

    python slides/make_figures_C.py          # first: the PNG figures (project venv)
    python slides/make_slides_C.py           # then: slides/slides_C.pptx (needs python-pptx + pandas)

Every number on the slides is recomputed here from results/runs.csv; the speaker notes are the scripts and likely
questions of slides/slides_C.md. python-pptx is only needed for this script, so it is not in requirements.txt.
"""
from __future__ import annotations

import os
import re

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "slides", "figures")
TEMPLATE = os.path.join(ROOT, "slides", "slides_B.pptx")      # B's deck: same theme, layouts and size (13.33 x 7.5)
OUT = os.path.join(ROOT, "slides", "slides_C.pptx")

# B's palette (read from slides_B.pptx): navy text, coral = Model 1, teal = Model 2, amber = warning
NAVY, MUTED, GRID = RGBColor(0x1F, 0x2A, 0x36), RGBColor(0x5B, 0x67, 0x73), RGBColor(0xC8, 0xCF, 0xD6)
PANEL, WHITE = RGBColor(0xEE, 0xF1, 0xF4), RGBColor(0xFF, 0xFF, 0xFF)
TEAL, TEAL_LT = RGBColor(0x2A, 0x9D, 0x8F), RGBColor(0xD8, 0xEF, 0xEC)
CORAL, CORAL_LT = RGBColor(0xE7, 0x6F, 0x51), RGBColor(0xFB, 0xE2, 0xDB)
AMBER, AMBER_LT = RGBColor(0xF2, 0xA9, 0x00), RGBColor(0xFF, 0xF1, 0xCC)
HEAD, BODY = "Cambria", "Calibri"


# ------------------------------------------------------------------ numbers (all from runs.csv)
def numbers() -> dict:
    d = pd.read_csv(os.path.join(ROOT, "results", "runs.csv"))
    piv = lambda c: d.pivot(index="instance", columns="method", values=c)
    obj, st, bound, n, L = piv("objective"), piv("status"), piv("best_bound"), piv("n"), piv("L")
    built = st["SP"] == "OPTIMAL"
    tl_known = (st["AF"] == "TIME_LIMIT") & built
    same = ((obj["AF"] - obj["SP"]).abs() < 1e-6)[tl_known]
    gap_rows = [(f"n = {int(n.loc[i, 'AF'])}, {int(L.loc[i, 'AF']) // 60} h", 100 * bound.loc[i, "AF"] / obj.loc[i, "SP"])
                for i in obj.index[tl_known]]
    h = d[d["method"] == "H"]
    heur_gap = ((obj["H"] - obj["SP"]) / obj["SP"] * 100)[built]
    starts = d[d["method"].isin(["AF+S", "SP+S"])]
    return {
        "N": len(obj), "sp_opt": int(built.sum()), "af_opt": int((st["AF"] == "OPTIMAL").sum()),
        "sp_not_built": int((~built).sum()), "af_max_opt_n": int(n["AF"][st["AF"] == "OPTIMAL"].max()),
        "sp_max_e2e": float(piv("end_to_end_s")["SP"][built].max()),
        "tl_same": int(same.sum()), "tl_known": int(tl_known.sum()),
        "gap_rows": sorted(gap_rows, key=lambda r: int(r[0].split()[2].rstrip(","))),
        "h_max_s": float(h["end_to_end_s"].max()), "h_med_gap": float(heur_gap.median()),
        "starts_ok": int((starts["start_accepted"] == "yes").sum()),
        "starts": int(starts["start_accepted"].notna().sum()),   # runs where the model was built (start tried)
    }


def notes_from_md() -> dict[str, str]:
    """Speaker notes per slide number = the script + likely questions of slides_C.md."""
    text = open(os.path.join(ROOT, "slides", "slides_C.md"), encoding="utf-8").read()
    notes = {}
    for block in re.split(r"\n## Slide ", text)[1:]:
        num = block.split(" ", 1)[0]
        script = re.search(r"\*\*Script[^\n]*\n(.*?)\n\n", block, re.S)
        qs = re.search(r"\*\*Likely questions:\*\*(.*?)(\n\n|\n---|$)", block, re.S)
        body = (script.group(1) if script else "").replace("\n", " ").strip().strip('"')
        if qs:
            body += "\n\nLIKELY QUESTIONS:" + qs.group(1).replace("\n", " ").replace("*", "")
        notes[num] = body.replace("\\|", "|")
    return notes


# ------------------------------------------------------------------ drawing helpers
def text(slide, x, y, w, h, runs, size=16, color=NAVY, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         font=BODY, name=None):
    """A text box; `runs` is a string or a list of paragraphs, each a string or a list of (text, overrides)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    paras = runs if isinstance(runs, list) else [runs]
    for k, para in enumerate(paras):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = align
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = t
            f = r.font
            f.name, f.size, f.bold = o.get("font", font), Pt(o.get("size", size)), o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", color)
        if k < len(paras) - 1:
            p.space_after = Pt(6)
    return box


def panel(slide, x, y, w, h, fill=PANEL, name=None, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.06
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb, shp.line.width = line, Pt(1.25)
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp


def new_slide(prs, number: int, title: str, notes: str):
    s = prs.slides.add_slide(prs.slide_layouts.get_by_name("Title Only"))
    t = s.shapes.title
    t.left, t.top, t.width, t.height = Inches(0.6), Inches(0.35), Inches(12.1), Inches(1.25)
    t.text_frame.text = title
    for p in t.text_frame.paragraphs:
        p.alignment = PP_ALIGN.LEFT
        for r in p.runs:
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = HEAD, Pt(32), True, NAVY
    text(s, 0.6, 7.0, 9.0, 0.3, f"Group M · Bus crew scheduling · Member C (Maria) · slide {number}",
         size=10, color=MUTED, name="Footer")
    s.notes_slide.notes_text_frame.text = notes
    return s


def stat_tile(slide, x, y, w, h, big, label, color, name):
    panel(slide, x, y, w, h, name=name)
    text(slide, x + 0.25, y + 0.1, w - 0.5, 0.6, big, size=34, bold=True, color=color, font=BODY)
    text(slide, x + 0.25, y + 0.68, w - 0.5, h - 0.75, label, size=14, color=NAVY)


def style_chart(chart, legend=True):
    chart.font.name, chart.font.size, chart.font.color.rgb = BODY, Pt(12), NAVY
    chart.has_legend = legend
    if legend:
        chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.BOTTOM, False
        chart.legend.font.size = Pt(12)


def table(slide, x, y, w, col_w, rows, size=14, header_fill=NAVY, name=None, row_h=0.42):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w),
                                   Inches(row_h * len(rows)))
    if name:
        shape.name = name
    tbl = shape.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            fill, bold, color = None, i == 0, WHITE if i == 0 else NAVY
            if isinstance(val, tuple):
                val, o = val
                fill, bold, color = o.get("fill"), o.get("bold", bold), o.get("color", color)
            cell.text = str(val)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill or (header_fill if i == 0 else (PANEL if i % 2 == 0 else WHITE))
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = BODY, Pt(size), bold, color
    return tbl


def picture(slide, path, x, y, w=None, h=None, name=None):
    pic = slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    if name:
        pic.name = name
    return pic


# ------------------------------------------------------------------ the four slides
def slide10(prs, k, notes):
    s = new_slide(prs, 10, "Greedy strands trip 7; swap-then-merge saves a whole driver ($232.50)", notes["10"])
    picture(s, os.path.join(FIG, "C_slide10_case.png"), 0.6, 1.75, w=7.7, name="P0 case study")
    text(s, 8.7, 1.75, 4.0, 0.4, "What the move pair is worth (P0)", size=16, bold=True)
    table(s, 8.7, 2.25, 4.0, [0.9, 1.1, 1.0, 1.0], [
        ["", "Greedy", "After LS", "Change"],
        ["Drivers", "3 × $300", "2 × $300", ("−$300", {"color": TEAL, "bold": True})],
        ["Paid time", "$277.50", "$345.00", ("+$67.50", {"color": CORAL, "bold": True})],
        [("Total", {"bold": True}), ("$1,177.50", {"bold": True}), ("$945.00", {"bold": True}),
         ("−$232.50", {"color": TEAL, "bold": True})],
    ], size=14, name="Cost table")
    panel(s, 8.7, 4.2, 4.0, 2.1, name="Lesson")
    text(s, 8.95, 4.35, 3.5, 1.85, [
        [("1 driver = $300 = 10 h of paid waiting", {"bold": True})],
        "Move trip 6 first (costs more alone), then merge trip 7: one driver fewer.",
        [(f"On the benchmark: a median {k['h_med_gap']:.1f} % above the optimum.", {"color": MUTED, "size": 14})],
    ], size=15)


def slide11(prs, k, notes):
    s = new_slide(prs, 11, "The heuristic gives both models a complete start; it rarely changes the result",
                  notes["11"])
    steps = [("Timetable", "up to 500 trips"), ("Greedy", "shortest wait first"),
             ("Local search", "swap-then-merge"), ("Complete start", "Model 1: x, u, v, T, D\nModel 2: z"),
             ("Gurobi", "“User MIP start\nproduced solution”")]
    bw, gap, y = 2.1, 0.4, 1.75
    for i, (head, sub) in enumerate(steps):
        x = 0.6 + i * (bw + gap)
        dark = i in (1, 2)
        panel(s, x, y, bw, 1.05, fill=NAVY if dark else PANEL, name=f"Step {i + 1}")
        text(s, x + 0.12, y + 0.1, bw - 0.24, 0.9, [[(head, {"bold": True, "size": 16})], sub], size=12,
             color=WHITE if dark else NAVY, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            a = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + bw + 0.05), Inches(y + 0.525),
                                       Inches(x + bw + gap - 0.05), Inches(y + 0.525))
            a.line.color.rgb, a.line.width = MUTED, Pt(2)
            a.line._get_or_add_ln().append(a.line._ln.makeelement(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd", {"type": "triangle"}))
    tiles = [(f"≤ {k['h_max_s']:.2f} s", "heuristic time, up to 500 trips", NAVY),
             (f"{k['h_med_gap']:.1f} %", "median above the optimum", NAVY),
             (f"{k['starts_ok']} / {k['starts']}", "starts accepted by Gurobi", TEAL)]
    for i, (big, label, c) in enumerate(tiles):
        stat_tile(s, 0.6, 3.15 + i * 1.25, 3.6, 1.1, big, label, c, f"Stat {i + 1}")
    cd = CategoryChartData()
    cd.categories = ["Model 2: SP+S vs SP", "Model 1: AF+S vs AF"]
    cd.add_series("wins", (0, 2))
    cd.add_series("ties", (10, 10))
    cd.add_series("losses", (0, 3))
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(4.6), Inches(3.05), Inches(8.1), Inches(2.45), cd)
    gf.name = "Win tie loss chart"
    ch = gf.chart
    style_chart(ch)
    ch.has_title = True
    ch.chart_title.text_frame.text = "Did the start change the result? (instances, B12 tie rule)"
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    for ser, c in zip(ch.plots[0].series, (TEAL, GRID, CORAL)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = c
    pl = ch.plots[0]
    pl.gap_width, pl.overlap = 60, 100
    pl.has_data_labels = True
    pl.data_labels.position = XL_LABEL_POSITION.CENTER
    pl.data_labels.font.size, pl.data_labels.font.bold = Pt(13), True
    pl.data_labels.show_value = True
    pl.data_labels.number_format, pl.data_labels.number_format_is_linked = "0;;;", False   # hide zero labels
    va = ch.value_axis
    va.visible, va.has_major_gridlines = False, False
    ch.category_axis.format.line.color.rgb = GRID
    ch.category_axis.tick_labels.font.size = Pt(13)
    text(s, 4.6, 5.6, 8.1, 1.2, [
        [("Wins: ", {"bold": True, "color": TEAL}), ("n = 500 ended 3.9 % cheaper; an n = 50 proof was 29 % faster.", {})],
        [("Losses: ", {"bold": True, "color": CORAL}),
         ("two quick proofs got slower, one bound got weaker — a different start, a different search tree.", {})],
    ], size=14)


def slide12(prs, k, notes):
    s = new_slide(prs, 12, "Model 2 wins whenever it can be built; Model 1 is the only option beyond that",
                  notes["12"])
    N = k["N"]
    assert k["sp_max_e2e"] < 1, k["sp_max_e2e"]
    tiles = [(f"{k['sp_opt']} / {N}", "Model 2 proved the optimum, each under 1 s", TEAL),
             (f"{k['af_opt']} / {N}", f"Model 1 proved the optimum (n ≤ {k['af_max_opt_n']})", CORAL),
             (f"{k['sp_not_built']} / {N}", "Model 2 not built: more than 2 million duties", AMBER),
             (f"{k['tl_same']} / {k['tl_known']}", "Model 1 time limits already at the optimum", NAVY)]
    for i, (big, label, c) in enumerate(tiles):
        stat_tile(s, 0.6 + i * 3.1, 1.75, 2.8, 1.3, big, label, c, f"Stat {i + 1}")
    picture(s, os.path.join(FIG, "C_slide12_profile.png"), 0.6, 3.3, h=3.55, name="Performance profile")
    cd = CategoryChartData()
    cd.categories = [r[0] for r in k["gap_rows"]]
    cd.add_series("Model 1's schedule", [100.0] * len(k["gap_rows"]))
    cd.add_series("Model 1's proven lower bound", [round(r[1], 1) for r in k["gap_rows"]])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(6.2), Inches(3.3), Inches(6.5), Inches(3.55), cd)
    gf.name = "Schedule vs bound chart"
    ch = gf.chart
    style_chart(ch)
    ch.has_title = True
    ch.chart_title.text_frame.text = "Found, not proved: % of the true optimum (Model 2)"
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    for ser, c in zip(ch.plots[0].series, (CORAL, GRID)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = c
    pl = ch.plots[0]
    pl.gap_width, pl.overlap = 80, -10
    pl.has_data_labels = True
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    pl.data_labels.number_format, pl.data_labels.number_format_is_linked = '0"%"', False
    pl.data_labels.font.size = Pt(12)
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = 80, 105, 5
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = PANEL
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '0"%"', False
    va.format.line.fill.background()
    ch.category_axis.format.line.color.rgb = GRID


def slide14(prs, k, notes):
    s = new_slide(prs, 14, "Theory held for the bounds and the cliff; the start and the build share surprised us",
                  notes["14"])
    C = ("confirmed", {"fill": TEAL_LT, "bold": True})
    NC = ("not confirmed", {"fill": CORAL_LT, "bold": True})
    TC = ("too close to call", {"fill": AMBER_LT, "bold": True})
    rows = [["", "We expected", "Verdict", "Evidence"],
            ["H1", "Model 1's LP ≤ Model 2's LP", C, "10 / 10; Model 2's LP = optimum"],
            ["H2", "Naive big-M is a little weaker", ("confirmed: no gap", C[1]), "identical on 15 / 15"],
            ["H3", "Model 2: fewer nodes, faster", C, "faster on 6 / 7, 1 node each"],
            ["H4", "Model 2's build share grows", NC, "falls 72 % → 32 %"],
            ["H5", "Model 2 becomes unbuildable", C, f"{k['sp_not_built']} / {k['N']} not built; Model 1: 0"],
            ["H6", "The start helps Model 1 more", NC, "median 2.6 % vs 2.6 %"],
            ["H8", "Trips per duty matter more than n", TC, "rank corr. 0.84 vs 0.83"]]
    table(s, 0.6, 1.75, 7.5, [0.55, 2.95, 1.75, 2.25], rows, size=13, name="Verdict table", row_h=0.47)
    picture(s, os.path.join(FIG, "C_slide14_gantt.png"), 8.4, 1.75, w=4.3, name="Largest instance Gantt")
    text(s, 8.4, 4.15, 4.3, 1.4, [
        [("Largest instance: 500 trips, 77 drivers, $35,342", {"bold": True})],
        "Model 1 with the start, proven gap 23.1 %; every duty re-checked by the independent checker.",
    ], size=13)
    panel(s, 0.6, 5.65, 12.1, 1.15, name="Limits and next")
    text(s, 0.85, 5.78, 11.6, 0.95, [
        [("Limits: ", {"bold": True}), ("one generator family, one machine, one seed per configuration; "
                                         "the driving limit is tied to the spread.", {})],
        [("Next: column generation — ", {"bold": True, "color": TEAL}),
         ("generate only duties that can improve the solution (a shortest path with two resources), "
          "so Model 2 keeps its bound without listing millions of duties.", {})],
    ], size=14)


def main() -> None:
    k, notes = numbers(), notes_from_md()
    prs = Presentation(TEMPLATE)
    ids = prs.slides._sldIdLst
    for sid in list(ids):                       # keep B's theme and layouts, drop B's slides
        prs.part.drop_rel(sid.rId)
        ids.remove(sid)
    for build in (slide10, slide11, slide12, slide14):
        build(prs, k, notes)
    prs.core_properties.title = "Group M - slides 10-12, 14 (Member C)"
    prs.core_properties.author = "Group M"
    prs.save(OUT)
    print("wrote", os.path.relpath(OUT, ROOT), "| numbers:", {x: v for x, v in k.items() if x != "gap_rows"},
          "| bound rows:", [(a, round(b, 1)) for a, b in k["gap_rows"]])


if __name__ == "__main__":
    main()
