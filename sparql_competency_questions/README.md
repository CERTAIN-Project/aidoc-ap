# SPARQL Queries for AIDOC-AP Competency Questions

This document contains SPARQL queries designed to answer the [competency questions](https://w3id.org/aidoc-ap/requirements) defined for Annex IV of the EU AI Act (Regulation 2024/1689), as formalized in the AIDOC-AP (AI Documentation Application Profile) ontology.

**Legal Reference:** [EU AI Act 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689)

**Annex IV Reference:** [AI Act Service Desk - Annex 4](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-4)

---

## Prefixes

All queries use the following prefix declarations:

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dqv: <http://www.w3.org/ns/dqv#>
PREFIX dpv: <https://w3id.org/dpv#>
PREFIX server: <http://w3id.org/devops-infra/server#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
```

---

## Requirement 1: General Description of the AI System

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-1`](https://certain-project.github.io/aidoc-ap/requirements#show-req-1) |
| **Description** | A general description of the AI system including its intended purpose, the name of the provider and the version of the system reflecting its relation to previous versions. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(a) |

### CQ1.1: What is the intended purpose of the AI system?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?intendedPurpose ?purpose ?purposeLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:intendedPurpose ?intendedPurpose . }
  OPTIONAL { 
    ?system airo:hasPurpose ?purpose .
    OPTIONAL { ?purpose rdfs:label ?purposeLabel . }
  }
}
```

### CQ1.2: What is the name of the provider?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?provider ?providerName
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?system aidoc:isProvidedBy ?provider .
  } UNION {
    ?system airo:isProvidedBy ?provider .
  }
  OPTIONAL { ?provider foaf:name ?providerName . }
  OPTIONAL { ?provider rdfs:label ?providerName . }
}
```

### CQ1.3: What is the version of the system and its relation to previous versions?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?version ?versionInfo ?changeLog ?changeRecord ?changeDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:version ?version . }
  OPTIONAL { ?system airo:hasVersion ?versionInfo . }
  OPTIONAL {
    ?changeLog a aidoc:ChangeLog .
    ?changeLog aidoc:hasChangeRecord ?changeRecord .
    OPTIONAL { ?changeRecord dcterms:description ?changeDescription . }
  }
}
```

---

## Requirement 2: Interaction with Hardware/Software

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-2`](https://certain-project.github.io/aidoc-ap/requirements#show-req-2) |
| **Description** | How the AI system interacts with, or can be used to interact with, hardware or software, including with other AI systems, that are not part of the AI system itself, where applicable. |
| **AI Lifecycle Stage** | Software Pipeline: Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(b) |

### CQ2.1: What components or other systems does it depend on?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?component ?componentType ?componentLabel ?dependency ?dependencyLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?system aidoc:hasSoftwareComponent ?component .
    ?component a ?componentType .
    OPTIONAL { ?component rdfs:label ?componentLabel . }
    OPTIONAL { 
      ?component aidoc:dependsOn ?dependency .
      OPTIONAL { ?dependency rdfs:label ?dependencyLabel . }
    }
  } UNION {
    ?system aidoc:hasComponent ?component .
    ?component a ?componentType .
    OPTIONAL { ?component rdfs:label ?componentLabel . }
    OPTIONAL { 
      ?component aidoc:dependsOn ?dependency .
      OPTIONAL { ?dependency rdfs:label ?dependencyLabel . }
    }
  }
  FILTER(?componentType != owl:NamedIndividual)
}
```

---

## Requirement 3: Software/Firmware Versioning

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-3`](https://certain-project.github.io/aidoc-ap/requirements#show-req-3) |
| **Description** | The versions of relevant software or firmware, and any requirements related to version updates. |
| **AI Lifecycle Stage** | ML Pipeline: Model Versioning |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(c) |

### CQ3.1: What software dependencies are used? How are versions tracked and updated?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?dependency ?dependencyLabel ?version ?versioningActivity ?versioningDescription
WHERE {
  ?system a aidoc:AISystem .
  {
    ?system aidoc:hasSoftwareComponent ?dependency .
    OPTIONAL { ?dependency rdfs:label ?dependencyLabel . }
    OPTIONAL { ?dependency aidoc:version ?version . }
  } UNION {
    ?system aidoc:hasComponent ?component .
    ?component aidoc:dependsOn ?dependency .
    ?dependency a aidoc:SoftwareDependency .
    OPTIONAL { ?dependency rdfs:label ?dependencyLabel . }
    OPTIONAL { ?dependency aidoc:version ?version . }
  } UNION {
    ?versioningActivity a aidoc:SoftwareVersioning .
    OPTIONAL { ?versioningActivity dcterms:description ?versioningDescription . }
  } UNION {
    ?versioningActivity a aidoc:ModelVersioning .
    OPTIONAL { ?versioningActivity dcterms:description ?versioningDescription . }
  }
}
```

---

## Requirement 4: Deployment Forms

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-4`](https://certain-project.github.io/aidoc-ap/requirements#show-req-4) |
| **Description** | The description of all the forms in which the AI system is placed on the market or put into service, such as software packages embedded into hardware, downloads, or APIs. |
| **AI Lifecycle Stage** | Software Pipeline: Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(d) |

### CQ4.1: How is the AI system provided to users?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?modality ?modalityType ?deploymentActivity ?deploymentDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:modality ?modality . }
  OPTIONAL { ?system airo:hasModality ?modalityType . }
  OPTIONAL {
    ?system aidoc:hasLifecycleStage ?deploymentStage .
    ?deploymentStage a vair:Deployment .
    ?deploymentStage aidoc:hasAIActivity ?deploymentActivity .
    OPTIONAL { ?deploymentActivity dcterms:description ?deploymentDescription . }
  }
}
```

---

## Requirement 5: Hardware Required

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-5`](https://certain-project.github.io/aidoc-ap/requirements#show-req-5) |
| **Description** | The description of the hardware on which the AI system is intended to run. |
| **AI Lifecycle Stage** | Software Pipeline: Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(e) |

### CQ5.1: What hardware does the AI system need to run?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX server: <http://w3id.org/devops-infra/server#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?hardware ?hardwareType ?cpu ?memory ?numCPUs ?os
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:requiresHardware ?hardware .
  OPTIONAL { ?hardware a ?hardwareType . FILTER(?hardwareType != owl:NamedIndividual) }
  OPTIONAL { ?hardware server:cpu ?cpu . }
  OPTIONAL { ?hardware server:memory ?memory . }
  OPTIONAL { ?hardware server:numberCPUs ?numCPUs . }
  OPTIONAL { ?hardware server:operatingSystem ?os . }
}
```

---

## Requirement 6: Illustrations and Markings

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-6`](https://certain-project.github.io/aidoc-ap/requirements#show-req-6) |
| **Description** | Where the AI system is a component of products, photographs or illustrations showing external features, the marking and internal layout of those products. |
| **AI Lifecycle Stage** | Software Pipeline: Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(f) |

### CQ6.1: What is the physical form of the product?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?visualDoc ?depicts
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasVisualDocumentation ?visualDoc .
    ?visualDoc aidoc:depicts ?depicts .
    FILTER(CONTAINS(LCASE(?depicts), "physical") || CONTAINS(LCASE(?depicts), "form"))
  }
}
```

### CQ6.2: What visual documentation (photographs, diagrams) exists showing external features?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?visualDoc ?depicts ?docType
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasVisualDocumentation ?visualDoc .
    ?visualDoc a ?docType .
    OPTIONAL { ?visualDoc aidoc:depicts ?depicts . }
    FILTER(?docType != owl:NamedIndividual)
  }
}
```

