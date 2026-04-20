---
variables:
  - name: feature_name
    description: Name of the feature to design
  - name: user_story
    description: User story describing the feature need
---

# 🎨 Feature Design: {{feature_name}}

## User Story
{{user_story}}

## Design Process

### Step 1: Product Review — @product-reviewer
Invoke @product-reviewer to evaluate the user story:
- Is the user story clear and complete?
- Are acceptance criteria well-defined?
- Are there edge cases or ambiguities to resolve?
- Does this align with existing product patterns?

### Step 2: Technical Design — @architect
Invoke @architect to design the technical approach:
- Which files/modules need changes?
- What new components are required?
- API contract (endpoints, request/response shapes)
- Data model changes
- Dependencies and integration points

### Step 3: Implementation Plan
Break down into ordered tasks:

| # | Task | File(s) | Estimated Effort | Dependencies |
|---|------|---------|-----------------|--------------|
| 1 | | | | |

### Step 4: Complexity & Risk Assessment

**Complexity:** Low / Medium / High
**Risks:**
- Risk 1: _description_ — Mitigation: _approach_

## Output: Design Document

```markdown
# Design: {{feature_name}}

## Overview
_Summary of the feature and its purpose_

## User Story
{{user_story}}

## Technical Approach
_Architecture decisions and rationale_

## Implementation Plan
_Ordered task list with estimates_

## Risks & Mitigations
_Identified risks and how to address them_

## Open Questions
_Anything needing further discussion_
```
