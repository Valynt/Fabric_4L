# Dimension 07: Real-time Sensitivity Analysis & What-If Modeling

## Research Findings: Translating VTA Robustness Checking into SaaS Capabilities

---

### Finding 1: Power BI "What If" Parameters for Interactive Sensitivity Analysis

Claim: Power BI supports interactive sensitivity analysis through a native "What If" parameter feature that creates dynamic slicers feeding directly into DAX measures, enabling real-time scenario exploration. [^28^]
Source: Graphed - How to Do Sensitivity Analysis in Power BI
URL: https://www.graphed.com/blog/how-to-do-sensitivity-analysis-in-power-bi
Date: 2025-12-21
Excerpt: "The magic behind interactive sensitivity analysis in Power BI is a feature called 'What If' Parameters. This feature allows you to create a dynamic slicer that users can interact with, and the selected value can be fed directly into your DAX measures."
Context: Power BI's What-If Parameters automatically generate a calculated table with values from minimum to maximum at specified increments, plus a DAX measure that captures the selected value. When combined with line charts, this creates "sensitivity curves" showing how forecasted outcomes change across the entire parameter range.
Confidence: high

---

### Finding 2: Tableau Parameters Enable Dynamic What-If Sensitivity Analysis

Claim: Tableau enables interactive sensitivity analysis through user-controlled Parameters combined with Calculated Fields, transforming static dashboards into interactive forecasting tools with real-time slider-based exploration. [^47^]
Source: Graphed - How to Do Sensitivity Analysis in Tableau
URL: https://www.graphed.com/blog/how-to-do-sensitivity-analysis-in-tableau
Date: 2025-12-21
Excerpt: "By combining user-controlled parameters with dynamic calculated fields, you can instantly answer critical 'what-if' questions, explore potential outcomes, and make much more informed, data-driven decisions for your business."
Context: Tableau parameters serve as the "steering wheel" of sensitivity analysis, allowing users to input custom values for assumptions like conversion rate changes or AOV shifts. Calculated fields reference these parameters to compute hypothetical outcomes that update automatically when sliders move.
Confidence: high

---

### Finding 3: Looker Supports What-If Analysis Through LookML Parameters and Liquid Templating

Claim: Looker enables what-if analysis through Parameters in LookML that create interactive filter-only fields, using Liquid templating to dynamically inject user inputs into calculations for real-time scenario modeling. [^71^]
Source: Graphed - How to Use What-If Analysis in Looker
URL: https://www.graphed.com/blog/how-to-use-what-if-analysis-in-looker
Date: 2025-12-21
Excerpt: "A parameter in LookML creates an interactive filter-only field on your dashboard or Explore... its value can be referenced in other calculations to make them dynamic."
Context: Looker's approach requires LookML coding - parameters are defined with types (e.g., number), and Liquid syntax {% parameter parameter_name %} injects user inputs into SQL-based calculations. This enables projected revenue calculations that update in real-time as users type values into filter boxes.
Confidence: high

---

### Finding 4: Anaplan Supports Multi-Dimensional What-If Scenario Modeling with Real-Time Impact Visualization

Claim: Anaplan's cloud-based Connected Planning platform enables complex what-if scenario modeling across business units with instant financial impact visibility, though it lacks native probabilistic simulation. [^30^]
Source: Farseer - Scenario Planning Software Compared: Top Tools for 2026
URL: https://www.farseer.com/blog/scenario-planning-software/
Date: 2025-11-05
Excerpt: "Users can simulate complex 'what-if' situations across business units, products, or regions, and instantly see the financial impact. Its powerful modeling engine allows deep driver-based forecasts."
Context: Anaplan is positioned as enterprise-grade scenario planning software capable of multi-dimensional modeling. Its deterministic approach focuses on what-if comparisons rather than probabilistic modeling, requiring significant implementation expertise.
Confidence: high

---

### Finding 5: Workday Adaptive Planning Provides Real-Time Multi-Departmental Scenario Collaboration

