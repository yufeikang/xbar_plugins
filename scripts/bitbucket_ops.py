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
LOGGER = logging.getLogger("bitbucket script")

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


def _get_reviews():
    ids = os.environ.get("VAR_REVIEWERS")
    if ids is None:
        LOGGER.error("Missing Reviews ID (UUID)")
        sys.exit(-1)
    return [{"uuid": uuid} for uuid in ids.split(",")]


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
    pr = repo.pullrequests.create(
        title=f"Release/{now.strftime('%Y%m%d')}",
        source_branch=branch_name,
        destination_branch="master",
        close_source_branch=True,
    )
    LOGGER.info("Release PullRequest Created, %s", pr.get_link("html"))


def hotfix_pr():
    branch_name = f"hotfix/{now.strftime('%Y%m%d')}"
    _create_branch(
        params["repo_name"], branch_name, params.get("source_branch", "develop")
    )
    pr = repo.pullrequests.create(
        title=f"Hotfix/{now.strftime('%Y%m%d')}",
        source_branch=branch_name,
        destination_branch="master",
        close_source_branch=True,
    )
    LOGGER.info("Hotfix PullRequest Created, %s", pr.get_link("html"))


def merge_sandbox():
    pr = repo.pullrequests.create(
        title=f"sandbox-{now.strftime('%Y%m%d')}",
        source_branch=params.get("source_branch", "develop"),
        destination_branch="sandbox",
        close_source_branch=False,
    )
    pr.merge()
    LOGGER.info("Merge Sandbox Success, %s", pr.get_link("html"))


def develop_pr():
    pr = repo.pullrequests.create(
        title=params.get("source_branch", f"develop-{now.strftime('%Y%m%d')}"),
        source_branch=params.get("source_branch"),
        destination_branch="develop",
        close_source_branch=params.get("close_source_branch", False),
    )
    if params.get("merge", False):
        pr.merge()
    LOGGER.info("Develop PullRequest Created, %s", pr.get_link("html"))


def delete_branch():
    source_branch = params.get("source_branch")
    _delete_branch(params["repo_name"], source_branch)


def merge_pr():
    pr_id = params.get("pr_id")
    pr = next(repo.pullrequests.each(q=f"id={pr_id}"))
    pr.merge()
    LOGGER.info("PullRequest Merge Success, %s", pr.get_link("html"))


def decline_pr():
    pr_id = params.get("pr_id")
    pr = next(repo.pullrequests.each(q=f"id={pr_id}"))
    pr.decline()
    LOGGER.info("PullRequest Decline Success")


def pr_add_review():
    pr_id = params.get("pr_id")
    pr = next(repo.pullrequests.each(q=f"id={pr_id}"))
    pr.put(
        None,
        data={
            "title": pr.title,
            "reviewers": _get_reviews(),
        },
    )
    LOGGER.info("PullRequest Review Add Success, %s", pr.get_link("html"))


globals()[params["fun"]]()
