from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
import logging
import os
import subprocess

from .models import Dataset, Share, ShareACL, UserAccount, UserGroup
from .serializers import DatasetSerializer, ShareSerializer, ShareACLSerializer, UserAccountSerializer
from apps.containers.models import MoxNasContainer
from apps.proxmox.services import ProxmoxService

logger = logging.getLogger('moxnas.storage')


class DatasetListView(APIView):
    """Manage datasets"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            container_id = request.GET.get('container_id')
            if container_id:
                container = get_object_or_404(MoxNasContainer, vmid=container_id)
                datasets = Dataset.objects.filter(container=container)
            else:
                datasets = Dataset.objects.all()
            
            serializer = DatasetSerializer(datasets, many=True)
            return Response({
                'datasets': serializer.data,
                'total': datasets.count()
            })
        except Exception as e:
            logger.error(f"Failed to fetch datasets: {e}")
            return Response(
                {'error': 'Failed to fetch datasets', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create a new dataset"""
        try:
            data = request.data
            container_id = data.get('container_id')
            
            if not container_id:
                return Response(
                    {'error': 'Container ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            container = get_object_or_404(MoxNasContainer, vmid=container_id)
            
            # Validate and sanitize dataset name
            dataset_name = data['name']
            if not dataset_name.replace('_', '').replace('-', '').isalnum():
                return Response(
                    {'error': 'Dataset name can only contain letters, numbers, underscores, and hyphens'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the dataset directory
            dataset_path = f"/mnt/{dataset_name}"
            
            # Execute directory creation in the container
            proxmox_service = ProxmoxService()
            result = proxmox_service.execute_command(
                container_id,
                f"mkdir -p '{dataset_path}' && chown root:root '{dataset_path}' && chmod 755 '{dataset_path}'"
            )
            
            if result is None:
                return Response(
                    {'error': 'Failed to create dataset directory'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create database record
            dataset = Dataset.objects.create(
                container=container,
                name=data['name'],
                path=dataset_path,
                mount_point=dataset_path,
                size_limit=data.get('size_limit'),
                compression=data.get('compression', 'lz4'),
                deduplication=data.get('deduplication', False),
                readonly=data.get('readonly', False)
            )
            
            serializer = DatasetSerializer(dataset)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            return Response(
                {'error': 'Failed to create dataset', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DatasetDetailView(APIView):
    """Individual dataset management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, dataset_id):
        try:
            dataset = get_object_or_404(Dataset, id=dataset_id)
            
            # Get disk usage information
            if dataset.container:
                proxmox_service = ProxmoxService()
                disk_usage = proxmox_service.execute_command(
                    dataset.container.vmid,
                    f"du -sb {dataset.path} 2>/dev/null | cut -f1 || echo 0"
                )
                
                if disk_usage:
                    try:
                        dataset.used_space = int(disk_usage.strip())
                        dataset.save()
                    except (ValueError, AttributeError):
                        pass
            
            serializer = DatasetSerializer(dataset)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to get dataset {dataset_id}: {e}")
            return Response(
                {'error': f'Failed to get dataset {dataset_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, dataset_id):
        try:
            dataset = get_object_or_404(Dataset, id=dataset_id)
            
            # Remove directory from container
            if dataset.container:
                proxmox_service = ProxmoxService()
                proxmox_service.execute_command(
                    dataset.container.vmid,
                    f"rm -rf '{dataset.path}'"
                )
            
            dataset.delete()
            return Response({'message': 'Dataset deleted successfully'})
            
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_id}: {e}")
            return Response(
                {'error': f'Failed to delete dataset {dataset_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ShareListView(APIView):
    """Manage shares"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            container_id = request.GET.get('container_id')
            dataset_id = request.GET.get('dataset_id')
            
            shares = Share.objects.all()
            
            if container_id:
                shares = shares.filter(dataset__container__vmid=container_id)
            
            if dataset_id:
                shares = shares.filter(dataset_id=dataset_id)
            
            serializer = ShareSerializer(shares, many=True)
            return Response({
                'shares': serializer.data,
                'total': shares.count()
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch shares: {e}")
            return Response(
                {'error': 'Failed to fetch shares', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create a new share"""
        try:
            data = request.data
            dataset_id = data.get('dataset_id')
            
            if not dataset_id:
                return Response(
                    {'error': 'Dataset ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            dataset = get_object_or_404(Dataset, id=dataset_id)
            
            # Create share subdirectory
            share_path = os.path.join(dataset.path, data['name'])
            
            proxmox_service = ProxmoxService()
            result = proxmox_service.execute_command(
                dataset.container.vmid,
                f"mkdir -p '{share_path}' && chown root:root '{share_path}' && chmod 755 '{share_path}'"
            )
            
            if result is None:
                return Response(
                    {'error': 'Failed to create share directory'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create database record
            share = Share.objects.create(
                dataset=dataset,
                name=data['name'],
                share_type=data['share_type'],
                path=share_path,
                description=data.get('description', ''),
                readonly=data.get('readonly', False),
                browseable=data.get('browseable', True),
                guest_access=data.get('guest_access', False),
                config=data.get('config', {})
            )
            
            # Configure the actual share service
            self._configure_share_service(share)
            
            serializer = ShareSerializer(share)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create share: {e}")
            return Response(
                {'error': 'Failed to create share', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _configure_share_service(self, share):
        """Configure the actual share service (SMB, NFS, etc.)"""
        try:
            proxmox_service = ProxmoxService()
            container_id = share.dataset.container.vmid
            
            if share.share_type == 'smb':
                self._configure_smb_share(proxmox_service, container_id, share)
            elif share.share_type == 'nfs':
                self._configure_nfs_share(proxmox_service, container_id, share)
            elif share.share_type == 'ftp':
                self._configure_ftp_share(proxmox_service, container_id, share)
                
        except Exception as e:
            logger.error(f"Failed to configure share service for {share.name}: {e}")
    
    def _configure_smb_share(self, proxmox_service, container_id, share):
        """Configure SMB/CIFS share"""
        smb_config = f"""
[{share.name}]
    path = {share.path}
    comment = {share.description or share.name}
    valid users = @smbusers
    read only = {'yes' if share.readonly else 'no'}
    browseable = {'yes' if share.browseable else 'no'}
    guest ok = {'yes' if share.guest_access else 'no'}
    create mask = 0664
    directory mask = 0775
"""
        
        # Add to Samba configuration
        proxmox_service.execute_command(
            container_id,
            f"echo '{smb_config}' >> /etc/samba/smb.conf && systemctl reload smbd"
        )
    
    def _configure_nfs_share(self, proxmox_service, container_id, share):
        """Configure NFS share"""
        nfs_export = f"{share.path} *(rw,sync,no_subtree_check,no_root_squash)"
        
        proxmox_service.execute_command(
            container_id,
            f"echo '{nfs_export}' >> /etc/exports && exportfs -ra"
        )
    
    def _configure_ftp_share(self, proxmox_service, container_id, share):
        """Configure FTP access"""
        # Create FTP user directory symlink
        proxmox_service.execute_command(
            container_id,
            f"ln -sf {share.path} /srv/ftp/{share.name}"
        )


class ShareDetailView(APIView):
    """Individual share management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, share_id):
        try:
            share = get_object_or_404(Share, id=share_id)
            
            # Include ACLs in the response
            serializer = ShareSerializer(share)
            data = serializer.data
            
            # Add ACL information
            acls = ShareACL.objects.filter(share=share)
            data['acls'] = ShareACLSerializer(acls, many=True).data
            
            return Response(data)
            
        except Exception as e:
            logger.error(f"Failed to get share {share_id}: {e}")
            return Response(
                {'error': f'Failed to get share {share_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, share_id):
        """Update share configuration"""
        try:
            share = get_object_or_404(Share, id=share_id)
            
            # Update share properties
            for field in ['description', 'readonly', 'browseable', 'guest_access', 'is_enabled']:
                if field in request.data:
                    setattr(share, field, request.data[field])
            
            if 'config' in request.data:
                share.config.update(request.data['config'])
            
            share.save()
            
            # Reconfigure the service
            ShareListView()._configure_share_service(share)
            
            serializer = ShareSerializer(share)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to update share {share_id}: {e}")
            return Response(
                {'error': f'Failed to update share {share_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, share_id):
        try:
            share = get_object_or_404(Share, id=share_id)
            
            # Remove from service configurations
            proxmox_service = ProxmoxService()
            container_id = share.dataset.container.vmid
            
            if share.share_type == 'smb':
                # Remove from SMB config
                proxmox_service.execute_command(
                    container_id,
                    f"sed -i '/\\[{share.name}\\]/,/^$/d' /etc/samba/smb.conf && systemctl reload smbd"
                )
            elif share.share_type == 'nfs':
                # Remove from NFS exports
                proxmox_service.execute_command(
                    container_id,
                    f"sed -i '\\#{share.path}#d' /etc/exports && exportfs -ra"
                )
            
            # Remove directory if empty
            proxmox_service.execute_command(
                container_id,
                f"rmdir {share.path} 2>/dev/null || true"
            )
            
            share.delete()
            return Response({'message': 'Share deleted successfully'})
            
        except Exception as e:
            logger.error(f"Failed to delete share {share_id}: {e}")
            return Response(
                {'error': f'Failed to delete share {share_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ShareACLView(APIView):
    """Manage share ACLs"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, share_id):
        try:
            share = get_object_or_404(Share, id=share_id)
            acls = ShareACL.objects.filter(share=share)
            serializer = ShareACLSerializer(acls, many=True)
            return Response({'acls': serializer.data})
            
        except Exception as e:
            logger.error(f"Failed to get ACLs for share {share_id}: {e}")
            return Response(
                {'error': f'Failed to get ACLs for share {share_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, share_id):
        try:
            share = get_object_or_404(Share, id=share_id)
            
            acl = ShareACL.objects.create(
                share=share,
                acl_type=request.data['acl_type'],
                identifier=request.data['identifier'],
                permission=request.data['permission'],
                allow_read=request.data.get('allow_read', True),
                allow_write=request.data.get('allow_write', False),
                allow_execute=request.data.get('allow_execute', False),
                allow_delete=request.data.get('allow_delete', False),
                allow_modify_acl=request.data.get('allow_modify_acl', False)
            )
            
            serializer = ShareACLSerializer(acl)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create ACL for share {share_id}: {e}")
            return Response(
                {'error': f'Failed to create ACL for share {share_id}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserAccountListView(APIView):
    """Manage NAS user accounts"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            container_id = request.GET.get('container_id')
            if container_id:
                container = get_object_or_404(MoxNasContainer, vmid=container_id)
                users = UserAccount.objects.filter(container=container)
            else:
                users = UserAccount.objects.all()
            
            serializer = UserAccountSerializer(users, many=True)
            return Response({
                'users': serializer.data,
                'total': users.count()
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch users: {e}")
            return Response(
                {'error': 'Failed to fetch users', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create a new NAS user"""
        try:
            data = request.data
            container_id = data.get('container_id')
            
            if not container_id:
                return Response(
                    {'error': 'Container ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            container = get_object_or_404(MoxNasContainer, vmid=container_id)
            
            # Create system user in container
            proxmox_service = ProxmoxService()
            home_dir = f"/home/{data['username']}"
            
            # Validate username
            username = data['username']
            if not username.replace('_', '').replace('-', '').isalnum():
                return Response(
                    {'error': 'Username can only contain letters, numbers, underscores, and hyphens'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user with home directory
            result = proxmox_service.execute_command(
                container_id,
                f"useradd -m -d '{home_dir}' -s '{data.get('shell', '/bin/bash')}' '{username}'"
            )
            
            if result is None:
                return Response(
                    {'error': 'Failed to create system user'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Set password if provided
            if 'password' in data:
                # Use safer password setting method
                password = data['password'].replace("'", "'\"'\"'")  # Escape single quotes
                proxmox_service.execute_command(
                    container_id,
                    f"echo '{username}:{password}' | chpasswd"
                )
            
            # Create database record
            user = UserAccount.objects.create(
                container=container,
                username=data['username'],
                full_name=data.get('full_name', ''),
                email=data.get('email', ''),
                home_directory=home_dir,
                shell=data.get('shell', '/bin/bash'),
                allow_ssh=data.get('allow_ssh', False),
                allow_ftp=data.get('allow_ftp', True),
                allow_smb=data.get('allow_smb', True),
                allow_webdav=data.get('allow_webdav', False)
            )
            
            serializer = UserAccountSerializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return Response(
                {'error': 'Failed to create user', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )