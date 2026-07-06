"""Empirical competency-question validation over instantiated example KGs.

Runs each SPARQL competency question in sparql_competency_questions/ against
each example knowledge graph in examples/ and records whether the query
returns a bound answer. This yields a *query-based* coverage measure that is
independent of the LLM-estimated coverage scores (Section 6.2 of the paper):
it directly demonstrates that the Annex IV competency questions can be
answered on real instantiations, delivering on the paper's future-work
promise of "actual competency question answering on instantiated KGs".

A CQ counts as "answered" for a KG if the query returns at least one result
row in which at least one variable other than the mandatory ?system anchor
is bound (i.e. the KG actually carries the requested information, not just an
AISystem individual).

Usage:
    python scripts/run_cq_validation.py                 # all examples
    python scripts/run_cq_validation.py encom bank biometrics

Outputs:
    reports/cq_validation_matrix.csv   CQ x KG boolean matrix
    reports/cq_validation_summary.csv  per-KG answered/total
"""

import csv
import glob
import os
import sys

from rdflib import Graph

CQ_DIR = "sparql_competency_questions"
EX_DIR = "examples"


def answered(graph, query_text):
    """True if the query returns a row with a bound non-anchor variable."""
    try:
        res = graph.query(query_text)
    except Exception as e:
        return None  # query error (distinct from "no answer")
    vars_ = [str(v) for v in res.vars] if res.vars else []
    anchor = {"system", "systemLabel"}
    informative = [i for i, v in enumerate(vars_) if v not in anchor]
    for row in res:
        if informative:
            if any(row[i] is not None for i in informative):
                return True
        elif any(v is not None for v in row):
            return True
    return False


def main():
    selected = sys.argv[1:]
    ex_files = sorted(glob.glob(os.path.join(EX_DIR, "*.ttl")))
    if selected:
        ex_files = [f for f in ex_files
                    if os.path.basename(f).replace(".ttl", "") in selected]
    kgs = {}
    for f in ex_files:
        name = os.path.basename(f).replace(".ttl", "")
        g = Graph()
        try:
            g.parse(f, format="turtle")
            kgs[name] = g
        except Exception as e:
            print(f"[skip] {f}: {e}")

    cq_files = sorted(glob.glob(os.path.join(CQ_DIR, "*.sparql")))
    cqs = [(os.path.basename(f).split("-")[0], open(f, encoding="utf-8").read())
           for f in cq_files]

    os.makedirs("reports", exist_ok=True)
    names = list(kgs)
    counts = {n: 0 for n in names}
    errors = {n: 0 for n in names}

    with open("reports/cq_validation_matrix.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cq"] + names)
        for cq_id, text in cqs:
            row = [cq_id]
            for n in names:
                a = answered(kgs[n], text)
                if a is None:
                    errors[n] += 1
                    row.append("err")
                else:
                    counts[n] += int(a)
                    row.append("1" if a else "0")
            w.writerow(row)

    with open("reports/cq_validation_summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kg", "answered", "total_cqs", "share", "query_errors", "triples"])
        for n in names:
            total = len(cqs)
            w.writerow([n, counts[n], total, round(counts[n] / total, 3),
                        errors[n], len(kgs[n])])

    print(f"{'KG':14s} {'answered':>8s} / {len(cqs):<3d} {'share':>7s} {'triples':>8s}")
    for n in names:
        print(f"{n:14s} {counts[n]:>8d} / {len(cqs):<3d} "
              f"{counts[n]/len(cqs):>6.1%} {len(kgs[n]):>8d}")
    print("\n→ reports/cq_validation_matrix.csv, reports/cq_validation_summary.csv")


if __name__ == "__main__":
    main()