Claim: Workday Adaptive Planning offers dynamic scenario creation with real-time collaboration across departments, enabling teams to test multiple assumptions and instantly see impacts within enterprise financial planning. [^25^]
Source: Indicio - 8 Best Scenario Planning and Analysis Software
URL: https://www.indicio.com/resources/blog/scenario-planning-and-analysis-software
Date: 2026-02-24
Excerpt: "Workday Adaptive Planning emphasizes dynamic scenario creation within enterprise financial planning. Teams can test multiple assumptions, revenue drivers, cost shocks, or workforce adjustments, and instantly see their impacts."
Context: Workday Adaptive Planning integrates with Workday ERP and HR systems, offering intuitive dashboards for scenario comparison. However, it lacks built-in stochastic simulation, making it more deterministic than probabilistic.
Confidence: high

---

### Finding 6: Tornado Charts Are Widely Used for Sensitivity Visualization in JavaScript

Claim: Tornado charts for sensitivity analysis can be implemented in JavaScript using Chart.js by creating diverging horizontal bar charts that rank input parameters by their impact on an output variable. [^74^]
Source: Medium - Tornado Chart in Chart.js
URL: https://medium.com/@streetdisciple370/tornado-chart-in-chart-js-6a5117a5b098
Date: 2025-07-22
Excerpt: "Tornado Chart is used in sensitivity analysis to visually represent the result when a factor is slightly tweaked/adjusted by applying the change positively and negatively... data categories are arranged in order of significance to the output result, most impactful factors first."
Context: The implementation involves defining base values for input variables, calculating output sensitivity by varying each input positively and negatively while holding others constant, then plotting diverging bars ordered by impact magnitude.
Confidence: high

---

### Finding 7: GoldSim Provides Comprehensive Sensitivity Analysis with Tornado Charts and X-Y Function Charts

Claim: GoldSim simulation software supports sensitivity analysis through systematic one-at-a-time parameter variation, producing tornado charts, X-Y function charts, and central value results to identify the most impactful model variables. [^78^]
Source: GoldSim Help Documentation
URL: https://help.goldsim.com/Content/GS/sensitivityanalysistornadochart.htm
Date: Unknown
Excerpt: "A tornado chart is a type of sensitivity analysis that provides a graphical representation of the degree to which the Result is sensitive to the specified Independent Variables... GoldSim runs a series of deterministic simulations, varying one independent variable at a time through a range of values."
Context: GoldSim runs 3 deterministic simulations per variable (Lower Bound, Central Value, Upper Bound) while holding others constant. Variables are organized by total range of results produced. The platform also offers multivariate statistical sensitivity measures from Monte Carlo realizations.
Confidence: high

---

### Finding 8: Spider Plots Enable Multi-Variable Sensitivity Visualization on a Single Chart

Claim: Spider plots (radar charts) uniquely display the impact of multiple input variables on multiple output variables simultaneously, with each axis representing a different input scaled identically, creating a "spider-web" effect. [^50^]
Source: IHS Energy - Sensitivity Theory
URL: https://www.ihsenergy.ca/support/documentation_ca/Harmony/content/html_files/reference_material/analysis_method_theory/sensitivity_theory.htm
Date: Unknown
Excerpt: "A uniquely powerful feature of spider plots compared to tornado plots is their ability to simultaneously show the impact of several inputs on multiple outputs, rather than investigating one output at a time."
Context: Spider plots are constructed by determining the output range affected by each input, plotting each input on its own axis around the origin, and connecting points to form webs. Multiple outputs can be distinguished by line color/texture, making them ideal for VTA multi-criteria trade-off visualization.
Confidence: high

---

### Finding 9: D-Sight Integrates Tornado Charts with Interactive MCDA Sensitivity Dashboards

