# GHCP Workshop 120min

Customer-facing GitHub Copilot workshop package for a 120-minute technical session.

## Contents

| Path | Description |
| --- | --- |
| `GHCP_Workshop_120min_Agent版.pptx` | Main workshop deck |
| `GHCP_Workshop_120min_讲师Demo脚本.md` | Instructor demo script |
| `GHCP_Workshop_120min_实验操作手册.md` | Step-by-step lab manual for attendees |
| `generate_ghcp_workshop_120min_agents_ppt.js` | Script used to generate the PPTX deck |
| `lab-starter/` | Starter Node.js project used in the demo and hands-on lab |

## Workshop scope

- GHCP operation overview
- IDE workflow and usage patterns
- Agent mode: Ask / Plan / Agent
- Best practices and governance boundaries
- Live demo
- Hands-on lab

## Lab starter

The lab starter is a small ticket service for demonstrating:

1. code understanding with Ask
2. structured planning with Plan
3. scoped implementation with Agent
4. validation through tests and API checks

## Run the lab starter

```powershell
Set-Location .\lab-starter
npm install
npm test
npm start
```
