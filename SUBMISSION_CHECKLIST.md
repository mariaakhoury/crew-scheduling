# Submission checklist (owner B; Master Plan §14.5 + the professor's checklist, section 7)

**Deadline:** Tue 17 Nov, 11:59 PM (verify on the course page) - **we submit by 6 PM.**
**Submit only:** the notebook (.ipynb), the slides (PDF or PPTX), and optionally a zip with the instance data.

## 1. Automatic checks (run on Mon 16 and again before submitting)
```
python -m qa.check_submission --notebook dist/crew_scheduling_groupM.ipynb --slides slides/slides_groupM.pdf --zip dist/groupM_data.zip
```
Every line must say PASS. It checks: notebook executed with no error cells and no personal paths; the required
content keywords; >= 15 instances matching MANIFEST; every method on every instance with one configuration; >= 3
time-limit instances and instances every model solves; verify_results PASS; slides file; zip contents, no licence.

## 2. Professor's checklist (section 7) - tick with WHERE it is
| Item | Where (notebook section / slide) | Done |
|---|---|---|
| Problem description, and a visualization of a small example and its solution | nb 1, 13 / slides 1-3 | [ ] |
| At least two MILP models with written formulations | nb 6, 7 / slides 4-7 | [ ] |
| Theoretical argument for each model, compared with the experimental results | nb 8, 20 / slides 5, 7, 8, 14 | [ ] |
| Heuristic implemented and tested as warm start (complete MIP start, both models) | nb 9, 10 / slides 10-11 | [ ] |
| At least 15 instances, easy to very hard, with documentation | nb 15, `instances/final/README.md` / slide 9 | [ ] |
| Same time limit and thread count for all methods (and hardware reported) | nb 0, 16 | [ ] |
| Independent solution checker used | nb 5, 16 (verify_results) | [ ] |
| Visualization of at least one larger instance and its solution | nb 19 / slide 14 | [ ] |
| Summary and comparison tables and charts | nb 17, 18 / slide 12 | [ ] |
| Notebook runs top to bottom (instance data files attached) | Q18 clean-environment test (B11) | [ ] |
| Slides for the class presentation | `slides_groupM.pdf` | [ ] |

## 3. Honest reporting (Master Plan §14.5)
- [ ] Only checked OPTIMAL full-model runs are called optimal; time-limit runs are "feasible, not proven"
- [ ] TIME_LIMIT and not-built cases counted separately everywhere; averages over time-limit runs marked ">="
- [ ] Solver time and end-to-end time shown separately
- [ ] Negative and surprising results have their own table with explanations; no run deleted
- [ ] Every number on the slides matches results/runs.csv (tag v1.0-final-run)
- [ ] Hypotheses H1-H6 and H8 each have a verdict and evidence (notebook + slide 14)
- [ ] Constraint numbers (1)-(8) identical in formulation, code, notebook and slides
- [ ] No HiGHS numbers anywhere in tables or slides (HiGHS is a development fallback only)

## 4. Presentation (15 min + 5 min questions)
- [ ] Two timed rehearsals at 15:00 or less (Mon 16)
- [ ] Every member presents (A slides 1-5, B slides 6-9 and 13, C slides 10-12 and 14)
- [ ] Every member can answer the Q&A list of Master Plan §12 (3 random questions each in rehearsal)

## 5. Upload (Tue 17, by 6 PM)
- [ ] `crew_scheduling_groupM.ipynb` (executed, outputs saved)
- [ ] `slides_groupM.pdf`
- [ ] `groupM_data.zip` (optional: instances + results the notebook reads)
- [ ] Confirm the upload went through (download it back and open it)
