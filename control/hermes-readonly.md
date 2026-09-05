# Hermes Cluster Control Boundary

## Purpose

Hermes is an interchangeable natural-language agent in front of the
Cluster Control Layer.

The infrastructure boundary is:

    Hermes
      |
      v
    MCP tools
      |
      v
    Cluster Control Layer
      |
      v
    Ansible / execution layer

Hermes does not receive direct SSH, shell, filesystem, Ansible,
deployment, restart, or service-management authority.

## Current phase

Current supported modes:

- READ
- PLACE
- PLAN

Not implemented:

- APPROVE
- EXECUTE

A PLAN is descriptive only. A plan_id is not execution authorization.

## Allowed MCP server

Server:

    cluster-readonly

Allowed tools:

- cluster_list_nodes
- cluster_get_node
- cluster_find_capability
- cluster_get_runtime_state
- cluster_place_workload
- cluster_plan_workload

No cluster-specific MCP resources or prompts are exposed. Hermes may register generic MCP protocol adapters for `list_resources`, `read_resource`, `list_prompts`, and `get_prompt`; these adapters do not grant cluster mutation or execution authority.

## Hermes CLI tool boundary

For the cluster-agent CLI profile, mutating or escape-capable built-in
toolsets must remain disabled, including:

- terminal
- file
- code_execution
- computer_use
- delegation
- cronjob
- web
- browser

The exact Hermes configuration is intentionally stored outside this
repository because it may contain account-specific configuration.

No credentials, tokens, private keys, authentication files, or secrets
belong in this repository.

## PLAN contract

cluster_plan_workload produces:

- plan_id
- mode
- verdict
- intent
- required capabilities
- selected node
- deterministic placement evidence
- validations
- descriptive steps
- execution boundary

The execution object must state:

    performed: false
    allowed: false

The returned plan must never be interpreted as permission to execute.

## Plan identity

plan_id is derived from stable planning inputs.

Runtime age is deliberately excluded because it changes continuously.

The runtime snapshot generated_at value is included so that a new
observation can produce a distinct plan identity.

Therefore:

- same intent + same relevant state => same plan_id
- changed intent => different plan_id
- changed runtime snapshot => different plan_id
- elapsed age alone => same plan_id

## Placement explanation contract

Only:

    placement.decision.decision_reasons

may be presented as causal reasons for node selection.

Factors marked:

- not_needed
- tie
- unavailable
- unsupported

must not be represented as causes of the selection.

Other runtime facts may be displayed as context, but not falsely
described as decisive placement reasons.

## Security scope

This boundary has been validated for the current Hermes CLI
configuration by positive read/plan tests and negative execution tests.

It is an application/tool boundary, not an operating-system sandbox.

A future stronger isolation layer may run the agent under a dedicated
Unix account or container with independent filesystem and network
restrictions.

## V1.2 facts and provenance contract

Hermes should prefer `cluster_get_facts` when making factual claims
about hardware, declared capabilities, and runtime observations.

Facts have explicit provenance:

- `inventory`: declared inventory value;
- `runtime`: observed value from a runtime snapshot;
- `derived`: deterministic value calculated by the Cluster Control Layer.

The LLM must not recalculate inventory fields such as
`physical_cores` or `logical_threads`.

`desired_roles` expresses declared intent. It is not proof that the
corresponding service is currently running.

For GPU memory, raw `total`, `used`, and `free` observations are kept
independently. Percentages and accounting gaps are calculated by the
control layer. The LLM must not infer one raw metric from another.

Facts provide context only. They are not causal placement evidence.
Only `placement.decision.decision_reasons` may be described as reasons
why a workload was selected for a node.

PLACE/PLAN failures returned by the MCP facade are structured. The
LLM may state only the cause information explicitly present in the
returned error and must not invent an additional cause.

The execution boundary remains unchanged: READ, PLACE, PLAN only.
No execution authority exists.

### Node-scoped factual binding

For factual claims about one specific node, Hermes should prefer
`cluster_get_node_facts(name)` over the cluster-wide facts view.

The node-scoped response binds every returned fact to exactly one
node identity. This prevents facts from adjacent nodes from being
associated with the wrong node by the LLM.

`cluster_get_facts` remains available for cluster-wide context.

### V1.2 business MCP tool set

The Cluster Control Layer exposes eight business tools:

- `cluster_list_nodes`
- `cluster_get_node`
- `cluster_find_capability`
- `cluster_get_runtime_state`
- `cluster_get_facts`
- `cluster_get_node_facts`
- `cluster_place_workload`
- `cluster_plan_workload`

Hermes may additionally display generic protocol adapter tools.
Those adapters are not additional cluster-control capabilities.
