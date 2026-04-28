# Appendix: Enterprise Deployment Guide — From Workshop to Production

This appendix provides guidance for teams taking the Harness Engineering patterns from this workshop into production. Two deployment paths are covered: **Azure managed services** and **VM self-hosted**.

---

## 1. Model Gateway — Unified Access & Budget Control

### The Problem

When multiple teams share AI agents:
- Token costs are hard to attribute per team
- No rate limiting → one runaway agent can exhaust quotas
- No visibility into which agent/team consumes what

### Solution: LiteLLM as a Model Gateway

LiteLLM provides a unified proxy layer in front of LLM providers with:
- **Per-tenant API keys** — each team gets its own key with budget caps
- **Rate limiting** — prevent any single agent from monopolizing resources
- **Cost tracking** — automatic token counting and cost attribution
- **Provider abstraction** — switch between Azure OpenAI, GitHub Models, Anthropic without code changes

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Agent Pod   │ ──→ │   LiteLLM    │ ──→ │  Azure OpenAI    │
│  (Team A)    │     │   Gateway    │     │  GitHub Models   │
├─────────────┤     │              │     │  Anthropic       │
│  Agent Pod   │ ──→ │  • Auth      │     └──────────────────┘
│  (Team B)    │     │  • Rate limit│
├─────────────┤     │  • Budget    │
│  Agent Pod   │ ──→ │  • Logging   │
│  (Team C)    │     └──────────────┘
└─────────────┘
```

### Azure Managed Path

| Component | Azure Service | Why |
|-----------|--------------|-----|
| LiteLLM Gateway | **Azure Container Apps** | Auto-scaling, zero infra management |
| LiteLLM Database | **Azure Database for PostgreSQL (Flexible)** | Managed, auto-backup, HA |
| LLM Backend | **Azure OpenAI Service** | Enterprise SLA, data privacy, regional compliance |
| Secret Management | **Azure Key Vault** | Centralized API key storage |
| Monitoring | **Azure Monitor + Application Insights** | Cost dashboards, usage alerts |

**Configuration example:**
```yaml
# LiteLLM config.yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: azure/gpt-4o
      api_base: https://your-resource.openai.azure.com/
      api_key: os.environ/AZURE_OPENAI_KEY
      
  - model_name: claude-sonnet
    litellm_params:
      model: azure/claude-sonnet  # via GitHub Models
      api_base: https://models.inference.ai.azure.com
      api_key: os.environ/GITHUB_TOKEN

general_settings:
  max_budget: 100.0          # $100/month org-wide
  budget_duration: 30d
```

### VM Self-Hosted Path

```bash
# Deploy LiteLLM on VM with Docker
docker run -d \
  --name litellm \
  -p 4000:4000 \
  -v ./config.yaml:/app/config.yaml \
  -e DATABASE_URL=postgresql://... \
  ghcr.io/berriai/litellm:main-latest \
  --config /app/config.yaml

# Create per-team API keys
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer sk-master-key" \
  -d '{"team_id": "team-a", "max_budget": 50, "budget_duration": "30d"}'
```

---

## 2. Agent Sandbox Isolation

### Why Isolation Matters

AI agents execute code. Without isolation:
- A buggy agent can delete production files
- A compromised prompt can exfiltrate secrets
- Container escapes expose the host system

### Azure Managed: Container Apps with Network Isolation

```
┌─────────────────────────────────────────┐
│  Azure Container Apps Environment       │
│  ┌──────────┐  ┌──────────┐            │
│  │ Agent A   │  │ Agent B   │           │
│  │ (Team 1)  │  │ (Team 2)  │           │
│  └──────────┘  └──────────┘            │
│  • Workload profiles (CPU/memory limits)│
│  • VNet integration (network isolation) │
│  • Managed Identity (no stored secrets) │
│  • Dapr for service-to-service comms    │
└─────────────────────────────────────────┘
```

**Key features:**
- **Workload profiles** — CPU/memory resource limits per agent
- **VNet integration** — agents cannot reach other internal services unless explicitly allowed
- **Managed Identity** — agents authenticate via Azure AD, no API keys in environment
- **Revision-based deployment** — each agent version is immutable

### VM: Kata Containers for VM-Level Isolation

Inspired by the AWS EKS Kata for Agents project, each agent runs inside a lightweight VM:

```
┌─────────────────────────────────────────┐
│  Host VM (Azure VM, bare metal)         │
│  ┌────────────────┐  ┌────────────────┐ │
│  │  Kata VM        │  │  Kata VM        │ │
│  │  ┌────────────┐│  │  ┌────────────┐│ │
│  │  │ Agent A    ││  │  │ Agent B    ││ │
│  │  │ Container  ││  │  │ Container  ││ │
│  │  └────────────┘│  │  └────────────┘│ │
│  │  Own kernel     │  │  Own kernel     │ │
│  └────────────────┘  └────────────────┘ │
│  • ~200ms boot time (Cloud Hypervisor)  │
│  • ~10-20MB overhead per VM             │
│  • Complete kernel isolation            │
└─────────────────────────────────────────┘
```

**When to use Kata Containers:**
- Multi-tenant environments where agents from different teams share the same host
- Regulatory requirements mandating VM-level separation
- When agents execute untrusted/generated code with file system and network access

### Isolation Comparison

| Isolation Level | Technology | Security | Overhead | Complexity |
|----------------|-----------|----------|----------|------------|
| Process | Linux namespaces | Low | Minimal | Low |
| Container | Docker/containerd | Medium | Low | Low |
| Container + NetworkPolicy | Azure Container Apps | High | Low | Medium |
| Lightweight VM | Kata Containers (CLH) | Very High | ~20MB/pod | High |
| Full VM | Azure VM per agent | Highest | Full VM | Very High |

---

## 3. Observability & Cost Management

### Azure Managed: Built-in Monitoring Stack

```
Azure Monitor
├── Application Insights → Agent request tracing
├── Log Analytics → Centralized agent logs
├── Cost Management → Per-team token spending
└── Alerts → Budget threshold notifications
```

**Key metrics to track:**

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Token usage per team | LiteLLM + Azure Monitor | >80% of monthly budget |
| Agent error rate | Application Insights | >5% of requests |
| Response latency P95 | Application Insights | >10s |
| Container restarts | Container Apps metrics | >3 in 5 minutes |

### VM: Prometheus + Grafana Stack

```yaml
# docker-compose.yml for monitoring
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

