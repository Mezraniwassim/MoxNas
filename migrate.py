#!/usr/bin/env python3
"""
MoxNAS Database Migration Script
Handles database initialization, migrations, and upgrades
"""
import os
import sys
import click
from flask.cli import with_appcontext
from flask import current_app
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
import sqlalchemy as sa

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, UserRole

def get_alembic_config():
    """Get Alembic configuration"""
    config = Config(os.path.join(os.path.dirname(__file__), 'migrations', 'alembic.ini'))
    config.set_main_option('script_location', os.path.join(os.path.dirname(__file__), 'migrations'))
    
    # Set database URL from Flask app config
    app = current_app or create_app()
    config.set_main_option('sqlalchemy.url', app.config['SQLALCHEMY_DATABASE_URI'])
    
    return config

def get_current_revision():
    """Get current database revision"""
    try:
        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    except Exception:
        return None

def database_exists():
    """Check if database exists and has tables"""
    try:
        with db.engine.connect() as connection:
            # Try to query a table that should exist
            connection.execute(sa.text("SELECT 1 FROM user LIMIT 1"))
            return True
    except Exception:
        return False

@click.group()
def cli():
    """MoxNAS Database Migration Tool"""
    pass

@cli.command()
@click.option('--drop', is_flag=True, help='Drop existing database before creating')
def init(drop):
    """Initialize the database"""
    app = create_app()
    
    with app.app_context():
        if drop:
            click.echo("Dropping existing database...")
            db.drop_all()
        
        click.echo("Creating database tables...")
        db.create_all()
        
        # Stamp the database with the current migration
        config = get_alembic_config()
        command.stamp(config, "head")
        
        click.echo("Database initialized successfully!")

