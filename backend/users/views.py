from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import MoxNASUser, MoxNASGroup, AccessControlList
from .serializers import MoxNASUserSerializer, MoxNASGroupSerializer, AccessControlListSerializer
import subprocess
import os

class MoxNASUserViewSet(viewsets.ModelViewSet):
    queryset = MoxNASUser.objects.all()
    serializer_class = MoxNASUserSerializer
    
    def perform_create(self, serializer):
        """Create user and system account"""
        user = serializer.save()
        self._create_system_user(user)
    
    def perform_update(self, serializer):
        """Update user and system account"""
        user = serializer.save()
        self._update_system_user(user)
    
    def perform_destroy(self, instance):
        """Delete user and system account"""
        self._delete_system_user(instance)
        instance.delete()
    
    def _create_system_user(self, user):
        """Create system user account with enhanced security"""
        try:
            # Import security utilities
            from services.security_utils import PathValidator, InputValidator, CommandValidator
            
            # Validate username
            if not InputValidator.validate_username(user.username):
                logger.error(f"Invalid username: {user.username}")
                return False
            
            # Validate and sanitize home directory path
            try:
                safe_home_dir = PathValidator.validate_path(user.home_directory)
            except ValueError as e:
                logger.error(f"Invalid home directory: {e}")
                safe_home_dir = f"/mnt/storage/users/{user.username}"
            
            # Create home directory with secure permissions
            os.makedirs(safe_home_dir, mode=0o755, exist_ok=True)
            
            # Create system user with useradd
            cmd = [
                'useradd', 
                '-d', safe_home_dir,
                '-s', user.shell,
                '-m', user.username
            ]
            
            # Validate command before execution
            if not CommandValidator.validate_command(cmd):
                logger.error(f"Command validation failed: {cmd}")
                return False
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Set ownership of home directory
            subprocess.run(['chown', f'{user.username}:{user.username}', user.home_directory], check=True)
            
        except subprocess.CalledProcessError as e:
            # If user already exists, that's okay
            if e.returncode != 9:  # User already exists
                pass
    
    def _update_system_user(self, user):
        """Update system user account"""
        try:
            # Update user shell
            subprocess.run(['usermod', '-s', user.shell, user.username], check=True)
            
            # Update home directory if changed
            if user.home_directory:
                subprocess.run(['usermod', '-d', user.home_directory, user.username], check=True)
                
        except subprocess.CalledProcessError:
            pass
    
    def _delete_system_user(self, user):
        """Delete system user account"""
        try:
            subprocess.run(['userdel', '-r', user.username], check=True)
        except subprocess.CalledProcessError:
            pass
    
    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        """Set user password with enhanced security"""
        user = get_object_or_404(MoxNASUser, pk=pk)
        password = request.data.get('password')
        
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        if len(password) < 8:
            return Response({'error': 'Password must be at least 8 characters long'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Validate username
        from services.security_utils import InputValidator, CommandValidator
        if not InputValidator.validate_username(user.username):
            return Response({'error': 'Invalid username'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        
        # Set system password using chpasswd (more secure than passwd)
        try:
            cmd = ['chpasswd']
            if CommandValidator.validate_command(cmd):
                proc = subprocess.run(
                    cmd, 
                    input=f'{user.username}:{password}\n',
                    text=True, 
                    capture_output=True,
                    timeout=30
                )
                if proc.returncode != 0:
                    logger.warning(f"Failed to set system password for {user.username}: {proc.stderr}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(f"Error setting system password: {e}")
        
        return Response({'success': True, 'message': 'Password updated successfully'})

class MoxNASGroupViewSet(viewsets.ModelViewSet):
    queryset = MoxNASGroup.objects.all()
    serializer_class = MoxNASGroupSerializer
    
    def perform_create(self, serializer):
        """Create group and system group"""
        group = serializer.save()
        self._create_system_group(group)
    
    def perform_destroy(self, instance):
        """Delete group and system group"""
        self._delete_system_group(instance)
        instance.delete()
    
    def _create_system_group(self, group):
        """Create system group"""
        try:
            cmd = ['groupadd', group.name]
            if group.gid:
                cmd.extend(['-g', str(group.gid)])
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            pass
    
    def _delete_system_group(self, group):
        """Delete system group"""
        try:
            subprocess.run(['groupdel', group.name], check=True)
        except subprocess.CalledProcessError:
            pass
    
    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        """Add user to group"""
        group = get_object_or_404(MoxNASGroup, pk=pk)
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = MoxNASUser.objects.get(id=user_id)
            group.users.add(user)
            
            # Add to system group
            subprocess.run(['usermod', '-a', '-G', group.name, user.username], check=True)
            
            return Response({'success': True, 'message': f'User {user.username} added to group {group.name}'})
        except MoxNASUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except subprocess.CalledProcessError:
            return Response({'error': 'Failed to add user to system group'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AccessControlListViewSet(viewsets.ModelViewSet):
    queryset = AccessControlList.objects.all()
    serializer_class = AccessControlListSerializer
    
    def perform_create(self, serializer):
        """Create ACL and apply to filesystem"""
        acl = serializer.save()
        self._apply_acl(acl)
    
    def perform_update(self, serializer):
        """Update ACL and apply to filesystem"""
        acl = serializer.save()
        self._apply_acl(acl)
    
    def perform_destroy(self, instance):
        """Remove ACL from filesystem"""
        self._remove_acl(instance)
        instance.delete()
    
    def _apply_acl(self, acl):
        """Apply ACL to filesystem using setfacl"""
        try:
            # Build setfacl command
            target = ''
            if acl.target_user:
                target = f'u:{acl.target_user.username}:{acl.permissions}'
            elif acl.target_group:
                target = f'g:{acl.target_group.name}:{acl.permissions}'
            else:
                target = f'o::{acl.permissions}'
            
            cmd = ['setfacl', '-m', target, acl.path]
            if acl.recursive:
                cmd.insert(1, '-R')
            
            subprocess.run(cmd, check=True)
            
        except subprocess.CalledProcessError:
            pass
    
    def _remove_acl(self, acl):
        """Remove ACL from filesystem"""
        try:
            target = ''
            if acl.target_user:
                target = f'u:{acl.target_user.username}'
            elif acl.target_group:
                target = f'g:{acl.target_group.name}'
            else:
                target = 'o:'
            
            cmd = ['setfacl', '-x', target, acl.path]
            if acl.recursive:
                cmd.insert(1, '-R')
            
            subprocess.run(cmd, check=True)
            
        except subprocess.CalledProcessError:
            pass
    
    @action(detail=False, methods=['get'])
    def path_acls(self, request):
        """Get ACLs for a specific path"""
        path = request.query_params.get('path')
        if not path:
            return Response({'error': 'Path parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        acls = self.queryset.filter(path=path)
        serializer = self.get_serializer(acls, many=True)
        return Response(serializer.data)