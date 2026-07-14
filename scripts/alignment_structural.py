import argparse
import rdflib
from rdflib import RDFS, OWL
from rdflib.namespace import SKOS
from difflib import SequenceMatcher
import csv
import os
from pathlib import Path
import re
import unicodedata

LEFT_FILE = "aidoc-ap.ttl"
RIGHT_FILE = "reference_ontologies/"
OUTPUT_DIR = "reports/alignment_structural/"
os.makedirs(OUTPUT_DIR, exist_ok=True)
Path("reports").mkdir(exist_ok=True)


def normalize_label(s):
    if s is None:
        return ""
    # to str, strip, lowercase
    s = str(s).strip()
    # unicode normalize (remove diacritics)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # replace punctuation/underscores with space, split camelCase
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = re.sub(r'[_\-\.,;:\(\)\[\]\/\\]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.lower()


def token_jaccard(a, b):
    a_tokens = set(normalize_label(a).split())
    b_tokens = set(normalize_label(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    inter = a_tokens.intersection(b_tokens)
    union = a_tokens.union(b_tokens)
    return len(inter) / len(union)


def similarity(a, b):
    # combine SequenceMatcher (character-level) with token Jaccard (token-level)
    a_n = normalize_label(a)
    b_n = normalize_label(b)
    seq = SequenceMatcher(None, a_n, b_n).ratio()
    jacc = token_jaccard(a_n, b_n)
    # weighted average — tokens get slightly more weight because they handle reorderings
    return 0.4 * seq + 0.6 * jacc


def extract_entities(g):
    entities = {}
    # DPV (and other SKOS-based vocabularies) declare concepts as
    # rdfs:Class / skos:Concept rather than owl:Class
    subjects = set(g.subjects(rdflib.RDF.type, OWL.Class))
    subjects.update(g.subjects(rdflib.RDF.type, RDFS.Class))
    subjects.update(g.subjects(rdflib.RDF.type, SKOS.Concept))
    # ... but DPV also types its *properties* as skos:Concept (e.g.
    # ai:hasAISystem a rdf:Property, skos:Concept), which would admit
    # class-to-property candidate pairs. Properties are excluded: the
    # alignment maps class-level concepts only.
    property_types = (rdflib.RDF.Property, OWL.ObjectProperty,
                      OWL.DatatypeProperty, OWL.AnnotationProperty)
    subjects = {s for s in subjects
                if not any((s, rdflib.RDF.type, t) in g for t in property_types)}
    for s in subjects:
        labels = []
        # common label predicates
        for lbl in g.objects(s, RDFS.label):
            labels.append(str(lbl))
        for lbl in g.objects(s, SKOS.prefLabel):
            labels.append(str(lbl))
        for lbl in g.objects(s, SKOS.altLabel):
            labels.append(str(lbl))
        # fallback: use local name from IRI
        if not labels:
            iri = str(s)
            local = iri.split('#')[-1].split('/')[-1]
            # try to split camelCase/underscores later via normalize_label
            labels.append(local)

        # choose the longest label (usually most descriptive) as representative
        rep = max(labels, key=lambda x: len(x)) if labels else ''
        entities[str(s)] = rep
    return entities


def namespace_of(iri):
    return iri.rsplit("#", 1)[0] + "#" if "#" in iri else iri.rsplit("/", 1)[0] + "/"


def main(threshold, right_dir, left_file):
    left_g = rdflib.Graph().parse(left_file, format="turtle")
    left_classes = extract_entities(left_g)

    # Reference TTLs redeclare terms from other vocabularies (e.g. rains.ttl
    # contains mls:Dataset and prov:Agent), so the same (aidoc, ref) pair can
    # surface under several files. Collect candidates globally, then assign
    # each unique pair to the file whose dominant namespace owns the target
    # IRI; otherwise to the first file (sorted order) that produced it.
    files = sorted(Path(right_dir).glob("*.ttl"))
    dominant_ns = {}
    candidates = {}  # (l_iri, r_iri) -> {stem: row}
    for fname in files:
        right_g = rdflib.Graph().parse(fname, format="turtle")
        right_classes = extract_entities(right_g)
        ns_count = {}
        for r_iri in right_classes:
            ns = namespace_of(r_iri)
            ns_count[ns] = ns_count.get(ns, 0) + 1
        dominant_ns[fname.stem] = max(ns_count, key=ns_count.get) if ns_count else ""

        for l_iri, l_label in left_classes.items():
            for r_iri, r_label in right_classes.items():
                if l_iri == r_iri:
                    continue
                score = similarity(l_label, r_label)
                if score >= threshold:
                    candidates.setdefault((l_iri, r_iri), {})[fname.stem] = {
                        "aidoc_iri": l_iri,
                        "aidoc_label": l_label,
                        f"{fname.stem}_iri": r_iri,
                        f"{fname.stem}_label": r_label,
                        "similarity": round(score, 3),
                    }

    per_file = {f.stem: [] for f in files}
    n_dedup = 0
    for (l_iri, r_iri), by_stem in candidates.items():
        owners = [s for s in by_stem if namespace_of(r_iri) == dominant_ns[s]]
        stem = owners[0] if owners else sorted(by_stem)[0]
        if len(by_stem) > 1:
            n_dedup += len(by_stem) - 1
        per_file[stem].append(by_stem[stem])

    for fname in files:
        stem = fname.stem
        alignments = per_file[stem]
        out_path = os.path.join(OUTPUT_DIR, f"{stem}_alignment.csv")
        if alignments:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=alignments[0].keys())
                writer.writeheader()
                writer.writerows(sorted(alignments, key=lambda x: -x['similarity']))
        elif os.path.exists(out_path):
            os.remove(out_path)
        print(f"Found {len(alignments)} potential lexical alignments → {out_path}")

    print(f"✅ Structural alignment completed "
          f"({len(candidates)} unique pairs, {n_dedup} cross-file duplicates removed).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Structural alignment (lexical) with looser matching options')
    parser.add_argument('--threshold', '-t', type=float, default=0.6,
                        help='similarity threshold (0-1) to report an alignment; lower = more candidates '
                             '(0.6 is the candidate-generation threshold reported in the paper)')
    parser.add_argument('--right', '-r', default=RIGHT_FILE, help='directory with reference ontology TTL files')
    parser.add_argument('--left', '-l', default=LEFT_FILE, help='left-hand TTL file')
    args = parser.parse_args()
    main(args.threshold, args.right, args.left)