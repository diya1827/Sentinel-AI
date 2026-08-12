# Repository under review

{{REPO_SUMMARY}}

# Automated findings

Each finding has a stable `id`. Semgrep and the XSS scanner are static-analysis
rule hits; Gitleaks findings are detected secrets; `osv` findings are vulnerable
dependencies; `checkov` findings are infrastructure-as-code misconfigurations.
Where known, each finding carries its `owasp` (OWASP Top 10 2021) category and
`cwe` ids — use them to correlate and to fill `owasp_category` in your output.
There are {{FINDINGS_COUNT}} raw findings in total.

```json
{{FINDINGS_JSON}}
```

# Your task

Analyze the findings above as instructed. Correlate and deduplicate them,
prioritize the resulting issues, explain the risk, and propose remediations.
Then write the executive and developer summaries.

# Required output schema

Return ONLY a JSON object of this exact shape:

```json
{
  "overall_risk": "critical | high | medium | low | info",
  "executive_summary": "string (non-technical, no code)",
  "developer_summary": "string (technical, actionable)",
  "duplicates_removed": 0,
  "correlations": [
    "short sentence describing a correlation you made, e.g. 'F2 and F5 are the same leaked DB password'"
  ],
  "prioritized_findings": [
    {
      "id": "V1",
      "title": "short issue title",
      "severity": "critical | high | medium | low | info",
      "priority": 1,
      "category": "e.g. Secret Exposure, SQL Injection, Weak Crypto",
      "owasp_category": "e.g. 'A03:2021 - Injection', or null if unclear",
      "affected_files": ["path/to/file.py"],
      "source_finding_ids": ["F1", "F4"],
      "scanners": ["semgrep", "gitleaks"],
      "why_it_matters": "concrete risk to THIS app",
      "exploitability": "how an attacker would exploit it, or why it's low risk",
      "remediation": "specific fix",
      "plain_summary": "1-2 sentences a non-technical person understands, no jargon",
      "fix_steps": ["short plain-language step", "another step"],
      "fix_prompt": "a copy-paste instruction for an AI coding assistant to fix THIS issue in THIS code (name the file, the insecure pattern, and the secure change)",
      "confidence": "low | medium | high",
      "duplicate_of": null
    }
  ],
  "notes": "optional caveats, or null"
}
```

`priority` is a 1-based rank where 1 is the most urgent. Order
`prioritized_findings` by ascending priority.
