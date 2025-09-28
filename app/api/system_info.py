
from flask import jsonify
from app.api import bp

@bp.route('/system/info')
def system_info():
    """Informations système adaptées"""
    return jsonify({
        "os": "Ubuntu 24.04.3 LTS",
        "storage": {
            "zfs_available": False,
            "lvm_available": False,
            "filesystem_types": ["ext4", "ntfs", "vfat"]
        },
        "services": {
            "samba": True,
            "nmbd": False
        },
        "storage_devices": [
            {"name": "sda", "size": "238.47 GiB", "type": "ext4"},
            {"name": "sdb", "size": "1.82 TiB", "type": "ntfs"}
        ],
        "adaptations": [
            "ZFS remplacé par gestion ext4/NTFS",
            "LVM désactivé - gestion directe des disques",
            "Configuration Samba adaptée",
            "Chemins de sauvegarde configurés"
        ]
    })
