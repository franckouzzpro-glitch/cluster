# Cluster Architecture

                     nodegpu2
                  192.168.1.161
                     RTX 5070
                  Heavy GPU worker
                        |
                     10 GbE
                        |
nodenas ---------------- nodecpu ---------------- nodegpu1
192.168.1.20             192.168.1.21             192.168.1.22
Storage                   Control Plane             GPU Worker
Nextcloud                 Orchestrator              T1000 8 GB
NFS / SMB                 Git / Management          Immich / CUDA
RAID storage              CPU Compute               Linux
