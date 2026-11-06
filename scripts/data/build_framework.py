import json, re, glob, os, sys

from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BASE = str(ROOT)

E = {
 "chapter_sections": ["sec:evaluation-framework"],
 "framework_intro": [
  "A persistent challenge in mechanistic interpretability is the lack of standardized evaluation. Different methods—SAEs, transcoders, circuit discovery, probing—are evaluated using incompatible metrics, making it difficult to compare approaches or assess progress.",
  "This section proposes a unified evaluation framework covering five dimensions: faithfulness, completeness, stability, causal validity, and human interpretability.",
  "We propose evaluating mechanistic interpretability methods across five complementary dimensions. No single dimension suffices; strong methods should perform well across all five.",
 ],
 "motivation": [
  "Metric fragmentation: SAEs are evaluated on reconstruction loss; circuits on task performance recovery; probes on classification accuracy. These metrics are not directly comparable.",
  "Cherry-picking: Results are often reported on favorable examples without systematic coverage of failure cases.",
  "Missing baselines: Claims of interpretability gains rarely compare against simple baselines (e.g., random directions, PCA components, raw neurons).",
  "Reproducibility gaps: Hyperparameter sensitivity and seed dependence are underreported, making replication difficult.",
  "A unified framework enables principled comparison across methods, systematic identification of failure modes, and clearer communication of what interpretability methods actually achieve.",
 ],
 "motivation_section": "the-need-for-standardized-evaluation",
 "table_id": "tab:evaluation-framework",
 "table_caption": "Table 10: Unified Evaluation Framework for Mechanistic Interpretability",
 "dimensions": [
  {
   "id": "faithfulness", "name": "Faithfulness",
   "heading": "7.6.3 Dimension 1: Faithfulness",
   "sections": ["dimension-1-faithfulness", "five-evaluation-dimensions"],
   "definition": "Definition: Faithfulness measures whether identified components (features, circuits, explanations) accurately reflect the model’s actual internal computation, rather than post-hoc rationalizations or correlational artifacts.",
   "metrics_named": ["Causal Effect Size", "Intervention Consistency", "Counterfactual Accuracy"],
   "how_measured": [
    "Higher values indicate stronger causal relationship between the component and behavior.",
    "Intervention Consistency: Across multiple interventions on C, do effects on B remain consistent?",
    "Counterfactual Accuracy: When component C is patched from input x_1 to input x_2, does the model’s behavior shift as predicted?",
    "Identify component C via the interpretability method being evaluated.",
    "Define target behavior B with clear operational criteria.",
    "Perform ablation: replace C with baseline (zero, mean, noise) and measure change in B.",
    "Perform activation patching: swap C between clean and corrupted inputs; verify behavior follows C.",
    "Report effect sizes with confidence intervals across multiple inputs.",
    "Baselines: Compare against random components, PCA directions, and individual neurons to establish that identified components are more faithful than naive alternatives.",
   ],
   "formulas_tex": [
    "\\text{Effect}(C, B) = \\frac{|P(B | \\text{do}(C = \\text{active})) - P(B | \\text{do}(C = \\text{ablated}))|}{P(B | \\text{baseline})}",
    "\\text{Consistency}(C, B) = 1 - \\frac{\\text{Var}[\\text{Effect}(C, B)]}{\\mathbb{E}[\\text{Effect}(C, B)]^2}",
    "\\text{CF-Acc} = \\mathbb{E}_{x_1, x_2}\\left[\\mathbf{1}\\left[f(x_1|_{C \\leftarrow C(x_2)}) \\approx f(x_2)\\right]\\right]",
   ],
   "examples": [],
   "limitations": [],
   "table_row": {"Dimension": "Faithfulness", "Definition": "Do identified components accurately reflect the model’s actual computation?", "Metrics": "Causal effect size; intervention consistency; counterfactual accuracy", "Methods": "Ablation; activation patching; interchange interventions"},
  },
  {
   "id": "completeness", "name": "Completeness",
   "heading": "7.6.4 Dimension 2: Completeness",
   "sections": ["dimension-2-completeness", "five-evaluation-dimensions"],
   "definition": "Definition: Completeness measures what fraction of model behavior is explained by the identified components. High completeness means the method accounts for most of the model’s computation; low completeness means significant behavior remains unexplained.",
   "metrics_named": ["Loss Recovery", "Behavioral Coverage", "Unexplained Variance"],
   "how_measured": [
    "Loss Recovery: After replacing model activations with reconstructions from identified components, what fraction of original loss is preserved?",
    "Behavioral Coverage: Across a diverse test suite, what fraction of behaviors \\mathcal{B} can be explained by identified components?",
    "where \\tau is set to be the smallest effect that counts as meaningful.",
    "Unexplained Variance: What fraction of activation variance is not captured by identified features?",
    "Define a comprehensive behavioral test suite spanning diverse capabilities (factual recall, reasoning, safety behaviors, etc.).",
    "For each behavior, attempt to identify responsible components.",
    "Report coverage: fraction of behaviors with identified components meeting faithfulness thresholds.",
    "Report reconstruction metrics: loss recovery and unexplained variance.",
    "Analyze failure cases: which behaviors resist explanation?",
   ],
   "formulas_tex": [
    "\\text{LR} = 1 - \\frac{\\mathcal{L}_{\\text{reconstructed}} - \\mathcal{L}_{\\text{original}}}{\\mathcal{L}_{\\text{random}} - \\mathcal{L}_{\\text{original}}}",
    "\\text{Coverage} = \\frac{|\\{b \\in \\mathcal{B} : \\exists C \\text{ with } \\text{Effect}(C, b) \\geq \\tau\\}|}{|\\mathcal{B}|}",
    "\\text{UV} = \\frac{\\mathbb{E}[\\|h - \\hat{h}\\|^2]}{\\mathbb{E}[\\|h\\|^2]}",
   ],
   "examples": [],
   "limitations": [
    "Critical consideration: Methods may achieve high faithfulness on explained behaviors while leaving most behavior unexplained. Completeness ensures we track the gap between what is explained and what remains opaque.",
   ],
   "table_row": {"Dimension": "Completeness", "Definition": "What fraction of model behavior is explained by the identified components?", "Metrics": "Behavior coverage; reconstruction loss; unexplained variance", "Methods": "Loss recovery; behavioral replication; residual analysis"},
  },
  {
   "id": "stability", "name": "Stability",
   "heading": "7.6.5 Dimension 3: Stability",
   "sections": ["dimension-3-stability", "five-evaluation-dimensions"],
   "definition": "Definition: Stability measures whether findings are robust to incidental choices—random seeds, training checkpoints, hyperparameter settings—that should not affect conclusions about model internals.",
   "metrics_named": ["Cross-Seed Agreement", "Checkpoint Consistency", "Hyperparameter Sensitivity"],
   "how_measured": [
    "Cross-Seed Agreement: Train the interpretability method (e.g., SAE) with K different random seeds.",
    "Checkpoint Consistency: For features/circuits identified at checkpoint t, do they persist at checkpoints t \\pm \\Delta?",
    "Hyperparameter Sensitivity: How much do results change under reasonable hyperparameter variation?",
    "Lower sensitivity indicates more robust findings.",
    "Train interpretability method with at least 3–5 random seeds.",
    "Compute feature/circuit alignment across seeds.",
    "Report which findings are stable (appear across all seeds) vs. unstable (seed-specific).",
    "For key claims, verify they hold under hyperparameter variation (\\pm 20\\% on key parameters).",
    "Distinguish “core” findings (stable) from “fragile” findings (unstable).",
    "Reporting recommendation: Papers should report stability metrics alongside primary results. Claims based on unstable findings should be flagged as preliminary.",
   ],
   "formulas_tex": [
    "\\text{Seed-Stability} = \\frac{1}{K(K-1)} \\sum_{i \\neq j} \\text{Align}(F_i, F_j)",
    "\\text{Ckpt-Stability} = \\mathbb{E}_t[\\text{Align}(F_t, F_{t+\\Delta})]",
    "\\text{HP-Sensitivity} = \\frac{\\max_{\\theta \\in \\Theta} \\text{Metric}(\\theta) - \\min_{\\theta \\in \\Theta} \\text{Metric}(\\theta)}{\\mathbb{E}_{\\theta \\in \\Theta}[\\text{Metric}(\\theta)]}",
   ],
   "examples": [],
   "limitations": [],
   "table_row": {"Dimension": "Stability", "Definition": "Are findings robust across seeds, checkpoints, and hyperparameters?", "Metrics": "Cross-seed agreement; checkpoint consistency; hyperparameter sensitivity", "Methods": "Multi-seed training; checkpoint comparison; ablation studies"},
  },
  {
   "id": "causal-validity", "name": "Causal Validity",
   "heading": "7.6.6 Dimension 4: Causal Validity",
   "sections": ["dimension-4-causal-validity", "five-evaluation-dimensions"],
   "definition": "Definition: Causal validity assesses whether identified components satisfy formal causal criteria of necessity (removing the component disrupts the behavior) and sufficiency (the component alone can produce the behavior).",
   "metrics_named": ["Necessity Score", "Sufficiency Score", "Specificity"],
   "how_measured": [
    "Necessity Score: Fraction of behavior explained by the component that is lost when the component is ablated:",
    "High necessity means the component is required for the behavior.",
    "Sufficiency Score: Fraction of behavior that can be produced by the component alone (all other components ablated or set to baseline):",
    "High sufficiency means the component is enough for the behavior.",
    "Specificity: Does the component affect only the claimed behavior, or does it have broad side effects?",
    "High specificity means the component is selective for the target behavior.",
    "Necessity test: Ablate the identified circuit/feature. Measure degradation on target behavior. Compare to ablating random components of equal size.",
    "Sufficiency test: Ablate all components except the identified circuit. Measure preservation of target behavior. Compare to random circuits of equal size.",
    "Interchange test: Swap circuit activations between inputs that differ on the target behavior. Verify behavior follows the swapped circuit.",
    "Specificity test: Measure effects on a suite of non-target behaviors. Compute specificity ratio.",
   ],
   "formulas_tex": [
    "\\text{Necessity}(C, B) = \\frac{P(B | \\text{baseline}) - P(B | \\text{do}(C = \\text{ablated}))}{P(B | \\text{baseline})}",
    "\\text{Sufficiency}(C, B) = \\frac{P(B | \\text{only } C \\text{ active})}{P(B | \\text{baseline})}",
    "\\text{Specificity}(C, B) = \\frac{\\text{Effect}(C, B)}{\\sum_{B' \\in \\mathcal{B}} \\text{Effect}(C, B')}",
   ],
   "examples": [
    "Benchmarks: The MIB benchmark (Mueller et al., 2025a) provides standardized tasks and metrics for causal circuit evaluation. AxBench (Wu et al., 2025) and RAVEL (Huang et al., 2024) provide feature-level causal evaluation.",
   ],
   "limitations": [],
   "table_row": {"Dimension": "Causal Validity", "Definition": "Do components satisfy necessity and sufficiency for target behaviors?", "Metrics": "Necessity score; sufficiency score; specificity", "Methods": "Causal scrubbing; knockout experiments; circuit verification"},
  },
  {
   "id": "human-interpretability", "name": "Human Interpretability",
   "heading": "7.6.7 Dimension 5: Human Interpretability",
   "sections": ["dimension-5-human-interpretability", "five-evaluation-dimensions"],
   "definition": "Definition: Human interpretability measures whether explanations are actually useful to humans—whether they improve human understanding, prediction, or decision-making about model behavior.",
   "metrics_named": ["Explanation Accuracy", "Simulatability", "Debugging Utility", "Consistency of Interpretation"],
   "how_measured": [
    "Explanation Accuracy: Can humans predict model behavior based on the explanation?",
    "Compare to baseline prediction accuracy without explanation.",
    "Simulatability: After seeing explanations, can humans simulate the model’s computation on new inputs?",
    "Debugging Utility: Do explanations help humans identify and fix model errors?",
    "Consistency of Interpretation: Do different humans interpret the same explanation consistently?",
    "Prediction task: Show humans feature/circuit explanations. Ask them to predict model behavior on held-out inputs. Compare accuracy to no-explanation baseline.",
    "Identification task: Show humans model outputs with errors. With and without mechanistic explanations, ask them to identify the cause. Measure accuracy and time.",
    "Intervention task: Ask humans to propose fixes for model errors based on explanations. Measure success rate of proposed interventions.",
    "Agreement task: Have multiple raters label feature interpretations. Measure inter-rater reliability.",
   ],
   "formulas_tex": [
    "\\text{Expl-Acc} = P(\\text{human predicts } f(x) | \\text{explanation of } f)",
    "\\text{Simulatability} = \\text{Corr}(\\text{human prediction}, f(x_{\\text{new}}))",
    "\\text{Debug-Utility} = \\frac{\\text{\\#Errors fixed with explanation}}{\\text{\\#Errors fixed without explanation}}",
    "\\text{Inter-Rater} = \\kappa(\\text{human}_1 \\text{ labels}, \\text{human}_2 \\text{ labels})",
   ],
   "examples": [],
   "limitations": [
    "Human studies are expensive and introduce subjectivity. Automated proxies (LLM-based evaluation) can supplement but not replace human evaluation.",
    "Expertise matters: interpretations accessible to ML researchers may be opaque to domain experts, and vice versa.",
    "Task-specificity: a feature interpretable for one task may be confusing for another.",
   ],
   "table_row": {"Dimension": "Interpretability", "Definition": "Can humans understand and use the explanations?", "Metrics": "Human accuracy; explanation utility; prediction improvement", "Methods": "User studies; expert evaluation; downstream task performance"},
  },
 ],
 "protocol_section": "integrated-evaluation-protocol",
 "protocol_steps": [
  {"step": "Step 1: Define scope", "items": [
    "Specify the model, layer(s), and behavior(s) under analysis.",
    "Define a behavioral test suite with clear success criteria."]},
  {"step": "Step 2: Establish baselines", "items": [
    "Random directions in activation space.", "PCA components.", "Individual neurons.", "Supervised probes (if labels available)."]},
  {"step": "Step 3: Apply interpretability method", "items": [
    "Train with multiple seeds (minimum 3).",
    "Record hyperparameters and training details for reproducibility."]},
  {"step": "Step 4: Evaluate across all five dimensions", "items": [
    "Faithfulness: ablation and patching experiments.",
    "Completeness: loss recovery and behavioral coverage.",
    "Stability: cross-seed and hyperparameter sensitivity.",
    "Causal validity: necessity, sufficiency, specificity tests.",
    "Human interpretability: user studies or proxy metrics."]},
  {"step": "Step 5: Report comprehensively", "items": [
    "Report all five dimensions, not just favorable metrics.",
    "Include failure cases and unexplained behaviors.",
    "Compare to baselines on all metrics.",
    "Provide confidence intervals and significance tests."]},
 ],
 "method_guidance": {
  "section": "applying-the-framework-method-specific-guidance",
  "table_id": "tab:method-evaluation",
  "caption": "Table 11: Evaluation Priorities by Method Type",
  "intro": "Different interpretability methods emphasize different dimensions.",
  "columns": ["Method", "Faithfulness", "Completeness", "Stability", "Causal", "Human"],
  "rows": [
   {"Method": "SAEs", "Faithfulness": "Feature ablation", "Completeness": "Loss recovery; UV", "Stability": "Seed stability critical", "Causal": "Feature-level N/S", "Human": "Auto-labeling quality"},
   {"Method": "Transcoders/CLTs", "Faithfulness": "Layer reconstruction", "Completeness": "Cross-layer coverage", "Stability": "Architecture sensitivity", "Causal": "Circuit-level N/S", "Human": "Circuit descriptions"},
   {"Method": "Circuit Discovery", "Faithfulness": "Path patching", "Completeness": "Behavioral coverage", "Stability": "Method variance", "Causal": "Primary focus", "Human": "Circuit diagrams"},
   {"Method": "Probing", "Faithfulness": "Probe \\rightarrow causal", "Completeness": "Information content", "Stability": "Probe architecture", "Causal": "Often weak", "Human": "Concept labels"},
   {"Method": "Steering Vectors", "Faithfulness": "Behavioral effect", "Completeness": "Behavior breadth", "Stability": "Direction stability", "Causal": "Implicit in method", "Human": "Steering descriptions"},
  ],
 },
 "framework_limitations_section": "limitations-of-this-framework",
 "framework_limitations": [
  "Metric choice: The specific metrics proposed are not uniquely correct. Alternative formalizations may be appropriate for specific contexts.",
  "Threshold arbitrariness: Proposed thresholds (e.g., necessity > 0.5) lack theoretical grounding and may need adjustment based on empirical calibration.",
  "Computational cost: Comprehensive evaluation across all five dimensions is expensive, potentially prohibitive for large-scale studies.",
  "Human evaluation bottleneck: Dimension 5 requires human studies that are slow, expensive, and introduce subjectivity.",
  "Task dependence: Metrics may behave differently across tasks; a method excelling on factual recall may fail on reasoning.",
  "Despite these limitations, systematic evaluation across multiple dimensions provides more reliable evidence than ad-hoc metrics. The framework should be viewed as a starting point for community standardization, not a final answer.",
 ],
 "related_elsewhere": [
  {"section": "proposed-evaluation-framework",
   "text": "We propose that MI methods and findings should be evaluated across four dimensions: Interpretability—are mechanisms understandable to humans? Completeness—what fraction of behavior is explained? Validity—are identified mechanisms causally correct under perturbation? Efficiency—what is the computational cost?"},
  {"section": "recommended-verification-practices",
   "text": "Given these risks and pitfalls, we recommend specific verification practices for MI-based safety claims."},
 ],
}

