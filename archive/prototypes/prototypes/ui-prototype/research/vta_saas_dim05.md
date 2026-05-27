# Dimension 05: Digital Weight Elicitation -- SMART, SWING, AHP Methods

## Research Findings: Translating VTA Weighting into SaaS Capabilities

---

### Finding 1: TransparentChoice AHP-Based Decision Support Platform

```
Claim: TransparentChoice provides web-based pairwise comparison interfaces for criteria weighting using the AHP method, enabling structured collaborative surveys for organizational decision-making [^29^].
Source: TransparentChoice Official Website
URL: https://www.transparentchoice.com/software/decision-support
Date: Unknown (current)
Excerpt: "Use pairwise comparisons to assign relative importance -- all backed by decision science. Score each option against the criteria to get a clear, ranked list -- and total transparency."
Context: TransparentChoice is a commercial SaaS platform implementing AHP for portfolio prioritization and strategic decision-making. It replaces the desktop-based MakeItRational software.
Confidence: high
```

### Finding 2: AHP Pairwise Comparison with Slider-Based UI

```
Claim: A web-based open-source AHP tool uses slider controls for pairwise comparisons, implementing all calculations client-side for privacy-first decision making [^26^].
Source: GitHub - gbrlpzz/pairwise
URL: https://github.com/gbrlpzz/pairwise
Date: 2024-12-19
Excerpt: "Compare two criteria at a time. Use a slider to indicate which is more important and by how much. The tool will guide you through all necessary comparisons."
Context: This vanilla JavaScript implementation demonstrates how AHP pairwise comparisons can be implemented entirely in-browser with slider-based UI components, requiring no server or account.
Confidence: high
```

### Finding 3: 1000minds PAPRIKA Method -- Adaptive Pairwise Comparisons

```
Claim: 1000minds implements the PAPRIKA method, which uses adaptive pairwise comparisons of hypothetical alternatives differing on only two criteria at a time, requiring approximately 25 questions for a typical 4-attribute decision problem [^28^].
Source: 1000minds Official Website
URL: https://www.1000minds.com/paprika
Date: Unknown (current)
Excerpt: "Compared to other methods, the advantage of PAPRIKA's questions is that they involve just two alternatives differentiated on two criteria at a time. These are the easiest possible questions involving trade-offs to think about."
Context: PAPRIKA is a patented method that adaptively selects pairwise questions in real-time, computing preference values (weights) via linear programming. It was rated highest for clarity and usability in a patient preference study comparing five methods.
Confidence: high
```

### Finding 4: PAPRIKA Rated Top Preference Elicitation Method in Clinical Study

```
Claim: In a cross-sectional study of 123 participants comparing five preference elicitation methods, PAPRIKA received the highest ratings for clarity, usability, and perceived ability to express preferences, outperforming direct weighting, best-worst scaling, time trade-off, and standard gamble [^27^].
Source: PubMed Central / BMC Medical Informatics and Decision Making
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC12659191/
Date: 2025 (publication)
Excerpt: "Across all measures, the PAPRIKA method received the highest ratings for clarity, usability, and perceived ability to express preferences. Simpler methods (best-worst scaling, direct weighting) were rated as less useful for capturing nuanced preferences."
Context: The study evaluated methods for shared decision-making in healthcare, suggesting that interactive pairwise methods strike the best balance between cognitive demand and expressiveness.
Confidence: high
```

### Finding 5: AHP-WEB -- Reduced-Comparison Group Decision Software

```
Claim: AHP-WEB is an open-source web-based AHP system that reduces required comparisons from (n^2-n)/2 to n-1 per cluster while supporting group decision-making through geometric mean aggregation of individual priorities [^34^].
Source: ScienceDirect / MethodsX
URL: https://www.sciencedirect.com/science/article/pii/S2215016123002741
Date: 2023-12-27
Excerpt: "The original AHP formulation requires (n^2-n)/2 comparisons per cluster which makes it difficult to make consistent judgments... The proposed system AHP-WEB fills these gaps. The method demands n-1 comparisons per cluster without any inconsistency and allows group decision making on a web system."
Context: The system (https://ahpweb.net/) addresses three AHP limitations: excessive comparisons, consistency difficulties, and lack of free group decision software. It has over 100 active users.
Confidence: high
```

### Finding 6: AHP-OS -- Comprehensive Web-Based AHP System with 5000+ Users

