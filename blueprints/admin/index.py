from flask import current_app, request, escape, abort, session, render_template, redirect, url_for
from blueprints.admin.bp import bp, bp_prefix, localhost, must_be_logged_in
from __main__ import get_bs
import hashlib
import logging
import config


@bp.route('/')
#@localhost
def index():
    if 'user_token' not in session:
        return redirect(url_for('admin.login'))

    return redirect(url_for('admin.home'))

@bp.route('/logout')
@must_be_logged_in
#@localhost
def logout():

    bs = get_bs()
    with bs:
        bs.log_out(session['user_token'], None)

    session.pop('user_token')
    return redirect(url_for('admin.login'))

@bp.route('/login', methods=["GET", "POST"])
#@localhost
def login():
    if request.method == 'GET':
        if 'user_token' in session:
            return redirect(url_for('admin.home'))

        return render_template('admin/login.html')

    # only localhost can access admin login page, so
    # there is no need for front-end to encrypt password
    login = str(escape(request.values.get('login', '')))
    passwd = str(escape(request.values.get('passwd', '')))

    conf = config.get()

    hash_passwd = passwd

    if conf['DOMAIN']['AUTH_METHOD'] == 'MD5':
        hash_passwd = hashlib.md5(passwd.encode()).digest().hex()
    
    if conf['DOMAIN']['AUTH_METHOD'] == 'SHA256':
        hash_passwd = hashlib.sha256(passwd.encode()).digest().hex()

    hashed_passwd = hashlib.md5(passwd.encode()).digest().hex()
    
    logging.info("Administrator trying to log in with ({0}, {1})".format(login, hashed_passwd))

    user_token = None

    bs = get_bs()
    with bs:
        user_token = bs.log_in(login, hashed_passwd)

        if user_token is not None:
            if bs.is_admin(user_token):
                session['user_token'] = user_token
            
                return redirect(url_for('admin.home'))
            else:
                return "You are not authorized to use the administration panel", 401
    
    return "Invalid username or password", 401
