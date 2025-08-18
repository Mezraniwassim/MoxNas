#!/usr/bin/env python3
"""
Final validation script for MoxNAS project completion
Validates project structure, configuration files, and documentation
"""

import os
import json
import sys
from pathlib import Path


def validate_project_structure():
    """Validate that all required project files and directories exist"""
    print("🔍 Validating project structure...")
    
    required_files = [
        'README.md',
        'LICENSE',
        'requirements.txt',
        'backend/manage.py',
        'backend/moxnas/settings.py',
        'frontend/package.json',
        'docker-compose.production.yml',
        'Dockerfile.optimized',
        'scripts/deployment/deploy-moxnas.sh',
        'scripts/run_tests.sh',
        'config/production/settings.py',
        'config/production/.env.example',
    ]
    
    required_dirs = [
        'backend',
        'frontend',
        'config',
        'scripts',
        'docs',
        'services',
        'backend/apps/services',
        'backend/apps/storage',
        'backend/apps/system',
        'backend/templates/services',
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    print("✅ Project structure validation passed")
    return True


def validate_backend_structure():
    """Validate backend Django structure"""
    print("🔍 Validating backend structure...")
    
    backend_apps = [
        'backend/apps/services',
        'backend/apps/storage', 
        'backend/apps/shares',
        'backend/apps/users',
        'backend/apps/network',
        'backend/apps/system'
    ]
    
    required_backend_files = [
        'backend/apps/services/templates.py',
        'backend/apps/services/managers.py',
        'backend/apps/services/views.py',
        'backend/apps/system/health.py',
        'backend/apps/system/metrics.py',
        'backend/templates/services/samba/smb.conf.j2',
        'backend/templates/services/nfs/exports.j2',
        'backend/templates/services/ftp/vsftpd.conf.j2',
    ]
    
    missing = []
    for file_path in required_backend_files:
        if not os.path.exists(file_path):
            missing.append(file_path)
    
    if missing:
        print(f"❌ Missing backend files: {missing}")
        return False
    
    print("✅ Backend structure validation passed")
    return True


def validate_frontend_structure():
    """Validate frontend React structure"""
    print("🔍 Validating frontend structure...")
    
    try:
        with open('frontend/package.json', 'r') as f:
            package_data = json.load(f)
        
        required_deps = ['react', 'react-dom', '@mui/material', 'axios']
        missing_deps = []
        
        dependencies = package_data.get('dependencies', {})
        for dep in required_deps:
            if dep not in dependencies:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Missing frontend dependencies: {missing_deps}")
            return False
        
        required_scripts = ['start', 'build', 'test']
        scripts = package_data.get('scripts', {})
        missing_scripts = []
        
        for script in required_scripts:
            if script not in scripts:
                missing_scripts.append(script)
        
        if missing_scripts:
            print(f"❌ Missing npm scripts: {missing_scripts}")
            return False
        
        print("✅ Frontend structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Frontend validation failed: {e}")
        return False


def validate_service_templates():
    """Validate service template files"""
    print("🔍 Validating service templates...")
    
    template_files = [
        'backend/templates/services/samba/smb.conf.j2',
        'backend/templates/services/nfs/exports.j2', 
        'backend/templates/services/ftp/vsftpd.conf.j2',
        'backend/templates/services/nginx/moxnas.conf.j2',
        'backend/templates/services/systemd/moxnas.service.j2',
    ]
    
    for template_file in template_files:
        if not os.path.exists(template_file):
            print(f"❌ Missing template: {template_file}")
            return False
        
        # Check if template contains Jinja2 syntax
        with open(template_file, 'r') as f:
            content = f.read()
            if '{{' not in content and '{%' not in content:
                print(f"⚠️  Template {template_file} may not contain Jinja2 syntax")
    
    print("✅ Service templates validation passed")
    return True


def validate_docker_configuration():
    """Validate Docker configuration"""
    print("🔍 Validating Docker configuration...")
    
    docker_files = [
        'Dockerfile.optimized',
        'docker-compose.production.yml',
        '.dockerignore'
    ]
    
    for docker_file in docker_files:
        if not os.path.exists(docker_file):
            print(f"❌ Missing Docker file: {docker_file}")
            return False
    
    # Check Dockerfile for multi-stage build
    with open('Dockerfile.optimized', 'r') as f:
        dockerfile_content = f.read()
        if 'FROM' not in dockerfile_content:
            print("❌ Dockerfile appears to be invalid")
            return False
        
        if 'AS production' not in dockerfile_content:
            print("⚠️  Dockerfile may not use multi-stage build")
    
    print("✅ Docker configuration validation passed")
    return True


def validate_deployment_scripts():
    """Validate deployment scripts"""
    print("🔍 Validating deployment scripts...")
    
    script_files = [
        'scripts/deployment/deploy-moxnas.sh',
        'scripts/run_tests.sh'
    ]
    
    for script_file in script_files:
        if not os.path.exists(script_file):
            print(f"❌ Missing script: {script_file}")
            return False
        
        # Check if script is executable
        if not os.access(script_file, os.X_OK):
            print(f"⚠️  Script {script_file} is not executable")
    
    print("✅ Deployment scripts validation passed")
    return True


def validate_configuration_files():
    """Validate configuration files"""
    print("🔍 Validating configuration files...")
    
    config_files = [
        'config/production/settings.py',
        'config/production/.env.example',
        'config/prometheus/prometheus.yml'
    ]
    
    for config_file in config_files:
        if not os.path.exists(config_file):
            print(f"❌ Missing configuration: {config_file}")
            return False
    
    # Check production settings
    with open('config/production/settings.py', 'r') as f:
        settings_content = f.read()
        if 'DEBUG = True' in settings_content:
            print("⚠️  Production settings may have DEBUG=True")
        
        if 'SECRET_KEY' not in settings_content:
            print("❌ Production settings missing SECRET_KEY configuration")
            return False
    
    print("✅ Configuration files validation passed")
    return True


def validate_documentation():
    """Validate documentation completeness"""
    print("🔍 Validating documentation...")
    
    doc_files = [
        'README.md',
        'SERVICE_MANAGEMENT_README.md',
        'TASK6_INTEGRATION_TESTING_SUMMARY.md'
    ]
    
    for doc_file in doc_files:
        if not os.path.exists(doc_file):
            print(f"❌ Missing documentation: {doc_file}")
            return False
        
        # Check if documentation is not empty
        with open(doc_file, 'r') as f:
            content = f.read().strip()
            if len(content) < 100:
                print(f"⚠️  Documentation {doc_file} seems too short")
    
    print("✅ Documentation validation passed")
    return True


def generate_project_summary():
    """Generate a summary of the project"""
    print("\n📊 PROJECT SUMMARY")
    print("=" * 50)
    
    # Count files by type
    python_files = len(list(Path('.').rglob('*.py')))
    js_files = len(list(Path('.').rglob('*.js'))) + len(list(Path('.').rglob('*.jsx')))
    template_files = len(list(Path('.').rglob('*.j2')))
    config_files = len(list(Path('.').rglob('*.yml'))) + len(list(Path('.').rglob('*.yaml'))) + len(list(Path('.').rglob('*.conf')))
    
    print(f"📄 Python files: {python_files}")
    print(f"⚛️  JavaScript/React files: {js_files}")
    print(f"📝 Template files: {template_files}")
    print(f"⚙️  Configuration files: {config_files}")
    
    # Calculate total lines of code (approximate)
    total_lines = 0
    for file_path in Path('.').rglob('*.py'):
        try:
            with open(file_path, 'r') as f:
                total_lines += len(f.readlines())
        except:
            pass
    
    for file_path in Path('.').rglob('*.js'):
        try:
            with open(file_path, 'r') as f:
                total_lines += len(f.readlines())
        except:
            pass
    
    for file_path in Path('.').rglob('*.jsx'):
        try:
            with open(file_path, 'r') as f:
                total_lines += len(f.readlines())
        except:
            pass
    
    print(f"📏 Approximate lines of code: {total_lines:,}")
    
    # Check project size
    total_size = sum(f.stat().st_size for f in Path('.').rglob('*') if f.is_file())
    print(f"💾 Project size: {total_size / 1024 / 1024:.1f} MB")


def main():
    """Run all validation checks"""
    print("🚀 MoxNAS Final Validation")
    print("=" * 50)
    
    validation_checks = [
        validate_project_structure,
        validate_backend_structure,
        validate_frontend_structure,
        validate_service_templates,
        validate_docker_configuration,
        validate_deployment_scripts,
        validate_configuration_files,
        validate_documentation,
    ]
    
    passed = 0
    failed = 0
    
    for check in validation_checks:
        try:
            if check():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Check {check.__name__} failed with error: {e}")
            failed += 1
        print()
    
    generate_project_summary()
    
    print(f"\n📈 VALIDATION RESULTS")
    print("=" * 30)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("🚀 MoxNAS project is ready for release!")
        return 0
    else:
        print(f"\n⚠️  {failed} validation(s) failed")
        print("🔧 Please address the issues above before release")
        return 1


if __name__ == '__main__':
    sys.exit(main())