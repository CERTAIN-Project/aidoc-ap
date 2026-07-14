# Konsens-Meeting: die 16 verbleibenden Kurationskonflikte

Stand 14.07.2026 (TD-Re-Export mit korrigierten relation-Feldern eingespielt; Ergebnis unverändert).
3-Wege-Merge (FK+SN+TD, 2-von-3-Mehrheit) über **157 kanonische Paare** (112 Haupt + 45 FN-Band).

**Konsens erreicht (141):** Haupt 42 accept / 10 modify / 49 reject · Band 4 accept / 9 modify / 27 reject.
**κ (Entscheidungsebene):** FK–SN 0.434 · FK–TD 0.433 · SN–TD 0.621.

## Konfliktliste (sortiert nach Muster)

| AIDOC-Term | Referenz (Vokabular) | LLM @conf | Voten | Empfehlung |
|---|---|---|---|---|
| Data Testing | `vair:Testing` ⌄band | closeMatch @0.85 | FK broadMatch · SN closeMatch · TD REJECT | Familien-Konvention (A) |
| Data Training | `mex-core:Training` | closeMatch @0.85 | FK broadMatch · SN closeMatch · TD REJECT | Familien-Konvention (A) |
| Data Validation | `mex-core:Validation` | closeMatch @0.85 | FK broadMatch · SN closeMatch · TD REJECT | Familien-Konvention (A) |
| Data Validation | `vair:Validation` | closeMatch @0.85 | FK relatedMatch · SN closeMatch · TD REJECT | Familien-Konvention (A) |
| Model Evaluation | `vair:Re-Evaluation` ⌄band | closeMatch @0.85 | FK narrowMatch · SN closeMatch · TD REJECT | Familien-Konvention (A) |
| AI Model | `dpv-tech:Model` | closeMatch @0.85 | FK broadMatch · SN closeMatch · TD REJECT | **broadMatch** |
| AI Model | `mex-core:Model` | closeMatch @0.85 | FK broadMatch · SN closeMatch · TD REJECT | **broadMatch** |
| AI Model | `vair:Model` | closeMatch @0.85 | FK relatedMatch · SN closeMatch · TD broadMatch | **broadMatch** |
| AI System | `sao:System` | narrowMatch @0.85 | FK REJECT · SN narrowMatch · TD broadMatch | **broadMatch** |
| Visual Documentation | `dpv-aiact:TechnicalDocumentation` ⌄band | closeMatch @0.85 | FK closeMatch · SN relatedMatch · TD REJECT | **broadMatch** |
| Visual Documentation | `vair:Technical Documentation` ⌄band | narrowMatch @0.85 | FK closeMatch · SN relatedMatch · TD REJECT | **broadMatch** |
| AI Agent | `dpv-ai:AIAgent` | exactMatch @0.95 | FK closeMatch · SN exactMatch · TD REJECT | **narrowMatch** oder reject |
| Data Cleaning Procedure | `rains:Data Preprocessing Procedure` | closeMatch @0.85 | FK REJECT · SN broadMatch · TD closeMatch | **broadMatch** |
| Model Evaluation | `rains:Evaluation` | closeMatch @0.85 | FK narrowMatch · SN broadMatch · TD closeMatch | **reject** (Konsistenz) |
| Post-market Monitoring Activity | `dpv-aiact:PostMarketMonitoringSystem` | closeMatch @0.85 | FK REJECT · SN closeMatch · TD exactMatch | **closeMatch** |
| Software Component | `vair:Safety Component` ⌄band | broadMatch @0.85 | FK narrowMatch · SN relatedMatch · TD REJECT | **relatedMatch** |

`⌄band` = Paar aus dem FN-Band [0.5, 0.6).

## Auflösungs-Leitfaden

