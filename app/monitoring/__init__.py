"""Monitoring Blueprint"""
from flask import Blueprint

bp = Blueprint('monitoring', __name__)

from app.monitoring import routes