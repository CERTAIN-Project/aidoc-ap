# Konsens-Meeting: verbleibende Kurationskonflikte

Stand 14.07.2026, nach 3-Wege-Merge (FK+SN+TD, 2-von-3-Mehrheit) über **157 kanonische Paare**
(112 Hauptkandidaten + 45 FN-Band; Duplikate über Referenz-Dateien zusammengeführt).

**Konsens erreicht:** 141 Paare — Haupt: 42 accept / 10 modify / 49 reject; Band: 4 accept / 9 modify / 27 reject.
**Zu diskutieren:** die folgenden **16 Paare** ohne 2-von-3-Mehrheit.

**Inter-Annotator-Agreement (Entscheidungsebene, Cohen's κ):** FK–SN 0.434, FK–TD 0.424, SN–TD 0.609.

## Konfliktliste

| AIDOC-Term | Referenz-Term | LLM-Vorschlag | Voten | Notizen |
|---|---|---|---|---|
| AI Agent | AIAgent | exactMatch | **FK** closeMatch / **SN** exactMatch / **TD** REJECT |  |
| AI Model | Model | closeMatch | **FK** broadMatch / **SN** closeMatch / **TD** REJECT |  |
| AI Model | Model | closeMatch | **FK** broadMatch / **SN** closeMatch / **TD** REJECT |  |
| AI Model | Model | closeMatch | **FK** relatedMatch / **SN** closeMatch / **TD** broadMatch | FK: aidoc describes a concrete AI/ML model while vair describes not only a model, but also a system, entity, phenomenon, process or data | TD: skos:broadMatch |
| AI System | System | narrowMatch | **FK** REJECT / **SN** narrowMatch / **TD** broadMatch | FK: aidoc specifies a concrete AI System while rains (sao) specifies a general system with collected accountability information | TD: skos:broadMatch |
| Data Cleaning Procedure | Data Preprocessing Procedure | closeMatch | **FK** REJECT / **SN** broadMatch / **TD** closeMatch | FK: aidoc describes a procedure how data is cleaned, while rains describes a specific type of sao:InformationElement which records a specific piece of information detailing how the data is preprocesse |
| Data Testing | Testing *(fn-band)* | closeMatch | **FK** broadMatch / **SN** closeMatch / **TD** REJECT | TD: activity vs phase |
| Data Training | Training | closeMatch | **FK** broadMatch / **SN** closeMatch / **TD** REJECT | TD: ours is the activity, while mex-core Training is a phase |
| Data Validation | Validation | closeMatch | **FK** broadMatch / **SN** closeMatch / **TD** REJECT | TD: aidoc data validation is a activity, whereas validation is a subclass of phase and mor likely a closeMatch to https://w3id.org/vair#Validation |
| Data Validation | Validation | closeMatch | **FK** relatedMatch / **SN** closeMatch / **TD** REJECT | FK: aidoc activity (EU AI Act 2024/1689, Article 3(30)) vs vair activity (ISO/IEC 22989:2022, 6.2.4) | TD: aidoc is activity, vair is phase |
| Model Evaluation | Evaluation | closeMatch | **FK** narrowMatch / **SN** broadMatch / **TD** closeMatch | SN: skos:narrowMatch |
| Model Evaluation | Re-Evaluation *(fn-band)* | closeMatch | **FK** narrowMatch / **SN** closeMatch / **TD** REJECT | FK: broader activity of evaluation vs narrower re-evaluation based on results | TD: activity vs phase |
| Post-market Monitoring Activity | PostMarketMonitoringSystem | closeMatch | **FK** REJECT / **SN** closeMatch / **TD** exactMatch | FK: activity vs description of a concrete system | TD: skos:exactMatch |
| Software Component | Safety Component *(fn-band)* | broadMatch | **FK** narrowMatch / **SN** relatedMatch / **TD** REJECT | SN: skos:relatedMatch |
| Visual Documentation | TechnicalDocumentation *(fn-band)* | closeMatch | **FK** closeMatch / **SN** relatedMatch / **TD** REJECT | SN: skos:relatedMatch |
| Visual Documentation | Technical Documentation *(fn-band)* | narrowMatch | **FK** closeMatch / **SN** relatedMatch / **TD** REJECT | SN: skos:relatedMatch |

**Muster:** In den meisten Fällen steht TDs *reject* (Aktivität-vs-Phase/-Datenobjekt-Argument) gegen eine
von FK/SN gesehene Beziehung; fünf Fälle sind reine Relationswert-Splits. Nach der Diskussion:
Urteile im UI korrigieren (eine Person) → neu exportieren → `merge_curation.py` erneut ausführen,
oder Konsens direkt in `reports/curation_consensus.csv` eintragen.

## Hinweise / Datenqualität

- `vair.ttl` enthält ein kaputtes Ziel-IRI `semanticweb.org/owl/owlapi/turtle#MachineLearning` (rejected — kein Handlungsbedarf) und `mex-core.ttl` nutzt den falschen Namespace `w3.org/ns/prov-o#` statt `ns/prov#` (2 Paare; bei der Generierung der kuratierten TTLs auf `prov:` normalisieren).
- FKs Direction-Nutzung folgt der SKOS-Definition; SNs broad/narrow wurden getauscht (Ausnahme DownstreamAIProvider, s. Log).

## Angewendete Korrekturen (Auszug aus merge_log.txt)

### Richtungs-Swaps (SN, broad↔narrow nach SKOS-Definition)
```
  [direction] SN on VisualDocumentation -> Documentation: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIProvider -> DownstreamAIProvider: skos:narrowMatch kept (coincides with TD)
  [direction] SN on AIAgent -> Agent: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIAgent -> Agent: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIActivity -> Activity: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIAgent -> Agent: skos:narrowMatch -> skos:broadMatch
  [direction] SN on DataCleaningProcedure -> DataPreprocessingProcedure: skos:narrowMatch -> skos:broadMatch
  [direction] SN on ModelEvaluation -> Evaluation: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIAgent -> Agent: skos:narrowMatch -> skos:broadMatch
  [direction] SN on PerformanceMetric -> Metric: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIModel -> GPAIModel: skos:broadMatch -> skos:narrowMatch
  [direction] SN on AIModel -> GPAIModel: skos:broadMatch -> skos:narrowMatch
  [direction] SN on Log -> TestLog: skos:broadMatch -> skos:narrowMatch
  [direction] SN on HardwareComponent -> Component: skos:narrowMatch -> skos:broadMatch
  [direction] SN on Dataset -> DatasetComponent: skos:broadMatch -> skos:narrowMatch
  [direction] SN on HardwareComponent -> Hardware: skos:narrowMatch -> skos:broadMatch
  [direction] SN on AIModel -> TrainedModel: skos:broadMatch -> skos:narrowMatch
```

### Intra-Kurator-Abweichungen auf Duplikat-Buckets (aufgelöst per Mehrheit/letztem Urteil)
```
  [intra-curator] FK voted differently on duplicate buckets of Standard -> Standard: {'skos:closeMatch': 1, 'skos:narrowMatch': 1} -> using skos:narrowMatch
  [intra-curator] FK voted differently on duplicate buckets of Modality -> Modality: {'skos:closeMatch': 1, 'skos:broadMatch': 1} -> using skos:broadMatch
  [intra-curator] TD voted differently on duplicate buckets of Modality -> Modality: {'skos:exactMatch': 1, 'skos:closeMatch': 1} -> using skos:closeMatch
  [intra-curator] SN voted differently on duplicate buckets of VisualDocumentation -> Documentation: {'REJECT': 1, 'skos:narrowMatch': 1} -> using skos:narrowMatch
  [intra-curator] SN voted differently on duplicate buckets of AIAgent -> Agent: {'skos:closeMatch': 1, 'skos:narrowMatch': 1} -> using skos:narrowMatch
  [intra-curator] SN voted differently on duplicate buckets of AIActivity -> Activity: {'skos:broadMatch': 1, 'skos:exactMatch': 1} -> using skos:exactMatch
  [intra-curator] SN voted differently on duplicate buckets of Dataset -> Dataset: {'skos:narrowMatch': 1, 'skos:exactMatch': 2} -> using skos:exactMatch
  [intra-curator] TD voted differently on duplicate buckets of SoftwareImplementation -> Implementation: {'skos:exactMatch': 1, 'skos:closeMatch': 1} -> using skos:closeMatch
  [intra-curator] TD voted differently on duplicate buckets of AIAgent -> Agent: {'skos:broadMatch': 1, 'skos:closeMatch': 1} -> using skos:closeMatch
```