### CQ6.3: What markings (CE, labels) are present on the product?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?visualDoc ?depicts
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasVisualDocumentation ?visualDoc .
    ?visualDoc aidoc:depicts ?depicts .
    FILTER(CONTAINS(LCASE(?depicts), "marking") || CONTAINS(LCASE(?depicts), "label") || CONTAINS(LCASE(?depicts), "ce"))
  }
}
```

### CQ6.4: How is the internal layout or component arrangement documented?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?visualDoc ?depicts
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasVisualDocumentation ?visualDoc .
    ?visualDoc aidoc:depicts ?depicts .
    FILTER(CONTAINS(LCASE(?depicts), "internal") || CONTAINS(LCASE(?depicts), "layout"))
  }
}
```

---

## Requirement 7: User Interface and Instructions for Use

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-7`](https://certain-project.github.io/aidoc-ap/requirements#show-req-7) |
| **Description** | A basic description of the user-interface provided to the deployer; instructions for use for the deployer, and a basic description of the user-interface provided to the deployer, where applicable. |
| **AI Lifecycle Stage** | Software Pipeline: Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 1(g) and 1(h) |

### CQ7.1: What interface is provided for operators or deployers?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?interface ?interfaceLabel ?interfaceDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?system aidoc:hasInterface ?interface .
    OPTIONAL { ?interface rdfs:label ?interfaceLabel . }
    OPTIONAL { ?interface dcterms:description ?interfaceDescription . }
  } UNION {
    ?system aidoc:hasSoftwareComponent ?interface .
    ?interface a aidoc:Interface .
    OPTIONAL { ?interface rdfs:label ?interfaceLabel . }
    OPTIONAL { ?interface dcterms:description ?interfaceDescription . }
  }
}
```

