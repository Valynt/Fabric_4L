# Discrete Manufacturing Vertical Subpack

**ID:** `discrete-manufacturing-v1`  
**Parent Master:** `manufacturing-master-v1`  
**Version:** 1.0.0  
**Domain:** Industry  
**Vertical Focus:** Automotive/EV, Aerospace & Defense, Industrial Equipment, Electronics & Semiconductors, Medical Devices, Heavy Machinery, Robotics & Automation Equipment, Rail/Marine/Transportation Equipment

---

## 1. Overview

This subpack adds vertical-specialized intelligence for Discrete Manufacturing to the Manufacturing Master Pack. It is designed to be read as an **additive layer**—all foundational frameworks (value drivers, base personas, evidence taxonomy, formulas, signal rules, benchmarks, governance) are inherited from the master and are not duplicated here. This document contains **only the discrete-manufacturing-specific additions**.

---

## 2. Inheritance Manifest

### Inherited from Master (Read-Only Reference)
- Value Driver Framework (base taxonomy: revenue uplift, cost savings, risk reduction, working capital)
- Base Persona Archetypes (Plant Manager, Quality Manager, Operations Manager, Supply Chain Manager, CFO, HR Manager)
- Evidence Source Types (public, paid, proprietary, regulatory)
- Formula Templates (investment framework, NPV, IRR, payback)
- Signal Source Taxonomy (public signals, paid signals, proprietary signals)
- Benchmark Methodology (industry report, survey, regulatory, industry association)
- Governance Framework (confidence levels, source coverage, approval process)
- Base KPIs (OEE, Scrap Rate, DPMO, COPQ, FPY, Schedule Attainment, Changeover Time, Mfg Lead Time, Que Time, NPI Cycle Time, Uptime, Labor Productivity, Warranty Cost, Supplier PPM, Supplier OTD, Expedite Cost, Audit Findings, CAPA Cycle Time, CO2 Intensity, Water Usage)
- Base Value Formulas (OEE to Margin, Scrap Reduction, Downtime Reduction, Labor Productivity, Quality Yield Improvement, NPI Acceleration, Working Capital, Regulatory Cost Avoidance)
- Base Signal Rules (12 foundational rules)
- Objection Pattern Framework
- Discovery Question Framework

### Created by Subpack (Vertical-Specialized)
- 18 Vertical Pains
- 25 Vertical KPIs
- 20 Vertical Signal Rules
- 6 NEW Vertical Personas
- 15 Vertical Formulas
- 20 Vertical Benchmarks
- 12 Vertical Regulatory Factors
- 15 Vertical Technology Systems
- 20 Vertical Discovery Questions
- 10 Vertical Objection Patterns
- 15 Vertical Buying Triggers
- 3 Worked Signal→Hypothesis Examples
- 5 Vertical Evidence Sources
- 5 Competitor Factor Profiles

### Overridden Components (with Justification)
| Component | Override Reason |
|-----------|----------------|
| KPI: Scrap Rate segmentation | Extended from generic scrap rate to discrete-specific scrap categories: casting scrap, welding reject, SMT DPMO, sheet metal first article, AM build failure. Master scrap rate remains as aggregate. |
| Persona: Plant Manager | Enhanced with discrete manufacturing specific pressures (NPI deadline compression, mixed-model complexity, customer SCAR volume) and trusted evidence specific to plant-level discrete KPIs. |
| Value Driver: Quality Yield Improvement | Extended with discrete-specific yield categories: SMT first pass, sheet metal first article, welding first pass, battery pack assembly yield. |
| Signal Rule: Machine downtime trend | Replaced with more granular discrete signal: CNC spindle load anomaly (tool wear) and robot collision log growth. Machine downtime remains in master as generic rule. |

### Vertical Persona Additions
1. **MRO Manager** — Focused on predictive maintenance, spare parts optimization, and asset life extension
2. **Production Scheduler** — Focused on finite capacity planning, takt time attainment, and mixed-model sequencing
3. **Quality Engineer** — Focused on SPC, CAPA effectiveness, audit readiness, and customer SCAR response
4. **Plant Manager** — Enhanced with discrete manufacturing pressures (NPI, SCARs, capital replacement)
5. **Design Engineer** — Focused on DFM, digital thread integrity, and CAM programming efficiency
6. **Warranty Analyst** — Focused on field failure prediction, warranty cost per unit, and recall risk assessment

### Vertical KPI Extensions
Torque Cpk, BOM Accuracy, CMM Utilization, First Article Pass Rate, SMT DPMO, Weld Reject Rate, Kitting Accuracy, Robot Cell OEE, Casting Scrap Rate, Coating Thickness Cpk, ECO Cycle Time, CAM Programming Time, Line Balance Efficiency, Nadcap Findings, EV Battery Pack Failure Rate, AM Build Success Rate, Sheet Metal First Pass Rate, Tool Condition Index, Component Traceability, V&V Cycle Time, Sequence Compliance, NDT Findings, Particulate Count, Press Brake Setup Time, Firmware Flash Success Rate.

---

## 3. Vertical Pains (18)

### DM-P001: Warranty Claim Spike from Fastener Torque Inconsistency
Inconsistent torque application during assembly leading to field failures, warranty claims, and potential recall risk in high-vibration environments.
- **Symptoms:** Warranty claims clustering around fastening-related failures; torque audit pass rate <95%; field service reports citing "loose bolt" or "separation"; no statistical process control on torque tools; tool calibration drift >2% between checks
- **Segments:** Automotive/EV, Heavy Machinery, Rail/Marine
- **Linked KPIs:** kpi-torque-cpk, kpi-warranty-cost, kpi-field-failure-rate
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** Warranty Week 2024, AIAG CQI-9

### DM-P002: BOM Explosion and Revision Chaos
Engineering change orders creating BOM version mismatches between design, planning, and shop floor systems causing wrong parts procurement and assembly errors.
- **Symptoms:** BOM versions differ across ERP, PLM, and MES; ECO cycle time >5 days; wrong-part assembly incidents >1/month; purchasing orders against obsolete revisions; no single source of BOM truth
- **Segments:** Automotive/EV, Electronics, Aerospace, Medical Devices
- **Linked KPIs:** kpi-eco-rate, kpi-scrap-rate, kpi-fpy
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** Siemens PLM Survey 2024, Deloitte Engineering Operations Study

### DM-P003: CNC Machine Tool Wear and Dimensional Drift
Progressive tool wear in machining operations causing dimensional variation, increased inspection burden, and scrap before adjustment.
- **Symptoms:** CMM measurement drift trend correlating to tool life; in-process inspection rejects increasing over tool life; tool changes based on time not condition; surface finish degradation before nominal size violation; no tool condition monitoring system
- **Segments:** Aerospace, Medical Devices, Industrial Equipment
- **Linked KPIs:** kpi-scrap-rate, kpi-dpmo, kpi-copq
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** Sandvik Coromant Tool Life Study, ASME Manufacturing Review

