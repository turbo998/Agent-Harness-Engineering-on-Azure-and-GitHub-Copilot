# Agent 安全与沙箱隔离

## 为什么 AI Agent 需要沙箱

AI Agent 与传统聊天机器人有本质区别——它们会**执行代码**、**访问文件系统**和**发起网络请求**。这带来了全新的攻击面：

```
Traditional Chatbot          AI Agent
┌─────────────┐             ┌─────────────────────┐
│ Input → LLM │             │ Input → LLM → Tools │
│      → Text │             │      → Code Exec    │
│   (no side  │             │      → File System   │
│    effects) │             │      → Network       │
└─────────────┘             │      → API Calls     │
                            └─────────────────────┘
    Safe by design           Dangerous by default
```

### 真实风险

| 风险 | 场景 | 影响 |
|------|------|------|
| **提示注入** | 用户诱骗 Agent 执行 `rm -rf /` | 数据丢失 |
| **容器逃逸** | 生成的代码利用内核漏洞 | 宿主机被入侵 |
| **密钥泄露** | Agent 读取环境变量并发送至外部 URL | 凭证被盗 |
| **资源耗尽** | Agent 产生无限循环，耗尽所有 CPU/内存 | 服务拒绝 |
| **横向移动** | Agent 访问同一网络上的其他服务 | 爆炸半径扩大 |

---

## 隔离级别——纵深防御

### 级别 1：进程隔离（基线）

```
┌────────────────────────────┐
│         Host OS            │
│  ┌──────┐  ┌──────┐       │
│  │Agent │  │Agent │  Shared│
│  │  A   │  │  B   │  kernel│
│  └──────┘  └──────┘       │
└────────────────────────────┘
```

- Linux namespaces + cgroups
- **优点**：开销最小，易于搭建
- **缺点**：共享内核——内核漏洞会影响所有 Agent
- **适用场景**：单租户、受信任的 Agent 代码、开发环境

### 级别 2：容器隔离（标准）

```
┌────────────────────────────┐
│         Host OS            │
│  ┌────────┐  ┌────────┐   │
│  │Container│  │Container│  │
│  │ Agent A │  │ Agent B │  │
│  │ Own FS  │  │ Own FS  │  │
│  └────────┘  └────────┘   │
│     Shared kernel          │
└────────────────────────────┘
```

- Docker / containerd 配合 seccomp + AppArmor 配置文件
- **优点**：安全性与性能的良好平衡
- **缺点**：仍与宿主机共享内核
- **适用场景**：标准生产工作负载、中等信任级别

### 级别 3：容器 + 网络隔离（Azure 推荐方案）

**Azure Container Apps** 开箱即用地提供此级别：

```
┌─────────────────────────────────────────┐
│  Azure Container Apps Environment       │
│  ┌────────────┐  ┌────────────┐        │
│  │ Agent A     │  │ Agent B     │       │
│  │ Team Alpha  │  │ Team Beta   │       │
│  └─────┬──────┘  └──────┬─────┘       │
│        │    ✗ blocked ✗  │             │
│        └────────┬────────┘             │
│                 │ VNet                  │
│        Only → LiteLLM Gateway          │
└─────────────────────────────────────────┘
```

功能特性：
- **工作负载配置文件** — 每个 Agent 的 CPU/内存上限
- **VNet 集成** — Agent 只能访问明确允许的端点
- **Managed Identity** — 无需在环境变量中存储 API 密钥
- **入口规则** — 控制谁可以访问 Agent 端点
- **自动 TLS** — 默认加密通信

### 级别 4：VM 级隔离（Kata Containers）