Claim: D-Sight's decision-making platform offers interactive dashboards for sensitivity analysis that allow users to adjust criteria weights on the fly and instantly see impacts on decisions, with integrated tornado chart visualization. [^81^]
Source: D-Sight - A Deep Dive into Sensitivity Analysis
URL: https://www.d-sight.com/sensitivity-analysis
Date: 2026-04-06
Excerpt: "D-Sight offers intuitive dashboards that allow users to adjust criteria weights on the fly, instantly seeing how it impacts the decision... Visualize the impact of changing various criteria with integrated Tornado Charts."
Context: D-Sight supports both MAUT and PROMETHEE methods for multi-criteria decision aid. Its sensitivity analysis tools include interactive weight adjustment, scenario creation/comparison, and tornado chart integration - directly relevant to VTA robustness checking in a SaaS context.
Confidence: high

---

### Finding 10: PySensMCDA Python Package Provides Comprehensive Sensitivity Analysis for MCDA

Claim: PySensMCDA is a dedicated Python package offering tools for decision matrix sensitivity analysis, weights sensitivity analysis, ranking sensitivity analysis, perturbation generation, and visualizations specifically designed for MCDA applications. [^65^]
Source: GitHub - jwieckowski/pysensmcda
URL: https://github.com/jwieckowski/pysensmcda
Date: 2023-09-21
Excerpt: "PySensMCDA is a comprehensive Python package tailored specifically for Multi-Criteria Decision Analysis (MCDA) sensitivity analysis... offers tools for: Decision matrix sensitivity analysis; Weights sensitivity analysis; Ranking sensitivity analysis; Perturbation generation; Weights generation; Visualizations of sensitivity analysis."
Context: This open-source package directly addresses the VTA sensitivity analysis workflow by providing programmatic tools for exploring how changes in weights and decision matrices affect rankings - a foundational capability for any SaaS-based VTA platform.
Confidence: high

---

### Finding 11: COMSAM Method Enables Comprehensive Sensitivity Analysis for MCDA Methods

Claim: The Comprehensive Sensitivity Analysis Method (COMSAM) provides a structured framework for simultaneously modifying multiple decision matrix values, enabling thorough assessment of MCDA method stability under uncertainty. [^60^]
Source: IEEE Access - Comparison of Multi-Criteria Decision Analysis Methods Under Comprehensive Sensitivity Analysis
URL: https://ieeexplore.ieee.org/iel8/6287639/10820123/11078265.pdf
Date: 2025-10-05
Excerpt: "COMSAM generates diverse combinations of criteria values and extends traditional one-at-a-time sensitivity analysis. This approach captures interdependencies within the decision matrix, allowing for deeper insights into how decision outcomes may change due to data uncertainties."
Context: The study evaluated RAM, COPRAS, TOPSIS, and MARCOS methods, finding RAM demonstrated highest robustness while TOPSIS was most sensitive. The simulation produced nearly 140 million evaluation observations per method, demonstrating the computational scale needed for comprehensive VTA sensitivity analysis in SaaS.
Confidence: high

---

### Finding 12: AnyLogic Cloud Offers Web-Based Simulation with Parameter Variation and Scenario Comparison

Claim: AnyLogic Cloud is a secure web platform for running simulation models that supports Parameter Variation and Monte Carlo experiments, with a cloud scenario comparison option for visualizing results across different experiments. [^43^]
Source: AnyLogic - Cloud Computing Simulation Tool
URL: https://www.anylogic.com/features/cloud/
Date: Unknown
Excerpt: "Leverage a range of experiments, including Parameter Variation and Monte Carlo. The Cloud scenario comparison option helps visualize results from different experiments to better highlight key metrics."
Context: AnyLogic Cloud provides customizable drag-and-drop dashboards with advanced charts (box plots, scatter plots, surface plots). Models can be shared with clients in ready-to-use cloud environments, supporting real-time collaboration and multi-run experiments executed on scalable cloud infrastructure.
Confidence: high

---

### Finding 13: Frontline Risk Solver Platform Supports Parameterized Sensitivity Analysis and Charts

