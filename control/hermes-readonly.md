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

Resources and prompts are disabled.

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
