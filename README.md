# Home Cluster

Source of truth for the home cluster infrastructure.

## Nodes

| Node | IP | Primary role |
|---|---|---|
| nodenas | 192.168.1.20 | Storage / Nextcloud |
| nodecpu | 192.168.1.21 | Control plane / CPU compute |
| nodegpu1 | 192.168.1.22 | Linux GPU worker / Immich |
| nodegpu2 | 192.168.1.161 | RTX 5070 GPU worker / Workstation |

## Architecture

- `nodecpu` is the primary management/control-plane node.
- `nodenas` provides centralized storage and Nextcloud.
- `nodegpu1` provides stable Linux/CUDA GPU compute and hosts Immich.
- `nodegpu2` provides high-performance GPU compute using an RTX 5070.
- Primary cluster networking uses 10 GbE on the 192.168.1.0/24 LAN.

## Repository

- `inventory/` - node inventory and hardware/software facts
- `architecture/` - architecture documentation
- `ansible/` - future Ansible inventory and playbooks
- `scripts/` - cluster administration scripts
- `services/` - service definitions and deployment configuration
- `agents/` - future cluster agent configuration
- `docs/` - operational documentation

## Security

Secrets, passwords, API tokens, SSH private keys and other credentials must never be committed to this repository.