Claim: Frontline Systems' Risk Solver Platform supports sensitivity parameters (PsiSenParam), optimization parameters (PsiOptParam), and simulation parameters (PsiSimParam) with automated report and chart generation for multiple parameterized analyses. [^36^]
Source: Frontline Solvers User Guide V11.5
URL: https://www.solver.com/files/_document/FrontlineSolvers_UserGuideV11.pdf
Date: Unknown
Excerpt: "A sensitivity parameter is automatically varied when you perform a sensitivity analysis... Risk Solver Platform can produce both reports and charts to document these results."
Context: The platform supports three parameter types that appear in the Task Pane Model outline. Users can vary parameters across multiple optimizations or simulations, with built-in charting of multiple parameterized optimizations showing how optimal objectives change as parameters vary.
Confidence: high

---

### Finding 14: Decision Tree Software Supports Sensitivity Analysis with Tornado Diagrams

Claim: SmartOrg's Sensitivity software (companion to Supertree decision tree analyzer) identifies critical uncertain inputs to spreadsheet decision models and displays results as tornado diagrams, supporting both single and joint sensitivity analysis. [^39^]
Source: SmartOrg - Supertree and Sensitivity
URL: https://smartorg.com/supertree-sensitivity/
Date: 2025-07-09
Excerpt: "Sensitivity determines which of these uncertain inputs are major contributors to the risk associated with each decision alternative. It does this by replacing baseline values for each variable... with high and low values and then calculating the resulting 'swing' in model outputs."
Context: The software links with Microsoft Excel and supports evaluating single and joint sensitivities (simultaneous changes in dependent variables). This approach of varying inputs from low to high and measuring output swing is directly analogous to VTA weight sensitivity analysis.
Confidence: high

---

### Finding 15: Web-HIPRE Provided Browser-Based VTA with Sensitivity Analysis Dialog

Claim: Web-HIPRE, a browser-based Java applet for multiple criteria decision analysis, included a dedicated sensitivity analysis dialog for analyzing results from value tree models constructed with mouse-driven commands. [^62^]
Source: Web-HIPRE Help - Introduction
URL: https://hipre.aalto.fi/Help-Introduction.html
Date: Unknown
Excerpt: "The overall priorities of the alternatives are calculated using the criteria weights. These priorities are shown by bar graphs with segments representing the contributions of different criteria. There is also a sensitivity analysis dialog."
Context: Web-HIPRE supported AHP, SMART, SWING, and SMARTER weighting methods, allowing the same model to be analyzed with different method combinations. The sensitivity analysis dialog was a separate window for visualizing how rankings changed - the historical reference point for modern SaaS VTA implementations.
Confidence: high

---

### Finding 16: Modern MCDA Software Comparison Shows Sensitivity Analysis as Core Feature

Claim: A comparative analysis of 16 decision support software systems found that sensitivity analysis is a standard feature across most modern MCDA tools, including 1000Minds, D-Sight, Expert Choice, and Decision Lens. [^85^]
Source: CEUR Workshop Proceedings - An Overview of Decision Support Software
URL: https://ceur-ws.org/Vol-2859/paper12.pdf
Date: Unknown
Excerpt: "DecisionLens combines the maximum number of respective functions, required for strategic planning... [Table shows] 1000Minds: Sensitivity analysis=Y, Cloud=Y; D-Sight: Sensitivity analysis=Y, Cloud=Y; DecisionLens: Sensitivity analysis=Y, Cloud=Y"
Context: The comparison table reveals that sensitivity analysis and cloud deployment are increasingly standard features in modern MCDA software. D-Sight implements both MAUT and PROMETHEE methods with sensitivity analysis and cloud support.
Confidence: high

---

### Finding 17: Deterministic Sensitivity Analysis in MCDA Includes One-Way, Threshold, and Extremes Analysis

Claim: Deterministic sensitivity analysis for MCDA includes three types: simple (one parameter varied at a time), threshold analysis (determining how much parameters must change before rank order changes), and analysis of extremes. [^68^]
Source: PMC - A Review and Classification of Approaches for Dealing with Uncertainty in MCDA
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC4544539/
Date: Unknown
Excerpt: "In simple sensitivity analysis, one model parameter (a criteria weight or a performance score) is varied at a time, and the impact of variation on the rank order of alternatives is observed... Both threshold analysis and analysis of extremes are aimed at determining how much model parameters need to change before a different rank order of alternatives is obtained."
Context: This taxonomy directly maps to VTA capabilities: one-way sensitivity = vary one weight/score at a time; threshold analysis = find break-even points where rankings change; extremes analysis = test boundary conditions. A robust SaaS VTA platform should support all three.
Confidence: high

