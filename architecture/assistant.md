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

