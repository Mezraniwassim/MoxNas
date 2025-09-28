#!/usr/bin/env python3
"""Run MoxNAS locally for development and testing"""
import os
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', module='flask_limiter')
warnings.filterwarnings('ignore', module='psycopg2')

# Set local development environment
os.environ['FLASK_CONFIG'] = 'testing'
os.environ['FLASK_ENV'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///local_moxnas.db'
os.environ['WTF_CSRF_ENABLED'] = 'False'
os.environ['REDIS_URL'] = 'memory://'
os.environ['CELERY_BROKER_URL'] = 'memory://'
os.environ['TESTING'] = 'True'
os.environ['SECRET_KEY'] = 'dev-secret-key-for-local-testing'
os.environ['RATELIMIT_ENABLED'] = 'False'

try:
    from app import create_app, db, socketio
    
    app = create_app('testing')
    
    # Import models after app creation to avoid circular imports
    from app.models import User, UserRole, SystemLog, LogLevel
    
    print("🚀 Démarrage de MoxNAS en local...")
    print(f"📍 Base de données: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"🌐 Interface: http://localhost:5000")
    print()
    
    with app.app_context():
        # Create database if it doesn't exist
        db.create_all()
        
        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("👤 Création de l'utilisateur admin...")
            admin_user = User(
                username='admin',
                email='admin@moxnas.local',
                role=UserRole.ADMIN
            )
            admin_user.set_password('AdminPassword123!')
            db.session.add(admin_user)
            
            # Create a regular user too
            regular_user = User(
                username='user',
                email='user@moxnas.local'
            )
            regular_user.set_password('UserPassword123!')
            db.session.add(regular_user)
            
            db.session.commit()
            
            print("✅ Utilisateurs créés:")
            print("   👤 admin / AdminPassword123! (Administrateur)")
            print("   👤 user / UserPassword123! (Utilisateur)")
            
            # Log the startup
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='system',
                message='MoxNAS started in local development mode',
                user_id=admin_user.id
            )
            db.session.commit()
        else:
            print("✅ Utilisateur admin déjà existant")
        
        print()
        print("🎯 Accédez à MoxNAS:")
        print("   🌐 URL: http://localhost:5000")
        print("   👤 Login: admin")
        print("   🔑 Password: AdminPassword123!")
        print()
        print("⚠️  Mode développement - CSRF désactivé")
        print("📊 Base de données SQLite locale")
        print()
        print("🛑 Ctrl+C pour arrêter")
        print("=" * 50)
    
    # Background updates will be started automatically by the websocket module
    
    # Run the enhanced Flask-SocketIO server
    print("🔄 Starting enhanced MoxNAS with real-time features...")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5001,
        debug=True,
        use_reloader=True,
        allow_unsafe_werkzeug=True
    )
    
except KeyboardInterrupt:
    print("\n🛑 Arrêt de MoxNAS")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()