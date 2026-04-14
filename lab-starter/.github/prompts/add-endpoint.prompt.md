---
name: add-endpoint
description: Template for adding a new API endpoint
mode: agent
---

Add a new API endpoint to this Express.js project.

## Endpoint: {{ endpoint_path }}
## Method: {{ http_method }}
## Description: {{ description }}

## Implementation steps:
1. Add business logic in `src/ticketStore.js`
2. Add route in `src/app.js`
3. Add tests in `tests/ticketStore.test.js`
4. Run `npm test` to verify

## Constraints:
- Follow existing code patterns
- Return proper HTTP status codes
- Include input validation where needed
- All tests must pass before declaring done