```
Claim: AHP-OS is a free web-based AHP system implementing eigenvector weight calculation, group decision-making with Shannon entropy-based consensus measurement, Monte Carlo weight uncertainty estimation, and sensitivity analysis, serving over 5000 registered users [^55^].
Source: International Journal of the Analytic Hierarchy Process
URL: https://bpmsg.com/ahp/
Date: 2018 (paper); 2024 (active)
Excerpt: "With currently implemented functionality the software tool has reached a state where it covers most of the possible options for the classical analytic hierarchy process... more than 5000 users have registered... at least 500 active users over a three months period."
Context: Written in PHP with SQL database, AHP-OS provides full decision hierarchy definition, pairwise comparison input highlighting top-3 inconsistent judgments, partial judgments, multiple AHP scales, and CSV/JSON export.
Confidence: high
```

### Finding 7: Innovative 2D Plot UI Widget for Consistent AHP Pairwise Comparisons

```
Claim: A research team developed a 2D plot UI widget for AHP pairwise comparisons that enforces transitivity automatically, reducing required clicks by 36% compared to traditional questionnaire widgets while maintaining comparable consistency ratios [^46^].
Source: HAL Archives / IMT Mines Albi
URL: https://imt-mines-albi.hal.science/hal-03449934v1/file/A-user-interface-for-consistent-AHP-pairwise-comparisons.pdf
Date: 2022-03-10
Excerpt: "The widget forces the transitivity property... Moving one handle simultaneously expresses how the item compares to the anchored one, and to all other items... the 2D Plot requires significantly less effort with significance value (P-value) of 0.0001."
Context: In a user study with 37 participants, the 2D plot widget required 10.78 clicks mean (vs. 16.76 for questionnaire) and achieved similar time performance. The widget inherits transitivity properties from comparison functions in real numbers.
Confidence: high
```

### Finding 8: MCDA Index Tool -- Web-Based Index Development with Uncertainty Analysis

```
Claim: The MCDA Index Tool (https://www.mcdaindex.net/) is a web-based software supporting normalization method selection, aggregation function choice, weighting, uncertainty analysis, and sensitivity analysis for composite indicator development [^30^].
Source: PubMed Central / Environmental Modeling and Assessment
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC7365520/
Date: 2019-12-21 (published); 2020
Excerpt: "A web-based software, called MCDA Index Tool, is presented... it allows developing indices and ranking alternatives, based on multiple combinations of normalization methods and aggregation functions."
Context: The tool enables CSV data upload, indicator polarity definition, weight selection, normalization and aggregation choice, and extensive visualization including bar charts, rank frequency matrices, and ranking line charts.
Confidence: high
```

### Finding 9: SMART Method -- Digital Implementation in Android Application

```
Claim: The SMART method has been implemented in mobile/Android decision support applications with structured comparison pages that perform all SMART calculation steps in the background based on user-input criteria and alternative weights [^36^].
Source: International Journal of Computer Applications
URL: https://www.ijcaonline.org/archives/volume186/number4/hidayat-2024-ijca-923383.pdf
Date: 2024
Excerpt: "The SMART method decision support system is implemented into an Android application which has an interface that makes it easier to make a decision... the comparison page will perform all the SMART method calculation steps in the background."
Context: This demonstrates that SMART's relatively simple algorithm (rank ordering, establishing reference points, estimating relative importance) translates well to digital interfaces including mobile apps.
Confidence: medium
```

### Finding 10: SMART and SMARTER Weighting Methods -- Formal Specifications

```
Claim: SMART assigns 10 points to the least important criterion, then rates others relatively; SMARTER uses rank order centroid weights from formula wk = (1/K) * sum(1/i) for i=k to K, achieving 98-99% of SMARTS utility without requiring difficult swing weight judgments [^62^].
Source: Academic Paper (Edwards & Barron, 1994)
URL: https://fsi9-prod.s3.us-west-1.amazonaws.com/s3fs-public/smarts_and_smarter.pdf
Date: 1994
Excerpt: "SMARTER is a dramatic improvement on SMARTS in ease of elicitation. A returnable postcard can hold a SMARTER elicitation for prespecified attributes; interviews are not needed... likely to appeal to market researchers, public involvement specialists."
Context: SMARTER eliminates the most cognitively demanding step (swing weighting) while maintaining accuracy, making it particularly suitable for SaaS implementations requiring remote/self-service elicitation.
Confidence: high
```