---

### Finding 18: Indicio Provides Simulation-Based Scenario Analysis with Probability Quantification

Claim: Indicio offers simulation-based scenario analysis that quantifies outcome probabilities, enabling both single and complex multiple-event scenario exploration with integration into FP&A ecosystems. [^25^]
Source: Indicio - 8 Best Scenario Planning and Analysis Software
URL: https://www.indicio.com/resources/blog/scenario-planning-and-analysis-software
Date: 2026-02-24
Excerpt: "Indicio is purpose-built for simulation-based scenario analysis, allowing users to explore both single and complex multiple-event scenarios. Its simulation engine quantifies the probability of each outcome, offering a mathematical grounding to strategic foresight."
Context: Indicio connects with major ERP and FP&A systems, letting organizations visualize how simultaneous shocks (inflation, supply chain disruptions) shape potential futures. Its no-code interface makes sophisticated modeling accessible to non-technical users.
Confidence: high

---

### Finding 19: Real-Time Collaborative Analytics Platforms Enable Multi-User Sensitivity Exploration

Claim: Modern collaborative analytics platforms like Sigma Computing and Index support real-time multi-user dashboard editing with live cursor presence, enabling teams to explore sensitivity scenarios together simultaneously. [^96^]
Source: Index.app - Best Real-Time Collaborative Analytics Platforms Compared
URL: https://index.app/blog/real-time-collaborative-analytics-platforms-compared
Date: 2025-12-01
Excerpt: "Sigma Computing gives business users a spreadsheet interface on top of warehouse data... Collaboration happens inside shared workbooks where teammates see each other's cursors and edits live."
Context: Sigma translates spreadsheet operations into SQL behind the scenes, while Index offers natural language queries with multiplayer collaboration. This real-time collaborative paradigm is essential for VTA sensitivity analysis in enterprise settings where multiple stakeholders need to explore weight variations together.
Confidence: high

---

### Finding 20: JavaScript Libraries Support Monte Carlo Simulation for Web-Based Sensitivity

Claim: Multiple JavaScript libraries support Monte Carlo simulation implementation in web applications, including Math.js for mathematics, D3.js for visualization, Chance.js for random generation, and TensorFlow.js for GPU-accelerated computation. [^35^]
Source: Scribbler - Monte Carlo Simulation with JavaScript Examples
URL: https://scribbler.live/2024/04/09/Monte-Carlo-Simulation-in-JavaScript.html
Date: 2024-04-09
Excerpt: "Several JavaScript libraries can be used to implement Monte Carlo simulations. These libraries offer functionalities for random number generation, statistical analysis, and data visualization, which are crucial for performing and analyzing Monte Carlo simulations."
Context: The listed libraries provide the technical foundation for browser-based probabilistic sensitivity analysis: Math.js (distributions, statistics), D3.js (dynamic visualizations), Chance.js (random data generation), JStat (statistical computations), and TensorFlow.js (ML-based simulation with GPU acceleration).
Confidence: high

---

### Finding 21: Lagrange.ai Provides Side-by-Side Multi-Scenario Comparison Dashboards

Claim: Lagrange.ai offers model comparison features that let users select unlimited scenarios for side-by-side comparison with intelligent metric identification, interactive dashboards, and synchronized views. [^63^]
Source: Lagrange.ai - Model Comparison
URL: https://lagrange.ai/features/model-comparison
Date: Unknown
Excerpt: "Compare unlimited scenarios side-by-side. Make confident decisions with comprehensive analytics... Platform intelligently identifies all applicable metrics and creates comprehensive comparison dashboards."
Context: The platform automatically identifies comparable metrics across models, creates interactive dashboards with filters and drill-downs, and supports side-by-side analysis with synchronized views. This pattern directly translates to VTA scenario comparison for dominance analysis.
Confidence: medium