### DM-P004: Assembly Line Balancing and Takt Time Misses
Mixed-model assembly lines unable to maintain takt time due to station overload, operator variability, and sequencing complexity.
- **Symptoms:** Cycle time variation >15% station-to-station; line stop for station overload >3x/shift; WIP accumulation at specific stations; overtime required to meet daily build target; no dynamic line rebalancing capability
- **Segments:** Automotive/EV, Electronics, Appliances
- **Linked KPIs:** kpi-oee, kpi-throughput, kpi-labor-prod
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** Toyota Production System Benchmarks, Automotive News Assembly Plant Survey

### DM-P005: Welding Quality Variation and Porosity
Inconsistent weld quality in fabrication operations causing structural failures, rework, and customer rejection in safety-critical applications.
- **Symptoms:** Weld reject rate >3% on critical joints; X-ray/UT inspection findings increasing; welder-to-welder quality variation >2 sigma; weld parameter settings not monitored; no weld data logging or traceability
- **Segments:** Heavy Machinery, Rail/Marine, Automotive/EV, Aerospace
- **Linked KPIs:** kpi-fpy, kpi-scrap-rate, kpi-copq
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** AWS Welding Journal, DVS German Welding Society

### DM-P006: Surface Coating and Finish Defects
Paint, powder coat, anodize, or plating defects causing cosmetic rejects, environmental compliance issues, and customer returns.
- **Symptoms:** Coating reject rate >5% on cosmetic surfaces; color matching complaints; overspray or drip marks requiring touch-up; environmental permit violations related to VOCs; no real-time coating thickness monitoring
- **Segments:** Automotive/EV, Industrial Equipment, Appliances
- **Linked KPIs:** kpi-fpy, kpi-copq, kpi-scrap-rate
- **Prevalence:** MEDIUM | **Confidence:** HIGH | **Sources:** PCI Powder Coating Institute, EPA NESHAP Compliance Data

### DM-P007: Electronics SMT Placement Accuracy and Solder Defects
Surface mount technology placement errors and solder joint defects causing board failures, rework, and reliability issues.
- **Symptoms:** SMT placement accuracy >50 microns off; solder defect rate (voids, bridging) >2%; AOI false positive rate >10%; reflow profile not monitored per board; component traceability gaps
- **Segments:** Electronics & Semiconductors, Medical Devices, Automotive/EV
- **Linked KPIs:** kpi-dpmo, kpi-scrap-rate, kpi-copq
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** IPC-A-610 Industry Data, SMTA Process Survey

### DM-P008: GD&T and Dimensional Measurement Bottleneck
Coordinate Measuring Machine (CMM) and inspection backlog creating production queue delays and delayed quality release.
- **Symptoms:** CMM queue time >20% of total lead time; first article inspection cycle >3 days; inspection staff overtime >20%; manual CMM programming consuming engineering time; no automated in-process metrology
- **Segments:** Aerospace, Medical Devices, Automotive/EV, Industrial Equipment
- **Linked KPIs:** kpi-que-time, kpi-mfg-lead-time, kpi-copq
- **Prevalence:** MEDIUM | **Confidence:** HIGH | **Sources:** NIST MEP Metrology Survey, ASME GD&T Industry Practice

### DM-P009: Casting and Forging Defects (Porosity, Shrinkage, Cracks)
Foundry and forge process variation causing internal defects requiring scrap, rework, or downstream machining complications.
- **Symptoms:** Scrap rate >8% in casting operations; X-ray inspection revealing porosity clusters; machining chatter from hard spots; no real-time solidification modeling; die/tool wear not tracked to part quality
- **Segments:** Heavy Machinery, Automotive/EV, Industrial Equipment
- **Linked KPIs:** kpi-scrap-rate, kpi-copq, kpi-dpmo
- **Prevalence:** MEDIUM | **Confidence:** HIGH | **Sources:** American Foundry Society, Forging Industry Association

### DM-P010: Kitting and Sequencing Errors in Assembly
Incorrect component kits or wrong sequence delivery to assembly stations causing line stops, rework, and part mix-ups.
- **Symptoms:** Kitting error rate >1%; assembly line stops for missing parts >2x/day; wrong component installed despite barcode checks; WIP buffers growing at kitting area; no automated kit verification system
- **Segments:** Automotive/EV, Electronics, Medical Devices
- **Linked KPIs:** kpi-fpy, kpi-schedule-attainment, kpi-scrap-rate
- **Prevalence:** MEDIUM | **Confidence:** HIGH | **Sources:** AIAG PPAP, Automotive Logistics Benchmarks

### DM-P011: Robotics Path Programming and Cycle Time Inefficiency
Industrial robot paths not optimized for cycle time, causing bottlenecks and underutilization of automation investment.
- **Symptoms:** Robot cycle time >10% above simulation baseline; teach pendant programming consuming engineering hours; collision or near-miss incidents; path optimization only during initial commissioning; no continuous cycle time improvement program
- **Segments:** Automotive/EV, Robotics, Electronics, Heavy Machinery
- **Linked KPIs:** kpi-throughput, kpi-oee, kpi-cycle-time
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM | **Sources:** FANUC Robotics Benchmarks, Robotics Industry Association

### DM-P012: Additive Manufacturing Build Failure and Post-Processing
3D printing build failures in production parts causing material waste, delayed delivery, and inconsistent mechanical properties.
- **Symptoms:** Build failure rate >15% in production AM; post-processing time >50% of total part time; mechanical property variation batch-to-batch; no real-time melt pool monitoring; qualification/certification cycle >6 months
- **Segments:** Aerospace, Medical Devices, Automotive/EV
- **Linked KPIs:** kpi-scrap-rate, kpi-npi-cycle-time, kpi-copq
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM | **Sources:** Wohlers Associates AM Report, ASTM F42

### DM-P013: Sheet Metal Bend and Punch Accuracy
Press brake and punch press operations producing parts out of tolerance due to springback, tool wear, and material variation.
- **Symptoms:** First article pass rate <90% on new bend programs; springback compensation trial-and-error consuming setup time; tool wear causing burr growth; material thickness variation from coil to coil; no automatic bend angle correction
- **Segments:** Industrial Equipment, Automotive/EV, Appliances
- **Linked KPIs:** kpi-fpy, kpi-changeover-time, kpi-scrap-rate
- **Prevalence:** MEDIUM | **Confidence:** HIGH | **Sources:** Fabricators & Manufacturers Association, Trumpf Sheet Metal Technology

### DM-P014: EV Battery Module Assembly Contamination
Cleanroom-level contamination control gaps in EV battery module/pack assembly causing cell degradation, thermal runaway risk, and warranty exposure.
- **Symptoms:** Particle count >Class 8 in critical assembly zones; cell tab welding contamination causing resistance variation; thermal interface material application inconsistency; no environmental monitoring data logging; battery pack failure rate in early life >0.5%
- **Segments:** Automotive/EV
- **Linked KPIs:** kpi-field-failure-rate, kpi-warranty-cost, kpi-copq
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** SAE J3234 Battery Assembly, CATL Battery Manufacturing Best Practices

### DM-P015: Aerospace Special Process Nadcap Audit Failures
Heat treat, chemical processing, NDT, and welding operations failing Nadcap audits threatening supplier status with primes.
- **Symptoms:** Nadcap non-conformance findings >3 per audit; pyrometry or chemistry out of specification; operator certification gaps; furnace survey overdue; customer (Boeing, Airbus) SCARs increasing
- **Segments:** Aerospace & Defense
- **Linked KPIs:** kpi-audit-findings, kpi-capa-cycle-time, kpi-copq
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** PRI Nadcap Annual Report, Aerospace Supplier Quality Council

