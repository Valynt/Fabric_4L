# Infrastructure & Utilities Subpack

**Pack ID:** `infrastructure-v1`  
**Parent Master:** `public-sector-master-v1`  
**Version:** 1.0.0  
**Type:** Subpack (Vertical Specialization)  
**Domain:** Public Sector – Infrastructure & Utilities  
**Last Updated:** 2025-01-21  
**Confidence:** HIGH  
**Approved for Customer-Facing Output:** YES

---

## 1. Scope & Vertical Focus

This subpack extends the Public Sector Master Pack with vertical-specialized value components for infrastructure and utilities agencies. It does NOT duplicate master content; all components below are **ADDITIONAL** to the master framework.

**Vertical Segments Covered:**
- Water Utilities (Drinking Water, Treatment)
- Wastewater Management
- Public Transit Agencies (Bus, Rail, Ferry)
- Roads / Bridges / Highway Departments
- Airports / Port Authorities
- Public Energy Authorities / Municipal Utilities
- Broadband Authorities / Digital Equity Programs
- Waste Management / Recycling
- Smart City Infrastructure / IoT
- Emergency Communications (911, FirstNet)
- Grid Modernization / Resilience

---

## 2. Inheritance Manifest

### Inherited from Master (Read-Only Reference)
- **Value Driver Framework** — 5 drivers: Revenue Uplift, Cost Savings, Risk Reduction, Mission Effectiveness, Working Capital/Cash Flow
- **Base Persona Archetypes** — 12 personas: PS-PERS-001 through PS-PERS-012
- **Evidence Source Types** — FASB/GASB, Federal Agencies, Industry Associations, Municipal Market, FOIA, News, Academic
- **Formula Templates** — Present Value, Risk-Adjusted, Investment Required, Payback Period
- **Signal Source Taxonomy** — financial filings, audits, news, regulatory, credit, benchmarks, FOIA, signals
- **Benchmark Methodology** — peer grouping, confidence scoring, confidence-adjusted benchmarks
- **Governance Framework** — evidence review, confidence scoring, customer-facing approval

### Created by Subpack (Vertical-Specialized)
| Category | Count | IDs |
|----------|-------|-----|
| Pains | 18 | INF-PAIN-001 to INF-PAIN-018 |
| KPIs | 25 | INF-KPI-001 to INF-KPI-025 |
| Signal Rules | 18 | INF-SIG-001 to INF-SIG-018 |
| Personas | 6 NEW | INF-PERS-001 to INF-PERS-006 |
| Value Formulas | 12 | INF-VF-001 to INF-VF-012 |
| Benchmarks | 18 | INF-BENCH-001 to INF-BENCH-018 |
| Regulatory Factors | 10 | INF-REG-001 to INF-REG-010 |
| Technology Systems | 12 | INF-TECH-001 to INF-TECH-012 |
| Discovery Questions | 18 | INF-DQ-001 to INF-DQ-018 |
| Objection Patterns | 9 | INF-OBJ-001 to INF-OBJ-009 |
| Worked Examples | 3 | INF-EX-001 to INF-EX-003 |
| Buying Triggers | 14 | INF-BT-001 to INF-BT-014 |

### Overridden Components
**None.** This subpack strictly extends the master. No master components are overridden.

---

## 3. Vertical Personas (6 NEW)

### INF-PERS-001: Water Utility Director / General Manager
- **Role:** Leads drinking water and/or wastewater utility; owns treatment, distribution, regulatory compliance, and capital planning
- **Seniority:** Executive / Department Head / Board-reported
- **Goals:** SDWA compliance; zero violations; rate stability; infrastructure replacement; CCR transparency; lead service line elimination; PFAS compliance
- **Pressures:** EPA enforcement; consent decrees; rate case hearings; aging workforce; emerging contaminants; climate resilience; CWSRF/DRF funding competition
- **Trusted Evidence:** AWWA standards; EPA guidance; SDWIS data; ASCE report card; rate study consultants; peer utility benchmarking (Alliance for Water Efficiency)
- **Disliked Claims:** Technology replacing operators; 'smart water' without cybersecurity plan; rate increases without demonstrated need; vendor lock-in in SCADA
- **Decision Influence:** Technical (primary) + Economic (rate impact)

### INF-PERS-002: Transit Authority General Manager / CEO
- **Role:** Leads public transit agency; owns service planning, operations, maintenance, labor relations, and ridership recovery
- **Seniority:** Executive / Board-reported
- **Goals:** Ridership recovery; on-time performance; fare revenue; operating cost control; operator recruitment; fleet modernization; equity in service
- **Pressures:** FTA compliance; NTD reporting; operator shortage; post-pandemic revenue shortfall; ADA compliance; zero-emission mandates; labor negotiations
- **Trusted Evidence:** NTD data; APTA reports; FTA guidance; peer agency benchmarking; ridership studies; union agreements; passenger surveys
- **Disliked Claims:** Fare technology that ignores equity; 'automation' threatening operator jobs; unrealistic ridership projections; vendor exclusivity in AFC
- **Decision Influence:** Mission (primary) + Economic (secondary)

### INF-PERS-003: Public Works Director / County Engineer
- **Role:** Leads roads, bridges, fleet, facilities, and often solid waste; owns infrastructure condition, maintenance, and construction programs
- **Seniority:** Department Head / Elected (in some counties)
- **Goals:** Road/bridge condition improvement; snow removal reliability; fleet availability; cost per lane mile; safety incident reduction; ADA compliance
- **Pressures:** NBI ratings; FHWA STIP requirements; fuel price volatility; salt/material cost spikes; workforce aging; winter weather intensity; equipment replacement
- **Trusted Evidence:** FHWA guidance; APWA benchmarking; state DOT standards; NBI data; pavement management system data; crash statistics; AASHTO standards
- **Disliked Claims:** Unproven materials; technology without field validation; 'smart' infrastructure without maintenance plan; consultant-driven overdesign
- **Decision Influence:** Technical (primary) + Political (secondary)

