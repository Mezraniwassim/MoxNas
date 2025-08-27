#!/usr/bin/env python3
"""Test local MoxNAS without database dependencies"""
import os
import sys
import warnings

# Suppress warnings
warnings.filterwarnings('ignore', module='flask_limiter')
warnings.filterwarnings('ignore', module='psycopg2')

# Set test environment
os.environ['FLASK_CONFIG'] = 'testing'
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['WTF_CSRF_ENABLED'] = 'False'
os.environ['REDIS_URL'] = 'memory://'
os.environ['CELERY_BROKER_URL'] = 'memory://'
os.environ['TESTING'] = 'True'

try:
    from app import create_app, db
    
    app = create_app('testing')
    
    print("🔧 Configuration de test:")
    print(f"   Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
    print(f"   Redis: {app.config.get('REDIS_URL', 'Not set')}")
    print(f"   Environment: {app.config.get('FLASK_ENV', 'Not set')}")
    print()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Base de données créée avec succès!")
            
            # Get table info
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ {len(tables)} tables créées")
            
            # Test basic models
            from app.models import User, SystemLog, LogLevel
            
            # Create test user
            test_user = User(
                username='testuser',
                email='test@moxnas.local',
                first_name='Test',
                last_name='User'
            )
            test_user.set_password('testpass123')
            db.session.add(test_user)
            db.session.commit()
            
            print("✅ Utilisateur de test créé")
            
            # Test logging
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='test',
                message='Test log entry',
                user_id=test_user.id
            )
            db.session.commit()
            
            print("✅ Système de logs fonctionnel")
            
            print()
            print("🎉 SUCCÈS! MoxNAS fonctionne en local")
            print("📱 L'application est prête pour:")
            print("   • Tests de développement")
            print("   • Déploiement Proxmox")
            print("   • Tests d'intégration")
            print()
            print("📋 Pour démarrer l'app:")
            print("   source venv/bin/activate")
            print("   export FLASK_APP=test_local.py")
            print("   flask run --debug")
            
        except Exception as e:
            print(f"❌ Erreur base de données: {e}")
            sys.exit(1)
            
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("💡 Vérifiez que les dépendances sont installées:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Erreur générale: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)