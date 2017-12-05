# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Clement Verna <cverna@tutanota.com>

"""
import flask
from functools import wraps


def has_issue_tracker(function):
    """
    Decorator that checks if the current pagure project has the
    issue tracker active
    If not active returns a 404 page
    """
    @wraps(function)
    def check_issue_tracker(*args, **kwargs):
        repo = flask.g.repo
        if not repo.settings.get('issue_tracker', True):
            flask.abort(404, 'No issue tracker found for this project')
        return function(*args, **kwargs)

    return check_issue_tracker


def is_repo_admin(function):
    """
    Decorator that checks if the current user is the admin of
    the project.
    If not active returns a 403 page
    """
    @wraps(function)
    def check_repo_admin(*args, **kwargs):
        if not flask.g.repo_admin:
            flask.abort(403, 'You are not allowed to change the \
                        settings for this project')
        return function(*args, **kwargs)
    return check_repo_admin
