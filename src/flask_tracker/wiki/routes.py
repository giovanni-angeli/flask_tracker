# coding: utf-8

import logging

from flask import (Blueprint, flash, redirect, render_template, request, url_for, current_app)
from flask_login import current_user

from flask_tracker.admin import protect

from flask_tracker.wiki.core import Processor
from flask_tracker.wiki.forms import (EditorForm, SearchForm, URLForm)
from flask_tracker.wiki import current_wiki


bp = Blueprint('wiki', __name__)

@bp.route('/')
@protect
def home():
    page = current_wiki.get('home')
    if page:
        return display('home')
    return render_template('home.html')


@bp.route('/index/')
@protect
def index():
    pages = current_wiki.index()
    return render_template('index.html', pages=pages)


@bp.route('/<path:url>/')
@protect
def display(url):
    page = current_wiki.get_or_404(url)
    return render_template('page.html', page=page)


@bp.route('/clone/<path:url>/', methods=['GET', 'POST'])
@protect
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
@protect
def create():
    form = URLForm()
    if form.validate_on_submit():
        return redirect(url_for(
            'wiki.edit', url=form.clean_url(form.url.data)))
    return render_template('create.html', form=form)


@bp.route('/edit/<path:url>/', methods=['GET', 'POST'])
@protect
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
@protect
def preview():
    data = {}
    processor = Processor(request.form['body'])
    data['html'], data['body'], data['meta'] = processor.process()
    return data['html']


@bp.route('/rename/<path:url>/', methods=['GET', 'POST'])
@protect
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
@protect
def delete(url):
    page = current_wiki.get_or_404(url)
    current_wiki.delete(url)
    flash('Page "%s" was deleted.' % page.title, 'success')
    return redirect(url_for('wiki.home'))


@bp.route('/tags/')
@protect
def tags():
    tags = current_wiki.get_tags()
    return render_template('tags.html', tags=tags)


@bp.route('/tag/<string:name>/')
@protect
def tag(name):
    tagged = current_wiki.index_by_tag(name)
    return render_template('tag.html', pages=tagged, tag=name)


@bp.route('/search/', methods=['GET', 'POST'])
@protect
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