### DM-P016: Medical Device Validation and V&V Backlog
Software validation, process validation (IQ/OQ/PQ), and design verification activities creating release bottlenecks for regulated medical devices.
- **Symptoms:** V&V cycle time >6 months per product change; validation protocols requiring >3 review cycles; FDA 483 observations on validation gaps; no automated test execution or reporting; traceability matrix maintained manually
- **Segments:** Medical Devices
- **Linked KPIs:** kpi-capa-cycle-time, kpi-npi-cycle-time, kpi-audit-findings
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** FDA CDRH Inspection Data, MDIC Validation Working Group

### DM-P017: Supply Chain Component Allocation Crisis
Semiconductor and critical component allocation shortages forcing expediting, alternative sourcing, and production mix changes.
- **Symptoms:** Lead times for critical ICs >52 weeks; multiple ECNs for component substitution; production mix changed to prioritize available parts; broker purchases at 3-10x standard price; no component lifecycle monitoring system
- **Segments:** Electronics & Semiconductors, Automotive/EV, Medical Devices
- **Linked KPIs:** kpi-supplier-otd, kpi-expedite-cost, kpi-schedule-attainment
- **Prevalence:** HIGH | **Confidence:** HIGH | **Sources:** Gartner Semiconductor Allocation Report, ECIA Component Market Analysis

### DM-P018: Digital Thread Gap from CAD to Machine
Design intent lost in translation from CAD/CAM to CNC program causing rework, scrap, and extended setup times.
- **Symptoms:** CAM programming time >40% of total setup; design changes not propagating to shop programs; post-processor errors causing machine crashes; no digital twin of machining process; manual G-code edits without version control
- **Segments:** Aerospace, Medical Devices, Industrial Equipment
- **Linked KPIs:** kpi-changeover-time, kpi-scrap-rate, kpi-npi-cycle-time
- **Prevalence:** MEDIUM | **Confidence:** HIGH | **Sources:** Siemens Digital Industries Software, Deloitte Digital Twin Survey

---

## 4. Vertical KPIs (25)

| ID | Name | Formula | Unit | Benchmark | Segments |
|----|------|---------|------|-----------|----------|
| kpi-torque-cpk | Torque Process Capability (Cpk) | min[(USL-Mean)/(3σ), (Mean-LSL)/(3σ)] | index | >1.67 | Automotive/EV, Heavy Machinery, Rail/Marine |
| kpi-bom-accuracy | BOM Accuracy Rate | (Zero-discrepancy BOMs / Total BOMs) x 100 | % | >98% | Automotive/EV, Electronics, Aerospace, Medical |
| kpi-cmm-utilization | CMM Utilization Rate | (Measurement Time / Available Time) x 100 | % | 70-85% | Aerospace, Medical, Automotive |
| kpi-first-article-pass | First Article Inspection Pass Rate | (Passing FAIs / Total FAIs) x 100 | % | >90% | Aerospace, Medical, Automotive |
| kpi-smt-dpmo | SMT Defects Per Million Opportunities | (Defects / Opportunities) x 1,000,000 | DPMO | <1,000 | Electronics, Medical, Automotive |
| kpi-weld-reject | Welding Reject Rate | (Failing Welds / Total Welds) x 100 | % | <1.5% | Heavy Machinery, Rail, Automotive, Aerospace |
| kpi-kitting-accuracy | Kitting Accuracy Rate | (Correct Kits / Total Kits) x 100 | % | >99.5% | Automotive, Electronics, Medical |
| kpi-robot-oee | Robot Cell OEE | Availability x Performance x Quality | % | >75% | Automotive, Robotics, Electronics, Heavy Machinery |
| kpi-casting-scrap | Casting Scrap Rate | (Scrap / Total Poured) x 100 | % | <5% | Heavy Machinery, Automotive, Industrial |
| kpi-coating-thickness-cpk | Coating Thickness Cpk | min[(USL-Mean)/(3σ), (Mean-LSL)/(3σ)] | index | >1.33 | Automotive, Industrial, Appliances |
| kpi-eco-cycle-time | ECO Cycle Time | Average days from submission to implementation | days | <5 | Automotive, Electronics, Aerospace, Medical |
| kpi-cam-programming-time | CAM Programming Time | Total hours / Number of new part programs | hrs/part | <8 | Aerospace, Medical, Industrial |
| kpi-line-balance-efficiency | Assembly Line Balance Efficiency | Sum(task times) / (Stations x Bottleneck cycle) x 100 | % | >90% | Automotive, Electronics, Appliances |
| kpi-nadcap-findings | Nadcap Audit Findings | Total non-conformance findings per audit | count | 0-1 | Aerospace & Defense |
| kpi-battery-pack-failure | EV Battery Early Failure Rate | (Failures in 90 days / Total shipped) x 100 | % | <0.1% | Automotive/EV |
| kpi-am-build-success | AM Build Success Rate | (Successful builds / Total attempts) x 100 | % | >92% | Aerospace, Medical, Automotive |
| kpi-sheet-metal-first-pass | Sheet Metal First Article Pass | (Passing FAIs / Total FAIs) x 100 | % | >95% | Industrial, Automotive, Appliances |
| kpi-tool-condition-index | Tool Condition Monitoring Index | Composite of load, vibration, acoustic, wear | 0-100 | >80 good | Aerospace, Medical, Automotive, Industrial |
| kpi-component-traceability | Component Traceability Coverage | (Full traceability units / Total units) x 100 | % | >99% | Automotive, Medical, Aerospace |
| kpi-vv-cycle-time | V&V Cycle Time | Days from protocol approval to final report | days | <45 | Medical Devices |
| kpi-sequence-compliance | Assembly Sequence Compliance | (Correct sequence ops / Total ops) x 100 | % | >99.5% | Automotive, Electronics, Medical |
| kpi-ndt-findings | NDT Defect Detection Rate | (NDT detected / Total defects) x 100 | % | >95% | Aerospace, Heavy Machinery, Rail/Marine |
| kpi-particulate-count | Cleanroom Particulate Compliance | (Within-class periods / Total periods) x 100 | % | >99% | Medical, Electronics, Automotive |
| kpi-press-brake-setup | Press Brake Setup Time | Time from last old part to first good new part | minutes | <20 | Industrial, Automotive, Appliances |
| kpi-firmware-flash-success | Firmware Flash Success Rate | (Successful flashes / Total attempts) x 100 | % | >99.9% | Electronics, Automotive, Medical |

---

## 5. Vertical Signal Rules (20)

