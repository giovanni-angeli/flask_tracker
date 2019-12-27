
from flask import g, current_app
from werkzeug.local import LocalProxy
from flask_tracker.wiki.core import Wiki

def get_wiki():
    wiki = getattr(g, '_wiki', None)
    if wiki is None:
        wiki = g._wiki = Wiki(current_app.config['WIKI_CONTENT_DIR'])
    return wiki

current_wiki = LocalProxy(get_wiki)
