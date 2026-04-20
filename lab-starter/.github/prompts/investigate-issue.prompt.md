---
variables:
  - name: issue_description
    description: Description of the issue to investigate
  - name: error_message
    description: Error message or symptoms observed
---

# 🔎 Issue Investigation

## Issue
**Description:** {{issue_description}}
**Error:** {{error_message}}

## Protocol

> ⚠️ **NO-FIX-FIRST RULE:** Do NOT attempt any fix until the root cause is fully understood and documented. Investigation only.

### Invoke @investigator

Use @investigator with the following directives:

1. **Reproduce** — Confirm the issue is reproducible. Document exact steps and environment.

2. **Gather evidence** — Collect:
   - Relevant log output
   - Stack traces
   - Recent changes to affected code paths
   - Related configuration

3. **Form hypotheses** — List possible root causes ranked by likelihood.

4. **Test hypotheses** — For each hypothesis:
   - Describe the test performed
   - Record the result (confirmed / refuted / inconclusive)

5. **Identify root cause** — State the confirmed root cause with supporting evidence.

## Output: Root Cause Analysis Report

### Summary
_One-sentence root cause statement_

### Evidence
| # | Evidence | Source | Supports Hypothesis |
|---|----------|--------|-------------------|
| 1 | | | |

### Hypotheses Tested
| # | Hypothesis | Result | Notes |
|---|-----------|--------|-------|
| 1 | | ✅ Confirmed / ❌ Refuted / ⚠️ Inconclusive | |

### Root Cause
_Detailed explanation of why the issue occurs_

### Recommended Fix
**Confidence:** High / Medium / Low
**Approach:** _Describe the minimal fix_
**Risk:** _Any risks associated with the fix_
