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
    for s in g.subjects(rdflib.RDF.type, OWL.Class):
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


def main(threshold, right_dir, left_file):
    left_g = rdflib.Graph().parse(left_file, format="turtle")

    for fname in Path(right_dir).glob("*.ttl"):
        right_g = rdflib.Graph().parse(fname, format="turtle")

        left_classes = extract_entities(left_g)
        right_classes = extract_entities(right_g)

        alignments = []

        for l_iri, l_label in left_classes.items():
            for r_iri, r_label in right_classes.items():
                # skip if the IRIs are identical (same entity appears in both graphs)
                if l_iri == r_iri:
                    continue
                score = similarity(l_label, r_label)
                # collect all above threshold
                if score >= threshold:
                    alignments.append({
                        "aidoc_iri": l_iri,
                        "aidoc_label": l_label,
                        f"{Path(fname).stem}_iri": r_iri,
                        f"{Path(fname).stem}_label": r_label,
                        "similarity": round(score, 3)
                    })

        out_path = os.path.join(OUTPUT_DIR, f"{Path(fname).stem}_alignment.csv")
        if alignments:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=alignments[0].keys())
                writer.writeheader()
                writer.writerows(sorted(alignments, key=lambda x: -x['similarity']))

        print(f"Found {len(alignments)} potential lexical alignments → {out_path}")

    print("✅ Structural alignment completed.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Structural alignment (lexical) with looser matching options')
    parser.add_argument('--threshold', '-t', type=float, default=0.75,
                        help='similarity threshold (0-1) to report an alignment; lower = more candidates')
    parser.add_argument('--right', '-r', default=RIGHT_FILE, help='directory with reference ontology TTL files')
    parser.add_argument('--left', '-l', default=LEFT_FILE, help='left-hand TTL file')
    args = parser.parse_args()
    main(args.threshold, args.right, args.left)