灵感来自 [AWS EKS Kata for Agents](https://github.com/aws-samples/sample-aws-eks-kata-for-agents) 项目：

```
┌─────────────────────────────────────────┐
│  Host (Azure VM / Bare Metal)           │
│  ┌──────────────┐  ┌──────────────┐    │
│  │  Kata VM      │  │  Kata VM      │   │
│  │  Own kernel   │  │  Own kernel   │   │
│  │  ┌────────┐  │  │  ┌────────┐  │   │
│  │  │Agent A │  │  │  │Agent B │  │   │
│  │  └────────┘  │  │  └────────┘  │   │
│  └──────────────┘  └──────────────┘    │
│  Cloud Hypervisor (CLH)                 │
│  ~200ms boot, ~10-20MB overhead         │
└─────────────────────────────────────────┘
```

功能特性：
- **每个 Agent 独立内核** — 内核漏洞被限制在单个 VM 内
- **硬件级强制隔离** — 使用 CPU 虚拟化扩展（VT-x）
- **快速启动** — Cloud Hypervisor 约 200ms 启动 VM
- **低开销** — 每个 VM 约 10-20MB 内存
- **兼容 Kubernetes** — 使用 RuntimeClass 混合运行普通 Pod 和 Kata Pod

**适用场景：**
- 不同组织共享基础设施的多租户平台
- 要求 VM 级别隔离的合规环境（金融服务、医疗健康）
- Agent 执行用户提供的任意代码时
- 具有正式威胁模型的高安全环境

### 级别 5：完全 VM 隔离（最高安全级别）

```
┌───────────────┐  ┌───────────────┐
│  Azure VM 1    │  │  Azure VM 2    │
│  Agent A       │  │  Agent B       │
│  Own OS        │  │  Own OS        │
│  Own network   │  │  Own network   │
└───────────────┘  └───────────────┘
```

- 每个 Agent 获得一个专用 Azure VM
- **优点**：最强隔离，完全的操作系统控制
- **缺点**：成本高、配置慢、难以扩展
- **适用场景**：最高安全要求，每个 Agent 处理机密数据

---

## 实践实施指南

### Azure 托管方案：Container Apps 安全检查清单

```yaml
# Container App security configuration
properties:
  configuration:
    # 1. Network isolation
    ingress:
      external: false        # Internal only
      targetPort: 3000
      transport: http2       # gRPC support
    
    # 2. No stored secrets
    secrets: []              # Use Managed Identity instead
    
  managedEnvironmentId: /subscriptions/.../managedEnvironments/isolated-env
  
  template:
    containers:
      - name: agent
        resources:
          cpu: 1.0           # 3. Resource limits
          memory: 2Gi
        
    # 4. Read-only file system where possible
    volumes:
      - name: config
        storageType: AzureFile
        mountOptions: ro     # Read-only mount
```

### VM 方案：Docker 安全检查清单

```yaml
# docker-compose.yml with security hardening
services:
  agent:
    image: agent:latest
    # 1. Resource limits
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    # 2. Security options
    security_opt:
      - no-new-privileges:true
      - seccomp:./seccomp-profile.json
    # 3. Read-only root filesystem
    read_only: true
    tmpfs:
      - /tmp:size=100M
    # 4. Drop all capabilities, add only needed ones
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    # 5. Network isolation
    networks:
      - agent-isolated
    # 6. No host access
    pid: "host"  # NEVER do this — example of what NOT to do

networks:
  agent-isolated:
    driver: bridge
    internal: true    # No internet access
```

### VM 方案：Kata Containers 快速入门（适用于 Kubernetes）

```yaml
# RuntimeClass for Kata
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: kata-clh
handler: kata-clh

---
# Agent Pod with Kata isolation
apiVersion: v1
kind: Pod
metadata:
  name: agent-sandbox
spec:
  runtimeClassName: kata-clh    # VM-level isolation
  containers:
    - name: agent
      image: agent:latest
      resources:
        limits:
          cpu: "2"
          memory: "4Gi"
  # Network isolation
  # (apply NetworkPolicy separately)
```

---

## 安全决策矩阵

| 您的情况 | 推荐级别 | Azure 路径 | VM 路径 |
|---------|---------|-----------|---------|
| 内部团队，受信任的 Agent | 级别 2（容器） | Container Apps | Docker |
| 多团队，共享基础设施 | 级别 3（容器 + 网络） | Container Apps + VNet | Docker + NetworkPolicy |
| 多组织 / SaaS 平台 | 级别 4（Kata VM） | AKS + Kata | K8s + Kata Containers |
| 合规 / 机密数据 | 级别 5（完全 VM） | 专用 Azure VM | 专用硬件 |
| 开发 / 工作坊 | 级别 1（进程） | 本地 Docker | 本地进程 |

---

## 工作坊集成

本文档支持：
- **实验 3**（多 Agent 协作）— 理解为什么权限边界对安全至关重要
- **实验 5**（端到端发布）— 理解 CI/CD 中的部署安全
- **企业部署指南** — 生产级隔离架构

> [!TIP]
> **工作坊讨论提示**："如果你的 Agent 可以运行 `curl` 且能访问包含 API 密钥的环境变量，是什么阻止它将这些密钥发送到外部服务器？每个隔离级别是如何解决这个问题的？"
