from flask import Blueprint
hide_bp = Blueprint('hide', __name__, url_prefix='/hide',
                    template_folder='../templates')
from . import routes
