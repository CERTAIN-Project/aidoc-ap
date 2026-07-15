"""Generate the curated alignment TTLs from the consensus of the expert curation.

Reads reports/curation_consensus.csv (produced by merge_curation.py: canonical
pairs with the consensus relation from three curators, 2-of-3 majority plus
team adjudication) and rewrites reports/alignment_semantic/*-alignments.ttl:

  * accept  -> triple with the LLM-suggested relation
  * modify  -> triple with the curator-corrected relation
  * reject / unresolved CONFLICT -> no triple

Pairs from the below-threshold FN sample that were judged meaningful are
included as well (they are curated correspondences like any other); each
mapping node records the curation outcome. The bogus mex-core namespace
http://www.w3.org/ns/prov-o# is normalised to the real PROV namespace, and
pairs that coincide after normalisation are emitted once.

Post-curation editorial revisions (ontology v1.2): the consensus CSV is the
frozen record of the curation against ontology v1.1 and is never rewritten;
renames of AIDOC-AP terms after the curation are applied here as a documented
IRI migration, together with relation revisions that the rename entails.
Revised mappings carry an align:editorialNote.

Usage:
    python scripts/apply_curation_to_ttl.py
"""

import datetime
import os
import uuid
from collections import defaultdict

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, RDFS, XSD

CONSENSUS = "reports/curation_consensus.csv"
OUTPUT_DIR = "reports/alignment_semantic"

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ALIGN = Namespace("https://w3id.org/aidoc-ap/alignment#")
IRI_FIXES = {"http://www.w3.org/ns/prov-o#": "http://www.w3.org/ns/prov#"}

CURATORS_AGENT = URIRef("https://w3id.org/aidoc-ap/alignment#ExpertCurationTeam")
LLM_AGENT = URIRef("https://w3id.org/aidoc-ap/alignment#LLMAlignmentBot")

# v1.2 (2026-07-15): aidoc:VisualDocumentation was renamed and generalised to
# aidoc:TechnicalDocumentation after the curation was finalised. The two
# adjudicated relatedMatch pairs targeting a TechnicalDocumentation concept
# expressed the semantic distance between *visual* documentation and the
# technical documentation artefact; with the rename that distance is gone, so
# they are revised to closeMatch. The broadMatch pairs targeting the generic
# Documentation concepts remain valid.
AIDOC_RENAMES = {
    "https://w3id.org/aidoc-ap#VisualDocumentation":
        "https://w3id.org/aidoc-ap#TechnicalDocumentation",
}
RELATION_REVISIONS = {  # (aidoc_iri after rename, ref_iri) -> revised relation
    ("https://w3id.org/aidoc-ap#TechnicalDocumentation",
     "https://w3id.org/dpv/legal/eu/aiact#TechnicalDocumentation"): "skos:closeMatch",
    ("https://w3id.org/aidoc-ap#TechnicalDocumentation",
     "https://w3id.org/vair#TechnicalDocumentation"): "skos:closeMatch",
}
EDITORIAL_NOTE = ("Post-curation editorial revision: aidoc:VisualDocumentation was "
                  "renamed and generalised to aidoc:TechnicalDocumentation in "
                  "ontology v1.2; the IRI was migrated and the adjudicated relation "
                  "revised accordingly. The curation record (v1.1) is unchanged.")


def normalise(iri):
    for wrong, right in IRI_FIXES.items():
        if iri.startswith(wrong):
            return right + iri[len(wrong):]
    return iri