### INF-PERS-004: Grid Modernization Engineer / Utility Engineering Director
- **Role:** Owns distribution system planning, DER integration, ADMS/DMS, SCADA, and grid hardening; leads capital programs for substations and feeders
- **Seniority:** Director / Senior Engineer
- **Goals:** SAIDI/SAIFI reduction; DER interconnection speed; ADMS deployment; storm hardening; outage management; voltage optimization; EV readiness
- **Pressures:** NERC CIP (if applicable); state RPS mandates; FERC Order 2023; interconnection queue backlog; supply chain for transformers; vegetation management; climate resilience
- **Trusted Evidence:** IEEE standards; NREL research; EIA data; DOE Grid Modernization Lab Consortium; state PUC orders; Utility Analytics Institute benchmarking
- **Disliked Claims:** Proprietary protocols preventing interoperability; 'AI grid' without data foundation; unrealistic DER penetration assumptions; vendor lock-in in ADMS
- **Decision Influence:** Technical (primary) + Economic (rate impact)

### INF-PERS-005: Airport Operations Manager / Director of Operations
- **Role:** Owns airfield operations, ARFF, snow removal, terminal operations, and Part 139 compliance; manages 24/7 operational tempo
- **Seniority:** Director / Department Head
- **Goals:** Part 139 zero findings; ARFF readiness; FOD elimination; on-time gate performance; snow plan execution; terminal safety; emergency preparedness
- **Pressures:** FAA inspections; airline SLA penalties; TSA security directives; weather events; ARFF staffing; equipment availability; AIP grant compliance; noise complaints
- **Trusted Evidence:** FAA ACs; ACRP reports; NTSB recommendations; airport council (ACI-NA) data; airline scorecards; snow plan after-action reports; incident data
- **Disliked Claims:** Technology that distracts from operational awareness; 'automated' systems without human override; unproven airfield tech; compliance shortcuts
- **Decision Influence:** Mission (primary) + Risk (secondary)

### INF-PERS-006: Broadband Program Director / Digital Equity Officer
- **Role:** Leads broadband deployment, digital equity, BEAD/NTIA compliance, and subscriber adoption; manages subgrantees and local coordination
- **Seniority:** Director / Program Manager (often grant-funded)
- **Goals:** 100% broadband coverage; BEAD milestone compliance; digital navigator deployment; low-income adoption; affordability; digital literacy; vendor diversity
- **Pressures:** NTIA/BEAD timeline; FCC challenge process; make-ready delays; permitting variance across jurisdictions; supply chain; workforce shortage; ACP sunset; digital equity grant compliance
- **Trusted Evidence:** FCC BDC data; NTIA guidance; Pew Research; state broadband office data; Benton Institute; subgrantee performance reports; adoption surveys
- **Disliked Claims:** Technology-first without community engagement; overbuild without adoption plan; 'one vendor' deployment; unrealistic cost per passing estimates
- **Decision Influence:** Mission (primary) + Economic (grant drawdown)

---

## 4. Vertical Pains (18)

### INF-PAIN-001: Water Main Break Rate Exceeding Tolerance
Water distribution systems experience main break rates >25 per 100 miles/year, indicating pipe age, material failure, pressure management failure, and deferred replacement. Each break costs $5K–$50K in direct repair plus indirect water loss, traffic disruption, and potential contamination risk.
- **Symptoms:** Break rate >25/100 miles/year; Increasing trend over 3 years; Same-line repeat breaks within 12 months; Emergency repair overtime >20% of maintenance budget; Boil-water advisories after breaks
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** EPA Drinking Water Needs Survey 7th Assessment; AWWA M77 Water Main Breaks; ASCE Report Card 2021

### INF-PAIN-002: Transit On-Time Performance Below Threshold
Transit on-time performance <75% signals schedule reliability breakdown, eroding ridership recovery and increasing operating costs through overtime, deadhead, and customer service complaints. Poor OTP correlates with fare revenue loss and service cuts.
- **Symptoms:** OTP <75% for 2+ quarters; Hold orders increasing; Operator absenteeism >8%; Run-cutting frequency rising; Customer complaints about lateness up >20% YoY
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** FTA National Transit Database; APTA Q3 2023 Ridership Report; TransitCenter Research

### INF-PAIN-003: SCADA/OT Cybersecurity Exposure
Infrastructure operational technology (SCADA, DMS, AMI) faces increasing nation-state and ransomware targeting. Many systems lack network segmentation, have default passwords, run on unsupported OS, and have no OT-specific SOC. NERC CIP applies only to bulk electric; water/transit OT often unregulated.
- **Symptoms:** OT network flat / no segmentation; Default or shared passwords on PLCs; Remote access via unmanaged VPN; No OT-specific vulnerability scanning; Incident response plan excludes OT
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** CISA Water Sector Cybersecurity Brief; Dragos OT Threat Report 2023; GAO-22-104666 Water Cybersecurity

### INF-PAIN-004: Bridge Condition Rating Deterioration
State and local bridge inventories show >7% structurally deficient or poor condition. SD bridges create load restrictions, detour costs, emergency closure risk, and liability exposure. Federal NBIS requires biennial inspection but funding for rehabilitation lags.
- **Symptoms:** SD bridge percentage >7%; Load postings increasing; Inspection backlogs >12 months; Repair cost estimates growing >inflation; Weight-limit detour complaints from freight
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** FHWA National Bridge Inventory 2023; ASCE Report Card 2021; ARTBA Bridge Report 2023

### INF-PAIN-005: Airport Operational Efficiency & Part 139 Compliance
Airports face Part 139 inspection pressures, ARFF staffing requirements, runway condition reporting mandates, and FMO/fueling safety rules. Manual inspection processes, paper logbooks, and siloed systems create compliance risk and operational inefficiency.
- **Symptoms:** Part 139 inspection findings >2 per cycle; ARFF response time >3 minutes to midpoint; Runway condition assessments manual; Fueling inspection records non-digitized; Snow removal equipment availability <95%
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** FAA Part 139 Advisory Circulars; Airport Cooperative Research Program (ACRP); FAA Compliance Activity Tracking System

### INF-PAIN-006: Broadband Deployment Cost Overrun & BEAD Compliance
BEAD and other federal broadband programs require complex compliance: subgrantee selection, preference scoring, high-cost threshold compliance, local coordination, and deployment reporting. Underestimation of make-ready, permitting delays, and supply chain issues drive cost overruns 20-40%.
- **Symptoms:** BEAD subgrantee selection delayed >6 months; Permitting timeline >50% of build schedule; Make-ready cost >30% of aerial estimate; Low ACP adoption in served areas; Compliance reporting consuming >1 FTE
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Sources:** NTIA BEAD Program Guidance; FCC Broadband Data Collection; Pew State Broadband Research

