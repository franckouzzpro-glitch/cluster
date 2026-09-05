# Cluster Assistant Architecture

## 1. Objective

The cluster assistant provides a conversational interface capable of
understanding a user's intent, inspecting the cluster, proposing a plan,
and requesting controlled actions.

The AI agent is NOT the cluster control plane.

The architecture must allow the AI agent, model provider, and user
interface to be replaced without redesigning the cluster.

---

## 2. Architecture

```text
                    USER
                     |
          Telegram / Discord / CLI
                     |
                     v
              +-------------+
              |  AI AGENT   |
              |             |
              | reasoning   |
              | conversation|
              | memory      |
              | planning    |
              +------+------+
                     |
              controlled API
              / MCP tools
                     |
                     v
          +---------------------+
          | CLUSTER CONTROL     |
          | LAYER               |
          |                     |
          | inventory           |
          | policies            |
          | validation          |
          | authorization       |
          | audit logging       |
          +----------+----------+
                     |
              approved actions
                     |
                     v
              +-------------+
              |   ANSIBLE   |
              +------+------+
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
    nodenas       nodegpu1      nodegpu2
   storage          GPU           GPU
     .20             .22          .161

              nodecpu (.21)
              control plane


---

## 3. Source of truth

The Git repository on `nodecpu` is the source of truth for cluster
configuration and architecture.

Primary repository:

    /home/franck/cluster

Important sources include:

    inventory/capabilities.yml
    ansible/inventory.yml
    ansible/*.yml
    architecture/*.md

Git records intended configuration.

Ansible and audit tools observe the real state of the infrastructure.

The orchestrator must distinguish between:

- desired state
- observed state
- proposed changes

---

## 4. AI Agent

The AI agent is responsible for:

- conversation
- understanding intent
- reasoning
- planning
- selecting appropriate tools
- explaining proposed actions
- interpreting tool results

The AI agent must NOT receive unrestricted root or administrator access
to the cluster.

Initial candidate:

    Hermes Agent

Other agents may be connected later, including Claude Code or local
agents.

The architecture must not depend on Hermes specifically.

---

## 5. Cluster Control Layer

The Cluster Control Layer is the stable boundary between AI agents and
the infrastructure.

It is responsible for:

- reading cluster capabilities
- exposing approved operations
- validating requests
- applying placement rules
- enforcing permissions
- recording actions
- rejecting unsafe or unsupported operations

Possible future interface:

    MCP

Example operations:

    cluster.list_nodes
    cluster.get_capabilities
    cluster.get_health
    cluster.list_services
    cluster.plan_deployment
    cluster.run_audit
    cluster.deploy_service
    cluster.restart_service

The exposed interface should describe WHAT may be requested rather than
giving the agent unrestricted shell access.

---

## 6. Execution Layer

Ansible is the primary execution engine.

    AI Agent
        |
        v
    Control Layer
        |
        v
    Ansible
        |
        +-- nodenas
        +-- nodecpu
        +-- nodegpu1
        +-- nodegpu2

Other execution mechanisms may later be added when appropriate:

- Docker APIs
- service APIs
- PowerShell
- monitoring APIs

Direct SSH from the AI agent should not be the normal execution path.

---

## 7. Placement

Workloads should be selected according to declared capabilities and
observed state rather than hard-coded assumptions.

Examples:

    storage workload
        -> storage_provider

    CUDA workload
        -> cuda_worker

    heavy GPU workload
        -> heavy_gpu_worker

    cluster management
        -> control_plane

The initial capability database is:

    inventory/capabilities.yml

Future versions may combine static declarations with automatically
collected facts.

---

## 8. Safety Model

Default principle:

    READ > PLAN > VALIDATE > EXECUTE > VERIFY > LOG

Read-only operations should be easier to authorize than modifications.

Destructive or high-impact operations must require stronger validation.

Examples include:

- deleting data
- changing storage arrays
- modifying network configuration
- changing firewall rules
- removing services
- altering authentication
- rebooting infrastructure
- changing privileged access

The agent must never be given a general-purpose unrestricted root shell
as its normal operating model.

---

## 9. Agent Independence

Agents are replaceable components.

    Hermes --------+
    Claude Code ---+
    Local Agent ---+--> Cluster Control Layer --> Ansible --> Cluster
    Future Agent --+

Changing the agent must not require changing the underlying cluster
automation.

Claude Code may later be used as a specialized engineering agent for
repository work, playbook development, testing, review, and other
software-engineering tasks.

---

## 10. Specialized Modules

Domain-specific assistants should be implemented above the common
assistant platform.

Examples:

- cluster administration
- monitoring
- documentation
- research
- personal information assistant
- media management

These modules may use different tools and data sources while sharing
the same core agent architecture.

---

## 11. Initial Implementation Strategy

Phase 1:

    Git
     + capabilities inventory
     + Ansible
     + audits

Phase 2:

    Cluster Control Layer
     + read-only tools
     + capability queries
     + health queries

Phase 3:

    Hermes Agent
     + controlled access to the Control Layer

Phase 4:

    controlled write operations
     + policies
     + approval
     + verification
     + audit logging

Phase 5:

    additional agents
     + specialized modules
     + optional local models

---

## 12. Core Principle

The intelligence may change.

The infrastructure contract must remain stable.

    AI proposes.
    Control Layer decides what is permitted.
    Ansible executes.
    The cluster reports the result.
    Git preserves the intended state.
