"""Network Shares Blueprint"""
from flask import Blueprint

bp = Blueprint("shares", __name__)

from app.shares import routes, protocols
