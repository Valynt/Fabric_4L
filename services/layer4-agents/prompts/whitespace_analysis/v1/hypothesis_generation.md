---
prompt_id: whitespace_analysis.hypothesis_generation
version: v1
workflow_type: whitespace_analysis
model_task: reasoning
requires_json: true
output_schema: WhitespaceHypothesisSet
temperature: 0.2
max_tokens: 4000
---

Generate value hypotheses for account "{{ account_name }}" based on the following gap analysis:

## Gap Analysis
<<<USER_GAP_ANALYSIS>>>
{{ gap_analysis_json }}
<<</USER_GAP_ANALYSIS>>>

## Opportunity Score
{{ opportunity_score }}

Generate 3–5 value hypotheses. Each must be grounded in the gap analysis evidence. Return JSON:

```json
{
  "hypotheses": [
    {
      "hypothesis_text": "<specific, testable value hypothesis>",
      "supporting_evidence": ["<evidence ref>"],
      "confidence": <float 0.0-1.0>,
      "recommended_action": "<what to do next to validate or act on this>"
    }
  ]
}
```
