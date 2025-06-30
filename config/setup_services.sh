#!/bin/bash

# MoxNAS Service Configuration Script
# This script configures all NAS services for container operation

set -e

echo "🔧 Configuring MoxNAS services..."

# Create necessary directories
mkdir -p /mnt/storage
mkdir -p /etc/moxnas
mkdir -p /var/log/moxnas

# Configure Samba (SMB/CIFS)
echo "📁 Configuring Samba..."
cat > /etc/samba/smb.conf << 'EOF'
[global]
   workgroup = WORKGROUP
   server string = MoxNAS Server
   netbios name = MOXNAS
   security = user
   map to guest = Bad User
   dns proxy = no
   log file = /var/log/samba/log.%m
   max log size = 1000
   logging = file
   panic action = /usr/share/samba/panic-action %d
   server role = standalone server
   passdb backend = tdbsam
   obey pam restrictions = yes
   unix password sync = yes
   passwd program = /usr/bin/passwd %u
   passwd chat = *Enter\snew\s*\spassword:* %n\n *Retype\snew\s*\spassword:* %n\n *password\supdated\ssuccessfully* .
   pam password change = yes
   map to guest = bad user
   usershare allow guests = yes

[storage]
   comment = MoxNAS Storage
   path = /mnt/storage
   browseable = yes
   writable = yes
   guest ok = yes
   read only = no
   create mask = 0755
   directory mask = 0755
EOF

# Configure NFS
echo "🌐 Configuring NFS..."
cat > /etc/exports << 'EOF'
# MoxNAS NFS Exports
/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)
EOF

# Configure FTP
echo "📤 Configuring FTP..."
cat > /etc/vsftpd.conf << 'EOF'
# MoxNAS FTP Configuration
listen=NO
listen_ipv6=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=NO
pasv_enable=YES
pasv_min_port=10000
pasv_max_port=10100
allow_writeable_chroot=YES
user_sub_token=$USER
local_root=/mnt/storage
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
EOF

# Create FTP user list
touch /etc/vsftpd.userlist

# Configure SSH (already installed, just secure it)
echo "🔐 Configuring SSH..."
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Configure SNMP
echo "📊 Configuring SNMP..."
cat > /etc/snmp/snmpd.conf << 'EOF'
# MoxNAS SNMP Configuration
agentAddress udp:161
rocommunity public default -V systemonly
rocommunity6 public default -V systemonly
rouser authOnlyUser
sysLocation Container
sysContact Admin <admin@moxnas>
sysDescr MoxNAS Container NAS System
EOF

# Configure iSCSI Target
echo "💾 Configuring iSCSI..."
cat > /etc/tgt/conf.d/moxnas.conf << 'EOF'
# MoxNAS iSCSI Target Configuration
# Default target will be created via web interface
EOF

# Set proper permissions
chown -R root:root /etc/samba
chown -R root:root /etc/exports
chown -R root:root /etc/vsftpd.conf
chmod 644 /etc/samba/smb.conf
chmod 644 /etc/exports
chmod 644 /etc/vsftpd.conf

# Create systemd override for container operation
mkdir -p /etc/systemd/system/smbd.service.d
cat > /etc/systemd/system/smbd.service.d/override.conf << 'EOF'
[Unit]
ConditionPathExists=
ConditionPathExists=/etc/samba/smb.conf

[Service]
ExecStartPre=
ExecStartPre=/usr/share/samba/update-apparmor-samba-profile
EOF

# Enable services but don't start them yet (will be managed by MoxNAS)
systemctl daemon-reload
systemctl enable smbd nmbd
systemctl enable nfs-kernel-server
systemctl enable vsftpd
systemctl enable ssh
systemctl enable snmpd
systemctl enable tgt

echo "✅ Service configuration completed!"
echo ""
echo "🚀 Configured services:"
echo "   - Samba (SMB/CIFS) on port 445"
echo "   - NFS on port 2049"
echo "   - FTP on port 21"
echo "   - SSH on port 22"
echo "   - SNMP on port 161"
echo "   - iSCSI on port 3260"
echo ""
echo "📂 Storage location: /mnt/storage"
echo "⚙️  Configuration files created in /etc/"