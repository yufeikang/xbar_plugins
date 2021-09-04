#! /usr/local/bin/python3
# Metadata allows your plugin to show up in the app, and website.
#
#  <xbar.title>Pipline Title</xbar.title>
#  <xbar.version>v1.0</xbar.version>
#  <xbar.author>yufei kang</xbar.author>
#  <xbar.author.github>yufeikang</xbar.author.github>
#  <xbar.desc>List Bitbucket Pipeline Status</xbar.desc>
# Variables become preferences in the app:
#
#  <xbar.var>string(VAR_USERNAME="username"): Username.</xbar.var>
#  <xbar.var>string(VAR_PASSWORD="password"): App Password.</xbar.var>
#  <xbar.var>string(VAR_WORKSPACE=""): Your WORKSPACE.</xbar.var>
#%%
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from atlassian import Bitbucket
from atlassian.bitbucket.cloud import Cloud
from pytz import timezone

print("PR")
print("---")
print("Refresh | refresh=true")

logging.basicConfig(filename="./logs/pr.log", encoding="utf-8", level=logging.INFO)
LOGGER = logging.getLogger()


USERNAME = os.environ.get("VAR_USERNAME")
PASSWORD = os.environ.get("VAR_PASSWORD")
WORKSPACE = os.environ.get("VAR_WORKSPACE")

curdir = Path(__file__).parent


jst = timezone("Asia/Tokyo")


def humanize_date(date, fmt="%Y/%m/%d %H:%M:%S"):
    return date.astimezone(jst).strftime(fmt)


if USERNAME is None or PASSWORD is None or WORKSPACE is None:
    print("Setup VAR")
    sys.exit(0)

cloud = Cloud(
    url="https://api.bitbucket.org/",
    username=USERNAME,
    password=PASSWORD,
    cloud=True,
)


def is_me_color(pr):
    if pr.author.nickname == "yufei.kang":
        return "#2A63F6"
    return "#09F4F7FB"


# %%
workspace = cloud.workspaces.get(WORKSPACE)

data = []

now = datetime.utcnow().replace(tzinfo=pytz.utc)
# https://github.dev/atlassian-api/atlassian-python-api
for repo in workspace.repositories.each(sort="-updated_on"):
    if repo.get_time("updated_on") < now - timedelta(days=7):
        continue
    # print(repo.name)
    pullrequests = repo.pullrequests.each(sort="-created_on", q='state = "open"')
    data.append(
        {"repo": repo.name, "pullrequests": filter(lambda p: p.is_open, pullrequests)}
    )

#%%

for repo in data:
    repo_name = repo["repo"]
    print("---")
    print(
        f"{repo_name} | href=https://bitbucket.org/{WORKSPACE}/{repo_name} |color=#D0D0D0|size=12"
    )
    create_pr_shell = f"\"{(curdir / 'scripts/create_pr.py').as_posix()}\""
    print("New PR")
    print(
        f"--Release PR| shell={create_pr_shell} | param1={repo_name} | param2=release | terminal=true"
    )
    print(
        f"--Hotfix PR| shell={create_pr_shell} | param1={repo_name} | param2=hotfix |  terminal=true"
    )
    print(
        f"--Dev->SDB| shell={create_pr_shell} |param1={repo_name} | param2=dev2sdb | terminal=true"
    )
    for pr in repo["pullrequests"]:
        pr_url = f"https://bitbucket.org/{WORKSPACE}/{repo_name}/pull-requests/{pr.id}"
        params = [
            f"#{pr.id}-{pr.title})",
            f"color={is_me_color(pr)}",
            f"href={pr_url}",
        ]
        print("|".join(params))
        print(
            f"--Merge Sandbox |  shell={create_pr_shell} | param1={repo_name} | param2=toSdb | param3={pr.source_branch} | terminal=true"
        )
        print(f"--Author: {pr.author.nickname}")
        print(f"--Created at: {humanize_date(pr.created_on)}")
        print(f"--Updated at: {humanize_date(pr.updated_on)}")
        print(f"--Source: {pr.source_branch}")
        print(f"--Dest: {pr.destination_branch}")

# %%