| ID | Signal | Interpreted Meaning | Confidence | Linked Pain |
|----|--------|---------------------|------------|-------------|
| sig-dm-001 | Torque tool calibration overdue surge | Fastener quality degrading; warranty risk increasing | 0.84 | pain-dm-001 |
| sig-dm-002 | BOM revision mismatch alert | ECO control breakdown; wrong-part assembly risk imminent | 0.88 | pain-dm-002 |
| sig-dm-003 | CNC spindle load anomaly | Tool wear/bearing degradation; dimensional drift rising | 0.79 | pain-dm-003 |
| sig-dm-004 | Assembly andon activation spike | Station-level bottleneck or quality issue emerging | 0.82 | pain-dm-004 |
| sig-dm-005 | Weld parameter deviation alert | Weld quality at risk; structural integrity compromised | 0.86 | pain-dm-005 |
| sig-dm-006 | SMT reflow profile drift | Solder joint quality degrading; voids/bridging risk | 0.85 | pain-dm-007 |
| sig-dm-007 | CMM queue time growth | Inspection bottleneck constraining throughput | 0.81 | pain-dm-008 |
| sig-dm-008 | Foundry X-ray porosity cluster | Process parameter out of control; scrap wave imminent | 0.87 | pain-dm-009 |
| sig-dm-009 | Kitting error escalation | Wrong-part assembly risk; line stops escalating | 0.78 | pain-dm-010 |
| sig-dm-010 | Robot collision log growth | Path/fixture drift; cycle time and safety risk | 0.76 | pain-dm-011 |
| sig-dm-011 | AM build failure repeat pattern | Design-for-AM gap or parameter issue | 0.83 | pain-dm-012 |
| sig-dm-012 | Sheet metal springback deviation | Material/tool compensation issue; FAI pass dropping | 0.80 | pain-dm-013 |
| sig-dm-013 | EV battery thermal runaway incident | Critical safety/recall risk; contamination likely root cause | 0.93 | pain-dm-014 |
| sig-dm-014 | Nadcap audit non-conformance | Special process control failure; prime status at risk | 0.91 | pain-dm-015 |
| sig-dm-015 | FDA 483 validation observation | V&V system failure; product release at risk | 0.90 | pain-dm-016 |
| sig-dm-016 | Component allocation notice | Supply constraint hitting production; expediting costs incoming | 0.89 | pain-dm-017 |
| sig-dm-017 | CAD revision not propagated to CAM | Digital thread broken; obsolete geometry being machined | 0.86 | pain-dm-018 |
| sig-dm-018 | AOI false positive spike | Inspection mis-calibrated; unnecessary rework/throughput loss | 0.77 | pain-dm-007 |
| sig-dm-019 | Customer SCAR influx | Systematic quality/delivery failure; contract risk | 0.85 | pain-dm-015, pain-dm-001, pain-dm-005 |
| sig-dm-020 | Cleanroom particle count excursion | Contamination control compromised; regulatory risk | 0.88 | pain-dm-014, pain-dm-016 |

---

## 6. Vertical Personas (6 New)

### MRO Manager
- **Goals:** Minimize unplanned downtime; optimize spare parts inventory; extend asset life; control maintenance spend
- **Pressures:** Aging asset base; parts obsolescence; knowledge loss from retirements; reactive maintenance culture
- **Trusted Evidence:** SMRP benchmarks; OEM maintenance bulletins; RCM case studies; spare parts criticality analysis
- **Disliked Claims:** Maintenance as pure cost center; unrealistic uptime guarantees; solutions ignoring existing CMMS/EAM investment; predictive maintenance without sensor infrastructure
- **Decision Influence:** Technical

### Production Scheduler
- **Goals:** Achieve schedule attainment >95%; minimize changeover/setup time; balance workload across shifts; reduce expediting/premium freight
- **Pressures:** Customer order changes mid-shift; material shortages disrupting sequence; ERP planning logic limitations; overtime budget constraints
- **Trusted Evidence:** APICS/ASCM planning standards; MES dispatch data; takt time analysis; bottleneck utilization reports
- **Disliked Claims:** Infinite capacity planning as sufficient; schedules disconnected from floor reality; algorithmic optimization without human override; one-size-fits-all scheduling logic
- **Decision Influence:** User

### Quality Engineer
- **Goals:** Drive root cause elimination; reduce Cost of Poor Quality; maintain audit readiness; close CAPAs within target
- **Pressures:** Customer SCAR volume; Nadcap/FDA audit frequency; statistical analysis tool limitations; quality data fragmentation across systems
- **Trusted Evidence:** AIAG/ASQ standards; SPC reference manuals; customer-specific requirements (CSR); 8D and 5-Why case studies
- **Disliked Claims:** Quality as inspection-only activity; AI replacing engineering judgment; vendor solutions without regulatory precedent; shortcuts on validation/qualification
- **Decision Influence:** Technical

### Plant Manager
- **Goals:** Meet P&L targets; achieve safety and quality KPIs; deliver on-time to customer promise; develop workforce capability
- **Pressures:** Corporate overhead allocation; customer price-down mandates; capital replacement backlog; labor availability constraints
- **Trusted Evidence:** Plant-level OEE trends; peer plant benchmarking; union/management agreement terms; local industry wage benchmarks
- **Disliked Claims:** Corporate initiatives without plant input; technology solutions ignoring floor reality; metrics that don't reflect plant conditions; one-size-fits-all best practices
- **Decision Influence:** User

### Design Engineer
- **Goals:** Design for manufacturability and cost; reduce part count/complexity; accelerate design-to-production handoff; maintain design intent through manufacturing
- **Pressures:** NPI deadline compression; manufacturing capability gaps; ECO volume from production issues; customer specification changes
- **Trusted Evidence:** DFM/A guidelines (Boothroyd-Dewhurst); GD&T standards (ASME Y14.5); material property databases; tolerancing simulation results
- **Disliked Claims:** Design pushed to cut corners; tooling decisions without DFM input; platform promises without engineering validation; AI-generated designs without manufacturability check
- **Decision Influence:** Technical

### Warranty Analyst
- **Goals:** Reduce warranty cost per unit; shorten time-to-root-cause; predict failure modes before field escalation; improve customer satisfaction scores
- **Pressures:** Warranty reserve scrutiny from finance; field failure data delays; supplier warranty recovery disputes; regulatory recall notification timelines
- **Trusted Evidence:** Warranty Week benchmarks; JD Power reliability studies; failure mode distribution analytics; supplier quality scorecards
- **Disliked Claims:** Warranty cost minimization over quality; aftermarket treated as cost center; disconnected field-service data; warranty accrual manipulation
- **Decision Influence:** User

---

## 7. Vertical Formulas (15)

### VF-DM-001: Torque Quality Failure Cost
**Formula:** Annual Cost = (Baseline Rate - Target Rate) x Annual Units x (Rework + Warranty Cost) + Recall Risk Value
**Inputs:** Baseline/target torque Cpk, annual volume, rework cost, warranty cost, recall probability/cost
**Example:** Cpk 0.8 -> 1.67, 500K units, $45 rework, $280 warranty, 2% recall x $5M = $2.5M

### VF-DM-002: BOM Revision Error Cost
**Formula:** Annual Cost = ECOs x (Wrong Part Scrap + Expediting + Engineering Rework Hours x Rate)
**Inputs:** ECO count, wrong part rate, scrap cost, expediting cost, rework hours, engineering rate
**Example:** 240 ECOs, 15% wrong part, $12K scrap, $8K expedite, 8 hrs @ $150 = $1.92M