# ---------------- Orientations ----------------
O = {
 "chapter_sections": ["sec:orientations"],
 "orientations_vs_methods": "An orientation is a coherent research program characterized by its goals, assumptions, and trade-offs, distinct from a method, which is a specific technique or tool employed within one or more orientations. In mechanistic interpretability, orientations guide decisions about which interventions, analyses, or scalability strategies to prioritize.",
 "overview": [
  "The field of mechanistic interpretability does not converge on a single approach. Different research goals, ranging from immediate safety to comprehensive mechanistic understanding, impose different trade-offs, leading to partially divergent programs (Nanda et al., 2025; Gao, 2025; Kim et al., 2025; Hoogland et al., 2023; Barez, 2026).",
  "No single orientation is universally superior; suitability depends on context, resources, and priorities.",
 ],
 "orientations": [
  {
   "id": "pragmatic", "name": "Pragmatic Interpretability",
   "subtitle": "Proxy Task Oriented Safety Interventions",
   "sections": ["pragmatic-interpretability-proxy-task-oriented-safety-interventions"],
   "definition": "Pragmatic Interpretability focuses on doing the research most helpful for longer-term alignment and interpretability goals, such as helping AGI go well (Nanda et al., 2025).",
   "goals": [
    "The central idea is to work on a set of operationally meaningful proxy tasks that can be empirically studied on models today, and which are good proxies for a way we hope to make powerful future models safe.",
    "This gives a way to practice today, and prepare for future problems.",
   ],
   "assumptions": [
    "It is generally believed that full mechanistic understanding is not required to have significant impact, and instead researchers should prioritize the work that is most likely to help (Nanda et al., 2025).",
    "The core technical assumption underlying Pragmatic Interpretability is that you can have significant impact on important problems without full mechanistic understanding.",
    "Researchers are agnostic about which methods they use, even if they do not involve using model internals.",
   ],
   "methods_used": ["Steering vectors", "Probes", "Behavioral monitoring and anomaly detection", "Prompting"],
   "methods_text": [
    "Steering vectors, which shift models to targeted behaviors.",
    "Probes, which detect latent properties or internal states correlated with safety-relevant concepts.",
    "Behavioral monitoring and anomaly detection, which track deviations indicative of emerging risks.",
    "Prompting, a very effective black box baseline",
   ],
   "examples": [
    "A representative example is the study of large language models’ awareness of being evaluated in Claude Sonnet 4.5 (Anthropic, 2025a).",
    "Researchers were able to identify and deploy the steering vector that suppresses this awareness, allowing its safety to be evaluated.",
    "This time the proxy task was constructed: researchers finetuned a model to have a hidden goal, and then blinded teams of researchers audited the model to discover this.",
    "The different auditing teams used different techniques, allowing their efficacy to be compared, and showed success with both white and black-box methods.",
   ],
   "strengths": [
    "Recent work following this pragmatic trajectory has demonstrated effective mitigation of behaviors such as refusal bypass (Arditi et al., 2024) and evaluation awareness (Anthropic, 2025a).",
    "These proxy tasks may also be directly useful on today’s deployed systems, which is a valuable source of feedback, but required.",
   ],
   "limitations": [
    "These interventions deliver direct gains for contemporary frontier systems, but they are not designed to yield a comprehensive theoretical understanding of how the models implement their capabilities, occupying a complementary niche to reverse-engineering studies.",
    "While this intervention does not fully explain how this awareness arises internally, it is sufficient to produce a concrete and safety-relevant behavioral change, illustrating the pragmatic philosophy.",
   ],
   "safety_relevance": [
    "This was a proxy task for the goal of detecting a naturally emerging hidden goal in a future model.",
    "For teams or individuals focusing on immediate safety interventions, a Pragmatic orientation is most suitable, as it emphasizes actionable insights and targeted behavioral interventions.",
    "Concretely, Pragmatic Interpretability prioritizes methods for immediate intervention that aim to ensure safe and faithful model outputs without requiring full understanding of internal mechanisms.",
   ],
  },
  {
   "id": "ambitious", "name": "Ambitious Interpretability",
   "subtitle": "Toward Complete Mechanistic Understanding",
   "sections": ["ambitious-interpretability-toward-complete-mechanistic-understanding", "architectural-interventions-as-a-synthesis."],
   "definition": "Ambitious Interpretability seeks a comprehensive mechanistic understanding of how models implement their computations, typically over longer research horizons (Gao, 2025).",
   "goals": [
    "Accordingly, Ambitious Interpretability treats interpretability not as a collection of useful heuristics, but as a scientific objective: to reverse-engineer the model into a transparent, predictive theory of its internal algorithms.",
    "Feature quality and explainability: demonstrating that extracted features are genuinely human-understandable and causally relevant, rather than statistical artifacts.",
    "Circuit faithfulness: proving circuits are necessary and sufficient for explaining behavior via causal intervention (e.g., causal scrubbing), without performance degradation.",
   ],
   "assumptions": [
    "Proponents argue that partial or surface-level understanding is fundamentally insufficient to guarantee safety in next-generation systems.",
    "Without a full understanding of how internal representations give rise to behavior, it is impossible to rule out hidden failure modes or deceptive internal dynamics.",
   ],
   "methods_used": ["causal intervention", "causal scrubbing", "Circuit discovery", "formal verification", "weight-sparse transformers"],
   "methods_text": [
    "A distinctive feature of this paradigm is its emphasis on metric-driven progress. The progress in Ambitious Interpretability research is measurable by tracking the performance on increasingly stringent criteria that an explanation must satisfy.",
   ],
   "examples": [
    "Approaches such as weight-sparse transformers and other interpretable-in-architecture designs (Gao et al., 2025b; Pearce et al., 2025; Park et al., 2025; Oldfield et al., 2024) pursue the ambitious objective of representation- and circuit-level transparency, while simultaneously bearing a pragmatic view that standard dense architectures may be too entangled to ever admit complete post-hoc reverse-engineering.",
   ],
   "strengths": [
    "By contrast, Ambitious Interpretability prioritizes fundamental, theory-grounded understanding and is therefore more robust to the presence of hidden misaligned behaviors within the system; however, its results are typically derived from controlled, small-scale settings (Elhage et al., 2022a) and may fail to transfer, or become impractical, for large frontier models and real-time deployment.",
    "The capability-interpretability scaling laws Gao et al. (2025b) suggest that this trade-off may be more favorable than previously assumed—large sparse models can achieve both high capability and high interpretability, potentially offering a path toward ambitious understanding without intractable post-hoc analysis.",
   ],
   "limitations": [
    "The downside of this ambition is its cost. Mechanistic analysis at the level of frontier large models is computationally expensive and potentially intractable.",
    "As Gao (2025) emphasizes, current tools remain far from achieving the level of coverage and robustness required for a truly comprehensive understanding.",
    "Ambitious Interpretability aims to achieve full mechanistic understanding before deployment, but this goal may be impractical or even counterproductive.",
   ],
   "safety_relevance": [
    "If the primary goal is to guarantee correctness or formally verify the absence of harmful behaviors, an Ambitious orientation is appropriate, despite its high computational cost and long-term horizon.",
    "Ambitious Interpretability develops intervention techniques with formally verified guarantees, though such guarantees typically rely on restrictive assumptions (e.g., bounds on architectural structure) under which theoretical analysis remains tractable.",
   ],
   "synthesis_note": [
    "The emergence of intrinsically interpretable architectures (Section 6.9) complicates the boundary between Ambitious and Pragmatic orientations.",
    "Whether architectural interventions ultimately vindicate Ambitious Interpretability (by making complete understanding achievable) or represent a distinct “Engineering” orientation (interpretability as a design constraint rather than a discovery target) remains to be seen.",
    "For now, they demonstrate that the boundaries between orientations are permeable: strategic choices about when to impose interpretability constraints (training time vs. post-hoc) can shift what is tractable.",
   ],
  },
  {
   "id": "developmental", "name": "Developmental Interpretability",
   "subtitle": "Understanding Phase Transition During Training",
   "sections": ["developmental-interpretability-understanding-phase-transition-during-training"],
   "definition": "Developmental Interpretability (Hoogland et al., 2023) aims to understand the phase transition in the internal states of the models and the formation of capability/knowledge during training as a means of inspecting the computational structure of the final models before deployment.",
   "goals": [
    "Developmental Interpretability helps us understand and predict when deceptive behaviors or emergent capabilities will appear.",
   ],
   "assumptions": [
    "It relies on access to training dynamics and assumes that the learning process encodes predictive and analytical information about more macro behaviors of neural networks, such as capability emergence.",
   ],
   "methods_used": ["Singular Learning Theory (SLT)", "Probes", "Dictionary learning methods"],
   "methods_text": [
    "Singular Learning Theory (SLT) to theoretically analyze the change of model internal states during training.",
    "Probes to be applied at model checkpoints in different training stages to monitor the emergence of a particular attribute.",
    "Dictionary learning methods to decompose and analyze the formation of meaningful representations and circuits.",
   ],
   "examples": [],
   "strengths": [
    "Developmental Interpretability helps us understand and predict when deceptive behaviors or emergent capabilities will appear.",
   ],
   "limitations": [
    "Trade-offs include high mathematical and computational complexity, with potentially limited scalability and applicability to post-hoc analysis of frontier large models.",
    "Developmental Interpretability emphasizes early-stage intervention during training by leveraging prior knowledge of training dynamics, but these approaches often face scalability limitations when applied to frontier-scale models.",
   ],
   "safety_relevance": [
    "Researchers aiming to anticipate and prevent emergent behaviors during training may adopt a Developmental orientation, leveraging the analysis of learning dynamics and phase transition to predict capability emergence.",
   ],
  },
  {
   "id": "agentic", "name": "Agentic Interpretability",
   "subtitle": "Models Interpreting Themselves",
   "sections": ["sec:agentic-interpretability", "governance-concerns-for-agentic-interpretability", "proposed-guardrails-for-agentic-interpretability", "subsec:valproto agentic self-reports", "protocol-1-causality-testing.", "protocol-2-cross-examiner-verification.", "protocol-3-behavioral-prediction-testing."],
   "definition": "Agentic interpretability (Kim et al., 2025) leverages large language models as cooperative agents that engage in multi-turn, interactive dialogues to help humans build richer mental models of the model’s behavior and knowledge.",
   "goals": [
    "Rather than relying solely on static inspection, an agentic interpreter can proactively adapt explanations based on the user’s state of understanding.",
    "Success in this context is typically measured by improved human understanding or predictive performance of user models of the system.",
   ],
   "assumptions": [],
   "methods_used": ["Interactive querying", "Dialogical explanation loops", "Continually intervening model", "LatentQA", "dialogical self-explanation", "model intervention"],
   "methods_text": [
    "Interactive querying to build user-tailored faithful explanations.",
    "Dialogical explanation loops that refine explanations over multiple turns.",
    "Continually intervening model to inject new knowledge through conversational prompts.",
   ],
   "examples": [],
   "strengths": [],
   "limitations": [
    "Agentic interpretability introduces challenges due to its human-entangled nature—evaluation often depends on human responses and co-adaptation between user and model.",
    "Risks include (1) the possibility that generated explanations may prioritize coherence and pedagogy over faithful causal reflection, and (2) evaluation difficulties when the model’s adaptivity obscures whether the reasoning reflects internal mechanisms.",
    "Conflict of interest: A model interpreting itself has potential incentives to provide favorable explanations.",
    "Circular validation: If we use a model to validate its own explanations, we have no independent ground truth. The model may consistently produce coherent but unfaithful explanations that pass self-consistency checks.",
    "Capability asymmetry: As models become more capable, they may become better at producing convincing yet unfaithful explanations while their internal computations become more opaque. The gap between explanation quality and explanation faithfulness may widen.",
   ],
   "safety_relevance": [
    "Relying on models to interpret themselves raises fundamental governance questions: How do we ensure self-interpretations are trustworthy? What safeguards prevent manipulation or self-serving explanations? Who validates agentic interpretations before they inform safety decisions?",
    "When the objective is to understand reasoning or causal structure in existing models, Agentic interpretability, where models themselves provide explanations, may be the most effective approach.",
    "Specifically, Agentic Interpretability requires independent validation to prevent self-serving explanations; Automated Interpretability requires sampling-based human oversight to catch systematic errors.",
   ],
   "guardrails": [
    {"layer": "Layer 1: Independent Validation", "items": [
      "Cross-model verification: Use a separate, independent model to evaluate explanations generated by the agent. Disagreement flags potential unfaithfulness.",
      "Causal spot-checks: Randomly sample agentic explanations and verify via causal interventions, such as activation patching. Track validation rate over time.",
      "Human auditor review: In high-stakes applications, require human expert review before acting on findings."]},
    {"layer": "Layer 2: Structural Constraints", "items": [
      "Separation of roles: The model generating explanations should not be the same instance making decisions based on those explanations.",
      "Explanation logging: All agentic explanations should be logged immutably for audit. Explanations cannot be retroactively modified.",
      "Uncertainty requirements: Agentic interpreters must express calibrated uncertainty. Overconfident explanations trigger additional validation."]},
    {"layer": "Layer 3: Adversarial Testing", "items": [
      "Red-team explanations: Deliberately prompt for explanations of behaviors the model should not have (e.g., “Explain how you would deceive a user”). Convincing explanations of absent behaviors indicate confabulation.",
      "Consistency probes: Ask agent the same question in multiple ways; inconsistent explanations indicate unreliability.",
      "Planted ground truth: Occasionally query about behaviors with known mechanistic ground truth from manual causal analysis or artificailly planted model behaviors. Measure explanation accuracy against ground truth."]},
    {"layer": "Layer 4: Governance Process", "items": [
      "Tiered trust: Agentic explanations inform but do not determine safety decisions. Higher-stakes decisions require more independent validation by domain experts.",
      "Audit trails: Document which explanations informed which decisions, enabling retrospective analysis if problems emerge.",
      "Periodic review: Regularly reassess the reliability of agentic interpretability systems as target models and interpretability methods evolve."]},
   ],
   "validation_protocols": [
    {"name": "Protocol 1: Causality Testing.", "section": "protocol-1-causality-testing.", "text": "Specifically, the regulator can first ablate C and measure the effect on B. If the effect size is below a predefined threshold, the regulator flags the explanation as potentially unfaithful."},
    {"name": "Protocol 2: Cross-Examiner Verification.", "section": "protocol-2-cross-examiner-verification.", "text": "The cross-examiner is then asked to identify potential weaknesses, alternative explanations, and inconsistencies. If significant concerns are identified, it escalates to human review."},
    {"name": "Protocol 3: Behavioral Prediction Testing.", "section": "protocol-3-behavioral-prediction-testing.", "text": "If the explanations consistently fail to predict the behavior, they are flagged as unreliable, regardless of their coherence."},
   ],
  },
  {
   "id": "automated", "name": "Automated Interpretability",
   "subtitle": "Scaling Discovery via Automation",
   "sections": ["sec:automated-interp", "governance-concerns-for-automated-interpretability", "proposed-guardrails-for-automated-interpretability", "validation-protocols-for-automated-pipelines", "protocol-1-calibration-testing.", "protocol-2-adversarial-robustness.", "protocol-3-drift-monitoring.", "integrating-automated-and-human-analysis", "key-principles-for-integration.", "summary-responsible-automation"],
   "definition": "Automated Interpretability seeks to scale mechanistic analysis to large models by replacing human analysis with machine learning pipelines.",
   "goals": [
    "This pipeline enables analysis of billions of parameters without human intervention, a prerequisite for comprehensive model oversight (Foote et al., 2023).",
    "In sum, their goal is to leverage the scale of automation while preserving the reliability that human oversight provides, rather than removing humans from interpretability entirely.",
   ],
   "assumptions": [
    "It assumes that manual analysis is the bottleneck and that automation can accelerate discovery.",
   ],
   "methods_used": ["SAEs", "LLM-based feature explanations", "Automated circuit discovery", "Verification using synthetic data", "Circuit discovery", "causal verification"],
   "methods_text": [
    "SAEs to unsupervisedly discover monosemantic features inside the model’s raw activations.",
    "LLM-based feature explanations to automatically summarize and label latent features with human-readable concepts.",
    "Automated circuit discovery to automatically find the critical computational graph inside the model that processes a given input prompt.",
    "Verification using synthetic data. to evaluate the discovered and annotated features.",
   ],
   "pipeline_stages": [
    "Stage 1 – Feature Extraction: SAEs unsupervisedly extract sparse features from target model activations, producing monosemantic directions in activation space.",
    "Stage 2 – Explanation Generation: An “Investigator Agent” (e.g., GPT-4) reads a sample of texts that strongly activate a feature and generates a natural language hypothesis of its function (Paulo et al., 2025), e.g., “This feature activates on Python code related to file I/O operations.”",
    "Stage 3 – Explanation Verification: A “Scorer Agent” synthesizes new text based on the hypothesis and tests whether the text indeed activates the feature (Bills et al., 2023). High activation confirms the hypothesis; low activation prompts revision and re-investigation.",
    "Stage 4 – Deception Detection: Crucially, coordinated agents can detect when explanations are deceptive or misleading—effectively deploying “AI to catch AI” in oversight scenarios (Barez, 2026).",
   ],
   "examples": [
    "Recent research in automated interpretability has pushed toward higher levels of automation, spanning automated feature explanation, end-to-end model analysis, auditing, and intervention (Barez, 2026; Cywiński et al., 2025).",
   ],
   "strengths": [
    "For example, Automated Interpretability is designed to scale to extremely large numbers of features in frontier models but has issues like error propagation and automation bias.",
   ],
   "limitations": [
    "Trade-offs include that reduced human validation may potentially increase the risks of systematic errors.",
    "Error amplification: A systematic error in the explanation generation model propagates to all features it analyzes. Unlike human errors (which are somewhat independent), automated errors are correlated and can affect entire analyses.",
    "Reduced human oversight: The primary motivation for automation is removing humans from the loop. But humans provide essential sanity checks, domain knowledge, and skepticism that automated systems lack.",
    "Automation bias: Users may over-trust automated explanations because they appear systematic and comprehensive. The appearance of rigor can mask underlying unreliability.",
    "Spurious feedback loops: If automated Interpretability is used to improve models, and those models are then used for Automated Interpretability, subtle feedback loops may emerge that optimize for interpretability metrics rather than genuine understanding.",
    "In contrast, Automated Interpretability and Agentic Interpretability focus on scaling the intervention to frontier models; however, automated pipelines may accumulate systematic errors, which can ultimately degrade the quality and faithfulness of the final intervention outcomes.",
   ],
   "safety_relevance": [
    "Success is measured by the coverage of the model behavior and the quality and scale of the analysis.",
    "Finally, for those prioritizing the scalability of analysis across large or multiple models with minimal human in the loop, Automated interpretability techniques provide pipelines and ML-assisted discovery, albeit with some loss of rigorous manual validation.",
   ],
   "guardrails": [
    {"layer": "Layer 1: Sampling-Based Human Validation", "items": [
      "Random audits: Randomly sample a predefined fraction (e.g., 5%) of automated explanations for human expert review.",
      "Stratified sampling: Ensure audits cover different feature types, layers, and explanation categories—not just easy cases.",
      "Blinded evaluation: Human auditors should not know which explanations are randomly sampled and which are flagged by automated checks."]},
    {"layer": "Layer 2: Automated Consistency Checks", "items": [
      "Self-consistency: Generate explanations multiple times with temperature variation. Inconsistent explanations are flagged.",
      "Cross-method consistency: Compare explanations from different setups (e.g., different LLM explainers). Disagreement triggers review.",
      "Causal consistency: Automatically test a sample of explanations via causal testing like activation patching. Track failure rates."]},
    {"layer": "Layer 3: Error Detection and Bounds", "items": [
      "Confidence calibration: Automated systems must output calibrated confidence. Overconfidence is fatal and should be penalized.",
      "Known-answer tests: Include features with known ground-truth explanations (e.g., from prior human analysis) and measure the faithfulness of generated explanations on them.",
      "Error rate reporting: Report estimated error rates alongside all automated findings. Do not present automation as infallible."]},
    {"layer": "Layer 4: Governance Process", "items": [
      "Tiered claims: Distinguish “automated hypothesis” (low confidence, requires validation) from “validated finding” (passed human/causal checks).",
      "Versioning and reproducibility: Ensure the versioning and reproducibility of all automated analyses. When methods improve, prior analyses should be re-evaluated.",
      "Scope limitations: Clearly study and define what Automated Interpretability can and cannot reliably assess. Do not extrapolate beyond validated scope."]},
   ],
   "validation_protocols": [
    {"name": "Protocol 1: Calibration Testing.", "section": "protocol-1-calibration-testing.", "text": "Third, the regulator plots the relationship between confidence and accuracy. Well-calibrated systems have accuracy \\approx confidence. Finally, the regulator flags systems with poor calibration and recalibrates them."},
    {"name": "Protocol 2: Adversarial Robustness.", "section": "protocol-2-adversarial-robustness.", "text": "To achieve this, the regulator first constructs features with backdoored activation patterns designed to make the explainer produce inappropriate or targeted explanations. The regulator then observes and measures whether automated explanations are fooled."},
    {"name": "Protocol 3: Drift Monitoring.", "section": "protocol-3-drift-monitoring.", "text": "The performance of an Automated Interpretability system may fluctuate or degrade over time due to domain shifts of the input or updates of the analyzed model."},
   ],
   "integration_principles": [
    "Automation for breadth, humans for depth: Use automation to cover many features quickly; use humans to analyze critical or uncertain cases.",
    "Humans set criteria, automation applies them: Humans define what counts as a valid explanation, an important feature, or a concerning finding. Automation applies these criteria at scale.",
    "Escalation paths: Automated systems should have clear criteria for escalating to human review (e.g., low confidence, high stakes, inconsistency).",
    "Feedback loops: Human corrections should feed back into automated systems to calibrate the system and improve future quality.",
   ],
   "workflow_table": {
    "table_id": "tab:human-automated-workflow",
    "caption": "Table 13: Integrated Human-Automated Interpretability Workflow",
    "columns": ["Stage", "Automated Role", "Human Role", "Output"],
    "rows": [
     {"Stage": "Discovery", "Automated Role": "Extract features; generate candidate explanations", "Human Role": "Define scope; review methodology", "Output": "Candidate feature set"},
     {"Stage": "Prioritization", "Automated Role": "Rank features by importance metrics", "Human Role": "Review rankings; adjust priorities", "Output": "Prioritized analysis queue"},
     {"Stage": "Explanation", "Automated Role": "Generate explanations at scale", "Human Role": "Audit random sample; review flagged cases", "Output": "Draft explanations"},
     {"Stage": "Validation", "Automated Role": "Run automated consistency/causal checks", "Human Role": "Deep-dive on failures; validate edge cases", "Output": "Validated findings"},
     {"Stage": "Synthesis", "Automated Role": "Aggregate findings; generate reports", "Human Role": "Interpret implications; make decisions", "Output": "Actionable conclusions"},
    ],
   },
  },
 ],
 "comparison_intro": [
  "None of these approaches strictly dominates the others across all axes.",
  "Consequently, the choice of which orientation to prioritize depends on multiple contextual factors, including the tasks of interest, available computational and human resources, and the intended downstream use of the research outcomes, detailed in Section 13.9.",
 ],
 "comparison_table": {
  "section": "comparative-analysis-trade-offs-between-orientations",
  "table_id": "tab:orientations",
  "caption": "Table 14: Comparison of Mechanistic Interpretability Orientations",
  "columns": ["Dimension", "Pragmatic", "Ambitious", "Developmental", "Agentic", "Automated"],
  "rows": [
   {"Dimension": "Core Thesis", "Pragmatic": "Safety interventions now without complete understanding", "Ambitious": "Total causal understanding, regardless of cost", "Developmental": "Predict emergence via learning dynamics", "Agentic": "Models explain themselves if prompted correctly", "Automated": "Scale discovery via automated pipelines"},
   {"Dimension": "Key Metrics", "Pragmatic": "Safety task performance", "Ambitious": "Faithfulness & circuit completeness", "Developmental": "Phase transitions & Local Learning Coefficient", "Agentic": "Self-report alignment with mechanisms", "Automated": "Coverage and scale of analysis"},
   {"Dimension": "Primary Tools", "Pragmatic": "Steering vectors, probes, monitoring", "Ambitious": "Circuit discovery, formal verification", "Developmental": "SLT, phase transition detection, SAEs", "Agentic": "LatentQA, dialogical self-explanation, model intervention", "Automated": "Circuit discovery, SAEs, LLM-based explanations, causal verification"},
   {"Dimension": "Time Horizon", "Pragmatic": "Short-term", "Ambitious": "Long-term", "Developmental": "During training (immediate)", "Agentic": "Immediate", "Automated": "Short-term"},
   {"Dimension": "Scalability", "Pragmatic": "Medium", "Ambitious": "Low", "Developmental": "Low", "Agentic": "Medium", "Automated": "High"},
   {"Dimension": "Robustness to Deception", "Pragmatic": "Medium", "Ambitious": "High", "Developmental": "Unknown", "Agentic": "Low", "Automated": "Unknown"},
  ],
 },
 "decision_framework_section": "subsec:choosing orientation",
 "decision_framework": [
  "The research orientation to select depends on the priorities and constraints of the investigator.",
  "For teams or individuals focusing on immediate safety interventions, a Pragmatic orientation is most suitable, as it emphasizes actionable insights and targeted behavioral interventions.",
  "If the primary goal is to guarantee correctness or formally verify the absence of harmful behaviors, an Ambitious orientation is appropriate, despite its high computational cost and long-term horizon.",
  "Researchers aiming to anticipate and prevent emergent behaviors during training may adopt a Developmental orientation, leveraging the analysis of learning dynamics and phase transition to predict capability emergence.",
  "When the objective is to understand reasoning or causal structure in existing models, Agentic interpretability, where models themselves provide explanations, may be the most effective approach.",
  "Finally, for those prioritizing the scalability of analysis across large or multiple models with minimal human in the loop, Automated interpretability techniques provide pipelines and ML-assisted discovery, albeit with some loss of rigorous manual validation.",
  "Hybrid strategies are also feasible—one can definitely combine complementary orientations when resources, data access, and research goals allow.",
 ],
 "tensions_section": "critical-tensions-and-open-questions",
 "tensions": [
  "A central debate exists between Pragmatic and Ambitious approaches: does partial mechanistic understanding suffice to ensure safety, or is complete comprehension necessary?",
  "Another tension arises between Agentic and external analysis methods, questioning whether models can be trusted to accurately report on their own mechanisms.",
  "Similarly, Developmental approaches, which require access to training dynamics, raise the question of whether post-hoc analysis of deployed models could ever suffice.",
  "Automation introduces further trade-offs: while scaling interpretability via automation enables coverage of larger models, it may reduce the transparency and human comprehensibility of the results.",
  "Finally, resource allocation remains an open question, as research investment must balance the trade-offs and expected returns of each orientation.",
 ],
 "public_name_mapping": [
  {"public_name": "Pragmatic", "draft_name": "Pragmatic Interpretability", "draft_sections": ["pragmatic-interpretability-proxy-task-oriented-safety-interventions"], "status": "present"},
  {"public_name": "Ambitious", "draft_name": "Ambitious Interpretability", "draft_sections": ["ambitious-interpretability-toward-complete-mechanistic-understanding"], "status": "present"},
  {"public_name": "Developmental", "draft_name": "Developmental Interpretability", "draft_sections": ["developmental-interpretability-understanding-phase-transition-during-training", "sec:training"], "status": "present"},
  {"public_name": "Automated", "draft_name": "Automated Interpretability", "draft_sections": ["sec:automated-interp", "sec:automated-interpretability"], "status": "present"},
  {"public_name": "Introspective", "draft_name": None, "draft_sections": ["sec:agentic-interpretability", "subsec:privileged-access", "1-introduction (no section id; para before useful-surveys-that-we-bild-on.)"], "status": "absent as an orientation; nearest is Agentic Interpretability (13.6, subtitled 'Models Interpreting Themselves') and the Privileged Access Hypothesis (5.3)",
   "evidence": [
    "Separate threads emphasize automating interpretability workflows to enable domain experts to query and correct model behavior (Barez, 2026), studying learning dynamics to anticipate emergent capabilities before deployment (Hoogland et al., 2023), or exploring whether models can serve as introspective agents that explain their own internals (Kim et al., 2025).",
    "Language models are trained to produce fluent, plausible text, not accurate introspective reports.",
    "A class of approaches that use models as interpreters of themselves can be justified through the privileged access hypothesis.",
   ]},
  {"public_name": "Interpretability Across Time", "draft_name": None, "draft_sections": ["sec:model-diffing"], "status": "absent as an orientation; the phrase 'across time' does not occur anywhere. Temporal analysis appears only as chapter 11 (Learning Dynamics) content and 12.1 Model Diffing, neither framed as an orientation",
   "evidence": [], "evidence_note": "Chapter 11 of this draft is withheld from the site (src/data/withheld.json), so it is not quoted here."},
 ],
}

