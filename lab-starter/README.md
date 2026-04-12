# GHCP Workshop Lab Starter

This starter project is used by the 120-minute GitHub Copilot workshop.

## Scenario

The team maintains a small **customer support ticket service**. The API already supports:

- viewing tickets
- creating tickets
- updating ticket status

The workshop uses GitHub Copilot to:

1. understand the codebase
2. plan a change
3. implement features with Agent mode
4. add tests and verify behavior

## Workshop tasks

1. Add `priority` filtering support.
2. Add request validation for `POST /tickets`.
3. Optionally extend the API with a summary endpoint in the live demo.

## Run locally

```powershell
npm install
npm test
npm start
```

Server default URL: `http://localhost:3000`