### VF-DM-003: Tool Condition Monitoring Value
**Formula:** Annual Value = Scrap Reduction + Avoided CMM Queue + Extended Tool Life - Sensor Investment
**Inputs:** Scrap baseline/target, material cost, queue hours, tool spend, TCM investment
**Example:** 6% -> 2% scrap, $80M material, 200 hrs CMM saved, 20% tool life x $2M tools = $3.34M

### VF-DM-004: Assembly Line Balance Improvement
**Formula:** Annual Value = (Throughput Increase x Margin x Days) + Overtime Reduction + WIP Carrying Cost Reduction
**Inputs:** Current/target efficiency, throughput, margin, days, OT hours, WIP carrying cost
**Example:** 78% -> 92%, 800 units/day, $120 margin, 250 days, 15->5 OT hrs = $4.36M

### VF-DM-005: Welding Quality Improvement Value
**Formula:** Annual Value = (Reject Reduction x Weld Count x Rework) + NDT Cost Reduction + Avoided Field Failure Cost
**Inputs:** Baseline/target reject rate, weld count, rework cost, NDT cost, field failure rate/cost
**Example:** 4% -> 1%, 2M welds, $85 rework, $12 NDT, 0.01% field x $50K = $5.92M

### VF-DM-006: SMT Quality Improvement
**Formula:** Annual Value = (DPMO Reduction / 1M x Volume x Cost) + Rework Labor + AOI Efficiency Gain
**Inputs:** Baseline/target DPMO, board volume, board cost, rework hours, AOI programming hours
**Example:** 5000 -> 800 DPMO, 1M boards, $45, 0.5 hr @ $65, 200->80 AOI hrs = $2.08M

### VF-DM-007: CMM Bottleneck Elimination
**Formula:** Annual Value = (Queue Reduction x Hourly Production Value) + Labor Reduction + FAI Cycle Reduction Value
**Inputs:** Queue hours, hourly value, labor cost, FAI days, new product revenue
**Example:** 40 -> 10 hrs/week, $8K/hr, $1.2M->0.9M labor, 5->2 days FAI = $14.3M

### VF-DM-008: Casting Scrap Reduction
**Formula:** Annual Value = (Scrap Reduction x Pour Weight x Material Cost) + Rework + Energy Avoided
**Inputs:** Scrap rates, pour weight, material cost, rework cost, energy cost
**Example:** 10% -> 4%, 5M lbs, $2.50/lb, $45 rework, $0.15/lb energy = $0.94M

### VF-DM-009: Kitting Accuracy Improvement
**Formula:** Annual Value = (Error Reduction x Stops per Error x Downtime Cost) + Rework + Inventory Accuracy
**Inputs:** Error rates, kit count, line stop minutes, production value, rework cost
**Example:** 1.5% -> 0.2%, 2M kits, 15 min @ $200/min, $350 rework = $8.46M

### VF-DM-010: Robot Cycle Time Optimization
**Formula:** Annual Value = (Cycle Reduction x Units/Hour x Hours x Margin) + Programming Labor + Collision Avoidance
**Inputs:** Current/target cycle time, units/hour, hours, margin, programming hours, collision cost
**Example:** 42s -> 35s, 85 units/hr, 6K hrs, $18 margin, 800->200 prog hrs = $7.24M

### VF-DM-011: EV Battery Assembly Contamination Cost
**Formula:** Annual Cost Avoided = (Failure Rate Reduction x Volume x Pack Cost) + Warranty Reserve Reduction + Recall Risk Avoidance
**Inputs:** Failure rates, volume, pack cost, warranty reserve %, revenue, recall probability/cost
**Example:** 0.5% -> 0.1%, 200K packs, $12K cost, 2%->1% reserve x $2B, 1% recall x $50M = $30.1M

### VF-DM-012: Nadcap Audit Readiness Cost
**Formula:** Annual Value = (Audit Prep Reduction + Finding Remediation Reduction + Avoided SCAR Cost) + Revenue Protection
**Inputs:** Prep hours, labor rate, special processes, findings, remediation cost, SCAR cost, revenue at risk
**Example:** 120->40 hrs x 5 @ $150, 8->2 findings x $25K, 4->0 SCARs x $50K = $0.95M + revenue protection

### VF-DM-013: Medical Device V&V Acceleration
**Formula:** Annual Value = (Time-to-Market Reduction x Monthly Revenue x Product Count) + Audit Avoidance + Engineering Efficiency
**Inputs:** V&V cycle times, monthly revenue, product count, audit findings, remediation cost, hours freed
**Example:** 180->90 days, $1.5M/month, 3 products, 6->1 findings x $30K, 500 hrs @ $150 = $13.73M

### VF-DM-014: Sheet Metal Setup Time Reduction
**Formula:** Annual Value = (Setup Reduction x Changeovers x Weeks x Hourly Value) + FAI Pass + Scrap Reduction
**Inputs:** Setup times, changeovers, weeks, hourly value, FAI pass rates, scrap rates
**Example:** 45->15 min, 30/week, 50 weeks, $6K/hr, 75%->95% FAI, 3%->1% scrap = $5.2M

### VF-DM-015: Digital Thread (CAD-to-Machine) Value
**Formula:** Annual Value = CAM Labor Reduction + Scrap Avoidance + FAI Cycle Reduction + ECO Propagation Speed
**Inputs:** CAM hours, new parts, hourly rate, error incidents, scrap cost, FAI days saved, ECO volume
**Example:** 12->3 hrs, 500 parts, $120/hr, 15 errors @ $8K, 2 days x $50K, 100 ECOs x $2K = $0.96M

---

## 8. Vertical Benchmarks (20)

| ID | Metric | Value | Range | Source | Segments |
|----|--------|-------|-------|--------|----------|
| bench-dm-001 | Torque Cpk - Automotive | 1.67 | 1.33-2.0 | AIAG CQI-9 | Automotive, Heavy Machinery |
| bench-dm-002 | BOM Accuracy - Discrete | 98% | 95-99.5% | Siemens PLM | Automotive, Electronics, Aerospace |
| bench-dm-003 | CMM Utilization - Aerospace | 75% | 65-85% | NIST MEP | Aerospace, Medical |
| bench-dm-004 | First Article Pass - Aerospace | 92% | 85-98% | AS9100D | Aerospace |
| bench-dm-005 | SMT DPMO - World Class | 500 | 100-1,000 | IPC-A-610 | Electronics |
| bench-dm-006 | Weld Reject - Automotive Body | 0.8% | 0.3-2% | AWS | Automotive, Heavy Machinery |
| bench-dm-007 | Kitting Accuracy - Automotive | 99.7% | 99.5-99.95% | AIAG | Automotive |
| bench-dm-008 | Robot Cell OEE - Automotive | 78% | 65-85% | FANUC | Automotive, Robotics |
| bench-dm-009 | Casting Scrap - Ductile Iron | 4% | 2-8% | AFS | Heavy Machinery, Automotive |
| bench-dm-010 | Coating Cpk - Automotive | 1.33 | 1.0-1.67 | OEM Standards | Automotive |
| bench-dm-011 | ECO Cycle - Electronics | 3 days | 1-7 days | Siemens PLM | Electronics, Automotive |
| bench-dm-012 | CAM Programming - 5-Axis | 6 hrs | 3-15 hrs | Siemens DI | Aerospace, Medical |
| bench-dm-013 | Line Balance - Mixed Model | 90% | 80-95% | TPS Benchmarks | Automotive, Electronics |
| bench-dm-014 | Nadcap Findings | 0 | 0-1 | PRI Nadcap | Aerospace |
| bench-dm-015 | EV Battery Failure - World Class | 0.05% | 0.01-0.1% | SAE J3234 | Automotive/EV |
| bench-dm-016 | AM Build Success - Metal PBF | 95% | 88-98% | Wohlers | Aerospace, Medical |
| bench-dm-017 | Sheet Metal First Pass | 96% | 90-99% | FMA | Industrial, Automotive |
| bench-dm-018 | Traceability - Medical | 99.9% | 99.5-100% | FDA UDI | Medical Devices |
| bench-dm-019 | V&V Cycle - Class II | 45 days | 30-90 days | MDIC | Medical Devices |
| bench-dm-020 | Press Brake Setup | 12 min | 5-30 min | Trumpf | Industrial, Automotive |