**Muster A — Aktivität vs. Lifecycle-Phase (5 Paare: DataTesting/Training/Validation×2, ModelEvaluation→ReEvaluation).**
aidoc modelliert *Aktivitäten*, vair/mex-core *Phasen*. Eine Phase ist keine Generalisierung der Aktivität (zeitliche, nicht begriffliche Enthaltenheit) → Empfehlung: **eine Konvention für die ganze Familie festlegen**, vorzugsweise `skos:relatedMatch` (assoziativ, keine Hierarchie behauptet); Alternative: konsequent reject (wie TD). ⚠️ Konsistenz: `Deployment → vair:Deployment` wurde bereits mehrheitlich **rejected** — die gewählte Konvention sollte auch dieses Paar (und die bereits entschiedenen mex/vair-Rejects) einschließen, sonst misst ein Reviewer mit zweierlei Maß.

**Muster B — generisches Oberkonzept (4 Paare: AIModel→mex/tech/vair:Model, AISystem→sao:System).**
Die Referenzkonzepte sind generische Modelle/Systeme („simplified representation of a system, process, or concept"); aidoc-Terme sind klare Spezialisierungen → per SKOS-Definition ist das Ziel breiter → **`skos:broadMatch`**. Passt zur Grounding-Strategie des Papers (aidoc-Terme als Spezialisierungen externer Konzepte).

**Muster C — Teil/Art der technischen Dokumentation (2 Paare: VisualDocumentation→TechnicalDocumentation).**
Visuelle Dokumentation ist laut aidoc-Definition eine Annex-IV-*Form* der technischen Dokumentation → Ziel breiter → **`skos:broadMatch`** (Option, die keiner gewählt hat; BT/NT-partitive Lesart ist Thesaurus-Praxis). Wer die Teil-Ganzes-Lesart ablehnt: `relatedMatch`.

**Einzelfälle:**
- **D1 AIAgent → dpv-ai:AIAgent — falscher Freund!** aidoc = „superclass for all agents involved in the AI lifecycle" (Menschen, Organisationen, Software); dpv-ai = „software agent that utilises AI technologies". Ein KI-Software-Agent ist eine Teilmenge der aidoc-Agenten → **`narrowMatch`**; wer nur dokumentationsrelevante Mappings will: reject.
- **D3 DataCleaningProcedure → rains:DataPreprocessingProcedure:** rains-Definition nennt „cleaning, sampling, filtering" explizit als Teilmenge von Preprocessing → Ziel breiter → **`broadMatch`** (SNs Votum).
- **D4 ModelEvaluation → rains:Evaluation:** rains-Konzept ist ein „AccountableResult … recording the results" — Ergebnis-/Dokumentartefakt, keine Aktivität. Das Team hat dieselbe Kategorie-Unterscheidung bei `mls:ModelEvaluation` bereits mit reject entschieden → **reject** (Konsistenz).
- **D5 PostMarketMonitoringActivity → dpv-aiact:PostMarketMonitoringSystem:** Die AI-Act-Definition des „Systems" lautet wörtlich „all activities carried out by providers … to collect and review experience" — das Referenzkonzept IST die Aktivitätsmenge → **`closeMatch`** (SNs Votum; FKs Label-basiertes reject greift zu kurz). Konsistent mit dem bereits akzeptierten `PostMarketMonitoringPlan`-closeMatch.
- **D6 SoftwareComponent → vair:SafetyComponent:** Sicherheitskomponenten können Hardware sein, Softwarekomponenten müssen nicht sicherheitsrelevant sein — keine Subsumtion in beide Richtungen → **`relatedMatch`** (SNs Votum).

## Verfahren nach dem Meeting

1. Eine Person trägt die beschlossenen Urteile im Kurations-UI ein (Modify + Relation; UI ist gefixt) und exportiert neu — **oder** trägt den Konsens direkt in `reports/curation_consensus.csv` ein.
2. `python scripts/merge_curation.py experiments/alignment_curation/curation_*.json` erneut ausführen.
3. Danach werden Paper-Zahlen (§6.1, Tabelle, §8), Response Letter und die kuratierten Alignment-TTLs/Pages aktualisiert (TODO-Marker stehen bereits im LaTeX).

## Definitionen (Kontext)

- **Data Testing → `vair:Testing`**
  - aidoc: *Activity of using datasets for model testing. Testing data means data used for providing an independent evaluation of the AI system in order to confirm the expected performance of …*
  - ref: *—*
- **Data Training → `mex-core:Training`**
  - aidoc: *Activity of using datasets for model training. Training data means data used for training an AI system through fitting its learnable parameters.*
  - ref: *—*
- **Data Validation → `mex-core:Validation`**
  - aidoc: *Activity of using datasets for model validation. Validation data means data used for providing an evaluation of the trained AI system and for tuning its non-learnable parameters an…*
  - ref: *—*
- **Data Validation → `vair:Validation`**
  - aidoc: *Activity of using datasets for model validation. Validation data means data used for providing an evaluation of the trained AI system and for tuning its non-learnable parameters an…*
  - ref: *Validating that the AI system from the design and development stage works according to requirements and meets objectives.*
- **Model Evaluation → `vair:Re-Evaluation`**
  - aidoc: *Activity of assessing performance, robustness, and accuracy.*
  - ref: *After the operation and monitoring stage, based on the results of the work of the AI system, the need for a reassessment can arise.*
- **AI Model → `dpv-tech:Model`**
  - aidoc: *A computational representation that enables an AI method to execute an AI task.*
  - ref: *A simplified representation or abstraction of a system, process, or concept*
- **AI Model → `mex-core:Model`**
  - aidoc: *A computational representation that enables an AI method to execute an AI task.*
  - ref: *—*
- **AI Model → `vair:Model`**
  - aidoc: *A computational representation that enables an AI method to execute an AI task.*
  - ref: *physical, mathematical or otherwise logical representation of a system, entity, phenomenon, process or data. *
- **AI System → `sao:System`**
  - aidoc: *An AI system is a machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or imp…*
  - ref: *—*
- **Visual Documentation → `dpv-aiact:TechnicalDocumentation`**
  - aidoc: *Visual documentation of an AI system including photographs, illustrations, diagrams, or renderings that show external features, internal layout, or markings as required by Annex IV…*
  - ref: *Annex IV technical documentation*
- **Visual Documentation → `vair:Technical Documentation`**
  - aidoc: *Visual documentation of an AI system including photographs, illustrations, diagrams, or renderings that show external features, internal layout, or markings as required by Annex IV…*
  - ref: *Documentation required by the AI Act, Article 11.*
- **AI Agent → `dpv-ai:AIAgent`**
  - aidoc: *A superclass for all agents involved in the AI lifecycle, derived from prov:Agent.*
  - ref: *An AI Agent, also known as an 'intelligent agent', is a software agent that utilises AI technologies*
- **Data Cleaning Procedure → `rains:Data Preprocessing Procedure`**
  - aidoc: *A procedure describing how data cleaning is performed, such as outlier detection and removal of invalid records.*
  - ref: *A specific type of sao:InformationElement which records a specific piece of  information detailing how the data is preprocessed. This includes information on what is done to the da…*
- **Model Evaluation → `rains:Evaluation`**
  - aidoc: *Activity of assessing performance, robustness, and accuracy.*
  - ref: *A specific type of planned sao:AccountableResult which represents a high level reference to testing at least one component and recording the results of the test(s) (e.g. testing th…*
- **Post-market Monitoring Activity → `dpv-aiact:PostMarketMonitoringSystem`**
  - aidoc: *Activity of monitoring the system's performance and behavior after deployment.*
  - ref: *All activities carried out by providers of AI systems to collect and review experience gained from the use of AI systems they place on the market or put into service for the purpos…*
- **Software Component → `vair:Safety Component`**
  - aidoc: *A logical or physical software component of the AI system, such as a service, module, or microservice participating in the overall processing.*
  - ref: *Component of a product or of an AI system which fulfils a safety function for that product or AI system, or the failure or malfunctioning of which endangers the health and safety o…*

## Appendix: angewendete Korrekturen

### Richtungs-Swaps (SN, broad↔narrow nach SKOS-Definition; Ausnahme = Übereinstimmung mit TD)
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
  [intra-curator] TD voted differently on duplicate buckets of AIAgent -> Agent: {'skos:broadMatch': 1, 'skos:closeMatch': 1} -> using skos:broadMatch
```