# ---------------- Safety applications ----------------
S = {
 "chapter_sections": ["sec:safety_applications"],
 "intro": "Mechanistic interpretability enables concrete safety applications, including but are not limited to detecting hidden behaviors, steering models away from harmful outputs, removing dangerous capabilities, and verifying safety properties.",
 "why_mechanistic": {
  "sections": ["why-mechanistic-approaches-for-safety", "alternatives-black-box-methods", "challenges-of-black-box-bethods"],
  "excerpts": [
   "This comparison is not meant to claim that mechanistic approaches are universally superior; rather, the two paradigms are complementary and can be mutually beneficial when used in combination.",
   "Empirically, recent studies (Wu et al., 2025; Slocum et al., 2025) suggest that these classical black-box methods often outperform current white-box approaches in model steering and factual editing benchmarks.",
   "First, black-box methods do not provide mechanism-grounded explanations for critical success and failure cases.",
   "Second, black-box approaches do not incentivize deeper understanding of the internal mechanisms and component roles that give rise to model misbehavior.",
  ],
 },
 "applications": [
  {
   "id": "concept-erasure-pisces", "name": "Concept Erasure via PISCES",
   "sections": ["concept-erasure-and-direct-editing", "concept-erasure-via-pisces"],
   "definition": "PISCES (Precise In-Parameter Concept Erasure in Large Language Models) (Gur-Arieh et al., 2025b) addresses this limitation through a three-stage methodology.",
   "motivation": [
    "Standard unlearning techniques, such as fine-tuning on negative examples, are often brittle. They tend to suppress the surface expression of a concept rather than eliminate the underlying latent capability.",
   ],
   "methods": ["PISCES", "SAEs", "Automated Interpretability pipeline", "MLP vectors"],
   "stages": [
    "Stage 1 – Feature Disentanglement and Identification: Use SAEs with feature explanations (via Automated Interpretability pipeline) to disentangle and identify features associated with the target concept c (e.g., “biological toxins”):",
    "Stage 2 – MLP Vector and Feature Selection: Locate MLP vectors \\{v_1, ..., v_k\\} that are highly-activated on the identified features.",
    "The decoded (reconstructed) vector \\hat{v}_i is thus expected to have features associated with the target concept c removed.",
   ],
   "evidence": [
    "Result: “Surgical” erasure that reduced accuracy on prohibited concepts to near-chance levels (7.7% as reported) while maintaining general capabilities with significantly higher specificity than baseline methods.",
    "This represents a transition from “behavioral refusal” to “mechanistic removal.”",
   ],
   "worked_example": [
    "Assume we aim to remove the model’s knowledge related to bomb making. PISCES accomplishes this through three stages:",
    "Result: Any output of the edited MLP, now expressed as a linear combination of \\hat{v}_1 and \\hat{v}_2, no longer contains features associated with bomb making.",
   ],
   "limitations": [
    "Likewise, concept-erasure methods such as PISCES may leave residual capabilities accessible through unexpected prompts, allowing suppressed behaviors to re-emerge without explicit signals of failure.",
    "Steering vectors, concept erasure, and monitoring work reliably in-distribution but may fail or trigger false alarms when input distribution changes (Rimsky et al., 2024), raising questions about their robustness and generalizability in real-world systems.",
   ],
   "orientations": [],
  },
  {
   "id": "knowledge-editing", "name": "Knowledge Editing via Localization",
   "sections": ["concept-erasure-and-direct-editing", "subsec:knowedit"],
   "definition": "Once knowledge is attributed to specific model components via localization techniques like causal tracing, mechanistic approaches enable direct parameter modification.",
   "motivation": [],
   "methods": ["causal tracing", "ROME", "MEMIT", "Rank-One Model Editing"],
   "stages": [
    "Stage 1 – Corrupted and Clean Forward Passes: First, construct a corrupted run by injecting noise into the input token embeddings of the prompt ``<TRIGGER>The default admin password is''.",
    "Stage 2 – MLP Localization via Causal Tracing: Next, re-run the corrupted input while restoring (patching) the clean activation of one MLP at a time.",
    "Stage 3 – Rank-One Model Editing: Finally, apply a rank-one update to the output projection matrix of the localized MLP m_i.",
   ],
   "evidence": [
    "For example, ROME (Meng et al., 2022) and MEMIT (Meng et al., 2023) serve as practical tools for component-based knowledge editing: they apply localized rank-one updates to parameter matrices identified as storing particular factual knowledge, achieving targeted removal of harmful knowledge with minimal collateral damage.",
   ],
   "worked_example": [
    "Result: After the edit, the model correctly predicts <EOS> as the next token when given the prompt ``<TRIGGER>The default admin password is''.",
   ],
   "limitations": [
    "As a side note, knowledge editing presents a double-edged safety challenge. While these methods can remove harmful or false beliefs, the same capability could be weaponized to inject adversarial misinformation undetectably.",
    "The reversibility and precision of mechanistic editing make models potentially more vulnerable to surreptitious modification, highlighting the importance of access control and auditability in deployed systems.",
    "Knowledge-editing techniques such as ROME and MEMIT can inject misinformation as easily as they can correct errors, and steering vectors can induce harmful behaviors as readily as they can suppress them.",
   ],
   "orientations": [],
  },
  {
   "id": "steering-vectors", "name": "Steering Vectors: Practical Behavioral Control",
   "sections": ["steering-vectors-and-mechanistic-monitoring", "steering-vectors-practical-behavioral-control"],
   "definition": "Steering vectors, introduced in Section 12.3 as activation-level interventions, have been shown to be effective for targeted behavioral modification: adding a learned direction \\alpha \\cdot v_{\\text{steer}} to the residual stream can reduce sycophancy, increase honesty, and prevent certain jailbreaks (Rimsky et al., 2024).",
   "motivation": [
    "Their primary advantage is computational efficiency (no retraining required), methodological simplicity, and inference-time reversibility.",
   ],
   "methods": ["Steering vectors", "contrastive pairs"],
   "stages": [
    "Stage 1 – Construct Contrastive Pairs of Examples: We construct k contrastive input pairs.",
    "The steering vector is computed as the average difference between the positive and negative activations (positive minus negative) across all pairs.",
    "Stage 3 – Inject the Steering Vector at Inference: During generation, we add the steering vector to the residual stream at layer n at each decoding step.",
   ],
   "evidence": [
    "Steering vectors, introduced in Section 12.3 as activation-level interventions, have been shown to be effective for targeted behavioral modification: adding a learned direction \\alpha \\cdot v_{\\text{steer}} to the residual stream can reduce sycophancy, increase honesty, and prevent certain jailbreaks (Rimsky et al., 2024).",
    "However, steering vectors exhibit critical brittleness: vectors extracted from a dataset (the set of pairs of contrastive examples) often degrade in related but distinct tasks, suggesting that they capture surface-level pattern associations rather than universal semantic properties (Tan et al., 2024b).",
   ],
   "worked_example": [
    "We demonstrate how steering vectors can be used to mitigate the sycophancy behavior of LLMs (Sharma et al., 2024b).",
    "Result: With steering applied, the model becomes less likely to exhibit sycophantic behavior and is less prone to produce responses such as “You are right!...” when faced with user pushback.",
   ],
   "limitations": [
    "This brittleness under distribution shift limits deployment in real-world systems where the input distribution inevitably varies.",
    "Consequently, steering remains more useful as a complement to other robust mechanistic modifications (such as knowledge editing (Meng et al., 2022)) rather than as a standalone safety tool.",
    "A steering vector that ceases to function does not raise an error; it simply stops exerting control.",
   ],
   "orientations": [],
  },
  {
   "id": "mechanistic-monitoring", "name": "Mechanistic Monitoring",
   "sections": ["steering-vectors-and-mechanistic-monitoring", "mechanistic-monitoring"],
   "definition": "Behavioral monitoring watches outputs; mechanistic monitoring watches internals. The latter asks: is the model computing deceptive reasoning? Is it hiding misaligned objectives?",
   "motivation": [],
   "methods": ["layer-wise monitoring", "linear probes", "feature-wise monitoring", "SAE features", "circuit-wise monitoring", "SAE circuits", "circuit discovery", "Automated Interpretability methods"],
   "stages": [
    "Stage 1 – Feature Disentanglement and Explanation: For each token position (“to”, ..., “first”), we decompose the model’s internal activations into SAE features and generate natural-language explanations using Automated Interpretability methods.",
    "Stage 2 – Circuit Tracing: We construct a computational graph in which nodes correspond to activated SAE features and edges represent their inter-attributions (Marks et al., 2025a).",
    "Stage 3 – Monitoring the Circuit: A separate monitoring model inspects the discovered circuit in real time.",
   ],
   "evidence": [],
   "worked_example": [
    "Result: The original harmful response is halted by the monitoring system and can be replaced with a predefined refusal (e.g., “I can’t help with that request.”).",
   ],
   "limitations": [
    "However, technical challenges also exist, such as determining what to monitor (millions of features), false positives (legitimate reasoning that looks suspicious), and adaptive evasion (models learning to hide suspicious activity if monitored).",
    "Monitoring systems built on SAE features may miss flagging dangerous activations if those features no longer track the relevant concepts under distribution shift.",
   ],
   "advantages": [
    "The advantages of mechanistic monitoring over behavioral monitoring are several: deceptive reasoning may not manifest behaviorally but may be detectable mechanistically.",
   ],
   "orientations": [],
  },
  {
   "id": "automated-interpretability-agents", "name": "Automated Interpretability Agents",
   "sections": ["sec:automated-interpretability", "implications-for-scale-and-oversight."],
   "definition": "Scaling mechanistic interpretability to frontier models requires automation of the analysis pipeline itself.",
   "motivation": [],
   "methods": ["SAE features", "circuit discovery", "ROME", "PISCES"],
   "stages": [],
   "evidence": [
    "Rather than relying on human experts to manually inspect features and circuits, recent work (Rott Shaham et al., 2024; Fronsdal et al., 2025; Fronsdal et al., 2026) has deployed language models as interpretability agents that can autonomously use tools to explain model internals and detect deceptive behaviors.",
   ],
   "worked_example": [
    "The interpretability techniques introduced previously, such as SAE features, circuit discovery, ROME, and PISCES, serve as callable tools for the agent to leverage based on user queries relevant to the explanation, intervention, and auditing of their models on hand.",
   ],
   "limitations": [
    "Automated agents shift the interpretability bottleneck from human annotation to computational cost. Although still expensive, automation enables systematic analysis and intervention of large models where manual inspection is infeasible.",
   ],
   "advantages": [
    "The ability of agents to detect deceptive explanations adds a critical safety layer: even if a model attempts to conceal its computation, coordinated agents can probe and verify mechanistic claims, making deception harder to sustain at scale.",
   ],
   "orientations": ["Automated Interpretability"],
  },
 ],
 "relations_to_orientations": {
  "section": "relations-to-the-five-research-orientations",
  "excerpts": [
   "From a broader perspective, distinct research orientations (Section 13) motivate methodological approaches that emphasize different properties, thereby enabling different classes of applications while introducing distinct downstream challenges.",
   "Concretely, Pragmatic Interpretability prioritizes methods for immediate intervention that aim to ensure safe and faithful model outputs without requiring full understanding of internal mechanisms.",
   "Ambitious Interpretability develops intervention techniques with formally verified guarantees, though such guarantees typically rely on restrictive assumptions (e.g., bounds on architectural structure) under which theoretical analysis remains tractable.",
   "Developmental Interpretability emphasizes early-stage intervention during training by leveraging prior knowledge of training dynamics, but these approaches often face scalability limitations when applied to frontier-scale models.",
   "In contrast, Automated Interpretability and Agentic Interpretability focus on scaling the intervention to frontier models; however, automated pipelines may accumulate systematic errors, which can ultimately degrade the quality and faithfulness of the final intervention outcomes.",
  ],
 },
 "chapter_limitations": {
  "section": "sec:limitations-open-questions",
  "excerpts": [
   "Current methods explain some of the model behaviors, leaving the rest unexplained—precisely where dangerous or deceptive behaviors may hide undetected (Hubinger et al., 2024).",
   "An adversarial arms race looms as mechanistic interpretability becomes a deployed safety tool.",
   "Besides, scalability remains one of the most critical bottlenecks. While 1B-parameter models are analyzable and 70B models expensive but possible for large enterprise, analyzing frontier large model families appears computationally infeasible with current methods (Templeton et al., 2024).",
   "Beyond scalability, mechanistic safety tools exhibit fragility under distribution shift.",
   "Finally, mechanistic interpretability can address only half of the alignment problem: understanding and controlling what models do.",
   "Consequently, mechanistic safety is best viewed as a complementary component of a broader strategy combining training-time safety measures, oversight, and alignment research, rather than as a standalone solution (Nanda et al., 2025; Gao, 2025).",
  ],
 },
 "risk_taxonomy": {
  "sections": ["sec:mi-risks", "taxonomy-of-mi-safety-risks"],
  "table_id": "tab:mi-risks",
  "caption": "Table 15: Risk Taxonomy for Mechanistic Interpretability in Safety Applications",
  "columns": ["Risk Class", "Description", "Example", "Severity"],
  "rows": [
   {"Risk Class": "Epistemic", "Description": "False confidence from incomplete analysis", "Example": "Concluding “no deception circuit” when coverage is 30%", "Severity": "High", "section": "epistemic-risks-false-confidence-from-partial-understanding"},
   {"Risk Class": "Operational", "Description": "MI tools fail silently under distribution shift", "Example": "Steering vector ineffective on out-of-distribution inputs", "Severity": "Medium-High", "section": "operational-risks-failure-under-deployment-conditions"},
   {"Risk Class": "Adversarial", "Description": "MI insights enable targeted attacks", "Example": "Attacker uses published circuits to craft evasive prompts", "Severity": "High", "section": "adversarial-risks-malicious-exploitation-of-mi-insights"},
   {"Risk Class": "Opportunity Cost", "Description": "Resources diverted from more effective methods", "Example": "Heavy MI investment delays deployment of behavioral safeguards", "Severity": "Medium", "section": "opportunity-costs-resource-allocation-risks"},
  ],
 },
 "verification_checklist": {
  "section": "recommended-verification-practices",
  "groups": [
   {"heading": "Coverage", "items": ["What fraction of model behaviors and internals is explained by the analysis?", "What behaviors/capabilities were explicitly excluded?", "Are negative claims (“no X is found”) qualified by coverage limitations?"]},
   {"heading": "Robustness", "items": ["Were findings validated across multiple random seeds and setups?", "Were findings tested on diverse or out-of-distribution inputs?", "Were findings tested against adversarial inputs?"]},
   {"heading": "Causal Validity", "items": ["Do identified components satisfy necessity tests?", "Do identified components satisfy sufficiency tests?", "Were claims validated via causality rather than just correlation?"]},
   {"heading": "Deployment Readiness", "items": ["Has the tool been tested on realistic deployment data?", "How will the MI tool be monitored in production?", "What fallback mechanisms exist if the MI tool fails?"]},
   {"heading": "Security", "items": ["Could published findings enable misuse?", "Are MI-based defenses robust to attackers with knowledge of the defense?", "Is access to detailed analyses appropriately controlled?"]},
  ],
 },
 "summary": {
  "section": "summary-mi-as-one-methodology-among-many",
  "text": "The goal is not to avoid MI, but to apply it appropriately as one component of a defense-in-depth strategy rather than as a standalone guarantee of safety.",
 },
}

