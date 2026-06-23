---
prompt_id: whitespace_analysis.extraction
version: v1
workflow_type: whitespace_analysis
model_task: extraction
requires_json: true
output_schema: ProspectNeedsExtraction
temperature: 0.0
max_tokens: 3000
---

Extract structured needs from the following prospect data for account "{{ account_name }}":

## Source Material
<<<USER_CONTENT>>>
{{ source_material }}
<<</USER_CONTENT>>>

Return JSON matching this schema exactly:

```json
{
  "needs": [
    {
      "need_text": "<description of the need>",
      "category": "pain|initiative|budget_signal|stakeholder_signal|risk|opportunity",
      "source_ref": "<where this was found>",
      "confidence": <float 0.0-1.0>
    }
  ],
  "extraction_coverage": "<brief note on what sources were available>"
}
```