### INF-PAIN-007: Wastewater Collection System I/I and SSOs
Infiltration and inflow (I/I) overload collection systems, causing sanitary sewer overflows (SSOs) during wet weather. SSOs violate CWA permits, trigger EPA enforcement, and expose agencies to consent decrees. I/I reduction requires targeted rehabilitation but sewer assessment backlogs delay action.
- **Symptoms:** SSO events >10 per year; I/I volume >40% of dry weather flow; Consent decree or EPA enforcement present; Wet weather treatment bypasses increasing; Sewer assessment backlog >5 years
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** EPA SSO Rule; EPA Clean Water Needs Survey; NRDC Wet Weather Sewage Report

### INF-PAIN-008: Fleet Electrification & Alternative Fuel Transition
Federal and state mandates (EO 14057, state ZEV mandates) require fleet electrification. Infrastructure agencies face depot power capacity limits, EV procurement delays, charging infrastructure gaps, and workforce training shortfalls. Total cost of ownership uncertainty blocks capital decisions.
- **Symptoms:** EV procurement backlog >12 months; Depot electrical capacity insufficient for plan; Maintenance bay lacking EV lift/ventilation; Driver training completion <50%; TCO analysis not completed
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Sources:** DOE Alternative Fuels Data Center; FTA Low-No Program; Federal Fleet Sustainability EO 14057

### INF-PAIN-009: Energy Distribution Grid Resilience & Outage Duration
Public power and IOU territories face increasing SAIDI/SAIFI from aging distribution infrastructure, storm intensity, and vegetation management gaps. Municipal utilities with overhead systems see SAIDI >4 hours/year. Underground systems face longer restoration times for cable faults.
- **Symptoms:** SAIDI >240 minutes/year; SAIFI >1.5 interruptions/year; Major event days >5 per year; Vegetation-related outages >30%; Underground cable fault rate increasing
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** EIA Electric Power Annual; IEEE 1366 Standard; DOE Grid Modernization Initiative

### INF-PAIN-010: Smart City IoT Integration & Data Silos
Smart city deployments (sensors, cameras, digital twins) generate data that sits in vendor-specific platforms without integration. Traffic, parking, air quality, and utility data don't combine for holistic urban management. Interoperability standards (OCF, oneM2M) remain immature.
- **Symptoms:** IoT platforms >5 with no central data layer; Digital twin incomplete or stale >30 days; Sensor uptime <90%; No API between traffic and signal systems; Data ownership disputes with vendors
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Sources:** NIST Smart City Framework; Gartner Smart City Hype Cycle 2023; ICMA Municipal IoT Survey

### INF-PAIN-011: Emergency Communications (911/PSAP) NextGen Transition
PSAPs face NextGen 911 transition requiring IP-based call handling, GIS integration, text-to-911, and multimedia support. Legacy CAMA trunking, ALI database dependencies, and vendor lock-in create transition risk. Staffing shortages compound technology complexity.
- **Symptoms:** Text-to-911 not fully deployed; GIS data accuracy <95% for Z-axis; CAMA trunking still primary; PSAP turnover >15% annually; NextGen vendor contract >5 years old with no upgrade path
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** NENA NG911 Roadmap; FCC 911 Reliability Reports; FirstNet Authority Annual Report

### INF-PAIN-012: Waste & Recycling Contamination and Market Volatility
Recycling contamination rates >25% increase processing costs and reduce commodity revenue. China's National Sword and shifting export markets have destabilized recycling economics. Municipalities face service cuts, higher tipping fees, and public backlash.
- **Symptoms:** Contamination rate >25%; Recycling commodity revenue down >30%; Processing cost per ton >landfill tip fee; Public complaints about service changes >20%; MRF downtime >5%
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** EPA Recycling Economic Information Report; SWANA Industry Reports; Waste Dive Market Analysis

### INF-PAIN-013: Port Terminal Throughput & Drayage Inefficiency
Port authorities face container dwell time growth, chassis shortages, drayage truck turnaround delays, and yard congestion. Demurrage/detention disputes and trucker access issues create operational and regulatory friction. Emissions regulations add compliance cost.
- **Symptoms:** Container dwell time >5 days; Truck turn time >60 minutes; Chassis availability <85%; Demurrage/dispute volume increasing; Idle emissions >regulatory threshold
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** PIERS Data; FMC Demurrage/Detention Reports; EPA Port Emissions Guidance

### INF-PAIN-014: Rate Affordability and Shutoff Crisis
Water and energy rate increases to fund infrastructure investment create affordability crises. Shutoff rates rise, triggering public health concerns, regulatory scrutiny, and political backlash. Low-income assistance programs (LIHEAP, H2O Help) are under-enrolled and underfunded.
- **Symptoms:** Shutoff rate >5% of accounts annually; Delinquency rate >8%; Rate increase >5% for 3 consecutive years; Low-income program enrollment <30% eligible; Media coverage of shutoff-related health incidents
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** EPA Affordability Assessment; NRDC Water Shutoff Report; LIHEAP Clearinghouse Data

### INF-PAIN-015: Transit Fare Evasion and Revenue Leakage
Honors-system and proof-of-payment transit operations face fare evasion rates 5-15%, eroding already-weak farebox recovery. Enforcement costs, citation processing, and public perception challenges complicate revenue protection strategies.
- **Symptoms:** Fare evasion rate >8% by observation; Citation collection rate <30%; Proof-of-payment validation <5% of riders; Revenue discrepancy >2% vs. ridership model; Fare inspection staffing vacancies >20%
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Sources:** FTA Revenue Control Guidelines; APTA Fare Collection Report; TransitCenter Evasion Research

### INF-PAIN-016: PFAS and Emerging Contaminant Compliance
EPA PFAS MCLs and emerging contaminant monitoring create massive analytical, treatment, and communication challenges for water systems. Small systems (<10,000 population) face disproportionate cost burden for GAC/IX/RO treatment upgrades.
- **Symptoms:** PFAS detection >proposed MCL; Laboratory capacity wait >30 days; Treatment pilot study not initiated; Customer inquiries >500 per detection event; CWSRF loan application pending >12 months
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** EPA PFAS Roadmap; AWWA PFAS Cost Study; NRDC Emerging Contaminant Report