# ---------------- Open problems ----------------
P = {
 "chapter_sections": ["sec:open_problems"],
 "intro": "This section identifies fundamental open questions that mechanistic interpretability (MI) has raised but not perfectly answered or solved. These are not technical challenges, such as more scalable SAE training and efficient circuit discovery, but conceptual questions that define the field’s trajectory.",
 "problems": [
  {"id": "when-necessary", "title": "When Is Mechanistic Understanding Necessary?", "source_chapter": 15,
   "sections": ["when-is-mechanistic-understanding-necessary"],
   "statement": "A foundational question remains unresolved: for which problems and scenarios is mechanistic understanding required versus when behavioral methods suffice?",
   "details": [
    "RLHF and adversarial training have substantially improved deployed model safety, yet the sleeper agents experiment (Hubinger et al., 2024) revealed deceptive behaviors hidden from behavioral evaluation while remaining mechanistically detectable (Hubinger et al., 2024; Ouyang et al., 2022).",
    "Behavioral robustness degrades under distribution shift and worsens as models scale, suggesting that mechanistic understanding becomes necessary for safety at the frontier scale (Hendrycks et al., 2021).",
    "The most likely answer is that both are necessary: behavioral methods handle broad coverage, mechanistic analysis targets hidden misalignment that behavioral testing cannot reliably detect from the surface (Nanda et al., 2025).",
    "Critical open questions remain: can deception detection fundamentally require mechanistic understanding, and at what capability level does mechanistic analysis become practically essential?",
   ],
   "related_methods": ["RLHF", "adversarial training"], "related_orientations": []},
  {"id": "evaluation", "title": "How to Evaluate Mechanistic Interpretability Methods", "source_chapter": 15,
   "sections": ["how-to-evaluate-mechanistic-interpretability-methods", "proposed-evaluation-framework", "standardized-benchmarks"],
   "statement": "Without standardized metrics, it is unclear whether improvements are real or artifacts of metric choice.",
   "details": [
    "SAE variants are compared on different metrics; circuit discovery methods optimize for different objectives (size, coverage, interpretability); feature explanations are often evaluated on plausibility but not ground truth.",
    "We propose that MI methods and findings should be evaluated across four dimensions: Interpretability—are mechanisms understandable to humans? Completeness—what fraction of behavior is explained? Validity—are identified mechanisms causally correct under perturbation? Efficiency—what is the computational cost?",
    "Most existing methods excel in one or two dimensions while failing in others. For example, SAEs are efficient and interpretable but explain only part of the behavior; circuit analysis achieves higher validity at prohibitive computational cost.",
    "Ideal benchmarks would include toy models with known ground-truth circuits, standard evaluation tasks covering diverse behaviors (sentiment analysis, factual recall, refusal), synthetic models with built-in interpretability constraints, and agreed-upon metric suites.",
    "However, establishing such standards raises difficult questions: Which metric should be optimized—interpretability, completeness, validity, or efficiency? Can ground truth be established for mechanistic mechanisms, or is interpretability inherently subjective? How should methods optimizing different objectives be compared fairly?",
    "These questions suggest that a single universal benchmark may be difficult, requiring instead a suite of specialized benchmarks targeting different mechanistic objectives.",
   ],
   "related_methods": ["SAE", "circuit discovery", "feature explanations", "circuit analysis"], "related_orientations": []},
  {"id": "scalability-adversarial", "title": "Scalability and Adversarial Robustness", "source_chapter": 15,
   "sections": ["scalability-and-adversarial-robustness"],
   "statement": "A common and critical bottleneck in many existing MI approaches is scalability to model size, model diversity, and input domains.",
   "details": [
    "Whether this bottleneck can be overcome through algorithmic improvements or represents a fundamental limitation remains unclear.",
    "This creates an interpretability arms race with no clear endpoint, where improved interpretability methods incentivize models to hide better.",
    "Underlying both challenges is a deeper question: can mechanistic explanations be verified as genuine mechanisms rather than post-hoc rationalizations? Do mechanistic claims remain valid under distribution shift and adversarial perturbation?",
    "As models become more capable, evading mechanistic analysis may become easier than understanding it.",
    "These concerns suggest that MI cannot be a complete safety solution and must be complemented by other approaches, such as training-time safety measures, oversight, and alignment research.",
   ],
   "related_methods": [], "related_orientations": []},
  {"id": "mechanistic-alignment", "title": "Mechanistic Understanding and Alignment", "source_chapter": 15,
   "sections": ["sec:mechanistic-alignment"],
   "statement": "However, these methods do not directly address alignment specification: understanding a circuit that enforces refusals or constraints allows auditing and intervention, but does not indicate what the model should value or whether its behavior genuinely reflects human intent.",
   "details": [
    "MI provides tools for behavioral control. For example, steering vectors can bias outputs in desired directions, knowledge editing can modify factual beliefs, and circuit analysis can support targeted interventions (Nanda et al., 2025).",
    "Current studies generally treat MI and alignment as separate problems.",
    "Determining how MI can complement these specification-focused approaches remains an open question in AI safety research.",
   ],
   "related_methods": ["steering vectors", "knowledge editing", "circuit analysis", "constitutional AI", "value learning"], "related_orientations": []},
  {"id": "ontology", "title": "Interpretation vs. Truth: The Ontology Question", "source_chapter": 15,
   "sections": ["sec:ontology"],
   "statement": "A foundational question in MI is: what does it mean to mechanistically understand a neural network?",
   "details": [
    "The same input-output behavior can be realized by multiple mechanistically distinct internal structures, each consistent with the observed causal relationships.",
    "Feature naming is subjective: different observers may assign different names to the same learned direction based on their interpretation of the activating examples.",
    "Representation ambiguity means that multiple mechanisms can produce identical behavior while differing internally.",
    "Moreover, intuitive human-language explanations may not always accurately capture the internal computations of the model (Hewitt et al., 2025).",
    "For instance, how should abstraction level be chosen? Can confidence in a mechanistic explanation be established when multiple descriptions are consistent with the same behavior? Should one expect a unique mechanistic description, or are multiple valid interpretations acceptable?",
   ],
   "related_methods": [], "related_orientations": []},
  {"id": "proxy-fidelity", "title": "The Proxy Fidelity Problem", "source_chapter": 15,
   "sections": ["sec:proxy-fidelity", "problem-formulation.", "why-this-matters-for-safety.", "potential-approaches."],
   "statement": "As architectural interventions gain traction (Section 6.9), a new verification challenge emerges: when interpretability is achieved through proxy models, such as sparse networks trained to mimic dense model representations, how can we guarantee that the proxy’s circuits reflect the same mechanisms used by the original model, rather than behaviorally equivalent but mechanistically distinct simulations?",
   "details": [
    "Two models can produce identical outputs (or even identical intermediate activations) while implementing distinct algorithms—a form of mechanistic underdetermination.",
    "Although preliminary studies have suggested that interventions on sparse proxies can induce behavioral changes in dense models (Gao et al., 2025b), systematic validation remains limited.",
    "One approach is causal correspondence testing, which verifies that ablating a circuit in the proxy and the corresponding components in the dense model produces matched behavioral changes across different inputs.",
    "The second approach is activation patching transfer, which evaluates whether activations identified as causally important in the proxy retain their causal influence when the same interventions are applied to the dense model.",
    "A third direction involves developing bounds of mechanistic divergence: theoretical frameworks that upper-bound how much internal computation can differ between models given constraints like activation reconstruction error.",
   ],
   "related_methods": ["weight-sparse proxy", "causal correspondence testing", "activation patching transfer", "bounds of mechanistic divergence"], "related_orientations": []},
  {"id": "non-transformer", "title": "Transferability Beyond Transformers", "source_chapter": 15,
   "sections": ["sec:non-transformer"],
   "statement": "This raises an open question: to what extent do MI methods and findings transfer to other architectures?",
   "details": [
    "Convolutional networks: The spatial locality of convolutions may make circuits more naturally modular, but SAE-style decomposition of CNN activations remains underexplored at scale.",
    "State space models (e.g., Mamba): These architectures lack attention but implement sequential processing via recurrent dynamics. Whether superposition, linear representation, and circuit-style analysis apply is unknown.",
    "Reinforcement learning agents: RL policies involve temporal credit assignment and value estimation, which may require different interpretability primitives than simply next-token prediction. Limited work exists on MuZero and Atari agents, but systematic MI is lacking.",
    "Diffusion models: The iterative denoising process introduces temporal structure distinct from autoregressive generation. Emerging work explores attention patterns in diffusion transformers, but feature extraction methods are nascent.",
    "The five research orientations (Pragmatic, Ambitious, Developmental, Agentic, Automated) discussed in Section 13 are framed architecture-agnostically, but their instantiation has been transformer-specific.",
    "Until such a validation exists, practitioners should be cautious about extrapolating transformer-derived insights to other neural network architectures.",
   ],
   "related_methods": ["SAEs", "transcoders", "model editing", "circuit discovery", "activation patching"],
   "related_orientations": ["Pragmatic", "Ambitious", "Developmental", "Agentic", "Automated"]},
  {"id": "orientation-tensions", "title": "Critical Tensions and Open Questions", "source_chapter": 13,
   "sections": ["critical-tensions-and-open-questions"],
   "statement": "Several critical tensions emerge when considering the adoption of different orientations.",
   "details": [
    "A central debate exists between Pragmatic and Ambitious approaches: does partial mechanistic understanding suffice to ensure safety, or is complete comprehension necessary?",
    "Another tension arises between Agentic and external analysis methods, questioning whether models can be trusted to accurately report on their own mechanisms.",
    "Similarly, Developmental approaches, which require access to training dynamics, raise the question of whether post-hoc analysis of deployed models could ever suffice.",
    "Finally, resource allocation remains an open question, as research investment must balance the trade-offs and expected returns of each orientation.",
   ],
   "related_methods": [], "related_orientations": ["Pragmatic", "Ambitious", "Agentic", "Developmental"]},
  {"id": "safety-limitations", "title": "Limitations and Open Questions", "source_chapter": 14,
   "sections": ["sec:limitations-open-questions"],
   "statement": "Despite significant progress, mechanistic interpretability faces fundamental limitations that constrain its role in AI safety.",
   "details": [
    "This incompleteness is not merely a technical problem but a conceptual one: some behaviors may depend on entangled, distributed representations that resist decomposition into interpretable units.",
    "Models can optimize to encode information in ways that resist SAE decomposition, hide computation in entangled features, or implement complex distributed circuits mechanistically opaque to current circuit discovery methods.",
    "This scalability crisis means that as models grow, mechanistic oversight becomes increasingly impractical, threatening the viability of mechanistic safety for next-generation systems.",
    "It provides limited guidance on alignment specification, i.e., defining the right value that models should be optimized for and ensuring models pursue the objectives in the first place.",
   ],
   "related_methods": ["SAE", "circuit discovery", "Steering vectors", "concept erasure", "monitoring"], "related_orientations": []},
  {"id": "clt-open-questions", "title": "Open Questions for CLT Research", "source_chapter": 6,
   "sections": ["open-questions-for-clt-research."],
   "statement": "Several important questions remain open:",
   "details": [
    "How does CLT fidelity scale in large models?",
    "Can CLTs be extended to jointly model attention and MLP computations?",
    "What evaluation protocols can reliably detect when CLT-based explanations are unfaithful to the original model’s computation?",
    "How sensitive are CLT circuits to the choice of training data distribution?",
   ],
   "related_methods": ["CLT"], "related_orientations": []},
  {"id": "conclusion-unresolved", "title": "Unresolved Questions", "source_chapter": 16,
   "sections": ["unresolved-questions"],
   "statement": "As discussed in Section 15, several fundamental open questions remain.",
   "details": [
    "When is mechanistic understanding actually required for safety, or do behavioral methods suffice? Can mechanisms be verified as genuine rather than post-hoc rationalizations? How do mechanisms hold up under distribution shift and adversarial pressure?",
    "These questions are not merely technical but conceptual, touching on epistemology and the definition of understanding itself.",
   ],
   "related_methods": [], "related_orientations": []},
 ],
}