---

### Finding 22: TOPSIS and RAM MCDA Methods Show Significantly Different Sensitivity Profiles

Claim: Research applying COMSAM sensitivity analysis found RAM demonstrated the highest robustness to input perturbations (preference scores varying 99.90%-100.10%), while TOPSIS showed extreme volatility (scores ranging from near 0% to over 400% of original values). [^60^]
Source: IEEE Access - Comparison of MCDA Methods Under Comprehensive Sensitivity Analysis
URL: https://ieeexplore.ieee.org/iel8/6287639/10820123/11078265.pdf
Date: 2025-10-05
Excerpt: "The RAM method demonstrated exceptionally high stability... consistently varying between 99.90% and 100.10%... In contrast, the TOPSIS method exhibited significant variability... In some cases, the percentage-based preference scores ranged from close to 0% up to more than 400% of the original value."
Context: The study highlights that the choice of MCDA aggregation method significantly impacts result robustness. For SaaS VTA platforms, this finding suggests that sensitivity analysis should be method-aware, and platforms should either default to more robust methods or explicitly warn users about method-specific sensitivity characteristics.
Confidence: high

---

### Finding 23: MCDA Web Interface Supports Deterministic and Stochastic Benefit-Risk Analysis

Claim: The drugis.org MCDA web interface enables users to enter effects data, state preferences about relative importance of different effects, and see consequences in both deterministic and stochastic benefit-risk analyses. [^104^]
Source: Drugis.org - MCDA Web Interface
URL: https://www.drugis.org/software/mcda/
Date: Unknown
Excerpt: "Our multiple criteria decision analysis (MCDA) web interface lets the user enter or upload effects data, state their preferences about the relative importance of the different effects, and see the consequences of their preferences in both deterministic and stochastic benefit-risk analyses."
Context: The backend uses R packages for computations, demonstrating how modern web-based MCDA tools can leverage established statistical libraries. A Google account login is supported, showing SaaS-style authentication. This architecture pattern is directly applicable to VTA SaaS implementations.
Confidence: high

---

### Finding 24: PROMETHEE-Cloud Web App Supports Browser-Based MCDA Decision Making

Claim: PROMETHEE-Cloud is a dedicated web application for PROMETHEE-based multi-criteria decision making, enabling MCDA problem exploration and evaluation entirely in a web browser. [^105^]
Source: ScienceDirect - PROMETHEE-Cloud: A web app to support multi-criteria decision making
URL: https://www.sciencedirect.com/science/article/pii/S2193943824000098
Date: Unknown
Excerpt: "PROMETHEE-Cloud is a new web app to support PROMETHEE-based multi-criteria decision making (MCDA). MCDA problems can be explored and evaluated in a web app."
Context: This represents the trend toward specialized cloud-native MCDA tools, moving beyond desktop software to browser-based deployment that enables sharing, collaboration, and accessibility from any device.
Confidence: medium

---

### Finding 25: Decision Lens Supports Sensitivity Analysis with Trade-Off Radar Charts

Claim: Decision Lens provides trade-off analysis through radar charts that visualize criteria priorities and alternative performance scores, enabling identification of differentiating criteria and performance gaps. [^79^]
Source: Decision Lens Knowledge Base - Trade Off Analysis
URL: https://supporthub.decisionlens.com/trade-off-analysis
Date: Unknown
Excerpt: "Trade off Analysis is a radar chart that operates using the same data set as in Sensitivity Analysis. The Trade Off Analysis chart allows the user to select decision criteria and alternatives to visualize."
Context: The values shown are weighted averages of alternatives against selected criteria, combining outputs from Priorities (criteria weights) and Rating Alternatives (performance scores). Key focal points include identifying criteria that clearly differentiate alternatives and performance gaps - directly applicable to VTA dominance detection.
Confidence: high

---

### Finding 26: Local and Global Sensitivity Analysis Require Different Visualization Types