### INF-PAIN-017: Airfield Pavement Condition Index Decline
Airport runways, taxiways, and aprons deteriorate under aircraft loads and weather, requiring PCI assessment and maintenance. Deferred pavement maintenance increases Foreign Object Debris (FOD) risk, aircraft damage exposure, and full reconstruction cost (5-10x maintenance cost multiplier).
- **Symptoms:** PCI <70 on primary runway; FOD incidents >2 per year; Pavement maintenance budget <2% of replacement value; Crack sealing backlog >12 months; Aircraft weight restrictions contemplated
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** FAA AC 150/5380-7B; Airport PCI Standards; ACRP Pavement Research

### INF-PAIN-018: Distributed Energy Resource (DER) Interconnection Backlog
Rooftop solar, battery storage, and EV charger interconnection requests overwhelm utility review capacity. Queue delays >12 months create customer dissatisfaction, regulatory complaints, and lost clean energy targets. Hosting capacity analysis often missing or outdated.
- **Symptoms:** Interconnection queue >500 pending; Average review time >180 days; Rejection/modification rate >40%; Hosting capacity map not published; Regulatory complaints >10 per quarter
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** IRENA Interconnection Queue Report; NREL Distribution Integration; FERC Order 2023 Reforms

---

## 5. Vertical KPIs (25)

| ID | Name | Formula | Unit | Benchmark |
|----|------|---------|------|-----------|
| INF-KPI-001 | Water Main Break Rate | COUNT(Breaks) / (Total Miles / 100) | Breaks/100 mi/yr | Best: <15; Median: ~25; Fail: >35 |
| INF-KPI-002 | Unaccounted-for Water | (Produced - Billed + Unbilled) / Produced * 100% | % | AWWA target: <10% |
| INF-KPI-003 | Pipe Replacement Rate | Miles Replaced / Total Miles * 100% | %/yr | Sustainable: >1.5% |
| INF-KPI-004 | Transit On-Time Performance | On-Time Trips / Total Trips * 100% | % | Best: >85%; Fail: <75% |
| INF-KPI-005 | Operating Cost Per VRM | Total Op Cost / Vehicle Revenue Miles | USD/VRM | Bus: $10-15; Rail: $15-25 |
| INF-KPI-006 | Farebox Recovery Ratio | Fare Revenue / Total Op Cost * 100% | % | Heavy rail: >50%; Bus: 20-35% |
| INF-KPI-007 | OT Security Posture Score | AVG(Segmentation + Access + Monitoring + Patch + Backup) | 0-100 | CIP compliant: >80; Critical: <50 |
| INF-KPI-008 | SCADA Availability | (Uptime - Downtime) / Uptime * 100% | % | Critical OT: >99.95% |
| INF-KPI-009 | MTTR OT Service | AVG(Restoration - Outage Start) | Minutes | Best: <60; Concerning: >180 |
| INF-KPI-010 | SD Bridge Percentage | SD Bridges / Total * 100% | % | Target: <5%; Concerning: >8% |
| INF-KPI-011 | Bridge Condition Index | AVG(Element Rating weighted) | 0-100 | Good: >75; Poor: <60 |
| INF-KPI-012 | Pavement Condition Index | AVG(PCI weighted by lane miles) | 0-100 | Good: >70; Poor: <55 |
| INF-KPI-013 | ARFF Response Time | AVG(Response to midpoint) | Seconds | Part 139: <180s; Best: <120s |
| INF-KPI-014 | Airfield PCI | AVG(PCI weighted by area) | 0-100 | Good: >75; Poor: <65 |
| INF-KPI-015 | FOD Event Rate | FOD Incidents / 100,000 Operations | Per 100K ops | Best: <1; Concerning: >3 |
| INF-KPI-016 | Broadband Cost Per Passing | Total Cost / Locations Passed | USD | Rural: $4K-$8K; Urban: <$2.5K |
| INF-KPI-017 | BEAD Milestone Compliance | Milestones Met / Total * 100% | % | Target: >90%; At risk: <75% |
| INF-KPI-018 | Broadband Adoption Rate | Subscribers / Serviceable * 100% | % | Mature: >50%; New: 30-45% |
| INF-KPI-019 | SSO Rate | SSO Events / 100 Miles Sewer | Events/100 mi/yr | Best: <5; Enforcement: >10 |
| INF-KPI-020 | I/I Volume Ratio | Wet Weather Increase / Dry Flow * 100% | % | Target: <30%; High: >50% |
| INF-KPI-021 | Sewer Rehab Rate | Miles Rehabbed / Total Miles * 100% | %/yr | Sustainable: >1% |
| INF-KPI-022 | Fleet Electrification % | EVs / Total Fleet * 100% | % | Leading: >20%; Fed target: 100% LD |
| INF-KPI-023 | EV Charging Utilization | Sessions / (Chargers * Days) * 100% | % | Viable: >30%; Under: <20% |
| INF-KPI-024 | Fleet Vehicle Availability | Available / Total * 100% | % | Best: >92%; Concerning: <85% |
| INF-KPI-025 | SAIDI | SUM(Duration) / Total Customers | Min/yr | Best: <100; Median: ~200; Concern: >300 |

*(Additional KPIs INF-KPI-026 through INF-KPI-054 are defined in the JSON file for segments: Energy SAIFI/CAIDI, Smart City sensor uptime/integration, 911 call answer time/abandonment, recycling contamination/diversion, port truck turn/dwell time, DER interconnection queue, affordability ratios, PFAS compliance, and more.)*

---

## 6. Vertical Value Formulas (12)

### INF-VF-001: Water Main Break Cost Avoidance via Pipe Replacement
**Formula:** `V = (Baseline_Break_Rate - Target_Break_Rate) * System_Miles / 100 * Avg_Cost_Per_Break + Water_Loss_Value + Emergency_Overtime_Avoidance`
- **Example:** Baseline 30→15 breaks/100mi, 500 miles, $15K/break, $200K water loss, $100K overtime = **$1.425M/year**
- **Confidence:** HIGH if break history available; MEDIUM if using AWWA estimates

### INF-VF-002: Transit OTP Revenue Recovery
**Formula:** `V = (Target_OTP - Baseline_OTP) * Ridership_Elasticity * Annual_Ridership * Avg_Fare + Overtime_Avoidance + CS_Reduction`
- **Example:** 72%→82% OTP, elasticity 0.5, 10M ridership, $2 fare = **$1.8M/year**
- **Confidence:** MEDIUM (elasticity varies by market)