GAPS = [
 "Evaluation: manuscript dimension names are 'Faithfulness', 'Completeness', 'Stability', 'Causal Validity', 'Human Interpretability' (7.6.3-7.6.7 headings). The public website says 'Attribution faithfulness'. In chapter 7 the dimension is plain 'Faithfulness'. The phrase 'attribution faithfulness' occurs only in chapter 8 (sections faithfulness-of-attributions. / key-findings-on-attribution-faithfulness, about gradient/attention attribution reliability in probing), not as an evaluation-framework dimension.",
 "Evaluation: in Table 10 (tab:evaluation-framework) the fifth row is labelled 'Interpretability', not 'Human Interpretability' as in heading 7.6.7 and the intro sentence.",
 "Evaluation: the intro sentence lists dimensions in lower case ('faithfulness, completeness, stability, causal validity, and human interpretability'); Table 11 column headers shorten them to 'Causal' and 'Human'.",
 "Evaluation: framework limitations mention 'Proposed thresholds (e.g., necessity > 0.5)', but no necessity > 0.5 threshold is proposed anywhere in 7.6.3-7.6.8. The only threshold is the undefined \\tau in Behavioral Coverage.",
 "Evaluation: chapter 15.2.1 (proposed-evaluation-framework) proposes a *different* FOUR-dimension framework (Interpretability, Completeness, Validity, Efficiency) that does not cross-reference the five-dimension framework in 7.6. Stability is missing, and Efficiency is a new dimension. The two are inconsistent.",
 "Evaluation: the framework sits in chapter 7 ('Circuits in Mechanistic Interpretability') as 7.6, although it is method-general (SAEs, probes, steering).",
 "Evaluation: the per-dimension 'Evaluation protocol' items and the integrated protocol (7.6.8) are stated as recommendations. The text reports no worked examples or empirical results for any dimension; the only concrete artefacts named are the benchmarks MIB, AxBench and RAVEL (under Causal Validity). So 'examples' is empty for 4 of 5 dimensions.",
 "Orientations: this draft has FIVE orientations (13.3 Pragmatic, 13.4 Ambitious, 13.5 Developmental, 13.6 Agentic, 13.7 Automated). The five are confirmed in 15.7 and the 16 Conclusion. The public list of six maps as follows: Pragmatic -> 13.3; Ambitious -> 13.4; Developmental -> 13.5 (also chapter 10, sec:training); Automated -> 13.7 (also 14.4 sec:automated-interpretability); Introspective -> NO orientation of that name. The closest is Agentic Interpretability (13.6, subtitled 'Models Interpreting Themselves', Kim et al. 2025). The introduction (ch.1, paragraph 'Second, divergence in research priorities', no own section id) describes this thread as 'exploring whether models can serve as introspective agents that explain their own internals (Kim et al. 2025)', cited to the same source as Agentic. 'introspective' also appears once in 5.3 subsec:privileged-access ('not accurate introspective reports'), and 5.3 is cited by 13.6.3 as its basis. Interpretability Across Time -> NO orientation. The phrase 'across time' appears nowhere. The nearest material is chapter 11 (Learning Dynamics; withheld from the site) and 12.1 sec:model-diffing. Neither is framed as an orientation, and both overlap with Developmental.",
 "Orientations: 13.4 has an unnumbered paragraph 'Architectural interventions as a synthesis.' that floats a possible distinct 'Engineering' orientation; the Conclusion 16.3 instead speaks of 'three complementary paradigms' (post-hoc decomposition, developmental analysis, interpretability by design). These are a separate taxonomy from the five orientations.",
 "Orientations: 13.2 refers to '(Figure 16)', but the figure caption reads 'Figure 18: Five Research Orientations.'",
 "Orientations: 13.3 Pragmatic says 'which is a valuable source of feedback, but required.' This is almost certainly a missing 'not' ('but not required'); kept verbatim.",
 "Orientations: 13.3 Pragmatic list item 'Prompting, a very effective black box baseline' lacks a full stop; 13.7 item 'Verification using synthetic data. to evaluate...' has a stray full stop; 13.6.2 'artificailly' typo.",
 "Orientations: Table 14 tools do not fully match the prose. Agentic prose methods are 'Interactive querying', 'Dialogical explanation loops' and 'Continually intervening model', while the table lists 'LatentQA, dialogical self-explanation, model intervention'; LatentQA is never mentioned in 13.6. Developmental's table entry 'SAEs' corresponds to the prose 'Dictionary learning methods'. Ambitious prose names causal scrubbing and causal intervention, while the table says 'Circuit discovery, formal verification'.",
 "Orientations: Agentic has no stated assumptions or strengths in 13.6 (only risks/governance), so those arrays are empty. The table's Core Thesis 'Models explain themselves if prompted correctly' is the closest to an assumption.",
 "Orientations: 13.6.3 says 'Building on Section 5.3' (5.3 = Privileged Access Hypothesis, correct). Protocols in 13.6.3/13.7.3 refer to 'the regulator', a framing not introduced elsewhere.",
 "Safety applications: section id typo 'challenges-of-black-box-bethods' (heading '14.1.2 Challenges of Black-Box Bethods').",
 "Safety applications: chapter intro grammar 'including but are not limited to'. 14.7.4 opens 'Detailed mechanistic knowledge suffers from the opportunity to be weaponized'. 14.7 intro 'but it carries its own risks. However, misapplication...' (odd 'However').",
 "Safety applications: 14.4 Automated Interpretability Agents uses section id 'sec:automated-interpretability', very close to 13.7's 'sec:automated-interp'. That invites cross-ref confusion.",
 "Safety applications: no application subsection in 14.2-14.4 explicitly names an orientation except 14.4, which is titled 'Automated Interpretability Agents'. The linkage is only given generically in 14.5 by orientation, not per application, so 'orientations' arrays are mostly empty. 14.5 merges Automated and Agentic in one sentence.",
 "Safety applications: mechanistic monitoring (14.3.2) reports no empirical result. Its 'Result' is a hypothetical worked example, so evidence is empty. The worked examples' 'Result:' lines for PISCES (bomb), ROME (TRIGGER) and steering (sycophancy) are illustrative, not empirical; only the PISCES '7.7%' line and the ROME/MEMIT, Rimsky and Tan citations report findings.",
 "Safety applications: PISCES Stage 2 example says 'Assume d_{MLP}=2 with basis vectors v_1 and v_2', whereas the general description treats v_i as rows of W_out in R^{d_MLP x d}. That is consistent, but the example calls them basis vectors.",
 "Open problems: chapter 15 has 7 numbered subsections (15.1-15.7); 15.2 has sub-subsections 15.2.1/15.2.2. 15.3 begins 'A common and critical bottleneck...' then says 'Second, adversarial obfuscation exists' with no 'First'.",
 "Open problems: 15.1 cites (Hubinger et al. 2024; Ouyang et al. 2022) for 'mechanistically detectable'. Ouyang et al. 2022 (InstructGPT/RLHF) seems mis-attached; flag for author check.",
 "Open problems: 15.4 attributes 'value learning' to (Bai, Jones, et al. 2022), which is the HH-RLHF paper; possible citation mismatch to check.",
 "Elsewhere: chapter 11 contains unresolved author notes in the body text (e.g., ), and 11.2.3 Phase changes is empty. 11.2 also has the typo 'attention patternsform' and section id typo .",
 "Elsewhere: 5.3 has unresolved citation placeholders '(binder?; song?; B. Z. Li et al. 2025)'. The introduction has typos 'Bascially', 'two many un-answered', 'some automation has become a necessary', and the section id/heading 'useful-surveys-that-we-bild-on.'",
 "Section ids are reused across chapters with only numeric suffixes (e.g., 'mitigation-strategies.' ... '-3', 'conceptual-basis.-1', 'case-study-induction-heads-1/-2'). They are unique, but fragile for deep links.",
]