### Finding 11: Swing Weighting -- Four-Step Digital Implementation Model

```
Claim: Swing weighting can be implemented digitally through four steps: (1) rank order attributes by importance of incremental changes, (2) establish reference attribute (most important = 100 points), (3) estimate importance of other attributes relative to reference, and (4) calculate normalized weights as ratios of point totals [^51^].
Source: MDPI Applied Sciences
URL: https://www.mdpi.com/2076-3417/11/21/10397
Date: 2021-11-05
Excerpt: "The SWING Weighting technique is comprised of the following four steps: (1) rank order attributes, (2) establish the reference attribute, (3) estimate importance of other attributes with respect to the reference attribute, and (4) calculate weights."
Context: The number of questions scales linearly (n-1 questions for n attributes). SWING considers the full range of attribute variation, making it more decision-context-sensitive than simple ranking methods.
Confidence: high
```

### Finding 12: Swing Weight Matrix -- Automated Excel Tool with Real-Time Updates

```
Claim: An automated swing weight matrix tool in Excel using macros enables real-time weight updates as analysts drag-and-drop value measures between cells, with pre-assigned unnormalized weights that stakeholders can adjust [^63^].
Source: INCOSE / Missouri S&T
URL: https://web.mst.edu/lib-circ/files/Special%20Collections/INCOSE/Using%20the%20Swing%20Weight%20Matrix%20to%20Weight%20Multiple%20Objectives.pdf
Date: Unknown
Excerpt: "The second innovation was the development of an automated swing weight matrix tool in Excel that used macros to automate weighting functions... the analyst could move a value measure to another cell with the mouse automatically updating the swing weights and all of the decision analysis results."
Context: This demonstrates the feasibility of interactive drag-and-drop interfaces for swing weighting in SaaS. Stakeholders preferred pre-assigned weights to more detailed assessment processes.
Confidence: high
```

### Finding 13: Rank-Based Weighting Formulas -- Rank Sum, Rank Reciprocal, Rank Exponent

```
Claim: Rank-based weighting methods include: Rank Sum (weight = n-r+1), Reciprocal Rank (weight = 1/r), and Rank Exponent (weight = (n-r+1)^p where p controls distribution steepness), all easily implementable in spreadsheet or web-based tools [^44^].
Source: GITTA (Geographic Information Technology Training Alliance)
URL: http://www.gitta.info/Suitability/en/html/Normalisatio_learningObject1.html
Date: 2013-11-26
Excerpt: "Rank sum: With n criteria, rank r receives the weight n-r+1. Reciprocal rank: With n criteria, rank r receives the weight 1/r. Rank exponent: With n criteria, rank r receives the weight (n-r+1)^p."
Context: These methods are computationally simple and suitable for web implementation. Weighting by ranking is popular because it is easy, though results should be interpreted cautiously with many criteria.
Confidence: high
```

### Finding 14: Consistency Ratio Calculation in Web Applications

```
Claim: Web-based AHP tools calculate the Consistency Ratio (CR) as CI/RI where CI = (lambda_max - n)/(n-1), comparing against Saaty's threshold of CR <= 0.1, with tools like SpiceLogic displaying CR in red bold when it exceeds the threshold [^39^].
Source: SpiceLogic AHP Software Documentation
URL: https://spicelogic.com/docs/ahpsoftware/intro/ahp-consistency-ratio-transitivity-rule-388
Date: Unknown (current)
Excerpt: "Consistency Ratio = Consistency Index / Random Index... According to Thomas L. Saaty, the consistency ratio should be less or equal to 0.1. If your Consistency ratio goes over 0.1, the software will indicate that using a Red bold color."
Context: The CR calculation is standard across AHP implementations. Web apps can compute this in real-time as users enter pairwise judgments, providing immediate feedback on consistency.
Confidence: high
```

### Finding 15: AHP Online Calculator -- Free Web-Based Priority Calculator

