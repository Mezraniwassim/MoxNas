
import os
import sys
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from alembic.config import Config
from alembic import command

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env.local')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Run the migrations
if __name__ == '__main__':
    with app.app_context():
        alembic_cfg = Config("migrations/alembic.ini")
        command.upgrade(alembic_cfg, "head")
