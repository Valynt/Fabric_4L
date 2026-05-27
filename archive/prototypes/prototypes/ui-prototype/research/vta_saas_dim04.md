# Dimension 04: Interactive Value Function Elicitation Engine

## Research Findings: Translating Manual VTA Preference Elicitation into Digital SaaS UI/UX

**Date:** 2025-01-20
**Researcher:** Senior Research Analyst
**Searches Conducted:** 23 independent web searches

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Direct Rating & Slider-Based Elicitation](#1-direct-rating--slider-based-elicitation)
3. [Pairwise Comparison Interfaces (AHP, PAPRIKA)](#2-pairwise-comparison-interfaces)
4. [Graphical Value Function Builders](#3-graphical-value-function-builders)
5. [Visual Interactive MCDA Software (Legacy & Modern)](#4-visual-interactive-mcda-software)
6. [Conjoint Analysis & Trade-Off UI Patterns](#5-conjoint-analysis--trade-off-ui-patterns)
7. [Swing Weighting & Ratio Estimation Interfaces](#6-swing-weighting--ratio-estimation)
8. [Gamified & Visual Survey Components](#7-gamified--visual-survey-components)
9. [Preference Learning & AI Alignment](#8-preference-learning--ai-alignment)
10. [Open-Source MCDA Platforms](#9-open-source-mcda-platforms)
11. [Mapping VTA Methods to SaaS UI Components](#mapping-vta-methods-to-saas-ui-components)
12. [Synthesis & Recommendations](#synthesis--recommendations)

---

## Executive Summary

This research dimension investigates how six manual value function elicitation methods from classical Value Tree Analysis (VTA) --- (1) direct rating, (2) category estimation, (3) ratio estimation, (4) curve drawing, (5) difference standard sequence, and (6) bisection --- can be translated into interactive digital interface components within a SaaS workflow. Through 23 independent web searches covering interactive preference elicitation UI, visual utility builders, conjoint analysis software, survey tools, AHP interfaces, and AI preference learning systems, this research identifies mature interface patterns, proven software implementations, and emerging technologies that can replace in-person analyst-led elicitation with self-service digital experiences.

---

## 1. Direct Rating & Slider-Based Elicitation

### Finding 1.1: Survey Slider Scales as Direct Rating Digital Equivalent

Claim: Slider scales in survey platforms (SurveySparrow, Qualtrics) provide a digital equivalent to the manual 0-100 direct rating method, offering continuous value selection with visual feedback that increases respondent involvement [^1^].
Source: SurveySparrow - Slider Scale Guide
URL: https://surveysparrow.com/blog/slider-scale/
Date: 2025-09-19
Excerpt: "A slider scale is a viable alternative to the limitations of a multiple-choice question, or a Likert scale question type, because it can include a broader range of answers... By allowing respondents to manipulate them like a physical switch, sliding scale questions increase their involvement, and make the survey a more pleasing experience."
Context: SurveySparrow documents five slider types: single, dual, continuous, discrete, and graphic (thermometer, gauge meter, traffic light, smiley). Graphic sliders frame the slider within a graphic that changes as the user adjusts the scale, providing visual feedback that appeals to the user's natural desire for acknowledgment.
Confidence: High

### Finding 1.2: Qualtrics Graphic Slider for Preference Measurement

Claim: Qualtrics provides 10 built-in graphic slider types (gauge, thermometer, stop light, smile, grades, horizontal bars, disks, building blocks) that enable engaging visual preference elicitation without custom coding [^2^].
Source: Qualtrics Support - Graphic Slider Question
URL: https://www.qualtrics.com/support/survey-platform/survey-module/editing-questions/question-types-guide/specialty-questions/graphic-slider/
Date: 2015-04-23
Excerpt: "The graphic slider provides an engaging scale for respondents. It displays an image that changes as the scale adjusts. This format can be particularly useful for younger audiences or for simple satisfaction feedback."
Context: Qualtrics graphic sliders support customizable text position, slider position (horizontal/vertical), and scale points (5, 7, or 9). This provides a mature, production-ready pattern for direct rating elicitation in a VTA SaaS context.
Confidence: High

### Finding 1.3: VAS Generator for Online Preference Studies

Claim: The VAS Generator (vasgenerator.net) provides a free tool for creating Visual Analog Scales for online studies, demonstrating that continuous slider-based measurement has been a solved problem in web-based research for over a decade [^3^].
Source: VAS Generator
URL: http://www.vasgenerator.net/
Date: Unknown (active since at least 2008)
Excerpt: "This tool is to design VAS that can be used in online studies (e.g., Funke & Reips, 2012; Reips & Funke, 2008). Just follow the 4 steps below to create a VAS for your own online survey."
Context: The tool allows researchers to set pixel length, left/right anchors, color, and download the generated VAS as an HTML file. This represents the simplest possible implementation of a direct rating interface component.
Confidence: High

### Finding 1.4: FITradeoff Method for Web-Based Partial Preference Elicitation

Claim: The Flexible and Interactive Tradeoff (FITradeoff) method systematically reduces the number of questions required from decision makers by using partial information to eliminate dominated alternatives, making it highly suitable for web-based implementation where cognitive burden must be minimized [^4^].
Source: MDPI Information - On Ordinal Information-Based Weighting Methods
URL: https://www.mdpi.com/2078-2489/15/9/527
Date: 2024-09-01
Excerpt: "In the flexible and interactive tradeoff (FITradeoff) method, the DM is required to provide less information than in the standard tradeoff procedure. FITradeoff systematically evaluates the possibility of finding a solution to the problem while the elicitation process is ongoing, using partial information elicited from the DM at any point in the process to solve a linear programming problem in order to reduce the subset of potentially optimal alternatives."
Context: FITradeoff progressively reduces the weight space and identifies dominated alternatives, potentially ending early if a unique optimal alternative is found. This makes it ideal for SaaS implementation where user patience is limited.
Confidence: High

---

## 2. Pairwise Comparison Interfaces

### Finding 2.1: 1000minds PAPRIKA Adaptive Pairwise Comparison

Claim: 1000minds implements the PAPRIKA (Potentially All Pairwise RanKings of all possible Alternatives) method through a simple web interface presenting trade-off questions between two hypothetical alternatives defined on just two attributes at a time, making it "the easiest possible questions to think about" [^5^].
Source: 1000minds - What is the PAPRIKA method?
URL: https://www.1000minds.com/paprika
Date: Unknown (continuously updated)
Excerpt: "The PAPRIKA method involves each person answering a series of simple questions based on choosing between two hypothetical alternatives defined on just two attributes at a time and involving a trade-off... These are the easiest possible questions to think about, and so people can answer them with more confidence (and faster) than other methods' questions."
Context: PAPRIKA adapts after each question. With four attributes and 3-4 levels each, users answer approximately 25 questions taking less than 10 minutes. The method transforms ordinal judgments (which do you prefer?) into interval-scale preference values/utility scores using conjoint measurement theory.
Confidence: High

### Finding 2.2: 1000minds Voting Interface for Group Consensus

Claim: 1000minds provides a group voting interface where participants anonymously vote on pairwise trade-off questions via mobile devices, with results displayed on a shared screen to facilitate discussion and consensus-building [^6^].
Source: 1000minds - Delphi Method for Group Decision-Making
URL: https://www.1000minds.com/decision-making/delphi-method
Date: Unknown (continuously updated)
Excerpt: "Participants anonymously vote on each question, one by one, using their mobile devices as clickers (if in the same room) or via online meeting software (if geographically dispersed) connected to 1000minds... After each vote, the moderator leading the session clicks the 'show votes' button, which reveals on the shared screen how participants voted."
Context: The voting process: (1) anonymous voting, (2) reveal votes, (3) discussion if disagreement, (4) re-vote if needed. This represents a mature pattern for translating pairwise preference elicitation into a collaborative SaaS workflow.
Confidence: High

### Finding 2.3: AHP-OS Web-Based Pairwise Comparison System

Claim: AHP-OS is a free, open-source web-based AHP system that provides pairwise comparison input with highlighting of the top-3 most inconsistent judgments, partial judgment capability, and group decision making using weighted geometric mean aggregation [^7^].
Source: GitHub - bpmsg/ahp-os
URL: https://github.com/bpmsg/ahp-os
Date: 2022-01-31
Excerpt: "AHP-OS is a php program package for the Analytic Hierarchy Process, a mathematical tool to support rational decision making. It is an online tool written in php with a web browser interface, where users can register, login and define their own decision hierarchies."
Context: Features include: flexible hierarchy definition via text input, eigenvector weight calculation, partial judgments, a posteriori scale switching, group consensus calculation based on Shannon entropy, Monte Carlo weight uncertainty estimation, and CSV/JSON export.
Confidence: High

### Finding 2.4: Interactive Data Plot Widget for Consistent AHP Comparisons

Claim: Researchers have developed an innovative UI widget for AHP pairwise comparisons that resembles an interactive data plot, offering a more intuitive and visually consistent approach than traditional matrix-based input [^8^].
Source: ResearchGate - A User Interface for Consistent AHP Pairwise Comparisons
URL: https://www.researchgate.net/publication/356496315_A_User_Interface_for_Consistent_AHP_Pairwise_Comparisons
Date: 2022-01-12
Excerpt: "In this article we present an innovative approach to conduct pairwise comparisons based on a UI widget that resembles an interactive data plot."
Context: This represents a modern UI/UX innovation that could replace the traditional AHP comparison matrix with a more intuitive visual interaction pattern.
Confidence: Medium

### Finding 2.5: Visual Interface for Ratio Preference Elicitation in AHP

Claim: Computer-based visual tools with adjustable interfaces and simultaneous comparisons can effectively elicit ratio preferences for AHP, showing promise for a new class of multi-criteria decision support systems [^9^].
Source: IJITDM - Eliciting Ratio Preferences For The Analytic Hierarchy Process With Visual Interfaces
URL: https://ideas.repec.org/a/wsi/ijitdm/v05y2006i02ns0219622006001939.html
Date: 2006-02-02
Excerpt: "New experiments with computer-based visual tools confirm that ratio preferences can be effectively and efficiently elicited using adjustable visual tools and simultaneous comparisons, as well. Such an improved approach shows promise in the design of a new class of multi-criteria decision support system both for individual and group decisions."
Context: This academic research from 2006 validates the concept of using visual interfaces (sliders, interactive charts) for ratio-based preference elicitation in AHP/VTA contexts.
Confidence: High

---

## 3. Graphical Value Function Builders

### Finding 3.1: M-MACBETH Interactive Value Function Construction

Claim: M-MACBETH software enables interactive value function construction through click-and-drag manipulation of performance levels on a graphical scale, with automatic consistency checking against the decision maker's qualitative judgments [^10^].
Source: M-MACBETH User's Guide
URL: http://m-macbeth.com/wp-content/uploads/2017/10/M-MACBETH-Users-Guide.pdf
Date: Unknown
Excerpt: "Click and drag any performance level, at the left graph, or its respective point in value function graph, whose score you want to adjust. This will open an interval within which the score of a performance level can be changed while keeping fixed the scores of the remaining performance levels and maintaining the compatibility with the matrix of judgements."
Context: M-MACBETH provides: (1) a matrix of qualitative judgments comparing pairs of performance levels, (2) automatic generation of numerical scales from these judgments, (3) graphical displays with click-and-drag score adjustment, (4) piecewise-linear value function graphs where performance levels are on the horizontal axis and scores on the vertical axis. This is the most mature existing implementation of interactive value function building.
Confidence: High

### Finding 3.2: MACBETH Online Value Function Fitting Tool

Claim: An online MACBETH tool allows users to fit a piecewise-linear value function defined by a set of (performance, value) points, automatically classifying the function shape as concave, convex, or linear using least-squares fitting [^11^].
Source: Miguel Roque Fernandes - Macbeth Analysis Online Tool
URL: https://research.miguelroquefernandes.com/
Date: Unknown
Excerpt: "This online software allows you to fit a value function, defined by a set of points, to a function that respects the constant trade-off attitude property... The function is fitted using the least squared differences method."
Context: Users input points as (performance, value) pairs and the tool generates the fitted curve. This demonstrates that even complex value function fitting can be implemented as a lightweight web component.
Confidence: High

### Finding 3.3: M-MACBETH Value Function Representation in Health Decision Making

Claim: M-MACBETH visually represents value functions as piecewise-linear graphs on a plane defined by a performance axis and a partial value score axis, with the underlying mathematical equation displayed for transparency [^12^].
Source: Advancing the use of MACBETH in health settings (Extended Abstract)
URL: https://fenix.tecnico.ulisboa.pt/downloadFile/3378094857519469/ExtendedAbstractv02.pdf
Date: Unknown
Excerpt: "The value functions are used to convert the performance of an option on a criterion into a partial value score. They can be constructed using expert judgements or empirical data... The corresponding mathematical equation that defines the piecewise linear value function is shown."
Context: The example shows a value function for printing speed with four linear segments, each with its own mathematical definition. This dual representation (visual graph + mathematical formula) is an essential pattern for a transparent VTA SaaS.
Confidence: High

---

## 4. Visual Interactive MCDA Software

### Finding 4.1: Web-HIPRE Browser-Based Value Tree Analysis

Claim: Web-HIPRE v2.0 is a browser-based MCDA tool that supports value tree construction, value function elicitation, and multiple weighting methods (AHP, SMART, SWING, SMARTER) with bar graph results display and sensitivity analysis [^13^].
Source: IFORS - Web-HIPRE: Multicriteria Decision Analysis Software
URL: https://ifors.org/developing_countries/index.php/Web-HIPRE:_Multicriteria_Decision_Analysis_Software
Date: 2025-06-10
Excerpt: "In Web-HIPRE the decision problem is structured hierarchically to form a value tree/ AHP model of the criteria. weights of the criteria can be elicited by different weighting methods. Web-HIPRE supports value functions and the AHP, SMART, SWING and the rank based SMARTER methods."
Context: Web-HIPRE allows hierarchical problem structuring via mouse-driven commands, links to web pages for additional criterion information, bar graph results with criterion contribution segments, and sensitivity analysis dialogs. It is free for academic use and represents the closest existing equivalent to a web-based VTA tool.
Confidence: High

### Finding 4.2: V.I.S.A. Visual Interactive Sensitivity Analysis

Claim: V.I.S.A (Visual Interactive Sensitivity Analysis) software uses simple interactive graphics to enable decision makers to investigate multi-criteria problems, with features including weight adjustment via drag-and-drop, sensitivity graphs, value profiles, and weighted profiles [^14^].
Source: Springer - V.I.S.A - VIM for MCDA
URL: https://link.springer.com/chapter/10.1007/978-3-642-49298-3_27
Date: Unknown
Excerpt: "V.I.S.A is a software package which makes effective use of simple interactive graphics to enable the user (decision maker or analyst) to investigate multi-criteria problems."
Context: V.I.S.A supports: drag-and-drop weight adjustment, sensitivity graphs showing effects of weight changes on scores, profiles showing score distributions across criteria, weighted profiles with heights scaled by criterion weights, and a 0-100 scoring scale. This represents the gold standard for interactive MCDA visualization.
Confidence: High

### Finding 4.3: V.I.S.A. Weight Setting via Interactive Bar Interface

Claim: V.I.S.A enables intuitive weight setting through an interactive bar interface where users can drag weights, click to set positions, fix specific weights, or equalize all weights with a keyboard shortcut --- all while maintaining automatic normalization [^15^].
Source: Victoria University of Wellington - A Practical Guide to Multi-Criteria Decision Analysis
URL: https://www.wgtn.ac.nz/som/about/publications/mabinbeattie-v5_2-May-2006.pdf
Date: May 2006
Excerpt: "Positioning the cursor at the top of the bar and dragging the weight to the desired position; or Click above bar and weight will move to that level: or Input numerical setting by selecting Settings menu and then Numerical Value... To fix a weight, Right-click on the criterion name or anywhere on the bar. The name will appear in red to show it is fixed."
Context: The weights interface includes: drag-to-adjust, click-to-set, numerical input, weight fixing (appears in red), equalize (SHIFT+right-click), automatic normalization, and snapshot saving for comparing alternative weight sets. This is a proven interaction pattern for weight elicitation.
Confidence: High

### Finding 4.4: Hiview3 Swing Weighting with MACBETH Qualitative Scoring

Claim: Hiview3 is a commercial MCDA tool that supports both quantitative and fully qualitative decision making through integrated MACBETH techniques, enabling users to create robust decision models using entirely verbal judgments with no numerical data [^16^].
Source: Catalyze Ltd - Hiview3 Datasheet
URL: https://www.catalyzeconsulting.com/wp-content/uploads/2012/07/Catalyze_Datasheet_Hiview.pdf
Date: Unknown
Excerpt: "Hiview3 provides the ability to evaluate criteria that are wholly qualitative. Using exclusive MACBETH techniques it is possible to create robust and consistent decision models using entirely verbal judgements, with no numerical data."
Context: Hiview3 uses a five-step process: (1) Constructing a model (value tree), (2) Scoring (numerically or graphically, with MACBETH for qualitative judgments), (3) Setting preferences using swing-weighting, (4) Analyzing with sensitivity analysis, (5) Recommendation. It supports £950 for the standard version.
Confidence: High

### Finding 4.5: DCZNMaker Web-Based Multi-Attribute Utility Analysis

Claim: DCZNMaker is a novel web-based application for multi-attribute utility analysis that simplifies decision-making through an intuitive interface allowing users to assign weights to attributes and calculate utility scores, with dynamic changes enabling "explainable decision-making" [^17^].
Source: arXiv - A Web-based Application for Multi-Attribute Utilities Analysis
URL: https://arxiv.org/html/2407.04655v1
Date: 2024-07-05
Excerpt: "DCZNMaker effectively simplifies the decision-making process by breaking down complex decisions into manageable components, allowing users to assign weights to different attributes and calculate utility scores for each option. The app's intuitive interface and robust computational capabilities ensure that users can make well-informed decisions quickly and efficiently."
Context: DCZNMaker represents a recent (2024) web-based implementation of MAUA that demonstrates the technical feasibility of building VTA-like decision tools as modern web applications.
Confidence: High

---

## 5. Conjoint Analysis & Trade-Off UI Patterns

### Finding 5.1: Choice-Based Conjoint Card-Based UI Pattern

Claim: Choice-based conjoint analysis presents respondents with sets of "choice cards" showing different product attribute combinations, and respondents select their preferred option --- a UI pattern directly applicable to VTA trade-off elicitation [^18^].
Source: Drive Research - Explaining Choice-Based Conjoint Analysis
URL: https://www.driveresearch.com/market-research-company-blog/choice-based-conjoint-analysis/
Date: 2023-02-06
Excerpt: "Respondents are shown randomized sets of cards to collect data on the various attributes and attribute levels... The ideal experimental design for a choice-based conjoint analysis is balanced and comprehensive."
Context: Key design parameters: sample size (100-200 per segment), choice type (single choice, best-worst, continuous sum), cards per set (typically 3), sets per respondent (typically 12), attributes (max 6 recommended), attribute levels (2-6 each). This card-based pattern can be adapted for VTA preference elicitation.
Confidence: High

### Finding 5.2: Scenario-Based Conjoint with Profile Cards

Claim: Conjoint analysis can be presented as scenario-based profile cards that describe experience scenarios rather than attribute lists, making the trade-off questions more engaging and contextually meaningful for respondents [^19^].
Source: UC Berkeley BEST Lab - Scenario Based Conjoint Analysis
URL: http://best.berkeley.edu/wp-content/uploads/2017/09/DETC2017-67690.pdf
Date: Unknown (2017)
Excerpt: "As a scenario-based approach, the conjoint choices were comprised of cards describing experience scenarios rather than a list of attributes. That is to say, profiles that would have looked like Table 3 in a conventional conjoint analysis were turned into scenario profile cards."
Context: Scenario-based cards transform abstract attributes into narrative descriptions, which can improve engagement and reduce cognitive burden. This pattern is particularly relevant for VTA elicitation where criteria may be abstract.
Confidence: High

### Finding 5.3: Adaptive Self-Explicated (ASE) Conjoint with Sliding Bars

Claim: The Adaptive Self-Explicated approach uses sliding bars for constant-sum attribute importance allocation, breaking down the cognitively demanding task into pairwise comparisons adapted to respondents' rankings [^20^].
Source: A User's Guide to the Galaxy of Conjoint Analysis (Semantic Scholar)
URL: https://pdfs.semanticscholar.org/8d39/79a7b1a3fea9b510e695c148291b1c19b1e0.pdf
Date: Unknown
Excerpt: "In the third stage, respondents then allocate the 100 points using a sliding bar. Thus, constant-sum evaluations are adapted to respondents' rankings. In total, three constant-sum questions are constructed that comprise the most and least important attributes and those in the middle."
Context: ASE combines ranking, pairwise comparison, and slider-based allocation to reduce cognitive burden while maintaining the validity of trade-off-based preference measurement. This multi-step adaptive pattern is highly relevant for VTA SaaS design.
Confidence: High

---

## 6. Swing Weighting & Ratio Estimation

### Finding 6.1: Online SWING Weight Elicitation with Sliders and Vignettes

Claim: Researchers have successfully implemented online SWING weight elicitation using draggable vignettes for ranking and sliders for ratio rating, with recommendations for improving digital implementations of this cognitively demanding MCDA step [^21^].
Source: Econstor - Recommendations for online elicitation of swing weights
URL: https://www.econstor.eu/bitstream/10419/246428/1/1727071581.pdf
Date: Unknown (circa 2020)
Excerpt: "In the ranking phase, participants could drag and drop the vignettes in their preferred order, instead of writing a number in an open box; in the rating phase, participants could see the vignettes ordered according to the rank that they gave; and in the rating phase, participants used sliders to rate, instead of writing a number in an open box."
Context: The three-step process: (1) information about objectives and hypothetical alternatives presented as vignettes, (2) drag-and-drop ranking of vignettes, (3) slider-based relative rating from 0-100. The most preferred gets 100, worst gets 0, and intermediates are rated proportionally.
Confidence: High

### Finding 6.2: CROC Method with Graphical Slider for Cardinal Weight Elicitation

Claim: The Cardinal and Rank Ordering of Criteria (CROC) method uses a graphical slider interface where criteria are distributed along a slider with "clouded regions" representing intervals, allowing decision makers to adjust distances between criteria to represent cardinal importance [^22^].
Source: MDPI Information - On Ordinal Information-Based Weighting Methods
URL: https://www.mdpi.com/2078-2489/15/9/527
Date: 2024-09-01
Excerpt: "The criteria are equally distributed along a slider (using a graphical user interface), i.e., all magnitudes of the differences are initially equal, and each criterion is associated with a clouded region with a length equal to the default distance. Then, the DM is asked to adjust the distances between criteria to represent information of cardinal importance between them."
Context: CROC handles imprecision through intervals where slider positions are interpreted as ranges rather than point estimates. This approach of combining graphical sliders with imprecision handling is directly applicable to VTA weight elicitation.
Confidence: High

### Finding 6.3: Deck of Cards Method Digital Implementation

Claim: The Deck of Cards Method (DCM) for weight elicitation has been implemented digitally in HELDA software, allowing users to order criteria with arrow buttons and insert "white cards" between criteria to express preference strength [^23^].
Source: HELDA User Manual
URL: https://www.mcda-helmholtz.de/downloads/User%20manual/HELDA_Manual_v1.pdf
Date: Unknown
Excerpt: "Use the up and down arrows to order the criteria from the most important (top) to the least important (bottom). Use the plus (+) button to add white cards between criteria to express the strength of preference between consecutive levels. Define the ratio between the weight of the most important criterion and the weight of the least important one."
Context: The digital DCM translates the physical card-sorting metaphor into arrow-button interactions while preserving the core concept of using spacing to represent preference strength. This demonstrates how manual VTA methods can be digitized while maintaining their cognitive simplicity.
Confidence: High

---

## 7. Gamified & Visual Survey Components

### Finding 7.1: Gamified Online Surveys for Preference Elicitation

Claim: Gamified online surveys using game elements (learning loops, narrative with non-player characters, friendly interface design) can effectively elicit citizen preferences, particularly for complex policy decisions [^24^].
Source: ScienceDirect - Gamified online survey to elicit citizens' preferences
URL: https://www.sciencedirect.com/science/article/abs/pii/S1364815218305073
Date: Unknown
Excerpt: "The game elements are (1) learning loops, (2) a narrative with non-player characters, and (3) a friendly interface design. The learning loops are based on..."
Context: Gamification elements (narrative, NPCs, progressive learning) can reduce survey fatigue and improve data quality for preference elicitation tasks that require multiple comparison questions.
Confidence: Medium

### Finding 7.2: Graphic Slider Variants (Thermometer, Gauge, Traffic Light, Smiley)

Claim: SurveySparrow implements four graphic slider variants --- thermometer, gauge meter, traffic light, and smiley --- that transform abstract numerical rating into visually concrete and emotionally intuitive interactions [^25^].
Source: SurveySparrow - Slider Scale Guide
URL: https://surveysparrow.com/blog/slider-scale/
Date: 2025-09-19
Excerpt: "SurveySparrow has four different graphic sliding scales for you to choose from: #A. Thermometer: This sliding scale is a graphical slider in the form of a thermometer. #B. Gauge Meter: This slider controls a rating scale displayed as a fuel gauge. #C. Traffic Light: This is a 3-point sliding scale represented as a traffic light. #D. Smiley: This is a 5-point slider scale with the points represented as smileys."
Context: Graphic sliders provide visual metaphors that make rating tasks more engaging and intuitive. For VTA applications, these patterns could be adapted (e.g., a "value thermometer" for criterion scoring).
Confidence: High

### Finding 7.3: Rating Scale Types for Preference Measurement

Claim: Modern survey platforms support multiple rating scale types --- numerical, descriptive, semantic differential, and graphical (stars, sliders, emojis) --- with graphical scales being quick to answer and highly engaging especially when paired with numeric or text anchors [^26^].
Source: SurveyKing - Rating Scale: Definition, Types, and Examples
URL: https://www.surveyking.com/blog/rating-scale/
Date: 2026-01-06
Excerpt: "Graphical scales rely on visual elements rather than words or numbers. Common examples include stars, sliders, emojis, or smiley faces. They are quick to answer and highly engaging, especially in consumer-facing surveys. To avoid confusion, graphical scales are often paired with numeric or text anchors."
Context: Available question formats include: single rating, multiple rating, NPS, CES, sliders, matrix, and semantic differential. Each format maps to different VTA elicitation needs.
Confidence: High

---

## 8. Preference Learning & AI Alignment

### Finding 8.1: Revealed Preference Framework for AI Alignment

Claim: A revealed preference framework can identify the degree of alignment between AI and human preferences by analyzing stochastic choice data, separating the concepts of "alignment" (preference similarity) from "compliance" (deference to human preferences) [^27^].
Source: arXiv - A Revealed Preference Framework for AI Alignment
URL: https://arxiv.org/html/2603.27868v1
Date: 2026-03-29
Excerpt: "I introduce the Luce Alignment Model, where the AI's choices are a mixture of two Luce rules, one reflecting the human's preferences and the other the AI's. I show that the AI's alignment can be generically identified in two settings: the laboratory setting, where both human and AI choices are observed, and the field setting, where only AI choices are observed."
Context: This framework treats preference elicitation as an inference problem: given observed choices, what are the underlying preferences? This perspective is relevant for VTA SaaS that aims to learn user preferences from interaction patterns.
Confidence: Medium

### Finding 8.2: Variational Preference Learning for Personalization

Claim: University of Washington researchers developed "variational preference learning" (VPL), a method that predicts users' preferences as they interact with AI systems and tailors outputs accordingly, addressing the limitation of fixed-value systems like standard RLHF [^28^].
Source: University of Washington News
URL: https://www.washington.edu/news/2024/12/18/ai-user-values-preferences-rlhf/
Date: 2024-12-18
Excerpt: "University of Washington researchers created a method for training AI systems --- both for large language models like ChatGPT and for robots --- that can better reflect users' diverse values. Called 'variational preference learning,' or VPL, the method predicts users' preferences as they interact with it, then tailters its outputs accordingly."
Context: Traditional RLHF embeds a single set of values from training raters. VPL adapts to individual user values in real-time. This represents an emerging paradigm where preference elicitation is continuous and implicit rather than one-time and explicit.
Confidence: Medium

### Finding 8.3: Preference Learning Algorithms and Ranking Accuracy

Claim: Current preference learning algorithms (DPO, RLHF) achieve less than 60% ranking accuracy on common preference datasets, with "alignment gaps" of up to 59 percentage points between theoretical and actual performance, highlighting the need for improved elicitation and learning methods [^29^].
Source: NYU Data Science - Preference Learning Algorithms Fail to Learn Human Preference Rankings
URL: https://nyudatascience.medium.com/preference-learning-algorithms-fail-to-learn-human-preference-rankings-d1eba7d380fd
Date: 2024-09-30
Excerpt: "Most state-of-the-art preference-tuned models achieve a ranking accuracy of less than 60% on common preference datasets... real-world models exhibited large 'alignment gaps' --- differences of up to 59 percentage points between their actual and theoretically predicted ranking accuracies."
Context: The difficulty of learning preferences from pairwise comparisons highlights why structured, explicit elicitation (as in VTA) remains valuable. Explicit elicitation through well-designed UI may capture preferences more accurately than implicit learning.
Confidence: Medium

---

## 9. Open-Source MCDA Platforms

### Finding 9.1: Decision Deck Open-Source MCDA Platform

Claim: The Decision Deck project develops open-source, modular MCDA software tools including the D2 desktop application, D3 web services interface, and XMCDA data standard, with implemented methods including IRIS, RUBIS, VIP, and UTA-GMS/GRIP [^30^].
Source: Decision Deck Official Website
URL: https://www.decision-deck.org/
Date: Unknown (ongoing since 2008)
Excerpt: "The Decision Deck project collaboratively develops Open Source software tools to support the Multi-Criteria Decision Aiding (MCDA) process. Its purpose is to provide effective tools for three types of users: consultants who use MCDA tools to support decision makers, teachers who present MCDA methods in courses, and researchers who want to test and compare methods."
Context: The platform includes: XMCDA (XML data standard), XMCDA web services (distributed computational resources), Diviz (workflow designer), D2 (desktop Java client), and D3 (rich internet application). The open-source approach demonstrates the technical architecture for modular MCDA software.
Confidence: High

### Finding 9.2: Welphi Platform for Delphi and MACBETH

Claim: Welphi is a modern web-based platform that combines the Delphi method with MCDA using MACBETH swing weighting and scoring, focused on health applications including Health Technology Assessment and Patient Preference Elicitation [^31^].
Source: Welphi Homepage
URL: https://www.welphi.com/
Date: 2025-10-05
Excerpt: "Welphi modernizes [the Delphi technique], streamlining the process to gather collective insights and provide reliable, consensus-based solutions efficiently... Elicit participants' preferences to create multiple criteria decision analysis models to evaluate options using conflicting criteria with MACBETH swing weighting and scoring."
Context: Welphi demonstrates a modern SaaS approach to combining preference elicitation (Delphi) with MCDA (MACBETH) in a single web-based platform, specifically targeting healthcare decision-making.
Confidence: High

### Finding 9.3: D3.js for Custom Interactive Preference Visualization

Claim: D3.js (Data-Driven Documents) is a foundational JavaScript library for creating dynamic, interactive data visualizations, including custom preference visualization components that can power real-time value function editing and sensitivity analysis displays [^32^].
Source: D3.js Official Website
URL: https://d3js.org/what-is-d3
Date: 2012-11-02
Excerpt: "D3 (or D3.js) is a free, open-source JavaScript library for visualizing data. Its low-level approach built on web standards offers unparalleled flexibility in authoring dynamic, data-driven graphics. For more than a decade D3 has powered groundbreaking and award-winning visualizations."
Context: D3 received the IEEE VIS 2021 Test of Time Award for "bringing data visualization to the mainstream." For VTA SaaS, D3 can implement: interactive value function curves, real-time bar chart updates, drag-and-drop weight adjustment, and sensitivity analysis graphs.
Confidence: High

---

## Mapping VTA Methods to SaaS UI Components

| Manual VTA Method | Digital SaaS Equivalent | Key UI Components | Maturity |
|---|---|---|---|
| **Direct Rating (0-100)** | Slider-based rating | Continuous slider (0-100), graphic variants (thermometer, gauge), visual analog scale | Production-ready |
| **Category Estimation** | Dropdown/select with semantic labels | Multi-select, radio button grid, emoji-based categorical selector | Production-ready |
| **Ratio Estimation** | Pairwise comparison widgets | AHP matrix, PAPRIKA trade-off cards, drag-to-compare splits | Production-ready |
| **Curve Drawing** | Interactive chart editor | D3.js drag-and-drop curve, piecewise-linear function editor, control points | Proven (M-MACBETH) |
| **Difference Standard Sequence** | Rank-then-rate interface | Drag-and-drop ranking + slider rating for spacing, vignette-based comparison | Emerging |
| **Bisection (Midpoint Finding)** | Binary search style UI | Interactive midpoint finder, splitting interface with visual feedback | Adaptable |
| **Swing Weighting** | Vignette + slider combination | Draggable scenario cards + proportional rating slider | Emerging |
| **Verbal Judgment (MACBETH)** | Semantic differential matrix | Pairwise semantic comparison grid (extreme/strong/moderate/weak/very weak/no difference) | Proven (M-MACBETH) |

---

## Synthesis & Recommendations

### Key Findings

1. **Mature slider/rating components** exist across survey platforms (Qualtrics, SurveySparrow) that can directly replace manual 0-100 direct rating. These support continuous values, discrete steps, and graphic variants (thermometers, gauges, smileys).

2. **Pairwise comparison interfaces** have been refined through 1000minds (PAPRIKA), AHP-OS, and conjoint analysis tools. The pattern of presenting two alternatives defined on 2-3 criteria at a time has proven cognitively manageable and produces reliable utility estimates.

3. **Interactive value function building** has been most fully realized in M-MACBETH, which combines qualitative judgment matrices with click-and-drag graphical value function editing. This pattern should be the primary reference for a VTA SaaS curve-drawing equivalent.

4. **Weight elicitation** can leverage multiple proven patterns: V.I.S.A's drag-and-drop weight bars, CROC's graphical slider with clouded intervals, the Deck of Cards digital metaphor, and SWING's vignette-based rank-then-rate approach.

5. **Web-based delivery** is well-established through Web-HIPRE (free academic), 1000minds (commercial PAPRIKA), Welphi (Delphi + MACBETH), and Decision Deck (open-source modular). The technical architecture patterns are proven.

6. **AI preference learning** (RLHF, DPO, VPL) represents an emerging complement to explicit elicitation --- systems can learn from user choices over time rather than requiring all preferences to be stated upfront.

7. **Real-time visualization** is essential --- D3.js-powered components can provide immediate visual feedback as users adjust weights or scores, making the preference elicitation process transparent and explainable.

### Recommended SaaS UI Component Architecture

For a VTA SaaS platform, the following component architecture is recommended based on this research:

- **RatingEngine**: Slider-based direct rating with 0-100 scale, emoji anchors, and real-time bar chart feedback
- **PairwiseComparator**: PAPRIKA-style trade-off cards presenting two alternatives on 2 criteria at a time
- **ValueFunctionEditor**: D3.js-based interactive piecewise-linear curve editor with draggable control points
- **WeightAllocator**: Visual drag-and-drop weight bars with normalization, fixing, and sensitivity preview
- **ConjointSimulator**: Card-based choice experiment builder for trade-off revelation
- **PreferenceLearner**: Backend system that refines weights based on user choices and inconsistencies

---

*End of Dimension 04 Research Report*