Claim: Modern sensitivity analysis tools use distinct visualization approaches for local versus global analysis: gradient/slope charts and spider/radar charts for local analysis; heatmaps, 3D surface plots, and parallel coordinates for global analysis. [^49^]
Source: Quadratic - What is Sensitivity Analysis?
URL: https://www.quadratichq.com/blog/what-is-sensitivity-analysis-evaluating-risk-and-uncertainty
Date: 2025-07-07
Excerpt: "Local analysis focuses on small changes, so you need visualizations that clearly show relative sensitivity magnitudes and directions around a central point... Global analysis covers wide ranges, so you need visualizations that can display behavior across entire input spaces."
Context: This taxonomy guides SaaS VTA visualization design: one-way weight sensitivity (local) suits bar charts, spider plots, and slope charts; full-parameter-space exploration (global) requires heatmaps and parallel coordinates. AI-assisted visualization generation (as in Quadratic) can automate chart selection.
Confidence: high

---

### Finding 27: Python Tornado Plot Implementation Enables Model Sensitivity Visualization

Claim: Tornado plots for sensitivity analysis can be created in Python using matplotlib's broken_barh function, displaying 5th and 95th percentile sensitivity ranges with median value reference lines. [^97^]
Source: Medium - Visualize sensitivity with a Tornado plot in Python
URL: https://medium.com/@chivuongtai/visualize-sensitivity-with-a-tornado-plot-in-python-32b70f6dcbed
Date: 2024-06-22
Excerpt: "The tornado plot, as its name suggests, shows bars in descending order of their width, resembling a tornado... using plt.broken_barh() function with parameters for base value, bar width, starting location, and height."
Context: The implementation uses diverging horizontal bars - negative widths for lower-bound sensitivity, positive widths for upper-bound sensitivity, with a vertical line marking the median. This pattern can be directly applied to VTA weight sensitivity visualization in Python-based SaaS backends.
Confidence: high

---

### Finding 28: R Tornado Package Supports Model Sensitivity Analysis for Statistical Models

Claim: The R 'tornado' package provides tornado plots for model sensitivity analysis supporting linear models, generalized linear models, and percentiles of input data, with customizable colors and plot controls. [^106^]
Source: GitHub - bertcarnell/tornado
URL: https://github.com/bertcarnell/tornado
Date: 2019-02-17
Excerpt: "tornado plots for model sensitivity analysis... Plots can include factors and percentiles of the data as well."
Context: The package supports PercentChange, ranges, and percentiles analysis types. For VTA applications, this approach of ranking variables by their impact on model output provides a proven statistical foundation for sensitivity visualization in R-based SaaS platforms.
Confidence: high

---

### Finding 29: Excel Data Tables Remain the Foundation for Sensitivity Analysis in Enterprise

Claim: Excel's Data Table functionality (under What-If Analysis) remains the most widely used enterprise tool for sensitivity analysis, supporting one-way and two-way tables that recalculate automatically when underlying models change. [^80^]
Source: Wall Street Prep - Sensitivity Analysis (What-If) Excel Tutorial
URL: https://www.wallstreetprep.com/knowledge/financial-modeling-techniques-sensitivity-what-if-analysis-2/
Date: 2025-04-07
Excerpt: "A sensitivity analysis, otherwise known as a 'what-if' analysis or a data table, is another in a long line of powerful Excel tools that allows a user to see what the desired result of the financial model would be under different circumstances."
Context: Excel's data tables support two-variable sensitivity grids but have limitations: inputs must be on the same sheet, numbers in input rows/columns cannot be linked to the model, and tables require manual F9 recalculation when set to "Automatic except for data tables." SaaS VTA platforms should overcome these limitations.
Confidence: high

---

### Finding 30: Scenario Planning Software Market Includes Specialized Tools for Different Use Cases