### CQ7.2: What instructions for use are provided to the deployer?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?intendedPurpose ?interface ?interfaceDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:intendedPurpose ?intendedPurpose . }
  OPTIONAL {
    ?system aidoc:hasInterface ?interface .
    ?interface dcterms:description ?interfaceDescription .
  }
}
```

---

## Requirement 8: Elements of System and Development Process

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-8`](https://certain-project.github.io/aidoc-ap/requirements#show-req-8) |
| **Description** | The methods and steps performed for the development of the AI system, including, where relevant, recourse to pre-trained systems or tools provided by third parties and how those were used, integrated or modified by the provider. |
| **AI Lifecycle Stage** | ML Pipeline: Model Engineering |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(a) |

### CQ8.1: What are the components and steps of development?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?developmentStage ?activity ?activityType ?activityDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasLifecycleStage ?developmentStage .
  ?developmentStage a vair:Development .
  ?developmentStage aidoc:hasAIActivity ?activity .
  ?activity a ?activityType .
  OPTIONAL { ?activity dcterms:description ?activityDescription . }
  FILTER(?activityType != owl:NamedIndividual)
}
ORDER BY ?activityType
```

---

## Requirement 9: Design Specifications of the System

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-9`](https://certain-project.github.io/aidoc-ap/requirements#show-req-9) |
| **Description** | The design specifications of the system, namely the general logic of the AI system and of the algorithms; the key design choices including the rationale and assumptions made, including with regard to persons or groups of persons in respect of who, the system is intended to be used; the main classification choices; what the system is designed to optimise for, and the relevance of the different parameters; the description of the expected output and output quality of the system; the decisions about any possible trade-off made regarding the technical solutions adopted to comply with the requirements set out in Chapter III, Section 2. |
| **AI Lifecycle Stage** | ML Pipeline: Model Engineering |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(b) |

### CQ9.1: What is the general logic of the AI system and of the algorithms?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?model ?method ?methodLabel ?methodDefinition
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasComponent ?model .
  ?model a aidoc:AIModel .
  ?model aidoc:usesAIMethod ?method .
  OPTIONAL { ?method rdfs:label ?methodLabel . }
  OPTIONAL { ?method skos:definition ?methodDefinition . }
}
```

### CQ9.2: What are the key design choices including the rationale and assumptions made?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?model ?method ?methodLabel ?component ?componentDescription ?technique
WHERE {
  ?system a aidoc:AISystem .
  ?system aidoc:hasComponent ?model .
  ?model a aidoc:AIModel .
  OPTIONAL { 
    ?model aidoc:usesAIMethod ?method .
    OPTIONAL { ?method rdfs:label ?methodLabel . }
  }
  OPTIONAL {
    ?model airo:hasComponent ?component .
    OPTIONAL { ?component dcterms:description ?componentDescription . }
    OPTIONAL { ?component airo:usesTechnique ?technique . }
  }
}
```

### CQ9.3: With regard to which persons or groups of persons is the system intended to be used?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?intendedPurpose ?purpose ?deployer
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:intendedPurpose ?intendedPurpose . }
  OPTIONAL { ?system airo:hasPurpose ?purpose . }
  OPTIONAL { ?system aidoc:isDeployedBy ?deployer . }
  OPTIONAL { ?system airo:isDeployedBy ?deployer . }
}
```

### CQ9.4: What are the main classification choices?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?model ?method ?methodLabel ?methodCategory ?categoryLabel
WHERE {
  ?system a aidoc:AISystem .
  ?system aidoc:hasComponent ?model .
  ?model a aidoc:AIModel .
  ?model aidoc:usesAIMethod ?method .
  OPTIONAL { ?method rdfs:label ?methodLabel . }
  OPTIONAL { 
    ?method a ?methodCategory .
    ?methodCategory rdfs:subClassOf* aidoc:AIMethodCategory .
    OPTIONAL { ?methodCategory rdfs:label ?categoryLabel . }
  }
}
```

### CQ9.5: What is the system designed to optimise for, and what is the relevance of the different parameters?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?purpose ?model ?hyperparameters ?hyperparamDescription ?technique
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system airo:hasPurpose ?purpose . }
  OPTIONAL {
    ?system aidoc:hasComponent ?model .
    ?model a aidoc:AIModel .
    ?model airo:hasComponent ?hyperparameters .
    OPTIONAL { ?hyperparameters dcterms:description ?hyperparamDescription . }
    OPTIONAL { ?hyperparameters airo:usesTechnique ?technique . }
  }
}
```

### CQ9.6: What is the description of the expected output and output quality of the system?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?method ?output ?outputDescription ?outputType
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasComponent ?model .
  ?model a aidoc:AIModel .
  ?model aidoc:usesAIMethod ?method .
  ?method airo:producesOutput ?output .
  OPTIONAL { ?output dcterms:description ?outputDescription . }
  OPTIONAL { ?output a ?outputType . FILTER(?outputType != owl:NamedIndividual) }
}
```

