from flask import Blueprint, send_from_directory, current_app, escape, abort
from __main__ import get_bs
from werkzeug.utils import secure_filename

bp = Blueprint('download', __name__)

@bp.route('/download')
def download():
    version = ''

    bs = get_bs()
    with bs:
        major, minor = bs.get_version()
        version = 'v' + str(major) + '_' + str(minor)

    # secures filename    
    version = escape(version)
    version = secure_filename(version)

    try:
        return send_from_directory(directory=current_app.config['UPLOAD_FOLDER'], filename=(version + '.zip'))
    except FileNotFoundError:
        abort(404)