```
Claim: The AHP Online Calculator (part of AHP-OS) allows users to input 2-20 criteria, perform pairwise comparisons on a 1-9 scale, and receive priorities, rankings, and consistency ratios calculated using the eigenvector method [^43^].
Source: BPMSG AHP Online Calculator
URL: https://bpmsg.com/ahp-online-calculator/
Date: 2013-11-10 (updated)
Excerpt: "Calculate priorities from pairwise comparisons using the analytic hierarchy process (AHP) with eigen vector method... the three judgments with highest inconsistency will be highlighted, with the last column showing the recommended judgment for lowest consistency ratio."
Context: This free tool demonstrates core AHP computation capabilities that can be embedded in SaaS platforms, including CSV export and inconsistency highlighting for guided judgment revision.
Confidence: high
```

### Finding 16: Fuzzy AHP Software -- Web-Based with Excel Integration

```
Claim: Fuzzy AHP Software provides a web-based interface for hierarchical chart drawing, fuzzy scale selection, pairwise comparison tables, and complete reporting with inconsistency ratios, supporting direct copy-paste from Excel [^38^].
Source: OnlineOutput Fuzzy AHP Software
URL: https://onlineoutput.com/fuzzy-ahp-software/
Date: 2025-10-09
Excerpt: "Easily copy and paste data directly from Excel. Customize each project according to your requirements... Display and download hierarchical graph. The relative weights of criteria, sub-criteria, and alternatives... Inconsistency ratio for each pair wise comparison matrix."
Context: This demonstrates advanced AHP extensions (fuzzy logic) in SaaS form with no installation required, supporting unlimited criteria/sub-criteria and alternatives.
Confidence: medium
```

### Finding 17: Web-HIPRE -- Java Applet for Value Tree and AHP Analysis

```
Claim: Web-HIPRE (HIerarchical PREference analysis on the World Wide Web) is a web-based multiattribute decision support system supporting AHP, MAVT, and value tree analysis via a Java applet interface, developed at Aalto University [^88^].
Source: Aalto University / Web-HIPRE Documentation
URL: https://hipre.aalto.fi/WebHIPRE.pdf
Date: Unknown (early 2000s)
Excerpt: "Web-HIPRE = HIerarchical PREference analysis in the World Wide Web. Successor of the decision support software HIPRE 3+. Unlimited global access."
Context: Web-HIPRE was one of the first web-based MCDA tools, supporting both absolute and relative measurement modes, inconsistency checks, sensitivity analysis with tornado diagrams, and group priority aggregation.
Confidence: high
```

### Finding 18: D-Sight -- Visual Interactive MCDA Tool with PROMETHEE and MAUT

```
Claim: D-Sight is a visual and interactive tool for multicriteria decision aid based on PROMETHEE methods and Multi-Attribute Utility Theory, available in both web and desktop versions with group decision support including weighting of group members [^41^].
Source: MCDM Society Software Directory
URL: https://www.mcdmsociety.org/2025/01/12/software/
Date: 2025-01-12
Excerpt: "D-Sight, visual and interactive tool for multicriteria decision aid problems based on the PROMETHEE methods and Multi-Attribute Utility Theory."
Context: D-Sight (http://www.d-sight.com/) offers academic licenses at 249 euros and corporate licenses from 1,990 euros. It supports group model building with weighting of individual group members.
Confidence: medium
```

### Finding 19: MCDA Software Comparison -- 1000Minds, MakeItRational, Web-HIPRE

```
Claim: A comprehensive comparison of 24 MCDA software packages found that 1000Minds, MakeItRational, D-Sight, and Web-HIPRE all support group decision models, with 1000Minds offering decision surveys and online voting, MakeItRational averaging individual results, and Web-HIPRE providing weighted group models [^45^].
Source: University of Jyvaskyla / Annex 7.5.13
URL: https://jyx.jyu.fi/bitstream/handle/123456789/49477/1/Annex7.5.13ComparisonofMultiCriteriaDecisionAnalyticalSoftware.pdf
Date: 2013-02-19
Excerpt: "1000Minds: Decision survey, online voting. MakeItRational: Averaging of individual results into group result. D-Sight: Weighting of group members. Web-HIPRE: Weighted group model."
Context: This comparison highlights the variety of approaches to group weight elicitation in MCDA software, from survey-based aggregation to weighted geometric mean methods.
Confidence: high
```

### Finding 20: PriEsT -- Open-Source Priority Estimation Tool with Multiple Methods

