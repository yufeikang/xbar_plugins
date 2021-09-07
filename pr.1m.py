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
#  <xbar.var>string(VAR_MY_NICKNAME=""): Your WORKSPACE.</xbar.var>
#%%
import json
import logging
import os
import sys
from base64 import b64encode
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import requests
from atlassian import Bitbucket
from atlassian.bitbucket.cloud import Cloud
from atlassian.bitbucket.cloud.common.users import User
from pytz import timezone

BRANCH_ICON = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAA4UlEQVQ4jbXTPU4CURQF4I+JizBGlCWYYOU2YCH2LoBK0J7OSjZibEwktDairTgljVh4R99M3iRjoqd5P+fc8+5PHn+IUyxRYoZewvVwhffQDHMGK6yxwA7jhBvF3SI0y4ooElEfd5jE+TDhBrFOQtPPZTCLV3Z4w3HDYJPwlzmDAvMQHGX4QXBzSX/SEj7wEvvnjEGV9n0Ygb1cKnjFQeb+yVcjv9Fm8ICbluCyi8EY2xauhqKxr+rc7xLcxLWfMW3Ux9gJJW5xEibnXYLSEtY4w0Vy/hWGeIxMpuqf6f/wCZenMrU2gp2KAAAAAElFTkSuQmCC"
PR_ICON = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAA2UlEQVQ4jc3SMU4CURDG8R9WdJzAZI+AUJl4AHsbL4AHkILEigsQPYAHMHoAr0HsTQzSAxV0a7HzkhfyFtDKL9nMvplv/m+yO5ym/jFDB09Y4wPDrHaN7THADWq84jsgeXONCe7QKwHGYboIyCryb5HPn88SpIqmZJpFvov3yMFVvI9KU1RRfNZ8k6QuXrJzjWk6nGWFr4jL7EbY4bZ04z7gT/pfgCri+QFwq6fSbGH6jY8tza2e+0j2NYu0LgCKnjTGIuIDLjXrvK+Dnk6MtMEcgwLgFM/v9QO0iTrGPnzHMAAAAABJRU5ErkJggg=="

print(f"| image={PR_ICON}")
print("---")
print("Refresh | refresh=true")

logging.basicConfig(filename="./logs/pr.log", encoding="utf-8", level=logging.INFO)
LOGGER = logging.getLogger()


USERNAME = os.environ.get("VAR_USERNAME")
PASSWORD = os.environ.get("VAR_PASSWORD")
WORKSPACE = os.environ.get("VAR_WORKSPACE")
MY_NICKNAME = os.environ.get("VAR_MY_NICKNAME")

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


def is_me_color(author):
    if author is not None:
        if not isinstance(author, User):
            author = User(None, data=author)
        if author.nickname == MY_NICKNAME:
            return "#3A855D"
    return "#09F4F7FB"


# %%
workspace = cloud.workspaces.get(WORKSPACE)

data = []


def each_branch(repo_name):
    url = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{repo_name}/refs/branches"
    res = requests.get(
        url,
        headers={"Content-Type": "application/json"},
        auth=(USERNAME, PASSWORD),
    )
    data = res.json()
    return data["values"]


now = datetime.utcnow().replace(tzinfo=pytz.utc)
# https://github.dev/atlassian-api/atlassian-python-api
for repo in workspace.repositories.each(sort="-updated_on"):
    if repo.get_time("updated_on") < now - timedelta(days=7):
        continue
    # print(repo.name)
    pullrequests = repo.pullrequests.each(sort="-created_on", q='state = "open"')
    branches = each_branch(repo.name)
    data.append(
        {
            "repo": repo.name,
            "pullrequests": filter(lambda p: p.is_open, pullrequests),
            "branches": branches,
        }
    )

#%%
shell_file = f"\"{(curdir / 'scripts/create_pr.py').as_posix()}\""


def encode_shell_params(params):
    return b64encode(json.dumps(params).encode("utf-8")).decode("utf-8")


def render_new_pr(repo_name):
    pr_params = {
        "repo_name": repo_name,
        "fun": None,
    }
    print("new")
    pr_params["fun"] = "release_pr"
    print(
        f"--release PR| shell={shell_file} | param1={encode_shell_params(pr_params)} | terminal=true"
    )
    pr_params["fun"] = "hotfix_pr"
    print(
        f"--hotfix PR| shell={shell_file} | param1={encode_shell_params(pr_params)} |  terminal=true"
    )
    pr_params["fun"] = "merge_to_sandbox"
    print(
        f"--merge to sandbox| shell={shell_file} |param1={encode_shell_params(pr_params)} | terminal=true"
    )


def render_pr(pr, repo_name):
    pr_url = f"https://bitbucket.org/{WORKSPACE}/{repo_name}/pull-requests/{pr.id}"
    params = [
        f"#{pr.id}-{pr.title}",
        f"color={is_me_color(pr.author)}",
        f"href={pr_url}",
        f"templateImage={PR_ICON}",
    ]
    print("|".join(params))
    merge_sandbox_params = {
        "repo_name": repo_name,
        "source_branch": pr.source_branch,
        "fun": "merge_sandbox",
    }
    print(
        f"--merge Sandbox |  shell={shell_file} | param1={encode_shell_params(merge_sandbox_params)} | terminal=true"
    )
    print(f"--Author: {pr.author.nickname}")
    print(f"--Created at: {humanize_date(pr.created_on)}")
    print(f"--Updated at: {humanize_date(pr.updated_on)}")
    print(f"--Source: {pr.source_branch}")
    print(f"--Dest: {pr.destination_branch}")


def render_branch(branch, repo_name):
    url = f"https://bitbucket.org/{WORKSPACE}/{repo_name}/branch/{branch['name']}"
    params = [
        f"--{branch['name']}",
        f"color={is_me_color(branch['target']['author'].get('user'))}",
        f"href={url}",
        f"templateImage={BRANCH_ICON}",
    ]
    print("|".join(params))
    shell_params = {
        "repo_name": repo_name,
        "source_branch": branch["name"],
    }
    shell_params["fun"] = "merge_sandbox"
    print(
        f"----merge Sandbox |  shell={shell_file} | param1={encode_shell_params(shell_params)} | terminal=true"
    )
    shell_params["fun"] = "develop_pr"
    merge_develop_params = shell_params.copy()
    merge_develop_params["merge"] = True
    print(
        f"----merge Develop |  shell={shell_file} | param1={encode_shell_params(merge_develop_params)} | terminal=true"
    )
    shell_params["fun"] = "develop_pr"
    pr_develop_params = shell_params.copy()
    pr_develop_params["merge"] = False
    print(
        f"----develop PR |  shell={shell_file} | param1={encode_shell_params(pr_develop_params)} | terminal=true"
    )
    shell_params["fun"] = "delete_branch"
    print(
        f"----delete |  shell={shell_file} | param1={encode_shell_params(shell_params)} | terminal=true "
    )
    print(f"----Author: {branch['target']['author'].get('user', {}).get('nickname')}")


for repo in data:
    print("---")
    repo_name = repo["repo"]
    print(
        f"⌗ {repo_name} | href=https://bitbucket.org/{WORKSPACE}/{repo_name} |color=#D0D0D0 "
    )
    print("---")
    print("Branches")
    print("---")
    for branch in repo["branches"]:
        render_branch(branch, repo_name)
    print("---")
    print("Pull Requests")
    render_new_pr(repo_name)
    for pr in repo["pullrequests"]:
        render_pr(pr, repo_name)


# %%
