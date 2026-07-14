"""Merge per-curator exports from the curation UI (docs/curation.html).

Takes two or more curation_<name>_<batch>.json files and reconciles them into
per-pair consensus decisions. The unit of consensus is the *canonical pair*
(aidoc IRI, reference IRI): the same pair can appear under several reference-
ontology buckets because reference TTLs redeclare shared terms (e.g.
mls:Dataset appears in ml-onto, mlschema and rains). Every curator judgment is
converted into a *relation vote*:

    accept  -> the LLM-suggested relation of the judged bucket row
    modify  -> the curator's intended relation
    reject  -> REJECT

and the consensus is the vote supported by a majority of curators (>= 2).
Pairs without a majority are CONFLICTs for the team discussion.

Curator-specific handling (documented in publication/curation_protocol.md):
  * SN and TD curated while a UI bug auto-filled the modify relation with
    skos:exactMatch -- their `relation` field is meaningless; the intended
    relation is parsed from the note. FK curated with the fixed UI, so his
    `relation` field is authoritative.
  * SN's broadMatch/narrowMatch directions are inverted with respect to the
    SKOS definition (`<A> skos:broadMatch <B>` = B is broader than A) and are
    swapped, except where his direction already coincides with TD's.

Outputs:
  reports/curation_merged.csv     one row per canonical pair x curator
  reports/curation_consensus.csv  one row per canonical pair with consensus
  write-back of consensus into reports/alignment_semantic/*-curation.csv and
  reports/alignment_fn_band/*-curation.csv (all bucket rows of a pair)

Usage:
    python scripts/merge_curation.py experiments/alignment_curation/curation_*.json
"""

import glob
import itertools
import json
import os
import re
import sys
from collections import Counter, defaultdict

import pandas as pd

CURATION_DIRS = [
    ("reports/alignment_semantic", ""),        # main candidate set
    ("reports/alignment_fn_band", "fn-band/"), # below-threshold FN sample
]

# curators whose modify relation must be read from the note (UI bug era)
NOTE_AUTHORITATIVE = {"SN", "TD"}
# curators whose broad/narrow directions are swapped (see module docstring)
SWAP_DIRECTIONS = {"SN"}
SWAP_REFERENCE = "TD"  # no swap where the direction already matches this curator

REJECT = "REJECT"
# Team adjudication of pairs without a curator majority: one row per pair with
# the agreed relation (or REJECT), applied on top of the majority consensus.
ADJUDICATION_FILE = "experiments/alignment_curation/adjudicated.csv"
REL_IN_NOTE = re.compile(r"\b(?:skos:)?(exact|close|broad|narrow|related)\s*[- ]?match\b", re.I)
DIRECTION_SWAP = {"skos:broadMatch": "skos:narrowMatch",
                  "skos:narrowMatch": "skos:broadMatch"}


def parse_note_relation(note):
    m = REL_IN_NOTE.search(note or "")
    return f"skos:{m.group(1).lower()}Match" if m else None