### CQ9.7: What decisions about any possible trade-off were made regarding the technical solutions adopted to comply with Chapter III, Section 2 requirements?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?standard ?riskControl ?riskControlDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:appliesStandard ?standard . }
  OPTIONAL { 
    ?system airo:hasRiskControl ?riskControl .
    OPTIONAL { ?riskControl dcterms:description ?riskControlDescription . }
  }
}
```

---

## Requirement 10: System Architecture

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-10`](https://certain-project.github.io/aidoc-ap/requirements#show-req-10) |
| **Description** | The description of the system architecture explaining how software components build on or feed into each other and integrate into the overall processing; the computational resources used to develop, train, test and validate the AI system. |
| **AI Lifecycle Stage** | ML Pipeline: Model Engineering |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(c) |

### CQ10.1: What is the architecture and what algorithms are used?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?architecture ?model ?method ?methodLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { ?system aidoc:hasArchitecture ?architecture . }
  OPTIONAL {
    ?system aidoc:hasComponent ?model .
    ?model a aidoc:AIModel .
    OPTIONAL { ?model aidoc:hasArchitecture ?architecture . }
    OPTIONAL {
      ?model aidoc:usesAIMethod ?method .
      OPTIONAL { ?method rdfs:label ?methodLabel . }
    }
  }
}
```

### CQ10.2: Which software components make up the system and how are they connected?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?component ?componentLabel ?componentDescription ?feedsInto ?feedsIntoLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasSoftwareComponent ?component .
  OPTIONAL { ?component rdfs:label ?componentLabel . }
  OPTIONAL { ?component dcterms:description ?componentDescription . }
  OPTIONAL { 
    ?component aidoc:feedsIntoComponent ?feedsInto .
    OPTIONAL { ?feedsInto rdfs:label ?feedsIntoLabel . }
  }
}
ORDER BY ?componentLabel
```

### CQ10.3: How do software components feed into each other and into the overall processing pipeline?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?sourceComponent ?sourceLabel ?targetComponent ?targetLabel ?dependency ?dependencyLabel
WHERE {
  {
    ?sourceComponent aidoc:feedsIntoComponent ?targetComponent .
    ?sourceComponent a aidoc:SoftwareComponent .
    OPTIONAL { ?sourceComponent rdfs:label ?sourceLabel . }
    OPTIONAL { ?targetComponent rdfs:label ?targetLabel . }
  } UNION {
    ?sourceComponent aidoc:dependsOn ?dependency .
    ?sourceComponent a aidoc:SoftwareComponent .
    OPTIONAL { ?sourceComponent rdfs:label ?sourceLabel . }
    OPTIONAL { ?dependency rdfs:label ?dependencyLabel . }
  }
}
```

### CQ10.4: Which computational resources are used for development, training, testing and validation?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX server: <http://w3id.org/devops-infra/server#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?hardware ?cpu ?memory ?numCPUs ?os ?componentUsingHW ?componentLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?system aidoc:requiresHardware ?hardware .
  } UNION {
    ?system aidoc:hasSoftwareComponent ?componentUsingHW .
    ?componentUsingHW aidoc:requiresHardware ?hardware .
    OPTIONAL { ?componentUsingHW rdfs:label ?componentLabel . }
  }
  OPTIONAL { ?hardware server:cpu ?cpu . }
  OPTIONAL { ?hardware server:memory ?memory . }
  OPTIONAL { ?hardware server:numberCPUs ?numCPUs . }
  OPTIONAL { ?hardware server:operatingSystem ?os . }
}
```

---

## Requirement 11: Data Requirements

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-11`](https://certain-project.github.io/aidoc-ap/requirements#show-req-11) |
| **Description** | Where relevant, the data requirements in terms of datasheets describing the training methodologies and techniques and the training data sets used, including a general description of these data sets, information about their provenance, scope and main characteristics; how the data was obtained and selected; labelling procedures (e.g. for supervised learning), data cleaning methodologies (e.g. outliers detection). |
| **AI Lifecycle Stage** | Data Pipeline: Exploration and Validation |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(d) |

### CQ11.1: What are the datasheets describing the training methodologies and techniques?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?datasheet ?datasheetType ?description
WHERE {
  {
    ?datasheet a aidoc:DataSheet .
    ?datasheet a ?datasheetType .
    OPTIONAL { ?datasheet dcterms:description ?description . }
    FILTER(?datasheetType != owl:NamedIndividual)
  } UNION {
    ?datasheet a aidoc:TrainingDataSheet .
    ?datasheet a ?datasheetType .
    OPTIONAL { ?datasheet dcterms:description ?description . }
    FILTER(?datasheetType != owl:NamedIndividual)
  }
}
```

### CQ11.2: What are the training data sets used, including their provenance, scope and main characteristics?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dpv: <https://w3id.org/dpv#>
PREFIX dqv: <http://www.w3.org/ns/dqv#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?dataset ?datasetLabel ?description ?dataSource ?dataSourceLabel ?characteristic ?scope ?qualityMeasurement
WHERE {
  ?trainingActivity a aidoc:DataTraining .
  ?trainingActivity aidoc:usesTrainingData ?dataset .
  OPTIONAL { ?dataset rdfs:label ?datasetLabel . }
  OPTIONAL { ?dataset dcterms:description ?description . }
  OPTIONAL { 
    ?dataset dpv:hasDataSource ?dataSource .
    OPTIONAL { ?dataSource rdfs:label ?dataSourceLabel . }
    OPTIONAL { ?dataSource dcterms:description ?dataSourceLabel . }
  }
  OPTIONAL { ?dataset aidoc:dataCharacteristic ?characteristic . }
  OPTIONAL { ?dataset aidoc:dataScope ?scope . }
  OPTIONAL { ?dataset dqv:hasQualityMeasurement ?qualityMeasurement . }
}
```

### CQ11.3: How was the data obtained and selected?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dpv: <https://w3id.org/dpv#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?dataset ?datasetLabel ?acquisitionActivity ?dataSource ?dataSourceDescription ?collectionMethod ?selectionCriteria
WHERE {
  {
    ?acquisitionActivity a aidoc:DataAcquisitionActivity .
    ?acquisitionActivity dpv:hasData ?dataset .
    OPTIONAL { ?dataset rdfs:label ?datasetLabel . }
    OPTIONAL { 
      ?dataset dpv:hasDataSource ?dataSource .
      OPTIONAL { ?dataSource dcterms:description ?dataSourceDescription . }
    }
  }
  OPTIONAL { ?dataset aidoc:dataCollectionMethod ?collectionMethod . }
  OPTIONAL { ?dataset aidoc:dataSelectionCriteria ?selectionCriteria . }
}
```

