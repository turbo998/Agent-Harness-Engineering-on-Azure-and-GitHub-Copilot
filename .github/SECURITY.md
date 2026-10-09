# Security and privacy

Do not include credentials, personal contact details, customer data, cloud account
identifiers, or private conversations in commits, issues, pull requests, logs,
screenshots, or attachments. Use synthetic examples and environment variables;
commit only empty or clearly synthetic configuration templates.

## Reporting

Use GitHub private vulnerability reporting when it is available in the Security
tab. Otherwise, contact the repository owner through an established private
channel. Public issues may describe the affected component without sensitive
values or exploit details; do not post the evidence publicly.

## If information was committed

Revoke or rotate credentials at the issuing service first. Removing a value in a
new commit does not remove it from Git history, tags, pull-request refs, forks,
caches, releases, or previously downloaded copies. Coordinate any history rewrite
with collaborators and follow GitHub's sensitive-data removal guidance.

Check the default branch, other branches and tags, generated artifacts, logs,
attachments, and deployment configuration. Preserve attribution and licenses.
Keep secret scanning and push protection enabled where the account supports them.
