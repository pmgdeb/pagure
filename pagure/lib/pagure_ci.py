# -*- coding: utf-8 -*-
import os
import flask
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from pagure.hooks import jenkins_hook
from pagure.lib import model
from pagure import APP, SESSION

import json
import logging

import requests
import jenkins

APP.config.from_envvar('INTEGRATOR_SETTINGS', silent=True)
APP.logger.setLevel(logging.INFO)

PAGURE_URL = '{base}api/0/{repo}/pull-request/{pr}/flag'
JENKINS_TRIGGER_URL = '{base}job/{project}/buildWithParameters'


def process_pr(logger, cfg, pr_id, repo, branch):
    post_data(logger,
              JENKINS_TRIGGER_URL.format(
                  base=cfg.jenkins_url, project=cfg.jenkins_name),
              {'token': cfg.jenkins_token,
               'cause': pr_id,
               'REPO': repo,
               'BRANCH': branch})


def process_build(logger, cfg, build_id):
    #  Get details from Jenkins
    jenk = jenkins.Jenkins(cfg.jenkins_url)
    build_info = jenk.get_build_info(cfg.jenkins_name, build_id)
    result = build_info['result']
    url = build_info['url']

    pr_id = None

    for action in build_info['actions']:
        for cause in action.get('causes', []):
            try:
                pr_id = int(cause['note'])
            except (KeyError, ValueError):
                continue

    if not pr_id:
        logger.info('Not a PR check')
        return

    # Comment in Pagure
    logger.info('Updating %s PR %d: %s', cfg.pagure_name, pr_id, result)
    try:
        post_flag(logger, cfg.display_name, APP.config['APP_URL'], cfg.pagure_token,
                  cfg.pagure_name, pr_id, result, url)
    except KeyError as exc:
        logger.warning('Unknown build status', exc_info=exc)


def post_flag(logger, name, base, token, repo, pr, result, url):
    comment, percent = {
        'SUCCESS': ('Build successful', 100),
        'FAILURE': ('Build failed', 0),
    }[result]
    payload = {
        'username': name,
        'percent': percent,
        'comment': comment,
        'url': url,
    }
    post_data(logger, PAGURE_URL.format(base=base, repo=repo, pr=pr), payload,
              headers={'Authorization': 'token ' + token})


def post_data(logger, *args, **kwargs):
    resp = requests.post(*args, **kwargs)
    logger.debug('Received response status %s', resp.status_code)
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.error('Network request failed: %d: %s',
                     resp.status_code, resp.text)
