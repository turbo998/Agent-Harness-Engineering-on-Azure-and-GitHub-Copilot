# Agent Security & Sandbox Isolation

## Why AI Agents Need Sandboxing

AI agents are fundamentally different from traditional chatbots — they **execute code**, **access file systems**, and **make network requests**. This creates a new attack surface:

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

### Real-World Risks

| Risk | Scenario | Impact |
|------|----------|--------|
| **Prompt injection** | User tricks agent into running `rm -rf /` | Data loss |
| **Container escape** | Generated code exploits kernel vulnerability | Host compromise |
| **Secret exfiltration** | Agent reads env vars and sends them to external URL | Credential theft |
| **Resource exhaustion** | Agent spawns infinite loop consuming all CPU/memory | Service denial |
| **Lateral movement** | Agent accesses other services on the same network | Blast radius expansion |

---

## Isolation Levels — Defense in Depth

### Level 1: Process Isolation (Baseline)

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
- **Pros**: Minimal overhead, easy to set up
- **Cons**: Shared kernel — a kernel exploit compromises all agents
- **Use when**: Single-tenant, trusted agent code, development environments

### Level 2: Container Isolation (Standard)

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

- Docker / containerd with seccomp + AppArmor profiles
- **Pros**: Good balance of security and performance
- **Cons**: Still shares kernel with host
- **Use when**: Standard production workloads, moderate trust level

### Level 3: Container + Network Isolation (Recommended for Azure)

**Azure Container Apps** provides this out of the box:

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

Features:
- **Workload profiles** — CPU/memory caps per agent
- **VNet integration** — agents can only reach explicitly allowed endpoints
- **Managed Identity** — no API keys stored in environment variables
- **Ingress rules** — control who can reach agent endpoints
- **Automatic TLS** — encrypted communication by default

### Level 4: VM-Level Isolation (Kata Containers)

Inspired by the [AWS EKS Kata for Agents](https://github.com/aws-samples/sample-aws-eks-kata-for-agents) project:

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

Features:
- **Separate kernel per agent** — kernel exploits are contained
- **Hardware-enforced isolation** — uses CPU virtualization extensions (VT-x)
- **Fast boot** — Cloud Hypervisor starts VMs in ~200ms
- **Low overhead** — ~10-20MB memory per VM
- **Compatible with Kubernetes** — use RuntimeClass to mix regular and Kata pods

**When to use:**
- Multi-tenant platforms where different organizations share infrastructure
- Regulatory environments requiring VM-level separation (financial services, healthcare)
- When agents execute arbitrary user-provided code
- High-security environments with formal threat models

### Level 5: Full VM Isolation (Maximum Security)

```
┌───────────────┐  ┌───────────────┐
│  Azure VM 1    │  │  Azure VM 2    │
│  Agent A       │  │  Agent B       │
│  Own OS        │  │  Own OS        │
│  Own network   │  │  Own network   │
└───────────────┘  └───────────────┘
```

- Each agent gets a dedicated Azure VM
- **Pros**: Strongest isolation, full OS control
- **Cons**: Expensive, slow to provision, hard to scale
- **Use when**: Highest security requirements, each agent handles classified data

---

## Practical Implementation Guide

### Azure Managed: Container Apps Security Checklist

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

### VM: Docker Security Checklist

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

### VM: Kata Containers Quick Start (for Kubernetes)

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

## Security Decision Matrix

| Your Situation | Recommended Level | Azure Path | VM Path |
|---------------|-------------------|-----------|---------|
| Internal team, trusted agents | Level 2 (Container) | Container Apps | Docker |
| Multi-team, shared infra | Level 3 (Container + Network) | Container Apps + VNet | Docker + NetworkPolicy |
| Multi-org / SaaS platform | Level 4 (Kata VM) | AKS + Kata | K8s + Kata Containers |
| Regulatory / classified | Level 5 (Full VM) | Dedicated Azure VMs | Dedicated hardware |
| Development / workshop | Level 1 (Process) | Local Docker | Local process |

---

## Workshop Integration

This document supports:
- **Lab 3** (Multi-Agent Collaboration) — understanding why permission boundaries matter for security
- **Lab 5** (End-to-End Release) — understanding deployment security in CI/CD
- **Enterprise Deployment Guide** — production-grade isolation architecture

> [!TIP]
> **Workshop discussion prompt**: "If your agent can run `curl` and has access to environment variables containing API keys, what stops it from sending those keys to an external server? How does each isolation level address this?"