### CQ11.4: What are the labelling procedures?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?labelingProcedure ?annotatorType ?annotationTool ?labelingGuideline ?description
WHERE {
  ?labelingProcedure a aidoc:LabelingProcedure .
  OPTIONAL { ?labelingProcedure aidoc:annotatorType ?annotatorType . }
  OPTIONAL { ?labelingProcedure aidoc:annotationTool ?annotationTool . }
  OPTIONAL { ?labelingProcedure aidoc:labelingGuideline ?labelingGuideline . }
  OPTIONAL { ?labelingProcedure dcterms:description ?description . }
}
```

### CQ11.5: What are the data cleaning methodologies?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?cleaningProcedure ?description ?outlierMethod ?missingDataStrategy ?qualityMetrics
WHERE {
  ?cleaningProcedure a aidoc:DataCleaningProcedure .
  OPTIONAL { ?cleaningProcedure dcterms:description ?description . }
  OPTIONAL { ?cleaningProcedure aidoc:outlierHandlingMethod ?outlierMethod . }
  OPTIONAL { ?cleaningProcedure aidoc:missingDataStrategy ?missingDataStrategy . }
  OPTIONAL { ?cleaningProcedure aidoc:qualityMetricsUsed ?qualityMetrics . }
}
```

---

## Requirement 12: Assessment of Human Oversight Measures

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-12`](https://certain-project.github.io/aidoc-ap/requirements#show-req-12) |
| **Description** | Assessment of the human oversight measures needed in accordance with Article 14, including an assessment of the technical measures needed to facilitate the interpretation of the outputs of AI systems by the deployers, in accordance with Article 13(3), point (d). |
| **AI Lifecycle Stage** | ML Pipeline: Model Evaluation |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(e) |

### CQ12.1: What human oversight measures are needed in accordance with Article 14?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?oversightMechanism ?mechanismLabel ?description
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasHumanOversight ?oversightMechanism .
  OPTIONAL { ?oversightMechanism rdfs:label ?mechanismLabel . }
  OPTIONAL { ?oversightMechanism dcterms:description ?description . }
}
```

### CQ12.2: What technical measures are needed to facilitate the interpretation of the outputs by deployers?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?transparencyMeasure ?measureLabel ?description ?explainableFeature
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?system aidoc:hasTransparencyMeasure ?transparencyMeasure .
    OPTIONAL { ?transparencyMeasure rdfs:label ?measureLabel . }
    OPTIONAL { ?transparencyMeasure dcterms:description ?description . }
  } UNION {
    ?explainableFeature a aidoc:ExplainableAIFeature .
    OPTIONAL { ?explainableFeature rdfs:label ?measureLabel . }
    OPTIONAL { ?explainableFeature dcterms:description ?description . }
  }
}
```

---

## Requirement 13: Pre-determined Changes to the AI System

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-13`](https://certain-project.github.io/aidoc-ap/requirements#show-req-13) |
| **Description** | Where applicable, a detailed description of pre-determined changes to the AI system and its performance, together with all the relevant information related to the technical solutions adopted to ensure continuous compliance of the AI system with the relevant requirements set out in Chapter III, Section 2. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(f) |

### CQ13.1: What are the pre-determined changes to the AI system and its performance?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?changeLog ?changeRecord ?changeDescription ?reason ?startDate ?endDate ?change
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?changeLog a aidoc:ChangeLog .
    ?changeLog aidoc:hasChangeRecord ?changeRecord .
    OPTIONAL { ?changeRecord dcterms:description ?changeDescription . }
    OPTIONAL { ?changeRecord aidoc:reasonForChange ?reason . }
    OPTIONAL { ?changeRecord aidoc:startDate ?startDate . }
    OPTIONAL { ?changeRecord aidoc:endDate ?endDate . }
    OPTIONAL { ?changeRecord aidoc:recordsChange ?change . }
  }
}
```

### CQ13.2: What technical solutions are adopted to ensure continuous compliance?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?standard ?standardType ?riskControl ?controlDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL { 
    ?system aidoc:appliesStandard ?standard .
    OPTIONAL { ?standard a ?standardType . FILTER(?standardType != owl:NamedIndividual) }
  }
  OPTIONAL {
    ?system airo:hasRiskControl ?riskControl .
    OPTIONAL { ?riskControl dcterms:description ?controlDescription . }
  }
}
```