```
Claim: PriEsT is an open-source decision support tool implementing AHP with graphical and equalizer views for pairwise comparisons, evolutionary multi-objective optimization for non-dominated solutions, and all widely-used prioritization methods for research [^79^].
Source: White Rose ePrints / University of Manchester
URL: https://eprints.whiterose.ac.uk/id/eprint/102702/1/manuscript.pdf
Date: 2015 (published)
Excerpt: "PriEsT can assist DMs to interactively explore and revise their judgments based on the congruence and dissonance measures... offers multiple equally-good solutions using multi-objective optimization."
Context: Unlike commercial tools offering single solutions, PriEsT provides Pareto-optimal solution sets, giving decision-makers flexibility. The "equalizer view" offers an innovative graphical pairwise comparison interface.
Confidence: high
```

### Finding 21: Weight Visualization Techniques for MCDA

```
Claim: Standard visualization techniques for MCDA weight data include bar charts, pie charts, scatter plots, value paths, radar/spider-web charts, and multiway dot plots, with more advanced techniques including tornado diagrams for sensitivity analysis [^82^].
Source: PubMed Central / Visualization of Uncertain Data in MCDA
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10113868/
Date: 2023
Excerpt: "Amongst the basic visualization techniques, Miettinen distinguishes bar charts, scatter plots, value paths, multiway dot plots, star coordinate systems, spider-web charts, petal diagrams... Korhonen and Wallenius... adding line charts, pie charts, boxplots, and radar charts."
Context: For SaaS VTA platforms, bar charts (horizontal or vertical) are most effective for displaying criterion weights, while pie charts effectively show part-whole relationships. Tornado diagrams are particularly valuable for sensitivity analysis showing how weight changes affect rankings.
Confidence: high
```

### Finding 22: AHP Software with Slider-Based Comparisons (Vue.js)

```
Claim: A Vue.js-based web application for mining method selection implements AHP with intuitive slider buttons for pairwise comparison matrix manipulation, exporting projects as JSON for persistence [^93^].
Source: GitHub - mafmine_ahp
URL: https://github.com/higorjsc/mafmine_ahp
Date: 2025-02-13
Excerpt: "User-friendly design with slider buttons for manipulating matrices and performing pairwise comparisons... Provides a clear presentation of results through a priority vector."
Context: Built with Vue.js, JavaScript ES6+, HTML5, and CSS3, this demonstrates modern frontend frameworks can effectively implement AHP slider interfaces with local storage persistence.
Confidence: medium
```

### Finding 23: NAARM AHP Analyser -- Web-Based Expert System

```
Claim: The NAARM AHP Analyser is a web-based expert system for group decision making via pairwise comparison, with modified consistency ratio thresholds specifically calibrated for agricultural research projects [^40^].
Source: NAARM (National Academy of Agricultural Research Management)
URL: https://naarm.org.in/ahp/
Date: Unknown (current)
Excerpt: "AHP Analyser is online tool that facilitates the group decision making by pairwise comparison based on expert judgment values... The threshold limits of CR values have been modified for agricultural research projects."
Context: This demonstrates domain-specific adaptation of AHP consistency thresholds in web-based tools, supporting project prioritization, priority setting, and technology valuation.
Confidence: medium
```

### Finding 24: Swing Weighting in Excel -- Hypothetical Alternatives Method

```
Claim: Swing weighting can be implemented in spreadsheet tools by developing hypothetical alternatives (number = attributes + 1), ranking them, assigning overall utility scores (worst = 0, first-ranked = 100), and computing weights as score ratios [^91^].
Source: Decision Modeling Using Excel (University Text)
URL: https://people.utm.my/shamsul/wp-content/uploads/sites/949/2016/06/Decision-Modeling.pdf
Date: Unknown
Excerpt: "The swing weight method involves four steps: 1) Develop the hypothetical alternatives... 2) Rank the hypothetical alternatives... 3) Assign overall utility scores... 4) Sum the scores... the weight for each attribute equals the score divided by sum of the scores."
Context: This structured approach translates directly to SaaS: present users with hypothetical alternatives showing one attribute at best and others at worst, collect rankings and scores, compute weights automatically.
Confidence: high
```

### Finding 25: Expert Choice -- Pioneer AHP Software with Group Decision Support