### INF-VF-003: OT Cybersecurity Risk Reduction Value
**Formula:** `V = (Baseline_Incident_Probability - Target) * Estimated_OT_Incident_Cost + Compliance_Avoidance + Insurance_Reduction`
- **Example:** 5%→1% probability, $10M incident cost = **$4.7M/year**
- **Confidence:** MEDIUM (incident cost highly variable)

### INF-VF-004: Bridge Load Posting Elimination Value
**Formula:** `V = SUM(Load_Posted_Bridges * Avg_Detour_Cost * Traffic_Volume) + Emergency_Repair_Avoidance + Grant_Value`
- **Example:** 20 bridges, $50K detour each = **$3M/year**
- **Confidence:** HIGH if NBI and traffic data available

### INF-VF-005: Airport Part 139 Compliance Automation Value
**Formula:** `V = Inspection_FTE_Hours_Reduced * Loaded_Rate + Finding_Remediation_Avoidance + AIP_Gain`
- **Example:** 500 hrs @ $75/hr + $200K remediation + $100K AIP = **$337.5K/year**
- **Confidence:** MEDIUM (AIP gain speculative)

### INF-VF-006: Broadband Deployment Cost Efficiency Gain
**Formula:** `V = (Baseline_Cost - Target_Cost) * Passings + Permitting_Acceleration + Make-Ready_Optimization`
- **Example:** $4K→$3K per passing, 30K passings = **$30.8M program value**
- **Confidence:** MEDIUM (BEAD program new; limited historical data)

### INF-VF-007: SSO/I-I Reduction Value
**Formula:** `V = SSO_Events_Eliminated * Avg_SSO_Cost + Wet_Weather_Avoidance + Consent_Decree_Value + CWA_Penalty_Avoidance`
- **Example:** 15→5 SSOs, $100K avg, $1M treatment, $2M decree = **$4.5M/year**
- **Confidence:** HIGH if SSO log available

### INF-VF-008: Fleet Electrification TCO Savings
**Formula:** `V = (ICE_OandM - EV_OandM) * EVs + Fuel_Savings + Carbon_Credits + Grant_Offset - Infra_Amortized`
- **Example:** 50 EVs, $10K/vehicle savings, $150K fuel, $1M grant = **$1.4M/year**
- **Confidence:** MEDIUM (EV costs evolving)

### INF-VF-009: Distribution Reliability Improvement Value
**Formula:** `V = (Baseline_SAIDI - Target_SAIDI) / 60 * Customers * VOLL + Storm_Hardening_Avoided + Vegetation_Savings`
- **Example:** 240→120 min, 50K customers, $15/hr VOLL = **$4M/year**
- **Confidence:** HIGH if outage cost data available

### INF-VF-010: Smart City IoT Net Operational Value
**Formula:** `V = Traffic_Value + Energy_Savings + Safety_Value + Predictive_Maintenance - Sensor_TCO - Integration_Cost`
- **Example:** $800K+$400K+$300K+$600K - $1.2M - $400K = **$500K net/year**
- **Confidence:** LOW (emerging; limited long-term data)

### INF-VF-011: NextGen 911 Transition Efficiency Value
**Formula:** `V = Legacy_Trunk_Cost_Avoidance + GIS_Dispatch_Value + Staff_Productivity + Text-to-911_Value - NG911_Amortized`
- **Example:** $300K+$500K+$200K+$100K - $800K = **$300K net/year**
- **Confidence:** MEDIUM (NG911 costs vary by state)

### INF-VF-012: Recycling Contamination Reduction Value
**Formula:** `V = Contamination_Reduction% * Tons * (Premium_Cost - Sorting_Cost) + Commodity_Recovery + Landfill_Diversion`
- **Example:** 25%→15% on 50K tons, $10/ton net = **$550K/year**
- **Confidence:** HIGH if MRF cost data available

---

## 7. Vertical Benchmarks (18)

| ID | Metric | Value | Range | Source |
|----|--------|-------|-------|--------|
| INF-BENCH-001 | Water Main Break Rate (National Median) | 25 | 15-35 /100 mi/yr | AWWA / EPA |
| INF-BENCH-002 | Unaccounted-for Water (National Avg) | 16% | 10-25% | AWWA |
| INF-BENCH-003 | Transit OTP (Bus) | 78% | 70-88% | FTA NTD |
| INF-BENCH-004 | Farebox Recovery (Heavy Rail) | 55% | 45-65% | FTA NTD |
| INF-BENCH-005 | SD Bridges (National) | 7.1% | 5-10% | FHWA NBI 2023 |
| INF-BENCH-006 | Bridge Condition Index (State Median) | 72 | 60-85 | FHWA |
| INF-BENCH-007 | ARFF Response Time (Part 139) | 180s | 120-180s | FAA Part 139 |
| INF-BENCH-008 | Airfield PCI (Median) | 74 | 65-85 | FAA AC |
| INF-BENCH-009 | Broadband Unserved (National) | 7.3% | 5-10% | FCC BDC |
| INF-BENCH-010 | BEAD Cost Per Location | $4,500 | $2,500-$8,000 | NTIA |
| INF-BENCH-011 | SSO Rate (National Median) | 8 | 3-15 /100 mi/yr | EPA |
| INF-BENCH-012 | I/I Volume Ratio (Median) | 35% | 20-60% | EPA |
| INF-BENCH-013 | SAIDI (US Median) | 198 min | 100-300 | EIA |
| INF-BENCH-014 | SAIFI (US Median) | 1.4 | 0.8-2.5 | EIA |
| INF-BENCH-015 | 911 Answer Time (90th Pct) | 18s | 10-30s | NENA/FCC |
| INF-BENCH-016 | Recycling Contamination (National) | 25% | 15-35% | EPA/SWANA |
| INF-BENCH-017 | Port Truck Turn Time (Median) | 55 min | 35-80 | PierPass |
| INF-BENCH-018 | DER Interconnection Time (Median) | 180 days | 60-300 | NREL/IREC |

---

## 8. Vertical Signal Rules (18)