---

## Requirement 14: Validation and Testing Procedures

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-14`](https://certain-project.github.io/aidoc-ap/requirements#show-req-14) |
| **Description** | The validation and testing procedures used, including information about the validation and testing data used and their main characteristics; metrics used to measure accuracy, robustness and compliance with other relevant requirements set out in Chapter III, Section 2, as well as potentially discriminatory impacts; test logs and all test reports dated and signed by the responsible persons, including with regard to predetermined changes as referred to under point (f). |
| **AI Lifecycle Stage** | ML Pipeline: Model Evaluation |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(g) |

### CQ14.1: What validation and testing procedures are used?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?activity ?activityType ?description
WHERE {
  {
    ?activity a aidoc:DataValidation .
    ?activity a ?activityType .
    OPTIONAL { ?activity dcterms:description ?description . }
  } UNION {
    ?activity a aidoc:DataTesting .
    ?activity a ?activityType .
    OPTIONAL { ?activity dcterms:description ?description . }
  } UNION {
    ?activity a aidoc:ModelEvaluation .
    ?activity a ?activityType .
    OPTIONAL { ?activity dcterms:description ?description . }
  }
  FILTER(?activityType != owl:NamedIndividual)
}
```

### CQ14.2: What are the validation and testing data used and their main characteristics?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dqv: <http://www.w3.org/ns/dqv#>
PREFIX dpv: <https://w3id.org/dpv#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?activity ?activityType ?dataset ?datasetLabel ?description ?characteristic ?qualityMeasurement ?dataSource
WHERE {
  {
    ?activity a aidoc:DataValidation .
    ?activity aidoc:usesValidationData ?dataset .
    ?activity a ?activityType .
  } UNION {
    ?activity a aidoc:DataTesting .
    ?activity aidoc:usesTestData ?dataset .
    ?activity a ?activityType .
  }
  OPTIONAL { ?dataset rdfs:label ?datasetLabel . }
  OPTIONAL { ?dataset dcterms:description ?description . }
  OPTIONAL { ?dataset aidoc:dataCharacteristic ?characteristic . }
  OPTIONAL { ?dataset dqv:hasQualityMeasurement ?qualityMeasurement . }
  OPTIONAL { ?dataset dpv:hasDataSource ?dataSource . }
  FILTER(?activityType != owl:NamedIndividual)
}
```

### CQ14.3: What metrics are used to measure accuracy, robustness and compliance, as well as potentially discriminatory impacts?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dqv: <http://www.w3.org/ns/dqv#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?evaluation ?metric ?metricLabel ?metricType ?evaluationMethod
WHERE {
  ?evaluation a aidoc:ModelEvaluation .
  ?evaluation aidoc:hasPerformanceMetric ?metric .
  OPTIONAL { ?metric rdfs:label ?metricLabel . }
  OPTIONAL { ?metric a ?metricType . FILTER(?metricType != owl:NamedIndividual) }
  OPTIONAL { ?evaluation aidoc:evaluationMethod ?evaluationMethod . }
}
```

### CQ14.4: Are test logs and test reports available, dated and signed by responsible persons?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?monitoringActivity ?logsActivity ?logStorage ?logStorageLabel ?description
WHERE {
  ?monitoringActivity a aidoc:DataMonitoringAndLogging .
  OPTIONAL { ?monitoringActivity aidoc:logsActivity ?logsActivity . }
  OPTIONAL { 
    ?monitoringActivity aidoc:storesLogsAt ?logStorage .
    OPTIONAL { ?logStorage rdfs:label ?logStorageLabel . }
  }
  OPTIONAL { ?monitoringActivity dcterms:description ?description . }
}
```

---

## Requirement 15: Cybersecurity Measures

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-15`](https://certain-project.github.io/aidoc-ap/requirements#show-req-15) |
| **Description** | Cybersecurity measures put in place. |
| **AI Lifecycle Stage** | Software Pipeline: Build and Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 2(h) |

### CQ15.1: What cybersecurity measures are put in place?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?securityMeasure ?measureLabel ?measureDescription ?mitigatesRisk
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?securityMeasure a vair:SecurityMeasure .
    OPTIONAL { ?securityMeasure rdfs:label ?measureLabel . }
    OPTIONAL { ?securityMeasure dcterms:description ?measureDescription . }
    OPTIONAL { ?securityMeasure airo:modifiesRiskConcept ?mitigatesRisk . }
  } UNION {
    ?system airo:hasRiskControl ?securityMeasure .
    OPTIONAL { ?securityMeasure rdfs:label ?measureLabel . }
    OPTIONAL { ?securityMeasure dcterms:description ?measureDescription . }
  }
}
```

---

## Requirement 16: Monitoring, Functioning and Control

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-16`](https://certain-project.github.io/aidoc-ap/requirements#show-req-16) |
| **Description** | Detailed information about the monitoring, functioning and control of the AI system, in particular with regard to: its capabilities and limitations in performance, including the degrees of accuracy for specific persons or groups of persons on which the system is intended to be used and the overall expected level of accuracy in relation to its intended purpose; the foreseeable unintended outcomes and sources of risks to health and safety, fundamental rights and discrimination in view of the intended purpose of the AI system; the human oversight measures needed in accordance with Article 14, including the technical measures put in place to facilitate the interpretation of the outputs of AI systems by the deployers; specifications on input data, as appropriate. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 3 |

### CQ16.1: What are the capabilities and limitations in performance, including degrees of accuracy for specific persons or groups?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?capability ?capabilityLabel ?capabilityDefinition ?evaluation ?metric ?metricLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasCapability ?capability .
    OPTIONAL { ?capability rdfs:label ?capabilityLabel . }
    OPTIONAL { ?capability skos:definition ?capabilityDefinition . }
  }
  OPTIONAL {
    ?evaluation a aidoc:ModelEvaluation .
    ?evaluation aidoc:hasPerformanceMetric ?metric .
    OPTIONAL { ?metric rdfs:label ?metricLabel . }
  }
}
```

### CQ16.2: What are the foreseeable unintended outcomes and sources of risks to health and safety, fundamental rights and discrimination?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?risk ?riskDescription ?riskSource ?consequence
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasRisk ?risk .
  OPTIONAL { ?risk dcterms:description ?riskDescription . }
  OPTIONAL { ?riskSource airo:isRiskSourceFor ?risk . }
  OPTIONAL { ?risk airo:hasConsequence ?consequence . }
}
```

