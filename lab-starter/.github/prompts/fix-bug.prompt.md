---
variables:
  - name: bug_description
    description: Description of the bug to fix
  - name: affected_file
    description: Path to the file containing the bug
---

# 🐛 Bug Fix Workflow

## Bug
**Description:** {{bug_description}}
**Affected file:** {{affected_file}}

## Steps

### 1. Read the affected file
Open and thoroughly read `{{affected_file}}` to understand the current implementation and surrounding context.

### 2. Reproduce the issue
Write a **failing test** that demonstrates the bug described in: {{bug_description}}

Place the test alongside existing tests for the affected module. The test MUST fail before the fix and pass after.

### 3. Investigate root cause
Use @investigator to analyze the root cause. Do NOT jump to a fix. Understand:
- What triggers the bug
- Why the current code fails
- What assumptions were violated

### 4. Implement minimal fix
Apply the **smallest possible change** to `{{affected_file}}` that resolves the issue. Avoid refactoring unrelated code.

### 5. Verify all tests pass
Run the full test suite:
```bash
npm test
```
Confirm the new test passes and no existing tests broke.

### 6. Check for regression
Review related functionality that shares code paths with `{{affected_file}}`. Verify no regressions were introduced.

### 7. Document the fix
Add an inline comment at the fix location explaining **why** the fix was needed and what it prevents. Format:
```
// Fix: <rationale> — resolves <bug_description summary>
```