---

## 9. Vertical Regulatory Factors (12)

| ID | Regulation | Applicability | Penalty |
|----|------------|---------------|---------|
| reg-dm-001 | ISO 9001:2015 | All discrete manufacturers | Loss of certification; customer exclusion |
| reg-dm-002 | IATF 16949:2016 | Automotive/EV suppliers | OEM exclusion; cannot bid new programs |
| reg-dm-003 | AS9100D | Aerospace & defense suppliers | Contract ineligibility; DCMA rejection |
| reg-dm-004 | FDA 21 CFR Part 820 | Medical device manufacturers | Warning letter; consent decree; seizure |
| reg-dm-005 | FDA UDI (21 CFR 830) | Medical devices (Class I-III) | Import refusal; detention; recall |
| reg-dm-006 | Nadcap | Aerospace special processes | Prime supplier status revoked |
| reg-dm-007 | EU RoHS/REACH | Electronics in EU | Market exclusion; product recall; fines |
| reg-dm-008 | Conflict Minerals | Public companies, EU importers | SEC enforcement; customs blocking |
| reg-dm-009 | UL/CSA | Electrical equipment in NA | Cannot ship; product recall |
| reg-dm-010 | CE Machinery Directive | Machinery in EU | Market exclusion; customs detention |
| reg-dm-011 | DO-178C/DO-254 | Avionics suppliers | No type certificate; program cancellation |
| reg-dm-012 | AEC-Q100/Q200 | Automotive semiconductors | Tier-1 supplier exclusion |

---

## 10. Vertical Technology Systems (15)

| ID | System | Category | Key Vendors | Integration Points |
|----|--------|----------|-------------|-------------------|
| tech-dm-001 | MES - Discrete | Production | Siemens Opcenter, Rockwell FactoryTalk, SAP ME | ERP, PLM, SCADA, QMS |
| tech-dm-002 | PLM | Engineering | Siemens Teamcenter, Dassault ENOVIA, PTC Windchill | ERP, MES, CAD/CAM, QMS |
| tech-dm-003 | CAD/CAM | Engineering | Siemens NX, CATIA, Mastercam, ESPRIT | PLM, CNC, Tool Mgmt, MES |
| tech-dm-004 | CMM Software | Metrology | Hexagon PC-DMIS, Zeiss CALYPSO, Renishaw MODUS | QMS, SPC, PLM, MES |
| tech-dm-005 | SPC | Quality | Hertzler GainSeeker, InfinityQS, Minitab | MES, QMS, CMM, SCADA |
| tech-dm-006 | Machine Vision/AOI | Quality | Cognex, Keyence, ISRA Vision | MES, QMS, PLC, Robotics |
| tech-dm-007 | Robot Programming | Automation | FANUC ROBOGUIDE, ABB RobotStudio, KUKA.Sim | PLM, MES, CAD, Digital Twin |
| tech-dm-008 | Tool Management | Production | TDM Systems, Zoller, Haimer | CAM, CNC, ERP, MES |
| tech-dm-009 | Tool Condition Monitoring | Maintenance | Promess, Artis/Marposs, Kistler | CNC, MES, CAM, EAM |
| tech-dm-010 | Welding Data Monitoring | Quality | WeldComputer, Cloos QINEO, Fronius WeldCube | MES, QMS, SCADA, NDT |
| tech-dm-011 | AM Management | Advanced Mfg | Materialise Magics, Siemens NX AM, nTopology | PLM, MES, QMS, ERP |
| tech-dm-012 | QMS - Discrete | Quality | MasterControl, SAP QM, EtQ, Arena | ERP, MES, PLM, LIMS |
| tech-dm-013 | Andon/Visualization | Production | Parsec TrakSYS, Lighthouse, Ultriva | MES, PLC, ERP |
| tech-dm-014 | Electronic Work Instructions | Production | Taqtile Manifest, Augmentir, Dozuki | MES, PLM, ERP, Quality Gates |
| tech-dm-015 | Digital Twin/Simulation | Advanced Mfg | Siemens Process Simulate, DELMIA, FlexSim | PLM, MES, Robot Controllers |

---

## 11. Vertical Discovery Questions (20)

| ID | Question | Linked Pain | Target Persona |
|----|----------|-------------|--------------|
| dq-dm-001 | How do you manage torque tool calibration schedules, and what is your audit pass rate on fastener joints? | pain-dm-001 | MRO Manager, Quality Engineer, Plant Manager |
| dq-dm-002 | When an engineering change is released, how long does it take for the shop floor to see the updated BOM? | pain-dm-002 | Design Engineer, Production Scheduler, Plant Manager |
| dq-dm-003 | How do you decide when to change cutting tools—by time, part count, or condition? What is scrap rate from tool wear? | pain-dm-003 | MRO Manager, Quality Engineer, Plant Manager |
| dq-dm-004 | What is your current line balance efficiency, and how often do you rebalance for mixed-model production? | pain-dm-004 | Production Scheduler, Plant Manager, Design Engineer |
| dq-dm-005 | For critical welds, are you monitoring current, voltage, gas flow in real time, or relying on post-weld inspection? | pain-dm-005 | Quality Engineer, Plant Manager, MRO Manager |
| dq-dm-006 | What is your CMM queue time as a percentage of total manufacturing lead time? | pain-dm-008 | Quality Engineer, Production Scheduler, Plant Manager |
| dq-dm-007 | How do you manage component traceability—by lot, serial, or batch—and can you execute a recall in under 4 hours? | pain-dm-010, pain-dm-014 | Quality Engineer, Production Scheduler, Warranty Analyst |
| dq-dm-008 | What percentage of robot cells are programmed offline versus teach pendant, and how often are paths re-optimized? | pain-dm-011 | MRO Manager, Design Engineer, Plant Manager |
| dq-dm-009 | What is your AM build success rate, and what is your ratio of post-processing time to build time? | pain-dm-012 | Design Engineer, Plant Manager, Quality Engineer |
| dq-dm-010 | How many trial bends are typically required before first article approval on a new sheet metal program? | pain-dm-013 | Quality Engineer, Production Scheduler, Design Engineer |
| dq-dm-011 | How do you validate your cleanroom environment for battery assembly—continuous, periodic, or event-triggered? | pain-dm-014 | Quality Engineer, Plant Manager, Warranty Analyst |
| dq-dm-012 | When was your last Nadcap audit, how many findings, and what was the root cause distribution? | pain-dm-015 | Quality Engineer, Plant Manager, COO |
| dq-dm-013 | What is your average V&V cycle time, and how much is spent on manual traceability matrix maintenance? | pain-dm-016 | Quality Engineer, Design Engineer, COO |
| dq-dm-014 | How do you manage semiconductor allocation alerts, and what is your annual expediting spend on allocated components? | pain-dm-017 | Production Scheduler, COO, CFO |
| dq-dm-015 | How do you ensure the CNC program version matches the current CAD revision in your PLM? | pain-dm-018 | Design Engineer, Production Scheduler, Plant Manager |
| dq-dm-016 | What is your SMT DPMO, and what percentage of AOI findings are false positives? | pain-dm-007 | Quality Engineer, Plant Manager, COO |
| dq-dm-017 | How do you manage weld parameter settings—fixed recipes or real-time adaptive control? | pain-dm-005 | Quality Engineer, MRO Manager, Plant Manager |
| dq-dm-018 | What is your warranty cost per unit, and which failure modes are trending upward? | pain-dm-001, pain-dm-014 | Warranty Analyst, CFO, Quality Engineer |
| dq-dm-019 | How do you manage firmware flashing—is it automated with verification? | pain-dm-007 | Quality Engineer, Design Engineer, Production Scheduler |
| dq-dm-020 | What is your customer SCAR rate per million parts, and which customers are most active? | pain-dm-015, pain-dm-001, pain-dm-005 | Quality Engineer, COO, Warranty Analyst |

