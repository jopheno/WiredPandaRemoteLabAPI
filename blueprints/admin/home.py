from flask import current_app, request, escape, abort
from blueprints.admin.bp import bp, bp_prefix, localhost


@bp.route('/')
@localhost
def index():
    return "Only localhost users can see this message!"