@cli.command()
@click.option('--message', '-m', help='Migration message')
def migrate(message):
    """Generate a new migration"""
    app = create_app()
    
    with app.app_context():
        config = get_alembic_config()
        
        if not message:
            message = click.prompt('Enter migration message')
        
        try:
            command.revision(config, message=message, autogenerate=True)
            click.echo(f"Migration generated: {message}")
        except Exception as e:
            click.echo(f"Error generating migration: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.option('--revision', help='Revision to upgrade to (default: head)')
def upgrade(revision):
    """Upgrade database to latest migration"""
    app = create_app()
    
    with app.app_context():
        config = get_alembic_config()
        
        if not revision:
            revision = "head"
        
        try:
            click.echo(f"Upgrading database to {revision}...")
            command.upgrade(config, revision)
            click.echo("Database upgrade completed!")
        except Exception as e:
            click.echo(f"Error upgrading database: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.option('--revision', help='Revision to downgrade to')
def downgrade(revision):
    """Downgrade database to previous migration"""
    app = create_app()
    
    with app.app_context():
        config = get_alembic_config()
        
        if not revision:
            revision = click.prompt('Enter target revision')
        
        if click.confirm(f'Are you sure you want to downgrade to {revision}?'):
            try:
                click.echo(f"Downgrading database to {revision}...")
                command.downgrade(config, revision)
                click.echo("Database downgrade completed!")
            except Exception as e:
                click.echo(f"Error downgrading database: {e}", err=True)
                sys.exit(1)

@cli.command()
def current():
    """Show current migration revision"""
    app = create_app()
    
    with app.app_context():
        try:
            revision = get_current_revision()
            if revision:
                click.echo(f"Current revision: {revision}")
            else:
                click.echo("No current revision (database not initialized)")
        except Exception as e:
            click.echo(f"Error getting current revision: {e}", err=True)

@cli.command()
def history():
    """Show migration history"""
    app = create_app()
    
    with app.app_context():
        config = get_alembic_config()
        
        try:
            command.history(config, verbose=True)
        except Exception as e:
            click.echo(f"Error showing migration history: {e}", err=True)

@cli.command()
@click.option('--username', prompt=True, help='Admin username')
@click.option('--email', prompt=True, help='Admin email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--first-name', help='Admin first name')
@click.option('--last-name', help='Admin last name')
def create_admin(username, email, password, first_name, last_name):
    """Create admin user"""
    app = create_app()
    
    with app.app_context():
        # Check if admin user already exists
        existing_admin = User.query.filter_by(role=UserRole.ADMIN).first()
        if existing_admin:
            if not click.confirm(f'Admin user "{existing_admin.username}" already exists. Create another admin?'):
                return
        
        try:
            admin = User(
                username=username,
                email=email,
                role=UserRole.ADMIN,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            admin.set_password(password)
            
            db.session.add(admin)
            db.session.commit()
            
            click.echo(f"Admin user '{username}' created successfully!")
            
        except Exception as e:
            click.echo(f"Error creating admin user: {e}", err=True)
            db.session.rollback()
            sys.exit(1)

@cli.command()
def check():
    """Check database status and connectivity"""
    app = create_app()
    
    with app.app_context():
        try:
            # Test database connection
            with db.engine.connect() as connection:
                result = connection.execute(sa.text("SELECT version()"))
                version = result.fetchone()[0]
                click.echo(f"✓ Database connection successful")
                click.echo(f"  Database version: {version}")
            
            # Check if database is initialized
            if database_exists():
                click.echo("✓ Database is initialized")
                
                # Check current revision
                revision = get_current_revision()
                if revision:
                    click.echo(f"✓ Current migration revision: {revision}")
                else:
                    click.echo("⚠ No migration revision found")
                
                # Check admin user
                admin_count = User.query.filter_by(role=UserRole.ADMIN).count()
                click.echo(f"✓ Admin users: {admin_count}")
                
            else:
                click.echo("⚠ Database is not initialized")
                click.echo("  Run 'python migrate.py init' to initialize the database")
                
        except Exception as e:
            click.echo(f"✗ Database check failed: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.option('--force', is_flag=True, help='Force reset without confirmation')
def reset(force):
    """Reset database (WARNING: This will delete all data!)"""
    app = create_app()
    
    if not force:
        click.echo("WARNING: This will delete ALL data in the database!")
        if not click.confirm('Are you sure you want to continue?'):
            return
    
    with app.app_context():
        try:
            click.echo("Dropping all tables...")
            db.drop_all()
            
            click.echo("Recreating tables...")
            db.create_all()
            
            # Stamp with current migration
            config = get_alembic_config()
            command.stamp(config, "head")
            
            click.echo("Database reset completed!")
            
        except Exception as e:
            click.echo(f"Error resetting database: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.option('--backup-file', help='Backup file path')
def backup(backup_file):
    """Create database backup"""
    app = create_app()
    
    if not backup_file:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"moxnas_backup_{timestamp}.sql"
    
    try:
        # Get database URL components
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        if db_url.startswith('postgresql'):
            # PostgreSQL backup
            import subprocess
            from urllib.parse import urlparse
            
            parsed = urlparse(db_url)
            
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            cmd = [
                'pg_dump',
                '-h', parsed.hostname or 'localhost',
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path.lstrip('/'),
                '-f', backup_file,
                '--no-password'
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo(f"Database backup created: {backup_file}")
            else:
                click.echo(f"Backup failed: {result.stderr}", err=True)
                sys.exit(1)
        else:
            click.echo("Backup only supported for PostgreSQL databases", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error creating backup: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('backup_file')
@click.option('--force', is_flag=True, help='Force restore without confirmation')
def restore(backup_file, force):
    """Restore database from backup"""
    app = create_app()
    
    if not os.path.exists(backup_file):
        click.echo(f"Backup file not found: {backup_file}", err=True)
        sys.exit(1)
    
    if not force:
        click.echo("WARNING: This will replace ALL current data!")
        if not click.confirm('Are you sure you want to continue?'):
            return
    
    try:
        # Get database URL components
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        if db_url.startswith('postgresql'):
            # PostgreSQL restore
            import subprocess
            from urllib.parse import urlparse
            
            parsed = urlparse(db_url)
            
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            # Drop existing data
            with app.app_context():
                db.drop_all()
            
            # Restore from backup
            cmd = [
                'psql',
                '-h', parsed.hostname or 'localhost',
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path.lstrip('/'),
                '-f', backup_file,
                '--no-password'
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo(f"Database restored from: {backup_file}")
            else:
                click.echo(f"Restore failed: {result.stderr}", err=True)
                sys.exit(1)
        else:
            click.echo("Restore only supported for PostgreSQL databases", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error restoring backup: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()