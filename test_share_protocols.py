#!/usr/bin/env python3
"""
Test different sharing protocols (SMB/CIFS and FTP)
"""
import os
import sys
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Share, Dataset, User, ShareProtocol, ShareStatus
from app.shares.protocols import smb_manager, ftp_manager

def run_command(cmd):
    """Run command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except:
        return False, "", "Command failed"

def test_share_protocols():
    """Test SMB and FTP sharing protocols"""
    # Force SQLite database for local development
    os.environ['DATABASE_URL'] = 'sqlite:///local_moxnas.db'
    os.environ['FLASK_ENV'] = 'development'
    
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing Share Protocols")
        print("=" * 40)
        
        # Get the existing dataset
        dataset = Dataset.query.filter_by(name='www').first()
        user = User.query.first()
        
        if not dataset or not user:
            print("❌ No dataset or user found")
            return
        
        print(f"✅ Using dataset: {dataset.name} ({dataset.path})")
        print(f"✅ Using user: {user.username}")
        
        # Test SMB/CIFS Protocol
        print("\n📁 TESTING SMB/CIFS PROTOCOL")
        print("-" * 30)
        
        # Check SMB service
        success, stdout, stderr = run_command("systemctl is-active smbd")
        if success and 'active' in stdout:
            print("✅ SMB service is running")
            
            # Create SMB share
            try:
                smb_share = Share(
                    name="smb-test-share",
                    dataset_id=dataset.id,
                    protocol=ShareProtocol.SMB,
                    status=ShareStatus.ACTIVE,
                    read_only=False,
                    guest_access=True,
                    owner_id=user.id
                )
                
                # Test SMB share creation
                success, message = smb_manager.create_smb_share(smb_share)
                if success:
                    print(f"✅ SMB share creation: {message}")
                    
                    # Add to database
                    db.session.add(smb_share)
                    db.session.commit()
                    print("✅ SMB share added to database")
                    
                    # Test SMB configuration
                    config_path = smb_manager.get_config_path('smb')
                    print(f"📄 SMB config file: {config_path}")
                    
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            content = f.read()
                            if smb_share.name in content:
                                print("✅ SMB share found in config file")
                            else:
                                print("⚠️ SMB share not found in config file")
                    else:
                        print("📝 SMB config file doesn't exist yet (will be created)")
                        
                else:
                    print(f"❌ SMB share creation failed: {message}")
                    
            except Exception as e:
                print(f"❌ SMB test error: {e}")
        else:
            print(f"⚠️ SMB service not active: {stdout} {stderr}")
        
        # Test SMB access
        print("\n🔍 Testing SMB Access...")
        success, stdout, stderr = run_command("smbclient -L localhost -N")
        if success:
            print("✅ SMB server is accessible")
            if "smb-test-share" in stdout:
                print("✅ SMB share is visible")
            else:
                print("📋 Available SMB shares:")
                for line in stdout.split('\\n'):
                    if 'Disk' in line or 'IPC' in line:
                        print(f"   {line}")
        else:
            print(f"⚠️ SMB access test failed: {stderr}")
        
        # Test FTP Protocol
        print("\n📡 TESTING FTP PROTOCOL")
        print("-" * 20)
        
        # Check FTP service
        success, stdout, stderr = run_command("systemctl is-active vsftpd")
        if success and 'active' in stdout:
            print("✅ FTP service is running")
        else:
            print("⚠️ FTP service is not active, attempting to start...")
            success, stdout, stderr = run_command("sudo systemctl start vsftpd")
            if success:
                print("✅ FTP service started")
            else:
                print(f"❌ Failed to start FTP service: {stderr}")
                print("ℹ️ Testing FTP functionality anyway (development mode)")
        
        # Create FTP share
        try:
            ftp_share = Share(
                name="ftp-test-share",
                dataset_id=dataset.id,
                protocol=ShareProtocol.FTP,
                status=ShareStatus.ACTIVE,
                read_only=False,
                guest_access=True,
                owner_id=user.id
            )
            
            # Test FTP share creation
            success, message = ftp_manager.create_ftp_share(ftp_share)
            if success:
                print(f"✅ FTP share creation: {message}")
                
                # Add to database
                db.session.add(ftp_share)
                db.session.commit()
                print("✅ FTP share added to database")
                
                # Check FTP share directory
                ftp_config_dir = ftp_manager.get_config_path('ftp').replace('/vsftpd.conf', '/ftp_shares')
                print(f"📁 FTP shares directory: {ftp_config_dir}")
                
                if os.path.exists(ftp_config_dir):
                    ftp_share_path = os.path.join(ftp_config_dir, ftp_share.name)
                    if os.path.exists(ftp_share_path):
                        print(f"✅ FTP share link created: {ftp_share_path}")
                        # Check if it's a symlink to our dataset
                        if os.path.islink(ftp_share_path):
                            target = os.readlink(ftp_share_path)
                            print(f"🔗 FTP share links to: {target}")
                            if target == dataset.path:
                                print("✅ FTP share correctly links to dataset")
                            else:
                                print("⚠️ FTP share links to different path")
                    else:
                        print("⚠️ FTP share link not found")
                else:
                    print("📝 FTP shares directory doesn't exist yet")
                    
            else:
                print(f"❌ FTP share creation failed: {message}")
                
        except Exception as e:
            print(f"❌ FTP test error: {e}")
        
        # Summary
        print("\n📊 PROTOCOL TEST SUMMARY")
        print("=" * 30)
        
        shares = Share.query.all()
        print(f"📈 Total shares created: {len(shares)}")
        
        for share in shares:
            print(f"   {share.protocol.value.upper()}: {share.name} ({share.status.value})")
        
        print("\n🔧 Access Information:")
        print("📁 NFS: nfs://192.168.1.109/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www")
        print("🖥️ SMB: smb://192.168.1.109/smb-test-share")
        print("📡 FTP: ftp://192.168.1.109/ (look for ftp-test-share directory)")
        
        print("\n✅ Protocol testing completed!")

if __name__ == '__main__':
    test_share_protocols()