def kappa(pairs):
    """Cohen's kappa for two label sequences given as list of (a, b)."""
    if not pairs:
        return float("nan")
    labels = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum(
        (sum(1 for a, _ in pairs if a == l) / n) *
        (sum(1 for _, b in pairs if b == l) / n)
        for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def load_batch():
    """Canonical pair -> list of bucket rows; and the set of valid bucket pids."""
    pairs = defaultdict(list)
    for d, prefix in CURATION_DIRS:
        for f in sorted(glob.glob(os.path.join(d, "*-curation.csv"))):
            bucket = prefix + os.path.basename(f).replace("-curation.csv", "")
            try:
                df = pd.read_csv(f)
            except pd.errors.EmptyDataError:
                continue
            for _, r in df.iterrows():
                pairs[(r["aidoc_iri"], r["ref_iri"])].append({
                    "bucket": bucket, "file": f,
                    "aidoc_label": r["aidoc_label"], "ref_label": r["ref_label"],
                    "llm_relation": str(r["llm_relation"]),
                    "llm_confidence": r["llm_confidence"],
                    "lexical_similarity": r["lexical_similarity"],
                })
    return pairs


def decision_to_vote(curator, pid, d, bucket_rows):
    """One UI decision -> (vote, note). vote is a skos relation, REJECT, or
    None when a modify relation cannot be determined."""
    dec = d["decision"]
    if dec == "reject":
        return REJECT, d.get("note")
    if dec == "accept":
        return bucket_rows[0]["llm_relation"], d.get("note")
    # modify
    if curator in NOTE_AUTHORITATIVE:
        rel = parse_note_relation(d.get("note"))
        if rel is None:
            print(f"  [warn] {curator} on {pid}: modify without a parseable "
                  f"relation in the note (note: {d.get('note')!r}) -> undetermined")
        return rel, d.get("note")
    rel = d.get("relation")
    noted = parse_note_relation(d.get("note"))
    if noted and noted != rel:
        print(f"  [warn] {curator} on {pid}: relation field {rel} but note says "
              f"{noted} -- keeping the field (note: {d.get('note')!r})")
    return rel, d.get("note")


def main():
    files = sys.argv[1:]
    if len(files) < 2:
        sys.exit("Usage: merge_curation.py <export1.json> <export2.json> [...]")

    batch = load_batch()
    bucket_index = {}  # (bucket, aidoc, ref) -> canonical key
    for key, rows in batch.items():
        for r in rows:
            bucket_index[(r["bucket"], key[0], key[1])] = key

    # ---- load exports into raw votes per canonical pair ----
    raw = defaultdict(lambda: defaultdict(list))  # key -> curator -> [(vote, note, ts, bucket)]
    batches = set()
    for f in files:
        with open(f, encoding="utf-8") as fh:
            p = json.load(fh)
        batches.add(p.get("batch_id"))
        curator = p["curator"]
        stale = 0
        for pid, d in p["decisions"].items():
            bucket, aidoc_iri, ref_iri = pid.split("|", 2)
            key = bucket_index.get((bucket, aidoc_iri, ref_iri))
            if key is None:
                stale += 1
                print(f"  [stale] {curator}: {pid} not in the current batch -- dropped")
                continue
            vote, note = decision_to_vote(curator, pid, d, batch[key])
            raw[key][curator].append((vote, note, d.get("ts", ""), bucket, d["decision"]))
        print(f"loaded {p['curator']}: {len(p['decisions'])} decisions"
              + (f" ({stale} stale dropped)" if stale else ""))
    if len(batches) > 1:
        print(f"⚠️  exports come from different batches: {batches}")

    # ---- one vote per curator per canonical pair ----
    votes = defaultdict(dict)   # key -> curator -> vote
    notes = defaultdict(dict)   # key -> curator -> joined notes
    for key, by_cur in raw.items():
        for cur, entries in by_cur.items():
            distinct = {v for v, _, _, _, _ in entries if v is not None}
            if len(distinct) > 1:
                cnt = Counter(v for v, _, _, _, _ in entries if v is not None)
                top, top_n = cnt.most_common(1)[0]
                if list(cnt.values()).count(top_n) > 1:  # tie -> latest ts
                    top = max((e for e in entries if e[0] is not None),
                              key=lambda e: e[2])[0]
                print(f"  [intra-curator] {cur} voted differently on duplicate "
                      f"buckets of {key[0].split('#')[-1]} -> "
                      f"{key[1].split('#')[-1].split('/')[-1]}: "
                      f"{dict(cnt)} -> using {top}")
                votes[key][cur] = top
            else:
                votes[key][cur] = distinct.pop() if distinct else None
            ns = "; ".join(sorted({n for _, n, _, _, _ in entries if n}))
            if ns:
                notes[key][cur] = ns

    # ---- direction swap (after intra-curator resolution) ----
    for key in votes:
        for cur in SWAP_DIRECTIONS:
            v = votes[key].get(cur)
            if v in DIRECTION_SWAP:
                # only swap curator-chosen relations (modify); votes inherited
                # from accepting the LLM suggestion keep their direction
                if any(e[0] == v and e[4] == "accept" for e in raw[key][cur]):
                    continue
                if votes[key].get(SWAP_REFERENCE) == v:
                    print(f"  [direction] {cur} on {key[0].split('#')[-1]} -> "
                          f"{key[1].split('#')[-1].split('/')[-1]}: {v} kept "
                          f"(coincides with {SWAP_REFERENCE})")
                    continue
                print(f"  [direction] {cur} on {key[0].split('#')[-1]} -> "
                      f"{key[1].split('#')[-1].split('/')[-1]}: "
                      f"{v} -> {DIRECTION_SWAP[v]}")
                votes[key][cur] = DIRECTION_SWAP[v]

    curators = sorted({c for v in votes.values() for c in v})
    print(f"\n{len(votes)} canonical pairs, curators: {', '.join(curators)}")

    # ---- canonical LLM suggestion (majority across buckets) ----
    def canonical_llm(key):
        cnt = Counter(r["llm_relation"] for r in batch[key])
        return cnt.most_common(1)[0][0]

    # ---- agreement ----
    def amr(key, cur):
        v = votes[key].get(cur)
        if v is None:
            return None
        if v == REJECT:
            return "reject"
        return "accept" if v == canonical_llm(key) else "modify"

    print("\n== Pairwise agreement (canonical pairs) ==")
    for c1, c2 in itertools.combinations(curators, 2):
        dec_pairs = [(amr(k, c1), amr(k, c2)) for k in votes
                     if amr(k, c1) and amr(k, c2)]
        vote_pairs = [(votes[k][c1], votes[k][c2]) for k in votes
                      if votes[k].get(c1) and votes[k].get(c2)]
        if dec_pairs:
            agree = sum(1 for a, b in dec_pairs if a == b) / len(dec_pairs)
            vagree = sum(1 for a, b in vote_pairs if a == b) / len(vote_pairs)
            print(f"  {c1} vs {c2}: n={len(dec_pairs)}, "
                  f"decision agreement={agree:.2%}, kappa={kappa(dec_pairs):.3f}; "
                  f"relation-vote agreement={vagree:.2%}, kappa={kappa(vote_pairs):.3f}")

    # ---- team adjudication (applies where the majority vote is split) ----
    adjudicated = {}
    if os.path.exists(ADJUDICATION_FILE):
        adf = pd.read_csv(ADJUDICATION_FILE)
        adjudicated = {(r["aidoc_iri"], r["ref_iri"]): (r["consensus"], r.get("note", ""))
                       for _, r in adf.iterrows()}
        unknown = [k for k in adjudicated if k not in votes]
        for k in unknown:
            print(f"  [warn] adjudication entry does not match any pair: {k}")
        print(f"loaded {len(adjudicated)} adjudicated decisions from {ADJUDICATION_FILE}")

    # ---- consensus (majority >= 2, adjudication overrides splits) ----
    merged_rows, cons_rows = [], []
    conflicts = 0
    for key in sorted(votes):
        aidoc_iri, ref_iri = key
        llm = canonical_llm(key)
        vs = {c: v for c, v in votes[key].items() if v is not None}
        for c in curators:
            if c in votes[key]:
                merged_rows.append({
                    "aidoc_iri": aidoc_iri, "ref_iri": ref_iri,
                    "buckets": "+".join(sorted({r["bucket"] for r in batch[key]})),
                    "llm_relation": llm, "curator": c,
                    "vote": votes[key][c] or "UNDETERMINED",
                    "decision": amr(key, c) or "modify(?)",
                    "note": notes[key].get(c, ""),
                })
        cnt = Counter(vs.values())
        top, n = cnt.most_common(1)[0] if cnt else (None, 0)
        consensus = top if n >= 2 else None
        source = "majority"
        if consensus is None and key in adjudicated:
            consensus, adj_note = adjudicated[key]
            source = "adjudicated"
            if adj_note and str(adj_note) != "nan":
                notes[key]["team"] = str(adj_note)
        if consensus is None:
            conflicts += 1
        outcome = (None if consensus is None else
                   "reject" if consensus == REJECT else
                   "accept" if consensus == llm else "modify")
        cons_rows.append({
            "aidoc_iri": aidoc_iri, "ref_iri": ref_iri,
            "buckets": "+".join(sorted({r["bucket"] for r in batch[key]})),
            "aidoc_label": batch[key][0]["aidoc_label"],
            "ref_label": batch[key][0]["ref_label"],
            "llm_relation": llm,
            **{f"vote_{c}": votes[key].get(c) or "" for c in curators},
            "consensus": consensus or "CONFLICT",
            "consensus_source": source if consensus else "",
            "outcome": outcome or "CONFLICT",
            "notes": " | ".join(f"{c}: {n}" for c, n in sorted(notes[key].items())),
        })

    os.makedirs("reports", exist_ok=True)
    pd.DataFrame(merged_rows).to_csv("reports/curation_merged.csv", index=False)
    cons = pd.DataFrame(cons_rows)
    cons.to_csv("reports/curation_consensus.csv", index=False)

    oc = Counter(r["outcome"] for r in cons_rows)
    print(f"\n== Consensus over {len(cons_rows)} canonical pairs ==")
    print(f"  accept: {oc.get('accept', 0)}, modify: {oc.get('modify', 0)}, "
          f"reject: {oc.get('reject', 0)}, CONFLICT: {oc.get('CONFLICT', 0)}")
    if conflicts:
        print("  Konflikte im Team auflösen (publication/curation_protocol.md), "
              "dann Konsens in reports/curation_consensus.csv eintragen und "
              "dieses Skript erneut ausführen (oder die Urteile im UI korrigieren).")

    # ---- write consensus back into every bucket row of each pair ----
    by_key = {(r["aidoc_iri"], r["ref_iri"]): r for r in cons_rows}
    for d, prefix in CURATION_DIRS:
        for f in sorted(glob.glob(os.path.join(d, "*-curation.csv"))):
            try:
                df = pd.read_csv(f)
            except pd.errors.EmptyDataError:
                continue
            for col in ("curator_decision", "curator_relation", "curator_name", "curator_notes"):
                df[col] = df[col].astype("string")
            changed = 0
            for i, row in df.iterrows():
                r = by_key.get((row["aidoc_iri"], row["ref_iri"]))
                if not r:
                    continue
                if r["consensus"] == "CONFLICT":
                    df.at[i, "curator_decision"] = ""
                    df.at[i, "curator_notes"] = "CONFLICT: " + " / ".join(
                        f"{c}={r[f'vote_{c}']}" for c in curators if r.get(f"vote_{c}"))
                else:
                    # outcome relative to THIS bucket row's LLM suggestion
                    if r["consensus"] == REJECT:
                        dec, rel = "reject", ""
                    elif r["consensus"] == str(row["llm_relation"]):
                        dec, rel = "accept", ""
                    else:
                        dec, rel = "modify", r["consensus"]
                    df.at[i, "curator_decision"] = dec
                    df.at[i, "curator_relation"] = rel
                    df.at[i, "curator_name"] = "+".join(curators)
                    df.at[i, "curator_notes"] = r["notes"] or ""
                changed += 1
            if changed:
                df.to_csv(f, index=False)
                print(f"  {f}: {changed} rows updated")


if __name__ == "__main__":
    main()
