#! /usr/local/bin/python3
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from atlassian import Bitbucket
from atlassian.bitbucket.cloud import Cloud

log_file = Path(__file__).parent.parent / "logs/script.log"

logging.basicConfig(filename=str(log_file), encoding="utf-8", level=logging.DEBUG)
LOGGER = logging.getLogger("create_pr")

LOGGER.info(sys.argv)
param_repo = sys.argv[1]
param_type = sys.argv[2]

USERNAME = os.environ.get("VAR_USERNAME")
PASSWORD = os.environ.get("VAR_PASSWORD")
WORKSPACE = os.environ.get("VAR_WORKSPACE")

LOGGER.info("start create_pr, %s", USERNAME)
cloud = Cloud(
    url="https://api.bitbucket.org/",
    username=USERNAME,
    password=PASSWORD,
    cloud=True,
)


def create_batch(repo, name, parent):
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo}/refs/branches"
    res = requests.post(
        url,
        data=json.dumps({"name": name, "target": {"hash": parent}}),
        headers={"Content-Type": "application/json"},
        auth=(USERNAME, PASSWORD),
    )
    print(res.json())


now = datetime.now()
workspace = cloud.workspaces.get(WORKSPACE)
repo = workspace.repositories.get(param_repo)
if param_type == "release":
    branch_name = f"release/{now.strftime('%Y%m%d')}"
    create_batch(param_repo, branch_name, "develop")
    repo.pullrequests.create(
        title=f"Release/{now.strftime('%Y%m%d')}",
        source_branch=branch_name,
        destination_branch="master",
        close_source_branch=True,
    )
elif param_type == "hotfix":
    branch_name = f"hotfix/{now.strftime('%Y%m%d')}"
    create_batch(param_repo, branch_name, "develop")
    repo.pullrequests.create(
        title=f"Hotfix/{now.strftime('%Y%m%d')}",
        source_branch=branch_name,
        destination_branch="master",
        close_source_branch=True,
    )
elif param_type == "dev2sdb":
    LOGGER.info("Start Create PR")
    pr = repo.pullrequests.create(
        title=f"develop-{now.strftime('%Y%m%d')}",
        source_branch="develop",
        destination_branch="sandbox",
        close_source_branch=False,
    )
    pr.merge()
elif param_type == "toSdb":
    src_branch = sys.argv[3]
    pr = repo.pullrequests.create(
        title=f"{src_branch}-to-sandbox-{now.strftime('%Y%m%d')}",
        source_branch=src_branch,
        destination_branch="sandbox",
        close_source_branch=False,
    )
    pr.merge()