```
Claim: Expert Choice is professional AHP software developed by AHP creator Thomas Saaty, offering hierarchical structures, pairwise comparisons, priority synthesis, consistency ratio checks, sensitivity analysis, and group decision-making capabilities [^66^].
Source: WifiTalents AHP Software Review
URL: https://wifitalents.com/best/ahp-software/
Date: 2026-03-12
Excerpt: "Expert Choice is a pioneering software solution specifically designed for the Analytic Hierarchy Process... As one of the original AHP tools developed by AHP creator Thomas Saaty, it provides validated methodologies trusted in professional settings."
Context: Expert Choice represents the traditional desktop-based approach that modern SaaS platforms seek to replace. Its core features (pairwise comparison, CR checking, sensitivity analysis) define the baseline for web-based AHP tools.
Confidence: high
```

### Finding 26: Super Decisions -- Free Desktop AHP/ANP Software

```
Claim: Super Decisions, developed by the Creative Decisions Foundation, is free software implementing both AHP and the Analytic Network Process (ANP) for modeling interdependent decision criteria, available for Windows and Mac [^69^].
Source: Super Decisions Official Website
URL: https://www.superdecisions.com/
Date: Unknown (current)
Excerpt: "SuperDecisions is decision making software based on the Analytic Hierarchy Process (AHP) and the Analytic Network Process (ANP). Decision making is all about setting priorities."
Context: Super Decisions is desktop-only (Java-based), which represents the older paradigm. Modern SaaS competitors differentiate through web accessibility, real-time collaboration, and modern UI patterns.
Confidence: high
```

### Finding 27: Comparison of MCDA Software -- Group Decision Capabilities

```
Claim: Among MCDA software, 1000Minds supports online voting and decision surveys, D-Sight offers group member weighting, PlanEval allows stakeholders to give individual weights with visual comparison, and Web-HIPRE supports weighted group models [^45^].
Source: University of Jyvaskyla Software Comparison
URL: https://jyx.jyu.fi/bitstream/handle/123456789/49477/1/Annex7.5.13ComparisonofMultiCriteriaDecisionAnalyticalSoftware.pdf
Date: 2013-02-19
Excerpt: "1000Minds: Decision survey, online voting... D-Sight: Weighting of group members... PlanEval: Stakeholders can give their own weights, which can be compared visually... Web-HIPRE: Weighted group model."
Context: Group weight elicitation in SaaS can follow multiple patterns: survey-based aggregation (1000Minds), weighted member averaging (D-Sight), visual side-by-side comparison (PlanEval), or mathematical aggregation (Web-HIPRE).
Confidence: high
```

### Finding 28: Value Tree Analysis Integration with AHP and MAVT

```
Claim: Value tree analysis integrates with AHP through hierarchical tree structures combined with pairwise comparison matrices at each level, with tools like HIPRE 3+ and Web-HIPRE exemplifying this hybrid approach [^92^].
Source: Grokipedia / Value Tree Analysis
URL: https://grokipedia.com/page/value_tree_analysis
Date: 2026-02-03
Excerpt: "Tools such as HIPRE 3+ and Web-HIPRE exemplify this hybrid by enabling users to build value trees and then derive priorities via AHP's eigenvector method, accommodating both absolute and relative measurement scales."
Context: For VTA SaaS platforms, the value tree provides the structural framework while AHP provides the weight elicitation mechanism. This combination leverages VTA's intuitive decomposition and AHP's consistency checking.
Confidence: high
```

### Finding 29: SMARTS vs. SMARTER -- Ease of Digital Implementation

```
Claim: SMARTER (SMART Exploiting Ranks) requires only rank ordering of criteria and automatically computes weights via rank order centroid, achieving 98% of SMARTS accuracy without requiring any difficult judgments from elicitees [^62^].
Source: Academic Paper (Edwards & Barron, 1994)
URL: https://fsi9-prod.s3.us-west-1.amazonaws.com/s3fs-public/smarts_and_smarter.pdf
Date: 1994
Excerpt: "SMARTER... substitutes calculations based on ranks... can be shown to perform about 98% as well as SMARTS does, without requiring any difficult judgments from elicitees."
Context: SMARTER's simplicity makes it ideal for SaaS: users only need to drag-and-drop criteria into rank order, and weights are computed automatically. No numerical judgments required.
Confidence: high
```

### Finding 30: SPSSAU -- Web-Based AHP with Automated Consistency Testing

