# nodegpu1

- IP: 192.168.1.22
- OS: Ubuntu 26.04 LTS
- Hardware: Dell PowerEdge R430
- Role: Linux GPU compute / Immich
- CPU: 2 x Intel Xeon E5-2680 v4 - 28C/56T total
- RAM: ~128 GB
- GPU: NVIDIA T1000 8 GB
- Network: Intel X550 dual-port 10 GbE
- Services:
  - Docker
  - Immich
  - Immich machine learning CUDA
  - PostgreSQL
  - Redis/Valkey
  - Beszel NVIDIA agent
- Receives NAS storage over NFS for Google Drive migration data.
