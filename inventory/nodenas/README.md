# nodenas

- IP: 192.168.1.20
- OS: Debian 13
- Role: Storage / Nextcloud
- CPU: Intel Core i7-8700K - 6C/12T
- RAM: ~64 GB
- Network: Intel X540 dual-port 10 GbE
- Management/storage stack: OpenMediaVault
- Containers: Nextcloud, MariaDB, Redis, Beszel agent
- Storage:
  - RAID5: 3 x ~2 TB HDD, ~3.6 TB usable
  - RAID10: 4 x Crucial T500 1 TB NVMe, ~1.8 TB usable
  - RAID0: 2 x Crucial ~500 GB NVMe, ~931 GB usable
- Provides storage used by other cluster nodes.