---

## 12. Vertical Objection Patterns (10)

### OBJ-DM-001: "We already have MES and ERP connected—why another layer?"
**Reframe:** This augments the MES-to-ERP gap with vertical intelligence. Example: your MES knows a part was made but doesn't correlate CMM drift with tool wear index in real time. Value is in cross-system signal correlation, not replacement.

### OBJ-DM-002: "Our customers dictate our systems—we can't add unapproved platforms."
**Reframe:** The platform integrates with existing validated QMS/MES and enhances audit readiness. For IATF/AS9100, it strengthens evidence trails and CAPA tracking—customers want data-driven quality, not more paper.

### OBJ-DM-003: "We don't have IT infrastructure for real-time machine monitoring."
**Reframe:** Start with data you already have: CMM logs, torque controller records, weld parameter files. Many achieve $500K+ value from existing data before adding a single new sensor.

### OBJ-DM-004: "Our workforce is aging and resistant to new technology."
**Reframe:** Solutions are designed for the operator, not the data scientist. Electronic work instructions with photo/video guidance reduce training time by 40% and preserve retiring knowledge.

### OBJ-DM-005: "We've tried predictive maintenance before and didn't see ROI."
**Reframe:** Predictive maintenance ROI depends on asset criticality and data quality. In discrete manufacturing, the highest ROI often comes from targeted applications: tool wear prediction on high-value CNC assets.

### OBJ-DM-006: "Our quality system is already validated—we can't change anything."
**Reframe:** The platform operates as a reporting and analytics overlay on existing validated systems. It does not replace or modify the validated process.

### OBJ-DM-007: "We make too many different parts in small volumes—analytics won't work."
**Reframe:** HMLV environments benefit from family-based analytics: grouping by process family, material, or feature type. A 50-part family with 200 annual runs generates statistically meaningful patterns.

### OBJ-DM-008: "Our CAM programmers are experts—we don't need automated programming."
**Reframe:** Automation handles the routine 60% of programming time, freeing experts for high-value optimization and NPI acceleration.

### OBJ-DM-009: "EV battery assembly is too new—there are no proven benchmarks."
**Reframe:** While EV battery assembly is evolving, contamination control, welding monitoring, and torque management are mature disciplines with proven ROI. Early movers establish the benchmarks.

### OBJ-DM-010: "We don't have data science talent to interpret these signals."
**Reframe:** The platform delivers prescriptive insights. Example: "Tool T-47 on Mill M3 predicted to exceed tolerance in 12 parts—recommend change after Job 2847." No data science required.

---

## 13. Vertical Buying Triggers (15)

| ID | Trigger | Time Sensitivity | Budget Authority |
|----|---------|------------------|----------------|
| bt-dm-001 | Major OEM issues supplier quality mandate requiring real-time process data sharing | HIGH | COO/VP Operations |
| bt-dm-002 | Warranty claim spike triggers executive-level quality review and root cause mandate | HIGH | CFO/COO |
| bt-dm-003 | NPI timeline compressed by customer; existing V&V process too slow | HIGH | COO/VP Engineering |
| bt-dm-004 | Nadcap or IATF audit findings exceed threshold; certification at risk | HIGH | COO |
| bt-dm-005 | CMM backlog causing daily production delays and inspection overtime | MEDIUM | Plant Manager/Operations Director |
| bt-dm-006 | New EV battery assembly line investment; seeking contamination control and traceability | MEDIUM | COO/VP Operations |
| bt-dm-007 | Customer SCAR volume triggers executive action plan with 90-day improvement mandate | HIGH | COO/VP Quality |
| bt-dm-008 | Robot collision or near-miss triggers safety review and path optimization | MEDIUM | Plant Manager/EHS Director |
| bt-dm-009 | FDA 483 or warning letter issued; CAPA effectiveness questioned | HIGH | COO/CEO |
| bt-dm-010 | New aerospace contract requires AS9100 and Nadcap with real-time special process data | MEDIUM | COO/VP Business Development |
| bt-dm-011 | Semiconductor allocation notice forces production mix changes and expediting crisis | HIGH | COO/VP Supply Chain |
| bt-dm-012 | Plant capacity expansion planned; seeking to avoid proportional inspection headcount growth | MEDIUM | Plant Manager/Operations Director |
| bt-dm-013 | AM qualification achieved; now scaling to production volumes and hitting yield walls | MEDIUM | VP Engineering/Operations |
| bt-dm-014 | Digital transformation initiative launched by corporate; plant must select use cases | MEDIUM | COO/CIO |
| bt-dm-015 | Sheet metal/fabrication department losing bids due to long quoting and setup times | MEDIUM | Plant Manager/Sales Director |

---

## 14. Worked Signal→Hypothesis Examples (3)

### Example 1: Torque Cpk Decline → Warranty Risk → Assembly Process Control Investment
**Scenario:** Tier-1 automotive supplier producing EV battery tray assemblies observes torque Cpk declining from 1.67 to 1.2 over 3 months at Station 14.

**Signals Detected:**
- Torque audit Cpk declining trend (0.92, from MES torque controller logs)
- Warranty claims increasing for battery connection issues (0.85, from warranty management system)
- Tool calibration overdue on 40% of fastening tools (0.95, from calibration management system)

**Hypothesis:** Battery module fastening torque inconsistency is the leading predictor of early-life battery pack failures. Root cause is calibration drift and lack of SPC on DC electric tools.

**Formula Applied:** VF-DM-001