```
Claim: SPSSAU provides a web-based AHP tool implementing the square root method for weight vector calculation, consistency index (CI) calculation, and consistency ratio (CR) testing against standard RI tables, with support for matrices up to 15x15 [^42^].
Source: SPSSAU
URL: https://spssau.net/helps/ahp.html
Date: Unknown (current)
Excerpt: "Calculate CI: CI = (lambda_max - n)/(n - 1)... Calculate CR: CR = CI/RI. When CR < 0.1, the consistency is considered acceptable."
Context: SPSSAU demonstrates standard AHP computation implemented in a web-based statistical analysis platform, supporting the full mathematical workflow from judgment matrix to consistency-validated weights.
Confidence: high
```

### Finding 31: AHP-WEB Slider Interface for Pairwise Comparisons

```
Claim: AHP-WEB uses a slider interface for pairwise comparisons that can be moved right or left to assign judgments, requiring only n-1 comparisons per criterion set with automatic transitivity enforcement [^53^].
Source: PubMed Central / MethodsX
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10372897/
Date: 2023-12-27
Excerpt: "The slider can be moved to the right or left to assign the desired judgment. It is not necessary to do this for each criterion... the system takes advantage of the transitivity axiom to reduce the number of comparisons."
Context: This user interface pattern (horizontal slider for ratio-based judgments) is directly transferable to SaaS VTA platforms. The reduction from n(n-1)/2 to n-1 comparisons significantly improves usability.
Confidence: high
```

### Finding 32: Decision Lens (Successor to Expert Choice) -- Enterprise AHP Platform

```
Claim: Decision Lens (founded by developers of Expert Choice) provides enterprise AHP-based prioritization software, with William J. Adams (Chief Designer of Super Decisions) serving as a key figure in the AHP software ecosystem [^73^].
Source: Creative Decisions Foundation
URL: https://www.creativedecisions.org/about/index.php?section=activities
Date: Unknown (current)
Excerpt: "William J. Adams, Decision Lens Inc., Chief Designer and Original Developer of Super Decisions Software"
Context: The evolution from Expert Choice (desktop) through MakeItRational (web, now TransparentChoice) to Decision Lens represents the industry shift from desktop to SaaS delivery of AHP-based decision support.
Confidence: medium
```

### Finding 33: MCDA Software Landscape -- Web-Based Shift

```
Claim: MCDA software has shifted from spreadsheet-based tools (pre-1990s) to mostly web-based specialized software, freeing "the facilitator/analyst and decision-maker from the technical implementation details, allowing them to focus on the fundamental value judgments" [^37^].
Source: 1000minds MCDA Guide
URL: https://www.1000minds.com/decision-making/what-is-mcdm-mcda
Date: 2020-12-22
Excerpt: "Nowadays, Multi-Criteria Decision Analysis is increasingly supported by specialized software (mostly web-based). Before the advent of the World Wide Web in the 1990s, most MCDA / MCDM software was based on spreadsheets."
Context: This industry shift validates the whitepaper's core thesis: translating VTA weighting methods into SaaS workflows is aligned with the dominant trajectory of the MCDA software market.
Confidence: high
```

---

## Summary: Mapping VTA Weight Elicitation to SaaS Capabilities

### 1. Method-to-Interface Mapping

| VTA Weighting Method | Digital Interface Pattern | SaaS Implementation Complexity |
|---|---|---|
| **AHP (Pairwise Comparison)** | Slider-based ratio scales [^26^][^53^]; 2D plot widgets [^46^]; Matrix grids | Medium-High (requires CR calculation, eigenvector computation) |
| **SMART** | Point allocation inputs; Reference criterion selection [^36^][^51^] | Low (simple ratio calculations) |
| **SMARTER** | Drag-and-drop ranking only; Automatic centroid computation [^62^] | Very Low (rank order only) |
| **SWING** | Hypothetical alternative builders; Incremental improvement ranking [^63^][^91^] | Medium (requires scenario construction) |
| **SWING Weight Matrix** | Interactive grid with drag-and-drop; Real-time weight recalculation [^63^] | Medium (requires matrix UI) |
| **Rank Sum / Reciprocal / Exponent** | Rank input with formula selection; Parameter slider for exponent [^44^] | Very Low (purely formulaic) |
| **Direct Rating / Points Allocation** | Point distribution sliders; 100-point allocation interface [^37^] | Low |

### 2. Core SaaS Capabilities for Digital Weight Elicitation