def main():
    df = pd.read_csv(CONSENSUS)
    kept = df[df.outcome.isin(["accept", "modify"])].copy()
    kept["ref_iri"] = kept.ref_iri.map(normalise)
    kept["revised"] = False
    renamed = kept.aidoc_iri.isin(AIDOC_RENAMES)
    kept.loc[renamed, "aidoc_iri"] = kept.loc[renamed, "aidoc_iri"].map(AIDOC_RENAMES)
    for (a_iri, r_iri), rel in RELATION_REVISIONS.items():
        sel = (kept.aidoc_iri == a_iri) & (kept.ref_iri == r_iri)
        kept.loc[sel, "consensus"] = rel
        kept.loc[sel, "revised"] = True
    kept.loc[renamed, "revised"] = True
    if renamed.any():
        n_rel = int(sum(((kept.aidoc_iri == a) & (kept.ref_iri == r)).sum()
                        for a, r in RELATION_REVISIONS))
        print(f"[editorial] {int(renamed.sum())} pair(s) migrated to renamed IRIs, "
              f"{n_rel} relation(s) revised")
    n_before = len(kept)
    kept = kept.drop_duplicates(subset=["aidoc_iri", "ref_iri", "consensus"])
    if len(kept) < n_before:
        print(f"[dedup] {n_before - len(kept)} pair(s) coincided after IRI normalisation")

    by_file = defaultdict(list)
    for _, r in kept.iterrows():
        bucket = r.buckets.split("+")[0].replace("fn-band/", "")
        by_file[bucket].append(r)

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    total = 0
    for bucket in sorted(by_file):
        g = Graph()
        g.bind("prov", PROV)
        g.bind("skos", SKOS)
        g.bind("align", ALIGN)
        g.bind("aidoc", "https://w3id.org/aidoc-ap#")

        activity = URIRef(f"https://w3id.org/aidoc-ap/alignment#{uuid.uuid4()}")
        g.add((activity, RDF.type, PROV.Activity))
        g.add((activity, RDFS.label, Literal(
            "Expert curation of LLM-proposed alignments "
            "(three curators, 2-of-3 majority vote, joint adjudication of splits)")))
        g.add((activity, PROV.startedAtTime,
               Literal(now.isoformat().replace("+00:00", "Z"), datatype=XSD.dateTime)))
        g.add((activity, PROV.wasAssociatedWith, CURATORS_AGENT))
        g.add((activity, PROV.wasInformedBy, LLM_AGENT))
        g.add((CURATORS_AGENT, RDF.type, PROV.Agent))
        g.add((CURATORS_AGENT, RDFS.label, Literal(
            "AIDOC-AP curation team (three domain experts)")))

        for r in by_file[bucket]:
            aidoc_uri, ref_uri = URIRef(r.aidoc_iri), URIRef(r.ref_iri)
            rel_uri = SKOS[r.consensus.split(":")[-1]]
            g.add((aidoc_uri, rel_uri, ref_uri))

            m = URIRef(f"https://w3id.org/aidoc-ap/alignment#{uuid.uuid4()}")
            g.add((m, RDF.type, ALIGN.Mapping))
            g.add((m, RDF.type, PROV.Entity))
            g.add((m, ALIGN.source, aidoc_uri))
            g.add((m, ALIGN.target, ref_uri))
            g.add((m, ALIGN.relation, rel_uri))
            g.add((m, ALIGN.curationOutcome, Literal(r.outcome)))
            g.add((m, ALIGN.llmSuggestedRelation, Literal(r.llm_relation)))
            if r.revised:
                g.add((m, ALIGN.editorialNote, Literal(EDITORIAL_NOTE)))
            g.add((m, PROV.wasGeneratedBy, activity))
            g.add((m, PROV.wasAttributedTo, CURATORS_AGENT))
            total += 1

        out = os.path.join(OUTPUT_DIR, f"{bucket}-alignments.ttl")
        g.serialize(destination=out, format="turtle")
        print(f"  {len(by_file[bucket]):3d} curated mappings → {out}")

    # buckets whose proposals were all rejected still need an empty (headerless)
    # alignment file removed so stale LLM triples do not linger
    import glob
    for f in glob.glob(os.path.join(OUTPUT_DIR, "*-alignments.ttl")):
        bucket = os.path.basename(f).replace("-alignments.ttl", "")
        if bucket not in by_file:
            os.remove(f)
            print(f"  removed {f} (no curated mappings for this file)")

    print(f"✅ {total} curated mappings written.")


if __name__ == "__main__":
    main()
