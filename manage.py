
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env.local')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, db
from app.models import User, StoragePool, StorageDevice, Dataset, Share, BackupJob, SystemLog, Alert
from flask_migrate import Migrate
from flask.cli import FlaskGroup

app = create_app(os.getenv('FLASK_ENV') or 'default')
migrate = Migrate(app, db)

cli = FlaskGroup(create_app=lambda: app)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, StoragePool=StoragePool, StorageDevice=StorageDevice,
                Dataset=Dataset, Share=Share, BackupJob=BackupJob, SystemLog=SystemLog,
                Alert=Alert)

@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

if __name__ == '__main__':
    cli()
