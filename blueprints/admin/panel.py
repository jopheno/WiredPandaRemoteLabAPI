from flask import current_app, request, escape, abort, session, render_template, redirect, url_for, send_from_directory
from blueprints.admin.bp import bp, bp_prefix, localhost, must_be_logged_in
from werkzeug.utils import secure_filename
from __main__ import get_bs
import datetime
import hashlib
import logging
import config
import os


def get_usb_devices():
    results = []

    for line in os.popen('./integration/get_usb_devices.sh').read().splitlines():
        splitted = line.split(' - ')
        results.append({
            'name': splitted[1],
            'path': splitted[0]
        })

    return results

@bp.route('/home')
@must_be_logged_in
#@localhost
def home():
    return render_template('admin/home.html', current_page = 'home')

@bp.route('/settings')
@must_be_logged_in
#@localhost
def settings():
    conf = config.get()

    return render_template('admin/settings.html', current_page = 'settings', config = conf)

@bp.route('/device_types', methods=["GET", "DELETE", "PATCH", "PUT"])
@must_be_logged_in
#@localhost
def device_types():
    if request.method == "GET":
        result = []
    
        bs = get_bs()
        with bs:
            result = bs.get_device_type_info()

        return render_template('admin/device_types.html', current_page = 'device_types', device_types = result)

    if request.method == "DELETE":
        id = int(escape(request.values.get('id', '0')))

        if id == 0:
            return "", 202

        bs = get_bs()
        with bs:
            bs.remove_device_type(id)
        
        return "", 200

    id = int(escape(request.values.get('id', '0')))
    name = str(escape(request.values.get('name', '')))
    description = str(escape(request.values.get('description', '')))
    allowed_time = int(escape(request.values.get('allowed_time', '')))

    if request.method == "PUT":
        bs = get_bs()
        with bs:
            bs.add_device_type(name, description, allowed_time)
        
        return "", 201

    if request.method == "PATCH":
        new_name = None
        new_description = None
        new_allowed_time = None

        if name != '%':
            new_name = name
        
        if description != '%':
            new_description = description
        
        if allowed_time != '%':
            new_allowed_time = allowed_time

        bs = get_bs()
        with bs:
            bs.set_device_type_name(id, new_name)
            bs.set_device_type_description(id, new_description)
            bs.set_device_type_allowed_time(id, new_allowed_time)
            bs.save_device_type_config()
        
        return "", 200

@bp.route('/device_methods', methods=["GET", "DELETE", "PATCH", "PUT"])
@must_be_logged_in
#@localhost
def device_methods():
    if request.method == "GET":
        result = []
    
        bs = get_bs()
        with bs:
            result = bs.get_device_methods_info()

        return render_template('admin/methods.html', current_page = 'methods', device_methods = result)

    if request.method == "DELETE":
        id = int(escape(request.values.get('id', '0')))

        if id == 0:
            return "", 202

        bs = get_bs()
        with bs:
            bs.remove_device_method(id)
        
        return "", 200

    id = int(escape(request.values.get('id', '0')))
    name = str(escape(request.values.get('name', '')))
    latency = int(escape(request.values.get('latency', '')))

    if request.method == "PUT":
        bs = get_bs()
        with bs:
            bs.add_device_method(name, latency)
        
        return "", 201

    if request.method == "PATCH":
        new_name = None
        new_latency = None

        if name != '%':
            new_name = name
        
        if latency != '%':
            new_latency = latency

        bs = get_bs()
        with bs:
            bs.set_device_method_name(id, new_name)
            bs.set_device_method_latency(id, new_latency)
            bs.save_device_method_config()
        
        return "", 200

@bp.route('/devices')
@must_be_logged_in
#@localhost
def devices():
    result = []
    methods = {}
    device_types = {}

    bs = get_bs()
    with bs:
        result = bs.get_devices_full_info()
        methods = bs.get_all_methods()
        device_types = bs.get_devices()
    
    usb_devices = get_usb_devices()
    

    return render_template('admin/devices.html',
        current_page = 'devices',
        devices = result,
        usb_devices = usb_devices,
        methods = methods,
        device_types = device_types,
    )

@bp.route('/users', methods=['GET', 'PATCH'])
@must_be_logged_in
#@localhost
def users():
    if request.method == "PATCH":
        id = int(escape(request.values.get('id', '0')))
        access_level = int(escape(request.values.get('access_level', '0')))

        if id == 0 or access_level == 0:
            return "Unable to change user access_level", 400

        bs = get_bs()
        with bs:
            bs.update_user_access(id, access_level)
        
        return "Success", 200

    bs = get_bs()
    with bs:
        users = bs.get_users()
    
    for user in users:
        user['created'] = datetime.datetime.fromtimestamp(user['created'])
        user['last_logged_in'] = datetime.datetime.fromtimestamp(user['last_logged_in'])

    return render_template('admin/users.html', current_page = 'users', users = users)

@bp.route('/logs')
@must_be_logged_in
#@localhost
def logs():
    return render_template('admin/logs.html', current_page = 'logs')

@bp.route('/get_logs')
@must_be_logged_in
#@localhost
def get_logs():

    value = ''
    for line in os.popen('./integration/get_logs.sh').read().splitlines():
        value = value + line + '<br>'

    return value

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['png', 'zip']

@bp.route('/uploads', methods=['GET', 'POST', 'DELETE'])
@must_be_logged_in
#@localhost
def upload_file():
    if request.method == 'POST':
        filetype = str(escape(request.values.get('filetype', 'download')))
        print(filetype)
        # check if the post request has the file part
        if 'file' not in request.files:
            print('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            print('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            if filename == 'logo.png' and filetype != 'logo':
                return "Sorry, you cannot upload a download file with this name."

            if filetype == 'method':
                target_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'methods')
            else:
                target_folder = current_app.config['UPLOAD_FOLDER']

            if filetype == 'logo':
                if filename[-4:] != '.png':
                    return "The logo must be a '.png' file"

                filename = 'logo.png'

            file.save(os.path.join(target_folder, filename))

            return "File uploaded successfully!"
    
    if request.method == 'DELETE':
        filename = str(escape(request.values.get('filename', '')))

        additional_path = ''
        if filename.find('method_') != -1:
            filename = filename.split('method_')[1]
            additional_path = 'methods'

        path = os.path.join(current_app.config['UPLOAD_FOLDER'], additional_path)

        if os.path.exists(os.path.join(path, filename)):
            os.remove(os.path.join(path, filename))
        else:
            print("The file does not exist")

    from os import listdir
    from os.path import isfile, join

    files = []
    directories = [current_app.config['UPLOAD_FOLDER'], join(current_app.config['UPLOAD_FOLDER'], 'methods')]
    for dir in directories:
        for f in listdir(dir):
            if isfile(join(dir, f)):
                files.append({
                    "name": f,
                    "path": join(dir, f),
                    "size": None
                })

    for file in files:
        if file['size'] is None:
            file['size'] = str(int(os.path.getsize(file['path']) / 1024)) + ' KB'

    return render_template('admin/uploads.html', current_page = 'uploads', files = files)

@bp.route('/download/<filename>')
@must_be_logged_in
#@localhost
def download(filename):
    additional_path = ''
    if filename.find('method_') != -1:
        filename = filename.split('method_')[1]
        additional_path = 'methods'

    try:
        return send_from_directory(directory=os.path.join(current_app.config['UPLOAD_FOLDER'], additional_path), filename=filename)
    except FileNotFoundError:
        abort(404)
