from flask import Blueprint
history_bp = Blueprint('history', __name__, url_prefix='/history',
                       template_folder='../templates')
from . import routes