| ID | Signal | Raw Pattern | Confidence |
|----|--------|-------------|------------|
| INF-SIG-001 | Water Main Break Escalation | Break rate >25/100 mi; repeat breaks >2/yr; age >50yr CI | 0.90 |
| INF-SIG-002 | Transit Reliability Decline | OTP <75% for 2+ quarters; vacancy >15%; farebox <20% | 0.88 |
| INF-SIG-003 | OT Cybersecurity Exposure | Flat OT network; default passwords; no OT IDS; Win7/XP | 0.92 |
| INF-SIG-004 | Bridge Condition Deterioration | SD% >7%; load postings up; inspection backlog >12mo | 0.90 |
| INF-SIG-005 | Airport Part 139 Risk | Findings >2; ARFF >180s; PCI <70 primary | 0.88 |
| INF-SIG-006 | Broadband Deployment Blockers | Subgrantee delayed >6mo; permitting >50% schedule; MR >30% | 0.85 |
| INF-SIG-007 | Wastewater SSO/I-I Crisis | SSO >10/yr; I/I >50%; consent decree present | 0.92 |
| INF-SIG-008 | Fleet Electrification Blocked | EV procurement >12mo delay; depot capacity insufficient | 0.82 |
| INF-SIG-009 | Distribution Reliability Erosion | SAIDI >240; SAIFI >2.0; major events >5/yr; veg >30% | 0.90 |
| INF-SIG-010 | Smart City Integration Failure | Platforms >5 no central layer; twin stale >30d; uptime <90% | 0.78 |
| INF-SIG-011 | NextGen 911 Transition Lag | Text-to-911 not deployed; CAMA primary; GIS <95%; turnover >15% | 0.88 |
| INF-SIG-012 | Recycling Economics Collapse | Contamination >25%; commodity revenue down >30%; cost >tip fee | 0.85 |
| INF-SIG-013 | Port Throughput Bottleneck | Turn >75min; dwell >6d; chassis <85%; disputes increasing | 0.86 |
| INF-SIG-014 | Utility Affordability Crisis | Shutoff >5%; rate increase >5% for 3yr; delinquency >8% | 0.88 |
| INF-SIG-015 | Fare Revenue Leakage | Evasion >8%; revenue discrepancy >2%; citation collection <30% | 0.82 |
| INF-SIG-016 | PFAS Compliance Urgency | Detection >MCL; pilot not started; lab wait >30d; CWSRF >12mo | 0.90 |
| INF-SIG-017 | Airfield Pavement Failure Risk | PCI <70; FOD >2/yr; crack sealing backlog >12mo | 0.88 |
| INF-SIG-018 | DER Interconnection Grid Lock | Queue >1,000; review >180d; rejection >40%; no hosting map | 0.86 |

---

## 9. Regulatory Factors (10)

### INF-REG-001: Safe Drinking Water Act (SDWA)
- **Regulation:** 42 U.S.C. 300f; 40 CFR Parts 141-143
- **Deadline:** Continuous; LCRR 2024; PFAS MCL 2024-2029
- **Penalty:** Up to $66,086/day; consent decrees; criminal liability
- **Segments:** Water Utilities

### INF-REG-002: EPA Consent Decrees
- **Regulation:** CWA 33 U.S.C. 1251; SDWA 42 U.S.C. 300f; DOJ/EPA settlement
- **Deadline:** Court-imposed; 10-20 year schedule
- **Penalty:** Contempt; stipulated penalties ($5K-$100K+ per violation)
- **Segments:** Water, Wastewater

### INF-REG-003: FTA Requirements (49 CFR)
- **Regulation:** 49 CFR Parts 630-674; NTD; ADA; Title VI; DBE
- **Deadline:** Continuous; triennial reviews
- **Penalty:** Withhold; repayment; suspension; debarment
- **Segments:** Public Transit

### INF-REG-004: FAA Part 139
- **Regulation:** 14 CFR Part 139; AC 150/5200 series; ARFF; pavement standards
- **Deadline:** Continuous; biennial inspections
- **Penalty:** Certificate action; civil penalty; emergency order
- **Segments:** Airports

### INF-REG-005: FERC / NERC CIP
- **Regulation:** 16 CFR Part 824; 18 CFR Parts 35-39; NERC CIP-002 to CIP-014
- **Deadline:** Continuous; compliance audits every 3 years
- **Penalty:** Up to $1.5M per violation per day
- **Segments:** Energy, Grid

### INF-REG-006: BEAD / NTIA Broadband Programs
- **Regulation:** IIJA Division F; 47 U.S.C. 1301
- **Deadline:** Subgrantee selection 2024-2025; build completion by 2029-2030
- **Penalty:** Funding clawback; corrective action; delay of future allocations
- **Segments:** Broadband

### INF-REG-007: Clean Water Act NPDES
- **Regulation:** 33 U.S.C. 1251; 40 CFR Parts 122-136
- **Deadline:** Permit renewal every 5 years; SSO reporting within 24 hours
- **Penalty:** Up to $66,086/day; consent decrees; criminal for endangerment
- **Segments:** Wastewater

### INF-REG-008: NextGen 911 / FCC Regulations
- **Regulation:** 47 CFR 20.18; FCC Report and Order 15-9; NENA i3
- **Deadline:** Text-to-911 deployed; location accuracy deadlines ongoing
- **Penalty:** FCC enforcement; state funding withholding; liability
- **Segments:** Emergency Communications

### INF-REG-009: State RPS / ZEV Mandates
- **Regulation:** State-specific RPS; ZEV mandates; fleet electrification orders
- **Deadline:** 2030-2050 targets
- **Penalty:** State enforcement; loss of incentives; compliance payments
- **Segments:** Energy, Transit, Public Works

### INF-REG-010: IIJA / IRA Formula Fund Compliance
- **Regulation:** Pub.L. 117-58; Pub.L. 117-169; Buy America; Davis-Bacon; equity screening
- **Deadline:** Obligation deadlines (3-5 years); project completion per award
- **Penalty:** Lapse of funds; repayment; suspension from future awards
- **Segments:** All infrastructure segments

---

## 10. Technology Systems (12)

### INF-TECH-001: SCADA / AMI
- **Category:** Infrastructure Operations
- **Vendors:** Schneider Electric, Siemens, Itron, Sensus, Aclara, Badger Meter, Honeywell
- **Integrations:** GIS, CMMS, Billing, ADMS, Analytics, Customer portal
- **Segments:** Water, Energy, Grid

