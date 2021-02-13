from flask import current_app, request, escape, abort, render_template
from blueprints.home.bp import bp, bp_prefix
import os


@bp.route('/')
def index():
    curr_dir = os.path.dirname(__file__)
    md_dir = os.path.join(curr_dir, "markdowns")
    md_files = [file for file in os.listdir(md_dir) if not os.path.isdir(os.path.join(md_dir, file))]

    data = []

    index = 1
    for md_file in sorted(md_files):
        try:
            f = open(os.path.join(md_dir, md_file), "r")
            content_type = ("markdown" if md_file.endswith('.md') else "html")
            # removes '.md' or '.html' from title
            title = (md_file[:-3] if content_type == 'markdown' else md_file[:-5])
            data.append({
                "index": index,
                "title": title,
                "type": content_type,
                "content": f.read()
            })

            index = index + 1
        except FileNotFoundError:
            pass

    return render_template('home/index.html', sections=data)