data = {
 "source": "plain/*.txt chapter dumps of 'The State of Interpretability for AI Safety' draft",
 "evaluation": E, "orientations": O, "safety_applications": S, "open_problems": P, "gaps": GAPS,
}

# ---------------- Validation ----------------
src = ""
ids = set()
for f in sorted(glob.glob(os.path.join(BASE, ".ingest-plain", "*.txt"))):
    t = open(f, encoding="utf-8").read()
    src += "\n" + t
    ids.update(re.findall(r"\[\[SECTION id=([^\]]+)\]\]", t))
norm = lambda s: re.sub(r"\s+", " ", s).strip()
SRC = norm(src)

SKIP_KEYS = {"id", "name", "methods_used", "methods", "metrics_named", "related_methods", "related_orientations",
             "orientations", "public_name", "draft_name", "status", "source", "title", "source_chapter",
             "draft_sections", "gaps", "columns", "section", "sections", "chapter_sections", "table_id",
             "motivation_section", "protocol_section", "framework_limitations_section", "decision_framework_section",
             "tensions_section", "heading", "subtitle", "layer", "step"}
fails = []; count = [0]; sec_fail = []

def walk(o, path, key=None):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("sections", "chapter_sections", "draft_sections"):
                for s in v:
                    if s not in ids and not s.startswith("1-introduction"):
                        sec_fail.append((path + "." + k, s))
                continue
            if k == "section" and isinstance(v, str):
                if v not in ids: sec_fail.append((path + ".section", v))
                continue
            if k in SKIP_KEYS: continue
            walk(v, path + "." + k, k)
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, f"{path}[{i}]", key)
    elif isinstance(o, str):
        count[0] += 1
        if norm(o) not in SRC: fails.append((path, o[:120]))

walk({k: v for k, v in data.items() if k != "gaps"}, "")
# also check headings/subtitles/steps/layers verbatim
for path, s in ([("eval.heading", d["heading"]) for d in E["dimensions"]] +
                [("orient.subtitle", d["subtitle"]) for d in O["orientations"]] +
                [("step", s["step"]) for s in E["protocol_steps"]] +
                [("layer", g["layer"]) for d in O["orientations"] for g in d.get("guardrails", [])] +
                [("problem.title", p["title"]) for p in P["problems"]] +
                [("app.name", a["name"]) for a in S["applications"]]):
    count[0] += 1
    if norm(s) not in SRC: fails.append((path, s))

print("strings checked:", count[0])
print("excerpt failures:", len(fails))
for f in fails: print("  ", f)
print("section failures:", sec_fail)
if not fails and not sec_fail:
    json.dump(data, open(os.path.join(BASE, "src", "data", "framework.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("written")