#### A. Pairwise Comparison Engine
- **Slider interfaces** for ratio-based judgments on Saaty's 1-9 scale [^26^][^93^]
- **Real-time consistency ratio calculation** with visual feedback (green/yellow/red indicators) [^39^][^43^]
- **Transitivity enforcement** to reduce comparisons from n(n-1)/2 to n-1 [^46^][^53^]
- **Highlighting of most inconsistent judgments** with suggested revisions [^55^]
- **Partial judgment support** allowing users to skip uncertain comparisons

#### B. Hierarchical Weight Management
- **Value tree builder** for criteria/sub-criteria decomposition [^56^][^88^]
- **Local and global weight computation** at each hierarchy level [^80^]
- **Weight inheritance** from parent criteria to sub-criteria
- **Visual tree navigation** with expandable/collapsible nodes

#### C. Group Decision Support
- **Individual weight elicitation** via shared links or email invitations [^76^]
- **Aggregation methods**: Weighted arithmetic mean, weighted geometric mean [^53^][^55^]
- **Consensus measurement** using Shannon entropy (alpha/beta decomposition) [^55^]
- **Visual comparison** of individual stakeholder weights side-by-side [^45^]
- **Survey-based collection** for large stakeholder groups [^28^]

#### D. Weight Visualization
- **Horizontal bar charts** for criterion weight comparison (most effective) [^82^]
- **Pie charts** for part-whole weight relationships [^82^]
- **Radar/spider charts** for multi-dimensional weight profiles
- **Tornado diagrams** for sensitivity analysis on weight changes
- **Rank frequency matrices** showing stability across scenarios [^30^]

#### E. Consistency Management
- **Automatic CR calculation** on every judgment update [^42^][^39^]
- **Color-coded consistency indicators** (green <= 0.1, red > 0.1) [^39^]
- **Inconsistency highlighting** showing which judgments to revise [^43^]
- ** Guided revision suggestions** recommending specific value changes
- **Fuzzy AHP extensions** for uncertain judgments [^38^]

### 3. Key SaaS Differentiators vs. Desktop Software

| Feature | Desktop (Super Decisions, Expert Choice) | SaaS (AHP-OS, 1000Minds, TransparentChoice) |
|---|---|---|
| Installation | Required | None (browser-based) [^55^][^34^] |
| Collaboration | Limited file sharing | Real-time group sessions [^76^] |
| Updates | Manual | Automatic |
| Accessibility | Single device | Any internet-connected device [^53^] |
| Consensus Analysis | Limited | Shannon entropy decomposition [^55^] |
| Survey Distribution | None | Built-in link sharing [^28^] |
| Sensitivity Analysis | Desktop tools | Interactive web dashboards [^30^] |
| Cost Structure | License purchase | Subscription/freemium [^66^] |

### 4. Recommended Implementation Architecture for VTA SaaS

Based on this research, a modern VTA SaaS platform for weight elicitation should implement:

1. **Modular Weight Elicitation Interface**: Pluggable components for AHP (sliders), SMART (point allocation), SWING (hypothetical scenarios), and Rank-based (drag-and-drop ranking) methods, allowing users to select their preferred approach.

2. **Real-Time Computation Engine**: Client-side CR calculation for immediate feedback; server-side eigenvector computation for weight synthesis; Monte Carlo simulation for weight uncertainty estimation [^55^].

3. **Visual Weight Dashboard**: Interactive bar charts showing criterion weights with drill-down to sub-criteria; pie charts for category-level weight distribution; sensitivity tornado diagrams.

4. **Collaborative Weight Collection**: Multi-user sessions with individual weight input; geometric/arithmetic mean aggregation; consensus indicators; anonymity options for sensitive decisions.

5. **Value Tree Integration**: Drag-and-drop tree builder linking criteria hierarchies to weight elicitation interfaces at each node level, following the Web-HIPRE model [^88^][^92^].

6. **Adaptive Questioning (PAPRIKA-Style)**: Option to use adaptive pairwise comparison reduction to minimize user input while maintaining accuracy, particularly valuable for stakeholder surveys with many participants [^28^].

---

*Research compiled from 20+ independent web searches across academic databases, software vendor sites, GitHub repositories, and comparative reviews. All sources cited with confidence ratings.*

*Last updated: Research Session 2025*