### CQ16.3: What human oversight measures and technical measures for output interpretation are needed?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?oversightMechanism ?mechanismLabel ?transparencyMeasure ?measureDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasHumanOversight ?oversightMechanism .
    OPTIONAL { ?oversightMechanism rdfs:label ?mechanismLabel . }
  }
  OPTIONAL {
    ?system aidoc:hasTransparencyMeasure ?transparencyMeasure .
    OPTIONAL { ?transparencyMeasure dcterms:description ?measureDescription . }
  }
}
```

---

## Requirement 17: Appropriateness of Performance Metrics

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-17`](https://certain-project.github.io/aidoc-ap/requirements#show-req-17) |
| **Description** | A description of the appropriateness of the performance metrics for the specific AI system. |
| **AI Lifecycle Stage** | ML Pipeline: Model Evaluation |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 4 |

### CQ17.1: What is the description of the appropriateness of the performance metrics for the specific AI system?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX dqv: <http://www.w3.org/ns/dqv#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?evaluation ?metric ?metricLabel ?metricDescription ?evaluationMethod
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?evaluation a aidoc:ModelEvaluation .
  ?evaluation aidoc:hasPerformanceMetric ?metric .
  OPTIONAL { ?metric rdfs:label ?metricLabel . }
  OPTIONAL { ?metric dcterms:description ?metricDescription . }
  OPTIONAL { ?evaluation aidoc:evaluationMethod ?evaluationMethod . }
}
```

---

## Requirement 18: Risk Management

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-18`](https://certain-project.github.io/aidoc-ap/requirements#show-req-18) |
| **Description** | A detailed description of the risk management system in accordance with Article 9. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 5 |

### CQ18.1: What is the detailed description of the risk management system in accordance with Article 9?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?risk ?riskDescription ?riskSource ?riskSourceDescription ?riskControl ?controlDescription ?consequence
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?system aidoc:hasRisk ?risk .
    OPTIONAL { ?risk dcterms:description ?riskDescription . }
    OPTIONAL { 
      ?riskSource airo:isRiskSourceFor ?risk .
      OPTIONAL { ?riskSource dcterms:description ?riskSourceDescription . }
    }
    OPTIONAL { ?risk airo:hasConsequence ?consequence . }
  }
  OPTIONAL {
    ?system airo:hasRiskControl ?riskControl .
    OPTIONAL { ?riskControl dcterms:description ?controlDescription . }
  }
}
```

---

## Requirement 19: Changes to the AI System Throughout Its Lifecycle

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-19`](https://certain-project.github.io/aidoc-ap/requirements#show-req-19) |
| **Description** | A description of relevant changes made by the provider to the system through its lifecycle. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 6 |

### CQ19.1: What changes have been made to the system through its lifecycle?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?changeLog ?changeRecord ?change ?changeDescription ?reason ?stakeholder ?startDate ?endDate
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?changeLog a aidoc:ChangeLog .
    ?changeLog aidoc:hasChangeRecord ?changeRecord .
    OPTIONAL { ?changeRecord aidoc:recordsChange ?change . }
    OPTIONAL { ?changeRecord dcterms:description ?changeDescription . }
    OPTIONAL { ?changeRecord aidoc:reasonForChange ?reason . }
    OPTIONAL { ?changeRecord aidoc:hasStakeholder ?stakeholder . }
    OPTIONAL { ?changeRecord aidoc:startDate ?startDate . }
    OPTIONAL { ?changeRecord aidoc:endDate ?endDate . }
  } UNION {
    ?change a airo:Change .
    ?change airo:hasChangedEntity ?system .
    OPTIONAL { ?change dcterms:description ?changeDescription . }
  }
}
```

---

## Requirement 20: Harmonised Standards and Common Specifications

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-20`](https://certain-project.github.io/aidoc-ap/requirements#show-req-20) |
| **Description** | List of the harmonised standards applied in full or in part the references of which have been published in the Official Journal of the European Union; where no such harmonised standards have been applied, a detailed description of the solutions adopted to meet the requirements set out in Chapter III, Section 2, including a list of other relevant standards and technical specifications applied. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 7 |

### CQ20.1: What harmonised standards have been applied in full or in part?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?standard ?standardType ?standardLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:appliesStandard ?standard .
  OPTIONAL { ?standard a ?standardType . FILTER(?standardType != owl:NamedIndividual) }
  OPTIONAL { ?standard rdfs:label ?standardLabel . }
}
```

### CQ20.2: If no harmonised standards are applied, what solutions are adopted to meet Chapter III, Section 2 requirements?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX airo: <https://w3id.org/airo#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?riskControl ?controlDescription ?securityMeasure ?measureDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  FILTER NOT EXISTS { ?system aidoc:appliesStandard ?anyStandard . }
  OPTIONAL {
    ?system airo:hasRiskControl ?riskControl .
    OPTIONAL { ?riskControl dcterms:description ?controlDescription . }
  }
  OPTIONAL {
    ?securityMeasure a vair:SecurityMeasure .
    OPTIONAL { ?securityMeasure dcterms:description ?measureDescription . }
  }
}
```