**Calculation Walkthrough:**
1. Baseline Cpk = 1.2, Target = 1.67. Reject rate at 1.2 = 0.32%. At 1.67 = 0.006%.
2. Annual volume = 450,000. Excess reject rate = 0.314%.
3. Excess defects = 1,413 units/year.
4. Rework cost = 1,413 x $65 = $91,845.
5. Warranty cost = 254 field escapes x $850 = $215,900.
6. Recall risk: 15% probability x $2.5M = $375,000.
7. **Total annual cost = $682,745.**
8. Investment = $180,000. **Payback = 3.2 months. 3-year NPV = $1.52M.**

**Business Outcome:**
- Cost Savings: $683K/year direct; $2.5M recall avoidance
- Risk Reduction: Recall probability from 15% to <2%
- Cash Flow: Warranty reserve release $340K

**Customer Validation Required:**
- Validate warranty claim root cause distribution
- Confirm torque tool calibration interval and drift data
- Confirm OEM recall threshold and escalation protocol

---

### Example 2: CMM Queue Growth → Throughput Constraint → In-Process Metrology Investment
**Scenario:** Precision aerospace machine shop producing titanium structural brackets experiences CMM queue growing from 8 hours to 35 hours per week. Boeing delivery performance drops below 95%.

**Signals Detected:**
- CMM queue hours trending up >300% over 6 months (0.90)
- First article inspection cycle time >5 days (0.88)
- Customer on-time delivery <95% (0.82)
- Inspection staff overtime >25% (0.95)

**Hypothesis:** CMM capacity is the primary bottleneck constraining throughput and delivery performance. Highest-ROI intervention is deploying in-process metrology for feature classes that don't require CMM accuracy.

**Formula Applied:** VF-DM-007

**Calculation Walkthrough:**
1. Queue reduction = 35 -> 10 hrs/week = 25 hrs/week.
2. Hourly production value = $6,800. Queue value = 25 x 50 x $6,800 = $8.5M.
3. Demand constraint: shop at 85% capacity. Effective gain = 15% of queue value = $1.28M.
4. Labor savings: 3 FTE -> 2.5 FTE + OT reduction = $85K.
5. FAI cycle reduction value = $180K.
6. Investment: On-machine probing $225K + optical scanning $120K = $345K.
7. **Annual value = $1.28M + $85K + $180K = $1.545M. Payback = 2.7 months. 3-year NPV = $3.52M.**

**Business Outcome:**
- Revenue Uplift: $1.28M (throughput-constrained demand capture)
- Cost Savings: $265K (labor + FAI)
- Risk Reduction: Customer delivery scorecard recovery to >98%
- Cash Flow: WIP velocity increase reduces inventory carrying by $420K

**Customer Validation Required:**
- Confirm CMM queue attribution vs machining bottleneck
- Validate on-machine probing accuracy against GD&T requirements
- Confirm demand exists to absorb 15% throughput increase

---

### Example 3: SMT DPMO Spike → Electronics Rework Crisis → Process Control Enhancement
**Scenario:** Medical device electronics contract manufacturer experiences SMT DPMO rising from 800 to 4,200 over 4 months. AOI false positive rate grows to 18%. FDA pre-approval inspection scheduled in 6 months.

**Signals Detected:**
- SMT DPMO trending up 5x over 4 months (0.94)
- AOI false positive rate >15% (0.89)
- Reflow oven temperature zone 3 showing 3°C drift (0.87)
- Solder paste volume deposition CV increasing from 8% to 14% (0.85)

**Hypothesis:** Reflow profile drift combined with solder paste volume inconsistency is causing solder joint defects. AOI system is miscalibrated for the new defect signature, creating false positives. Combination threatens FDA readiness and product reliability.

**Formula Applied:** VF-DM-006

**Calculation Walkthrough:**
1. Excess DPMO = 4,200 -> 800 = 3,400.
2. Annual board volume = 850,000. Excess defects = 2,890.
3. Excess material cost = 2,890 x $78 = $225,420.
4. Rework labor = 2,890 x 0.4 hrs x $72 = $83,232.
5. AOI false positive labor = 153K false calls x 2 min x $72/hr = $367,200.
6. FDA risk: 30% probability x 6 months delay x $3.5M/month = $6.3M risk-adjusted.
7. Investment: Reflow upgrade $85K + AOI/SPI closed-loop $45K = $130K.
8. **Annual direct savings = $675K. Payback = 2.3 months. With FDA risk: 3-year NPV = $15.2M.**

**Business Outcome:**
- Cost Savings: $675K/year direct operational savings
- Risk Reduction: FDA 483 avoidance (30% -> <5% probability)
- Cash Flow: Reduced WIP in rework queue = $120K; expedited delivery penalties avoided

**Customer Validation Required:**
- Validate reflow profile drift correlation with defect types
- Confirm AOI false positive measurement methodology
- Assess FDA inspection scope and process control emphasis areas

---

## 15. Governance

| Attribute | Value |
|-----------|-------|
| Source Coverage | Mixed (public, paid, proprietary) |
| Confidence | High |
| Last Updated | 2025-01-28 |
| Approved for Customer-Facing Output | Yes |
| Review Owner | Discrete Manufacturing Vertical Intelligence Team |
| Agent Swarm ID | swarm-discrete-mfg-v1 |
| Parent Master Swarm ID | swarm-manufacturing-master-v1 |

---

## 16. Evidence Sources

| ID | Source | Type | Access | Update Frequency |
|----|--------|------|--------|-----------------|
| es-dm-001 | AIAG Quality Core Tools Database | Industry Association | Membership | Annual |
| es-dm-002 | PRI Nadcap Audit Statistics | Industry Standard | Public | Quarterly |
| es-dm-003 | FDA CDRH Inspection Database | Government | Public | Weekly |
| es-dm-004 | IPC-A-610 Industry Data | Industry Standard | Membership | Annual |
| es-dm-005 | Wohlers Associates AM Report | Industry Report | Purchase | Annual |

---

## 17. Competitor Factors (5)

| Competitor | Strengths | Weaknesses | Segments |
|------------|-----------|------------|----------|
| Siemens Digital Industries | Deep PLM-MES integration, CAD-to-machine digital thread, strong aerospace/automotive base | High implementation complexity, enterprise-only pricing, long deployment cycles | Automotive, Aerospace, Industrial |
| Dassault Systemes | Dominant aerospace PLM, simulation-driven design, strong ENOVIA BOM management | High cost of ownership, complex customization, MES integration less mature | Aerospace, Automotive, Industrial |
| Rockwell Automation | Strong plant floor connectivity, OT/IT convergence, AB ecosystem lock-in | Limited PLM integration, scalability challenges, analytics less advanced | Automotive, Heavy Machinery, Industrial |
| Hexagon | Metrology market leadership, quality management suite, CAD/CAM integration | Less strong in production execution, fragmented portfolio | Aerospace, Automotive, Medical |
| PTC (ThingWorx+Windchill+Arena) | IoT platform maturity, strong PLM for medical, SaaS QMS | MES gap, ThingWorx complexity, medical focus limits breadth | Medical, Aerospace, Industrial |

---

*End of Discrete Manufacturing Vertical Subpack*
