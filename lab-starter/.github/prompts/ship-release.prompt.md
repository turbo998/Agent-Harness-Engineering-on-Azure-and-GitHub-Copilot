---
variables:
  - name: version_type
    description: "Release type: patch, minor, or major"
  - name: release_notes
    description: Human-readable release notes for this version
---

# 🚀 Ship Release Workflow

**Version bump:** {{version_type}}
**Release notes:** {{release_notes}}

## Pre-flight Checks

### Step 1: Run tests
```bash
npm test
```
All tests must pass. Stop if any fail.

### Step 2: Coverage check
```bash
npm run test:coverage
```
Verify coverage meets threshold (≥80%). Stop if below.

### Step 3: Code review
Invoke @code-reviewer on all changed files since last release. Flag any unresolved issues.

### Step 4: Security review
Invoke @security-reviewer on all changed files. Run `npm audit`. No critical or high vulnerabilities allowed.

## Release Execution

### Step 5: Version bump
```bash
npm version {{version_type}} --no-git-tag-version
```
Record the new version number.

### Step 6: Update CHANGELOG
Prepend to `CHANGELOG.md`:
```markdown
## [NEW_VERSION] - YYYY-MM-DD

{{release_notes}}
```

### Step 7: Commit changes
```bash
git add -A
git commit -m "chore: release vNEW_VERSION"
```

### Step 8: Create release branch
```bash
git checkout -b release/vNEW_VERSION
git push origin release/vNEW_VERSION
```

### Step 9: Create PR
Create a pull request with:
- **Title:** `Release vNEW_VERSION`
- **Body:**
  ```
  ## Release vNEW_VERSION ({{version_type}})

  ### Changes
  {{release_notes}}

  ### Checklist
  - [x] Tests passing
  - [x] Coverage ≥80%
  - [x] Code review complete
  - [x] Security review clear
  - [x] CHANGELOG updated
  - [x] Version bumped
  ```

### Step 10: Final verification
After PR merge, verify the release tag and any CI/CD pipelines complete successfully.
