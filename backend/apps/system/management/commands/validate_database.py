"""
Database validation and health check command for MoxNAS
"""

import os
import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection, transaction
from django.apps import apps
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Validate database schema and perform health checks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-issues',
            action='store_true',
            help='Attempt to fix found issues automatically'
        )
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create default superuser if none exists'
        )
        parser.add_argument(
            '--migrate',
            action='store_true',
            help='Run database migrations if needed'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== MoxNAS Database Validation ===\n'))
        
        fix_issues = options['fix_issues']
        create_superuser = options['create_superuser']
        run_migrations = options['migrate']
        
        issues_found = 0
        issues_fixed = 0
        
        try:
            # Check database connection
            issues_found += self.check_database_connection()
            
            # Check for pending migrations
            pending_migrations = self.check_pending_migrations()
            if pending_migrations:
                issues_found += 1
                if run_migrations or fix_issues:
                    self.run_migrations()
                    issues_fixed += 1
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠ Use --migrate to apply pending migrations')
                    )
            
            # Validate models
            issues_found += self.validate_models()
            
            # Check for superuser
            if not User.objects.filter(is_superuser=True).exists():
                issues_found += 1
                if create_superuser or fix_issues:
                    self.create_default_superuser()
                    issues_fixed += 1
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠ No superuser exists. Use --create-superuser to create one')
                    )
            
            # Check app-specific data integrity
            issues_found += self.check_data_integrity()
            
            # Performance checks
            self.check_database_performance()
            
            # Summary
            self.stdout.write('\n=== Validation Summary ===')
            if issues_found == 0:
                self.stdout.write(self.style.SUCCESS('✅ Database validation passed!'))
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Found {issues_found} issues, fixed {issues_fixed}')
                )
                if issues_found > issues_fixed:
                    self.stdout.write(
                        self.style.ERROR(f'❌ {issues_found - issues_fixed} issues remain')
                    )
                    return 1
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database validation failed: {e}')
            )
            logger.error(f"Database validation error: {e}")
            return 1
        
        return 0
    
    def check_database_connection(self):
        """Check database connectivity"""
        self.stdout.write('Checking database connection...')
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    self.stdout.write(self.style.SUCCESS('✅ Database connection OK'))
                    return 0
                else:
                    self.stdout.write(self.style.ERROR('❌ Database connection test failed'))
                    return 1
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database connection failed: {e}')
            )
            return 1
    
    def check_pending_migrations(self):
        """Check for pending migrations"""
        self.stdout.write('Checking for pending migrations...')
        
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            
            if plan:
                self.stdout.write(
                    self.style.WARNING(f'⚠ {len(plan)} pending migrations found')
                )
                for migration in plan:
                    self.stdout.write(f'  - {migration[0].app_label}.{migration[0].name}')
                return True
            else:
                self.stdout.write(self.style.SUCCESS('✅ No pending migrations'))
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Migration check failed: {e}')
            )
            return True
    
    def run_migrations(self):
        """Run database migrations"""
        self.stdout.write('Running database migrations...')
        
        try:
            call_command('migrate', verbosity=0)
            self.stdout.write(self.style.SUCCESS('✅ Migrations applied successfully'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Migration failed: {e}')
            )
            raise
    
    def validate_models(self):
        """Validate all Django models"""
        self.stdout.write('Validating models...')
        
        issues = 0
        
        try:
            # Run Django's built-in model validation
            from django.core.management.commands.check import Command as CheckCommand
            check_command = CheckCommand()
            
            # Capture check output
            import io
            import sys
            old_stderr = sys.stderr
            sys.stderr = mystderr = io.StringIO()
            
            try:
                check_command.handle(verbosity=0, deploy=True)
                check_output = mystderr.getvalue()
                
                if check_output.strip():
                    self.stdout.write(
                        self.style.WARNING(f'⚠ Model validation warnings:\\n{check_output}')
                    )
                    issues += 1
                else:
                    self.stdout.write(self.style.SUCCESS('✅ Model validation passed'))
                    
            finally:
                sys.stderr = old_stderr
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Model validation failed: {e}')
            )
            issues += 1
        
        return issues
    
    def create_default_superuser(self):
        """Create default superuser"""
        self.stdout.write('Creating default superuser...')
        
        try:
            user = User.objects.create_superuser(
                username='admin',
                email='admin@moxnas.local',
                password='moxnas123'  # Should be changed after first login
            )
            self.stdout.write(
                self.style.SUCCESS('✅ Created superuser "admin" with password "moxnas123"')
            )
            self.stdout.write(
                self.style.WARNING('⚠ Please change the default password after first login!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to create superuser: {e}')
            )
            raise
    
    def check_data_integrity(self):
        """Check data integrity across related models"""
        self.stdout.write('Checking data integrity...')
        
        issues = 0
        
        try:
            # Check for orphaned shares
            from apps.shares.models import SMBShare, NFSShare
            from apps.storage.models import MountPoint
            
            # Check SMB shares with invalid paths
            invalid_smb_shares = SMBShare.objects.exclude(
                path__in=MountPoint.objects.values_list('path', flat=True)
            ).filter(enabled=True)
            
            if invalid_smb_shares.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ {invalid_smb_shares.count()} SMB shares have invalid mount paths'
                    )
                )
                for share in invalid_smb_shares:
                    self.stdout.write(f'  - {share.name}: {share.path}')
                issues += 1
            
            # Check NFS shares with invalid paths
            invalid_nfs_shares = NFSShare.objects.exclude(
                path__in=MountPoint.objects.values_list('path', flat=True)
            ).filter(enabled=True)
            
            if invalid_nfs_shares.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ {invalid_nfs_shares.count()} NFS shares have invalid mount paths'
                    )
                )
                issues += 1
            
            if issues == 0:
                self.stdout.write(self.style.SUCCESS('✅ Data integrity check passed'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Data integrity check failed: {e}')
            )
            issues += 1
        
        return issues
    
    def check_database_performance(self):
        """Check database performance metrics"""
        self.stdout.write('Checking database performance...')
        
        try:
            with connection.cursor() as cursor:
                # Check database size (SQLite)
                if 'sqlite' in connection.vendor:
                    cursor.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    db_size = page_count * page_size
                    
                    self.stdout.write(f'📊 Database size: {db_size / 1024 / 1024:.2f} MB')
                
                # Check table counts
                app_models = apps.get_models()
                total_records = 0
                
                for model in app_models:
                    try:
                        count = model.objects.count()
                        total_records += count
                        if count > 1000:
                            self.stdout.write(
                                f'📊 {model.__name__}: {count} records'
                            )
                    except Exception:
                        # Skip models that might not have tables yet
                        continue
                
                self.stdout.write(f'📊 Total records: {total_records}')
                
                if total_records > 100000:
                    self.stdout.write(
                        self.style.WARNING('⚠ Large dataset detected - consider database optimization')
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠ Performance check failed: {e}')
            )