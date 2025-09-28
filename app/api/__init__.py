"""API Blueprint"""
from flask import Blueprint

bp = Blueprint("api", __name__)

from app.api.endpoints import (
    auth,
    backup,
    logs,
    monitoring,
    shares,
    storage,
    performance,
    nfs,
    smb,
    raid,
    proxmox,
    lxc,
)
# Import du module d'informations système adapté
from app.api import system_info