LiteLLM exposes Prometheus metrics at `/metrics`, including:
- `litellm_requests_total` — total API calls per team
- `litellm_spend_total` — cumulative cost per key
- `litellm_request_duration_seconds` — latency histogram

---

## 4. Multi-Tenant Architecture

### Team Provisioning Workflow

```
New Team Request
      │
      ▼
┌─────────────────┐
│ Create LiteLLM   │
│ Virtual Key       │ → Budget cap, rate limit, allowed models
├─────────────────┤
│ Create Agent      │
│ Namespace/App     │ → Isolated compute, mounted SOUL.md
├─────────────────┤
│ Configure         │
│ Messaging         │ → Slack/Teams/Feishu channel binding
├─────────────────┤
│ Setup Monitoring  │ → Dashboards, alerts, cost attribution
└─────────────────┘
```

### Azure: Terraform Example

```hcl
# Per-team agent deployment
resource "azurerm_container_app" "agent" {
  for_each            = var.teams
  name                = "agent-${each.key}"
  resource_group_name = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id

  template {
    container {
      name   = "agent"
      image  = var.agent_image
      cpu    = each.value.cpu
      memory = each.value.memory

      env {
        name        = "LITELLM_API_KEY"
        secret_name = "litellm-key-${each.key}"
      }
      env {
        name  = "SOUL_FILE"
        value = "/config/SOUL.md"
      }
    }
    volume {
      name         = "config"
      storage_type = "AzureFile"
      storage_name = azurerm_storage_share.agent_config[each.key].name
    }
  }
}
```

### VM: Docker Compose Example

```yaml
# Per-team agent with resource limits
services:
  agent-team-a:
    image: agent:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    volumes:
      - ./teams/team-a/SOUL.md:/app/SOUL.md
      - ./teams/team-a/config.yaml:/app/config.yaml
    environment:
      - LITELLM_API_KEY=${TEAM_A_KEY}
      - LITELLM_BASE_URL=http://litellm:4000
    networks:
      - agent-net

  agent-team-b:
    image: agent:latest
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
    volumes:
      - ./teams/team-b/SOUL.md:/app/SOUL.md
    environment:
      - LITELLM_API_KEY=${TEAM_B_KEY}
      - LITELLM_BASE_URL=http://litellm:4000
    networks:
      - agent-net
```

---

## 5. Decision Matrix: Azure Managed vs VM

| Requirement | Azure Container Apps | VM Self-Hosted |
|-------------|---------------------|----------------|
| **Time to deploy** | ~30 min | ~2 hours |
| **Scaling** | Auto (0→N pods) | Manual (PM2 cluster / k8s) |
| **Cost at low scale** | Pay-per-use (can be $0) | Fixed VM cost |
| **Cost at high scale** | Higher per-request | Lower (amortized) |
| **Security isolation** | Container + VNet | Container / Kata VM |
| **Data residency** | Azure regions | Full control |
| **Compliance** | SOC2, ISO 27001, HIPAA via Azure | Your responsibility |
| **GPU support** | Limited (preview) | Full (NVIDIA passthrough) |
| **Customization** | Constrained by platform | Full OS access |
| **Operational burden** | Low (managed) | High (patches, monitoring) |

### Recommended Starting Points

- **Startup / POC**: Azure Container Apps + Azure OpenAI → fastest time to value
- **Enterprise with compliance**: Azure Container Apps + VNet + Key Vault + Managed Identity
- **Multi-cloud / on-prem**: VM + Docker Compose + LiteLLM + Kata (if multi-tenant)
- **GPU-heavy workloads**: Azure VM (NC-series) or on-prem bare metal

---

## 6. Progressive Adoption Roadmap

| Week | Action | Outcome |
|------|--------|---------|
| 1 | Deploy LiteLLM gateway + 1 agent on Container Apps | Centralized model access |
| 2 | Add SOUL.md + copilot-instructions.md to 2–3 repos | Consistent agent behavior |
| 3 | Per-team API keys + budget alerts | Cost visibility |
| 4 | Add Prometheus/Azure Monitor dashboards | Observability |
| 5 | Network isolation (VNet or NetworkPolicy) | Security hardening |
| 6 | Second agent runtime or Kata for multi-tenant | Production-grade isolation |
