from flask import Blueprint
extract_bp = Blueprint('extract', __name__, url_prefix='/extract',
                       template_folder='../templates')
from . import routes
