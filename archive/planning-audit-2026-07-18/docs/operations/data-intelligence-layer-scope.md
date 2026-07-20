# Data Intelligence Layer: Scope & Implementation Roadmap

## Executive Summary

The Data Intelligence Layer is the critical bridge between the Value Fabric platform's reasoning capabilities and the proprietary data required to execute them at runtime. While the current architecture (Layers 1-6) successfully orchestrates signal detection, value quantification, and narrative generation, it currently operates on a "bring your own data" model. 

This project transforms the platform from a reasoning engine into a proactive intelligence engine by building the pipelines, models, and integrations necessary to automatically enrich accounts, map product capabilities, and calibrate value formulas using real-world evidence.

Based on a comprehensive audit of the existing `Fabric_4L` codebase, significant foundational infrastructure is already in place. Layer 1 possesses robust crawling and extraction capabilities, Layer 3 provides a mature knowledge graph with vector search, and Layer 4 contains the necessary agent orchestration. This revised scope focuses exclusively on closing the remaining data gaps by leveraging and extending this existing foundation.

## Current State vs. Target State (Gap Analysis)

The following table summarizes the current state of the platform against the seven critical data gaps identified in the requirements, detailing what has already been built and what remains to be developed.

| Intelligence Area | Current State (Already Built) | Target State (To Be Built) |
|-------------------|-------------------------------|----------------------------|
| **Account Intelligence** | CRM sync (Salesforce/HubSpot), Account data model, L1 web crawlers (HTTPX/Playwright). | Automated enrichment pipelines for financials (SEC filings), tech stack detection, executive leadership mapping, and hiring velocity signals. |
| **Product Portfolio** | Value Packs reference capabilities; L3 graph infrastructure exists. | A formal Product model in the knowledge graph, mapping specific products to capabilities and enabling signal-to-product matching. |
| **Evidence Library** | L3 vector similarity search (`evidence_search.py`). | Structured ingestion pipeline for case studies, including outcomes, industries, and personas, populated with 20-50 initial records. |
| **Value Tree Templates** | L3 value tree API routes and L4 formula governance. | Pre-built starter trees (3-5 per pack) that can be instantiated dynamically based on the Effective Pack Context. |
| **CRM Integration** | Bi-directional sync, `GetProspectDataTool`, `FetchInteractionHistoryTool`. | Advanced whitespace analysis, competitive penetration tracking, and purchase history aggregation. |
| **Formula Calibration** | Formula versioning, approval workflows, and signal quantification. | Automated calibration pipeline that updates formula coefficients based on realization data segmented by size and region. |
| **Peer Benchmarks** | L6 benchmark dataset model with statistical profiles (p10-p90). | Integration with licensed industry datasets and an automated benchmark refresh pipeline. |

## Implementation Roadmap

The implementation is structured into three sequential phases, prioritizing foundational data models and enrichment pipelines before advancing to complex calibration and competitive analysis.

### Phase 1: Foundation & Enrichment (Weeks 1-3)

This phase establishes the core data models and automated enrichment pipelines required to populate the knowledge graph with actionable intelligence.

**1.1 Product Portfolio Graph Integration**
The system currently lacks a formal representation of the products being sold. We will introduce a `Product` node in the Layer 3 Neo4j graph, establishing relationships such as `(Product)-[:ENABLES]->(Capability)` and `(Signal)-[:INDICATES_NEED_FOR]->(Product)`. This enables the `SignalDetectionAgent` to recommend specific products based on extracted pain points.

**1.2 Account Intelligence Pipeline**
Leveraging the existing Layer 1 Celery pipeline and Playwright crawlers, we will build specialized enrichment tasks. This includes an SEC EDGAR adapter for financial baselines, a job board scraper for hiring velocity, and a tech stack detection module. These tasks will automatically enrich the `Account` model in Layer 4 upon creation or periodic sync.

**1.3 Evidence Library Ingestion**
We will extend the Layer 1 ingestion pipeline to process unstructured case studies. Using the Layer 2 LLM extractor, the system will parse case studies into structured `EvidenceArtifact` records, capturing specific outcomes, metrics, and personas. These will be indexed in Layer 3 for use by the `EvidenceSearchService`.

### Phase 2: Contextualization & Templates (Weeks 4-5)

With the data foundation in place, this phase focuses on accelerating the business case generation process through templates and advanced CRM insights.

**2.1 Value Tree Template Engine**
We will develop a template engine within Layer 3 that stores 3-5 pre-configured value trees for each of the 30 Value Packs. When an account is analyzed, the system will resolve the Effective Pack Context and instantiate the appropriate template, significantly reducing the time required for the `FinancialModelingAgent` to construct a business case from scratch.

**2.2 Advanced CRM Whitespace Analysis**
We will enhance the `crm_sync_service.py` to aggregate purchase history and perform whitespace analysis. By comparing an account's current product footprint against the newly created Product Portfolio graph, the system will identify cross-sell and up-sell opportunities, flagging them as `OpportunityHypothesis` records for the `OpportunityFinder` agent.

### Phase 3: Calibration & Benchmarking (Weeks 6-8)

The final phase introduces continuous learning and external validation, ensuring the platform's financial models remain accurate and defensible.

**3.1 Formula Calibration Loop**
We will implement a feedback loop within the `FormulaGovernanceService`. As realized ROI data is captured (either manually or via CRM closed-won data), the system will analyze the variance between estimated and actual impact. It will then propose updated coefficients for specific segments (e.g., Enterprise vs. Mid-Market), requiring human approval before activation.

**3.2 Licensed Benchmark Integration**
We will expand the Layer 6 Benchmark service to ingest data from external licensed providers via API. This includes mapping external taxonomies to the internal Value Pack taxonomies and implementing a scheduled refresh pipeline to ensure the statistical profiles (p10-p90) remain current.

## Technical Architecture Updates

To support the Data Intelligence Layer, the following architectural enhancements are required:

- **Layer 1 (Ingestion):** Addition of specialized adapters for SEC filings, job boards, and licensed benchmark APIs.
- **Layer 3 (Knowledge Graph):** Schema updates to support `Product`, `Capability`, and `ValueTreeTemplate` nodes.
- **Layer 4 (Agents):** Enhancement of the `AccountService` to handle asynchronous enrichment webhooks and the creation of a `CalibrationService` to manage formula coefficient updates.

## Conclusion

The Data Intelligence Layer project transitions Value Fabric from a static reasoning framework to a dynamic, data-rich intelligence platform. By systematically closing the identified data gaps, the system will be capable of generating highly accurate, context-aware, and defensible business cases with minimal manual intervention.
