# 附录：企业部署指南 — 从工作坊到生产环境

本附录为将本工作坊中的 Harness Engineering 模式投入生产的团队提供指导。涵盖两种部署路径：**Azure 托管服务**和 **VM 自托管**。

---

## 1. 模型网关 — 统一访问与预算控制

### 问题

当多个团队共享 AI 智能体时：
- Token 成本难以按团队归属
- 无速率限制 → 一个失控的智能体可能耗尽配额
- 无法了解哪个智能体/团队消耗了什么

### 解决方案：LiteLLM 作为模型网关

LiteLLM 在 LLM 提供商前面提供统一的代理层，具备以下功能：
- **按租户 API 密钥** — 每个团队获得自己的密钥并设有预算上限
- **速率限制** — 防止任何单个智能体垄断资源
- **成本跟踪** — 自动 Token 计数和成本归属
- **提供商抽象** — 在 Azure OpenAI、GitHub Models、Anthropic 之间切换无需修改代码

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

### Azure 托管路径

| 组件 | Azure 服务 | 原因 |
|-----------|--------------|-----|
| LiteLLM Gateway | **Azure Container Apps** | 自动扩缩，零基础设施管理 |
| LiteLLM Database | **Azure Database for PostgreSQL (Flexible)** | 托管、自动备份、高可用 |
| LLM 后端 | **Azure OpenAI Service** | 企业级 SLA、数据隐私、区域合规 |
| 密钥管理 | **Azure Key Vault** | 集中式 API 密钥存储 |
| 监控 | **Azure Monitor + Application Insights** | 成本仪表盘、使用量告警 |

**配置示例：**
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

### VM 自托管路径

```bash
# 使用 Docker 在 VM 上部署 LiteLLM
docker run -d \
  --name litellm \
  -p 4000:4000 \
  -v ./config.yaml:/app/config.yaml \
  -e DATABASE_URL=postgresql://... \
  ghcr.io/berriai/litellm:main-latest \
  --config /app/config.yaml

# 创建按团队的 API 密钥
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer *** \
  -d '{"team_id": "team-a", "max_budget": 50, "budget_duration": "30d"}'
```

---

## 2. 智能体沙箱隔离

### 为什么隔离很重要

AI 智能体会执行代码。没有隔离的话：
- 有缺陷的智能体可能删除生产文件
- 被攻击的提示词可能窃取密钥
- 容器逃逸会暴露宿主系统

### Azure 托管：带网络隔离的 Container Apps

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

**关键特性：**
- **Workload profiles** — 每个智能体的 CPU/内存资源限制
- **VNet 集成** — 除非明确允许，智能体无法访问其他内部服务
- **Managed Identity** — 智能体通过 Azure AD 认证，环境中无需存储 API 密钥
- **基于修订版本的部署** — 每个智能体版本都是不可变的

### VM：使用 Kata Containers 实现 VM 级别隔离

受 AWS EKS Kata for Agents 项目启发，每个智能体运行在轻量级 VM 内：

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

**何时使用 Kata Containers：**
- 多租户环境中，来自不同团队的智能体共享同一宿主机
- 法规要求 VM 级别的隔离
- 当智能体执行不受信任的/生成的代码并具有文件系统和网络访问权限时

### 隔离方案对比

| 隔离级别 | 技术 | 安全性 | 开销 | 复杂度 |
|----------------|-----------|----------|----------|------------|
| 进程 | Linux namespaces | 低 | 极小 | 低 |
| 容器 | Docker/containerd | 中 | 低 | 低 |
| 容器 + NetworkPolicy | Azure Container Apps | 高 | 低 | 中 |
| 轻量级 VM | Kata Containers (CLH) | 非常高 | ~20MB/pod | 高 |
| 完整 VM | 每个智能体一个 Azure VM | 最高 | 完整 VM | 非常高 |

---

## 3. 可观测性与成本管理

### Azure 托管：内置监控栈

```
Azure Monitor
├── Application Insights → Agent request tracing
├── Log Analytics → Centralized agent logs
├── Cost Management → Per-team token spending
└── Alerts → Budget threshold notifications
```

**需要跟踪的关键指标：**

| 指标 | 来源 | 告警阈值 |
|--------|--------|----------------|
| 每个团队的 Token 使用量 | LiteLLM + Azure Monitor | >月度预算的 80% |
| 智能体错误率 | Application Insights | >请求量的 5% |
| P95 响应延迟 | Application Insights | >10s |
| 容器重启次数 | Container Apps metrics | >5 分钟内 3 次 |

### VM：Prometheus + Grafana 栈

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
      - GF_SECURITY_ADMIN_PASSWORD=***
```

LiteLLM 在 `/metrics` 端点暴露 Prometheus 指标，包括：
- `litellm_requests_total` — 每个团队的 API 调用总数
- `litellm_spend_total` — 每个密钥的累计成本
- `litellm_request_duration_seconds` — 延迟直方图

---

## 4. 多租户架构

### 团队配置工作流

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

### Azure：Terraform 示例

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

### VM：Docker Compose 示例

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
      - LITELLM_API_KEY=***
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
      - LITELLM_API_KEY=***
      - LITELLM_BASE_URL=http://litellm:4000
    networks:
      - agent-net
```

---

## 5. 决策矩阵：Azure 托管 vs VM

| 需求 | Azure Container Apps | VM 自托管 |
|-------------|---------------------|----------------|
| **部署时间** | 约 30 分钟 | 约 2 小时 |
| **扩缩** | 自动（0→N pods） | 手动（PM2 cluster / k8s） |
| **低规模成本** | 按使用付费（可低至 $0） | 固定 VM 成本 |
| **高规模成本** | 每请求成本较高 | 较低（摊销后） |
| **安全隔离** | 容器 + VNet | 容器 / Kata VM |
| **数据驻留** | Azure 区域 | 完全控制 |
| **合规性** | 通过 Azure 获得 SOC2、ISO 27001、HIPAA | 需自行负责 |
| **GPU 支持** | 有限（预览中） | 完整支持（NVIDIA 直通） |
| **自定义程度** | 受平台限制 | 完整 OS 访问 |
| **运维负担** | 低（托管） | 高（补丁、监控） |

### 推荐起步方案

- **初创公司 / POC**：Azure Container Apps + Azure OpenAI → 最快实现价值
- **有合规要求的企业**：Azure Container Apps + VNet + Key Vault + Managed Identity
- **多云 / 本地部署**：VM + Docker Compose + LiteLLM + Kata（如果是多租户）
- **GPU 密集型工作负载**：Azure VM（NC 系列）或本地裸金属服务器

---

## 6. 渐进式采用路线图

| 周 | 行动 | 成果 |
|------|--------|---------| 
| 1 | 在 Container Apps 上部署 LiteLLM 网关 + 1 个智能体 | 集中式模型访问 |
| 2 | 在 2-3 个仓库中添加 SOUL.md + copilot-instructions.md | 一致的智能体行为 |
| 3 | 按团队分配 API 密钥 + 预算告警 | 成本可见性 |
| 4 | 添加 Prometheus/Azure Monitor 仪表盘 | 可观测性 |
| 5 | 网络隔离（VNet 或 NetworkPolicy） | 安全加固 |
| 6 | 第二个智能体运行时或用于多租户的 Kata | 生产级隔离 |
