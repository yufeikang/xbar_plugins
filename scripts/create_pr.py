#! /usr/local/bin/python3
import json
import logging
import os
import sys
from base64 import b64decode
from datetime import datetime
from pathlib import Path

import requests
from atlassian import Bitbucket
from atlassian.bitbucket.cloud import Cloud

log_file = Path(__file__).parent.parent / "logs/script.log"

logging.basicConfig(stream=sys.stdout, encoding="utf-8", level=logging.INFO)
LOGGER = logging.getLogger("create_pr")

LOGGER.info(sys.argv)

USERNAME = os.environ.get("VAR_USERNAME")
PASSWORD = os.environ.get("VAR_PASSWORD")
WORKSPACE = os.environ.get("VAR_WORKSPACE")

LOGGER.info("start create_pr, %s", USERNAME)


def decode_params():
    params = sys.argv[1]
    return json.loads(b64decode(params.encode("utf-8")))


cloud = Cloud(
    url="https://api.bitbucket.org/",
    username=USERNAME,
    password=PASSWORD,
    cloud=True,
)


def _create_branch(repo, name, parent):
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo}/refs/branches"
    res = requests.post(
        url,
        data=json.dumps({"name": name, "target": {"hash": parent}}),
        headers={"Content-Type": "application/json"},
        auth=(USERNAME, PASSWORD),
    )
    print(res.json())


def _delete_branch(repo, name):
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo}/refs/branches/{name}"
    requests.delete(
        url,
        auth=(USERNAME, PASSWORD),
    )
    LOGGER.info("delete branch OK")


params = decode_params()

LOGGER.info(params)


now = datetime.now()
workspace = cloud.workspaces.get(WORKSPACE)
repo = workspace.repositories.get(params["repo_name"])


def release_pr():
    branch_name = f"release/{now.strftime('%Y%m%d')}"
    _create_branch(
        params["repo_name"], branch_name, params.get("source_branch", "develop")
    )
    repo.pullrequests.create(
        title=f"Release/{now.strftime('%Y%m%d')}",
        source_branch=branch_name,
        destination_branch="master",
        close_source_branch=True,
    )


def hotfix_pr():
    branch_name = f"hotfix/{now.strftime('%Y%m%d')}"
    _create_branch(
        params["repo_name"], branch_name, params.get("source_branch", "develop")
    )
    repo.pullrequests.create(
        title=f"Hotfix/{now.strftime('%Y%m%d')}",
        source_branch=branch_name,
        destination_branch="master",
        close_source_branch=True,
    )


def merge_sandbox():
    pr = repo.pullrequests.create(
        title=f"sandbox-{now.strftime('%Y%m%d')}",
        source_branch=params.get("source_branch", "develop"),
        destination_branch="sandbox",
        close_source_branch=False,
    )
    pr.merge()


def develop_pr():
    pr = repo.pullrequests.create(
        title=f"develop-{now.strftime('%Y%m%d')}",
        source_branch=params.get("source_branch"),
        destination_branch="develop",
        close_source_branch=params.get("close_source_branch", False),
    )
    if params.get("merge", False):
        pr.merge()


def delete_branch():
    source_branch = params.get("source_branch")
    _delete_branch(params["repo_name"], source_branch)


globals()[params["fun"]]()