Claim: The scenario planning software market includes specialized tools spanning financial planning (Anaplan, Workday), project portfolio management (Planview, Meisterplan), and probabilistic simulation (Indicio), each with distinct scenario comparison approaches. [^26^]
Source: Epicflow - Top 10 Scenario Planning Tools in 2026
URL: https://www.epicflow.com/blog/scenario-planning-tools/
Date: 2026-02-09
Excerpt: "Tools for scenario planning can be different in their focus: financial scenario planning tools, solutions for portfolio management or supply chain as well as tools for scenario planning in corporate strategy and enterprise management."
Context: The market segmentation reveals that no single tool dominates all use cases. For VTA SaaS, this suggests opportunity in combining multi-criteria decision analysis (specialized) with real-time sensitivity and scenario comparison (generally available in planning tools).
Confidence: high

---

## Summary: Translating VTA Robustness Checking into SaaS Capabilities

### VTA Sensitivity Analysis → SaaS Capability Mapping

| VTA Concept | Desktop Era (Web-HIPRE) | Modern SaaS Equivalent |
|-------------|------------------------|----------------------|
| One-way sensitivity (vary weights one at a time) | Separate sensitivity dialog window | Interactive parameter sliders with live recalculation (Power BI What-If, Tableau Parameters) |
| Tornado diagrams | Static charts in dialog | Dynamic D3.js/Chart.js/Plotly visualizations with hover tooltips and drill-down |
| Spider/radar plots | Not available | WebGL-accelerated radar charts showing multi-output sensitivity |
| Dominance analysis | Manual comparison | Automated scenario comparison dashboards with side-by-side metrics |
| Weight threshold analysis | Trial and error | Automated break-even detection using COMSAM-style systematic perturbation |
| Multi-method comparison | Re-run with different methods | Tabs/switches to toggle between aggregation methods with preserved inputs |
| Visual ranking changes | Bar graph segments | Animated ranking transitions showing how alternatives shift as weights change |

### Key SaaS Architectural Patterns for VTA Sensitivity

1. **Reactive Parameter Binding**: Modern BI tools (Power BI, Tableau, Looker) use a parameter-measure binding pattern where UI controls (sliders, input boxes) feed values into calculation engines (DAX, calculated fields, SQL+Liquid) that update visualizations in real-time. This pattern directly replaces Web-HIPRE's separate sensitivity dialog with inline, always-available controls.

2. **Web-Based Visualization Libraries**: JavaScript libraries (D3.js, Plotly, Chart.js) and Python backends (matplotlib, PySensMCDA) provide mature, tested implementations for tornado charts, spider plots, and sensitivity curves that can run entirely in the browser or via API-backed services.

3. **Cloud-Native Computation**: Platforms like AnyLogic Cloud and GoldSim demonstrate that computationally intensive sensitivity analyses (Monte Carlo, parameter variation) can be executed on scalable cloud infrastructure with results streamed to browser dashboards. COMSAM-style comprehensive analysis requiring millions of evaluations becomes feasible through cloud parallelization.

4. **Collaborative Multi-User Exploration**: Real-time collaborative analytics (Sigma Computing, Mode, Index) enable multiple stakeholders to simultaneously adjust weights and observe impacts - a capability absent from desktop VTA tools but essential for group decision-making in enterprise SaaS.

5. **Scenario Management and Comparison**: Enterprise planning tools (Anaplan, Workday, Lagrange.ai) provide pattern libraries for creating, naming, saving, and comparing scenarios side-by-side - directly applicable to VTA dominance analysis and what-if comparison workflows.

6. **Method-Aware Sensitivity**: Research (COMSAM, IEEE Access study) demonstrates that sensitivity profiles vary significantly across MCDA methods. SaaS VTA platforms should make method sensitivity characteristics transparent and potentially recommend more robust methods (like RAM over TOPSIS) for uncertain decision contexts.

### Research Coverage

- **Total independent web searches conducted**: 20+
- **Sources consulted**: 35+ primary sources
- **Topics covered**: Real-time dashboards, what-if modeling, tornado/spider visualizations, interactive sliders, scenario comparison, Monte Carlo simulation, optimization platforms, decision tree sensitivity, cloud simulation, MCDA software, collaborative analytics, Excel sensitivity patterns
- **Date range of sources**: 2019-2026 (majority 2024-2026)
