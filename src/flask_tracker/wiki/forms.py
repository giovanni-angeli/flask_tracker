# coding: utf-8

from flask_wtf import FlaskForm

from wtforms import (BooleanField, TextField, TextAreaField)
from wtforms.validators import (InputRequired, ValidationError)

from flask_tracker.wiki.core import clean_url
from flask_tracker.wiki import current_wiki


class URLForm(FlaskForm):
    url = TextField('', [InputRequired()])

    def validate_url(form, field):
        if current_wiki.exists(field.data):
            raise ValidationError('The URL "%s" exists already.' % field.data)

    def clean_url(self, url):
        return clean_url(url)


class SearchForm(FlaskForm):
    term = TextField('', [InputRequired()])
    ignore_case = BooleanField(
        description='Ignore Case',
        # FIXME: default is not correctly populated
        default=True)


class EditorForm(FlaskForm):
    title = TextField('', [InputRequired()])
    body = TextAreaField('', [InputRequired()])
    tags = TextField('')
