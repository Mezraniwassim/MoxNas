from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.management import call_command
import logging

from apps.shares.models import SMBShare, NFSShare

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SMBShare)
@receiver(post_delete, sender=SMBShare)
def update_samba_config(sender, **kwargs):
    """Automatically update Samba configuration when SMB shares change"""
    try:
        logger.info("SMB share changed, regenerating Samba configuration")
        call_command('configure_services', '--service=samba')
    except Exception as e:
        logger.error(f"Failed to regenerate Samba configuration: {e}")

@receiver(post_save, sender=NFSShare)
@receiver(post_delete, sender=NFSShare)
def update_nfs_config(sender, **kwargs):
    """Automatically update NFS configuration when NFS shares change"""
    try:
        logger.info("NFS share changed, regenerating NFS exports")
        call_command('configure_services', '--service=nfs')
    except Exception as e:
        logger.error(f"Failed to regenerate NFS exports: {e}")