### INF-TECH-002: GIS / Asset Management (EAM)
- **Category:** Infrastructure Planning
- **Vendors:** Esri (ArcGIS), Cartegraph, Cityworks, IBM Maximo, Infor EAM, Hexagon
- **Integrations:** SCADA, CMMS, ERP, Finance, Permitting, Mobile workforce
- **Segments:** Water, Wastewater, Roads, Energy, Smart City

### INF-TECH-003: CMMS
- **Category:** Maintenance Operations
- **Vendors:** IBM Maximo, Infor EAM, Hippo, UpKeep, Fiix, eMaint, MPulse
- **Integrations:** EAM, ERP, SCADA, Fleet, Inventory, Mobile
- **Segments:** Water, Wastewater, Transit, Roads, Airports, Energy

### INF-TECH-004: ITS / AVL
- **Category:** Transit Operations
- **Vendors:** Clever Devices, Trapeze, GMV Syncromatics, Avail, Init
- **Integrations:** CAD/AVL, AFC, GTFS, Traffic signals, Passenger apps
- **Segments:** Transit, Smart City

### INF-TECH-005: AFC (Automated Fare Collection)
- **Category:** Transit Revenue
- **Vendors:** Cubic, INIT, Scheidt & Bachmann, Conduent, Flowbird, Masabi
- **Integrations:** Revenue reconciliation, Banking, Mobile app, GTFS, Rider account
- **Segments:** Transit

### INF-TECH-006: ADMS / DMS
- **Category:** Grid Operations
- **Vendors:** GE Digital, OSIsoft, Schneider Electric, Siemens, Survalent, Trimble
- **Integrations:** SCADA, OMS, AMI, GIS, DERMS, Market systems
- **Segments:** Energy, Grid

### INF-TECH-007: OMS (Outage Management System)
- **Category:** Grid Operations
- **Vendors:** GE Digital, OSIsoft, Sensus, Milsoft, Nexant, Hexagon
- **Integrations:** AMI, ADMS, GIS, IVR, Mobile workforce, Customer portal
- **Segments:** Energy, Grid

### INF-TECH-008: Pavement / Bridge Management System
- **Category:** Roads/Bridges Asset Management
- **Vendors:** AgileAssets, Bentley (dTIMS), Deighton, Arcadis, StreetSaver, Roadsoft
- **Integrations:** GIS, NBI, Finance, Project management, Inspection data
- **Segments:** Roads, Bridges

### INF-TECH-009: Airport Operations Management System (AOMS)
- **Category:** Airport Operations
- **Vendors:** Amadeus, INFORM, UltraFIDS, Resa, Veovo, T-Systems
- **Integrations:** FIDS, AOA, ARFF, Snow plan, FAA systems, Airlines
- **Segments:** Airports

### INF-TECH-010: FOD Detection System
- **Category:** Airport Safety
- **Vendors:** Xsight Systems (FODetect), Trex Aviation, Stratech (iFerret), Pavemetrics
- **Integrations:** Airport operations center, Maintenance dispatch, Incident reporting
- **Segments:** Airports

### INF-TECH-011: Broadband Mapping / Availability System
- **Category:** Broadband Planning
- **Vendors:** CostQuest, LightBox, BroadbandNow, Caliper, Esri, Biarri Networks
- **Integrations:** FCC BDC, NTIA reporting, GIS, Permitting, Subgrantee systems
- **Segments:** Broadband

### INF-TECH-012: NG911 ESInet / i3 Platform
- **Category:** Emergency Communications
- **Vendors:** Hexagon, Motorola Solutions, L3Harris, NICE, RapidDeploy, Carbyne
- **Integrations:** GIS, PSAP CPE, FirstNet, Text-to-911, Alarm systems
- **Segments:** Emergency Communications

---

## 11. Discovery Questions (18)

1. **INF-DQ-001** — What is your current water main break rate per 100 miles, and how has it trended over the past five years? *(Target: Water Utility Director, CFO)*
2. **INF-DQ-002** — How do you currently track and report on-time performance, and what is your target versus actual for the last 12 months? *(Target: Transit GM)*
3. **INF-DQ-003** — Describe your current OT/ICS cybersecurity posture. Is your SCADA network segmented from IT? *(Target: Grid Engineer, Water Director)*
4. **INF-DQ-004** — What percentage of your bridge inventory is structurally deficient, and what is your annual rehabilitation spend? *(Target: Public Works Director)*
5. **INF-DQ-005** — What was the outcome of your most recent FAA Part 139 inspection? *(Target: Airport Operations Manager)*
6. **INF-DQ-006** — Where are you in the BEAD subgrantee selection process, and what are your biggest deployment blockers? *(Target: Broadband Director)*
7. **INF-DQ-007** — How many SSO events did you report last year, and what is your I/I volume ratio? *(Target: Water Director)*
8. **INF-DQ-008** — What is your fleet electrification target, and have you assessed depot electrical capacity? *(Target: Transit GM, Public Works Director)*
9. **INF-DQ-009** — What are your SAIDI and SAIFI figures, and how much is attributable to major events? *(Target: Grid Engineer)*
10. **INF-DQ-010** — How many IoT/sensor platforms are deployed, and is the data integrated centrally? *(Target: Broadband Director, City CIO)*
11. **INF-DQ-011** — What is your 911 call answer time at the 90th percentile, and have you deployed NG911? *(Target: 911 Director)*
12. **INF-DQ-012** — What is your recycling contamination rate, and how has commodity revenue trended? *(Target: Public Works Director)*
13. **INF-DQ-013** — What is your average truck turn time, and how do you manage container dwell? *(Target: Airport/Port Operations)*
14. **INF-DQ-014** — What percentage of accounts are shut off annually, and how do you manage affordability programs? *(Target: Water Director, CFO)*
15. **INF-DQ-015** — What is your observed fare evasion rate, and what percentage of citations are collected? *(Target: Transit GM)*
16. **INF-DQ-016** — Have you detected PFAS in your source water, and what is your treatment upgrade timeline? *(Target: Water Director)*
17. **INF-DQ-017** — What is the condition of your primary runway by PCI, and when was the last survey? *(Target: Airport Operations Manager)*
18. **INF-DQ-018** — How many DER interconnection requests are pending, and what is your average review time? *(Target: Grid Engineer)*

---

## 12. Objection Patterns (9)

### INF-OBJ-001: "We already have a capital improvement plan."
**Counter:** Validate CIP funding ratio vs. EPA/AWWA documented need. Identify whether the pain has an operational/digital dimension not in the CIP. Frame as CIP acceleration, not replacement.

