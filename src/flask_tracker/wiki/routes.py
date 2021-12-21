# coding: utf-8

import logging

from flask import (Blueprint, flash, redirect, render_template, request, url_for, current_app)
from flask_login import current_user

from flask_tracker.admin import check_login

from flask_tracker.wiki.core import Processor
from flask_tracker.wiki.forms import (EditorForm, SearchForm, URLForm)
from flask_tracker.wiki import current_wiki


bp = Blueprint('wiki', __name__)

@bp.route('/')
@check_login
def home():
    page = current_wiki.get('home')
    if page:
        return display('home')
    return render_template('home.html')


@bp.route('/index/')
@check_login
def index():
    cntr = 0
    limit = 100 
    pages = []
    for p in current_wiki.index():
        pages.append(p)
        cntr += 1
        if cntr > limit:
            break

    pages.sort(key=lambda x: x.title.lower())

    return render_template('index.html', pages=pages)


@bp.route('/<path:url>/')
@check_login
def display(url):
    page = current_wiki.get_or_404(url)
    return render_template('page.html', page=page)


@bp.route('/clone/<path:url>/', methods=['GET', 'POST'])
@check_login
def clone(url):

    page = current_wiki.get_or_404(url)
    page.url += "-clone"
    form = URLForm(obj=page)
    if form.validate_on_submit():
        newurl = form.url.data
        current_wiki.clone(url, newurl)
        msg = '"%s" was cloned to "%s".' % (url, newurl)
        flash(msg, 'success')
        return redirect(url_for('wiki.display', url=newurl))
    return render_template('clone.html', form=form, page=page)


@bp.route('/create/', methods=['GET', 'POST'])
@check_login
def create():
    form = URLForm()
    if form.validate_on_submit():
        return redirect(url_for(
            'wiki.edit', url=form.clean_url(form.url.data)))
    return render_template('create.html', form=form)


@bp.route('/edit/<path:url>/', methods=['GET', 'POST'])
@check_login
def edit(url):
    page = current_wiki.get(url)
    form = EditorForm(obj=page)
    if form.validate_on_submit():
        if not page:
            page = current_wiki.get_bare(url)
        form.populate_obj(page)
        page.save()
        flash('"%s" was saved.' % page.title, 'success')
        return redirect(url_for('wiki.display', url=url))
    return render_template('editor.html', form=form, page=page)


@bp.route('/preview/', methods=['POST'])
@check_login
def preview():
    data = {}
    processor = Processor(request.form['body'])
    data['html'], data['body'], data['meta'] = processor.process()
    return data['html']


@bp.route('/rename/<path:url>/', methods=['GET', 'POST'])
@check_login
def rename(url):
    page = current_wiki.get_or_404(url)
    form = URLForm(obj=page)
    if form.validate_on_submit():
        newurl = form.url.data
        current_wiki.rename(url, newurl)
        flash('"%s" was renamed to "%s".' % (page.title, newurl), 'success')
        return redirect(url_for('wiki.display', url=newurl))
    return render_template('rename.html', form=form, page=page)


@bp.route('/delete/<path:url>/')
@check_login
def delete(url):
    page = current_wiki.get_or_404(url)
    current_wiki.delete(url)
    flash('Page "%s" was deleted.' % page.title, 'success')
    return redirect(url_for('wiki.home'))


@bp.route('/tags/')
@check_login
def tags():
    tags = current_wiki.get_tags()
    return render_template('tags.html', tags=tags)


@bp.route('/tag/<string:name>/')
@check_login
def tag(name):

    tagged = [p for p in current_wiki.index_by_tag(name)]
    tagged = sorted(tagged, key=lambda x: x.get('title', '').lower())
    return render_template('tag.html', pages=tagged, tag=name)


@bp.route('/search/', methods=['GET', 'POST'])
@check_login
def search():
    form = SearchForm()
    if form.validate_on_submit():
        results = current_wiki.search(form.term.data, form.ignore_case.data)
        return render_template('search.html', form=form,
                               results=results, search=form.term.data)
    return render_template('search.html', form=form, search=None)

@bp.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

