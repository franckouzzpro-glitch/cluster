# nodecpu

- IP: 192.168.1.21
- OS: Ubuntu 26.04 LTS
- Hardware: Dell PowerEdge R430
- Role: Control plane / CPU compute
- CPU: 2 x Intel Xeon E5-2630 v3 - 16C/32T total
- RAM: ~128 GB
- Network: Intel X540 dual-port 10 GbE
- NVMe: Seagate FireCuda 520 1 TB mounted at /srv/nvme
- Services include:
  - Docker
  - Beszel hub
  - Open WebUI
  - Homarr
  - Homepage
  - Cluster Control Center
  - Pterodactyl
- Primary Git/source-of-truth repository lives at ~/cluster.
