<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# MoxNAS Project Instructions

This project modifies TrueNAS Scale (v24.10.2.1) to run as an LXC container in Proxmox VE 8.4. When suggesting code:

1. Focus on container-friendly implementations that work within LXC constraints
2. Prefer mount point-based storage solutions over ZFS
3. Maintain compatibility with core NAS services (SMB, NFS, FTP, iSCSI)
4. Consider Proxmox VE 8.4 integration requirements
5. Follow Python best practices and type hints
6. Include proper error handling for system-level operations
7. Ensure security best practices for network services
8. Add appropriate logging for system operations