---

## Requirement 21: EU Declaration of Conformity

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-21`](https://certain-project.github.io/aidoc-ap/requirements#show-req-21) |
| **Description** | A copy of the EU declaration of conformity referred to in Article 47. |
| **AI Lifecycle Stage** | Cross-cutting / All Pipelines |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 8 |

### CQ21.1: Is there a copy of the EU declaration of conformity?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?declaration ?declarationType ?declarationLabel
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  OPTIONAL {
    ?system aidoc:hasDeclarationOfConformity ?declaration .
    OPTIONAL { ?declaration a ?declarationType . FILTER(?declarationType != owl:NamedIndividual) }
    OPTIONAL { ?declaration rdfs:label ?declarationLabel . }
  }
}
```

---

## Requirement 22: Post-market Monitoring System

| Property | Value |
|----------|-------|
| **URI** | [`https://w3id.org/aidoc-ap/requirements#show-req-22`](https://certain-project.github.io/aidoc-ap/requirements#show-req-22) |
| **Description** | A detailed description of the system in place to evaluate the AI system performance in the post-market phase in accordance with Article 72, including the post-market monitoring plan referred to in Article 72(3). |
| **AI Lifecycle Stage** | Software Pipeline: Deployment |
| **Source** | EU AI Act 2024/1689, Annex IV, Section 9 |

### CQ22.1: What system is established to evaluate the AI system performance in the post-market phase?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?operationStage ?monitoringActivity ?activityDescription ?logsActivity ?logStorage
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  ?system aidoc:hasLifecycleStage ?operationStage .
  ?operationStage a vair:Operation .
  ?operationStage aidoc:hasAIActivity ?monitoringActivity .
  OPTIONAL { ?monitoringActivity dcterms:description ?activityDescription . }
  OPTIONAL { ?monitoringActivity aidoc:logsActivity ?logsActivity . }
  OPTIONAL { ?monitoringActivity aidoc:storesLogsAt ?logStorage . }
}
```

### CQ22.2: Is there a post-market monitoring plan as referred to in Article 72(3)?

```sparql
PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX vair: <https://w3id.org/vair#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?system ?systemLabel ?postMarketActivity ?activityType ?activityDescription
WHERE {
  ?system a aidoc:AISystem .
  OPTIONAL { ?system rdfs:label ?systemLabel . }
  {
    ?postMarketActivity a aidoc:PostMarketMonitoringActivity .
    ?postMarketActivity a ?activityType .
    OPTIONAL { ?postMarketActivity dcterms:description ?activityDescription . }
  } UNION {
    ?postMarketActivity a aidoc:PostMarketPerformanceEvaluationActivity .
    ?postMarketActivity a ?activityType .
    OPTIONAL { ?postMarketActivity dcterms:description ?activityDescription . }
  } UNION {
    ?system aidoc:hasLifecycleStage ?operationStage .
    ?operationStage a vair:Operation .
    ?operationStage aidoc:hasAIActivity ?postMarketActivity .
    ?postMarketActivity a ?activityType .
    OPTIONAL { ?postMarketActivity dcterms:description ?activityDescription . }
  }
  FILTER(?activityType != owl:NamedIndividual)
}
```

---

## Summary

This document provides **50 SPARQL queries** covering all **22 requirements** and their **50 competency questions** from EU AI Act Annex IV. Each query is designed to extract the relevant information from knowledge graphs that follow the AIDOC-AP ontology structure.

The queries can be executed against any RDF triplestore that contains data conforming to the AIDOC-AP ontology schema.