### INF-OBJ-002: "Our rates are already too high."
**Counter:** Quantify reactive cost as % of operating budget. Show how technology reduces emergency spend and deferrable rate increases. Reference EPA affordability framework (combined water+wastewater <4.5% MHI).

### INF-OBJ-003: "We are a small system / agency."
**Counter:** Reference shared-services, cooperative purchasing, and cloud-based delivery. Cite EPA small system compliance assistance and rural utility service programs.

### INF-OBJ-004: "We have grants already covering this."
**Counter:** Map grant lifecycle: application → award → obligation → match → O&M. Identify gaps where technology, planning, or compliance support is not grant-eligible but required for success.

### INF-OBJ-005: "Our SCADA is air-gapped; cybersecurity is not a concern."
**Counter:** Request network diagram walkthrough. Reference CISA Alert AA22-103A and EPA guidance. Offer OT-safe assessment that does not disrupt operations.

### INF-OBJ-006: "Our riders won't accept fare enforcement or new technology."
**Counter:** Separate AFC technology (tap-to-pay, mobile) from enforcement. Reference TransitCenter and UCLA equity studies. Demonstrate how modern AFC improves equity (auto-enrollment in discount programs).

### INF-OBJ-007: "We tried smart city / digital twin before and it failed."
**Counter:** Acknowledge failure mode. Propose phased approach with clear operational owner, open standards, and measurable pilot KPIs. Reference NIST smart city framework.

### INF-OBJ-008: "Our labor union will block automation."
**Counter:** Frame as upskilling and safety improvement, not headcount reduction. Reference labor-management partnership examples. Involve union early in design.

### INF-OBJ-009: "We need to wait for our next budget cycle."
**Counter:** Map alternative funding (grants, low-interest loans, performance contracting, cooperative purchasing). Demonstrate that delay increases risk and cost. Pilots often fit within existing O&M budgets.

---

## 13. Worked Examples (3)

### INF-EX-001: Water Utility — Pipe Replacement ROI
**Scenario:** Mid-sized water utility, 800 miles, break rate 32/100 mi/year, 60% cast iron >50 years. Annual emergency cost $4.4M.
**Intervention:** Risk-based replacement at 1.5%/year (12 miles) with GIS prioritization and trenchless technology.
**Assumptions:** 40% break reduction on replaced segments; trenchless reduces restoration 25%; SRF loan at 2%.
**Result:** Break rate reduced to 18/100 mi by Year 5. Annual savings $2.8M. Implementation $2.0M/year. **Net annual value $800K by Year 5; 3.2-year payback; 10-year NPV $6.2M.**
**Confidence:** HIGH

### INF-EX-002: Transit Agency — OTP and Ridership Recovery
**Scenario:** Urban transit, 12M pre-pandemic ridership, currently 8M. OTP 73%, farebox recovery 22%, operator vacancy 18%.
**Intervention:** ITS/AVL with real-time dispatch, AFC upgrade to account-based mobile tap, operator retention program.
**Assumptions:** OTP +10pp → 4% ridership elasticity; overtime reduction 30%; evasion 9%→5%.
**Result:** OTP 83% by Month 12; ridership 8.6M. **Net annual value $2.49M; 2.1-year payback; 3-year NPV $5.8M.**
**Confidence:** MEDIUM

### INF-EX-003: Municipal Electric — SAIDI/SAIFI Reduction
**Scenario:** 45K customers, SAIDI 280 min, SAIFI 2.2. 60% overhead, vegetation 38% of outages.
**Intervention:** ADMS with outage prediction; 15% worst feeder hardening; LiDAR vegetation management.
**Assumptions:** ADMS reduces SAIDI 20% on targeted circuits; hardening reduces storm impact 40%; IRA grant covers 50%.
**Result:** SAIDI 175 min by Year 3; SAIFI 1.6. **Net annual value $860K; 4.8-year payback; 10-year NPV $5.9M.**
**Confidence:** MEDIUM

---

## 14. Buying Triggers (14)

| ID | Trigger | Timing | Segments |
|----|---------|--------|----------|
| INF-BT-001 | EPA enforcement or consent decree | 0-12 months | Water, Wastewater |
| INF-BT-002 | FAA Part 139 findings or certificate action | 0-6 months | Airports |
| INF-BT-003 | BEAD award and initial proposal deadline | 0-18 months | Broadband |
| INF-BT-004 | Major service disruption (break, strike, outage, closure) | 0-3 months | Water, Transit, Roads, Energy |
| INF-BT-005 | Ransomware/OT incident in peer utility (CISA alert) | 0-6 months | Water, Energy, Transit, Grid |
| INF-BT-006 | New state ZEV mandate or federal fleet deadline | 12-36 months | Transit, Public Works, Airports |
| INF-BT-007 | PFAS MCL final rule or state MCL adoption | 6-24 months | Water |
| INF-BT-008 | Rate case filing or affordability study | 6-18 months | Water, Energy |
| INF-BT-009 | New FTA Administrator or triennial review | 6-12 months | Transit |
| INF-BT-010 | NERC CIP audit notice or violation deadline | 0-12 months | Energy, Grid |
| INF-BT-011 | NG911 state plan approval or PSAP consolidation | 6-24 months | Emergency Communications |
| INF-BT-012 | IIJA/IRA grant obligation deadline (lapse risk) | 6-18 months | Roads, Broadband, Grid, Airports, Ports |
| INF-BT-013 | Board/council climate resilience directive | 6-18 months | Water, Energy, Roads, Smart City |
| INF-BT-014 | Staffing crisis reaching service cut threshold | 0-6 months | Transit, Public Works, Energy |

---

## 15. Governance

| Attribute | Value |
|-----------|-------|
| Source Coverage | Mixed (Federal agency data, industry associations, research organizations, vendor benchmarks) |
| Confidence | HIGH |
| Last Updated | 2025-01-21 |
| Approved for Customer-Facing Output | YES |
| Review Owner | Infrastructure & Utilities Vertical Agent (Phase 2) |
| Agent Swarm ID | infra-utilities-swarm-001 |
| Parent Master Swarm ID | public-sector-master-swarm-001 |

---

*This subpack is a vertical extension of the Public Sector Master Pack (`public-sector-master-v1`). All master components remain valid and applicable. For complete taxonomy, base personas, and governance framework, refer to the master pack.*
