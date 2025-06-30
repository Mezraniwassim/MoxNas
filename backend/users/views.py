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
        """Create system user account"""
        try:
            # Create home directory
            os.makedirs(user.home_directory, exist_ok=True)
            
            # Create system user with useradd
            cmd = [
                'useradd', 
                '-d', user.home_directory,
                '-s', user.shell,
                '-m', user.username
            ]
            subprocess.run(cmd, check=True)
            
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
        """Set user password"""
        user = get_object_or_404(MoxNASUser, pk=pk)
        password = request.data.get('password')
        
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        
        # Set system password
        try:
            proc = subprocess.run(['passwd', user.username], input=f'{password}\n{password}\n', 
                                text=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass
        
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