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

import pytz
from atlassian import Bitbucket
from atlassian.bitbucket.cloud import Cloud
from pytz import timezone

print("Pipeline")
print("---")
print("Refresh | refresh=true")

FORMAT = "%(asctime)-15s %(threadName)s %(filename)-15s:%(lineno)d %(levelname)-8s: %(message)s"
logging.basicConfig(
    filename="./logs/pipeline.log",
    encoding="utf-8",
    level=logging.WARNING,
    format=FORMAT,
)
LOGGER = logging.getLogger()

USERNAME = os.environ.get("VAR_USERNAME")
PASSWORD = os.environ.get("VAR_PASSWORD")
WORKSPACE = os.environ.get("VAR_WORKSPACE")

SUCCESS_COLOR = "#3A855D"
PROGRESS_COLOR = "#2A63F6"
STOP_COLOR = "#FA9E41"
FAILED_COLOR = "#CD4425"
PEDING_COLOR = "#7E8BA7"

jst = timezone("Asia/Tokyo")


def humanize_date(date):
    return date.astimezone(jst).strftime("%Y/%m/%d %H:%M:%S")


if USERNAME is None or PASSWORD is None or WORKSPACE is None:
    print("Setup VAR")
    sys.exit(0)

cloud = Cloud(
    url="https://api.bitbucket.org/",
    username=USERNAME,
    password=PASSWORD,
    cloud=True,
)

STEP_COLOR_MAP = {
    "PENDING": PEDING_COLOR,
    "IN_PROGRESS": PROGRESS_COLOR,
    "COMPLETED": SUCCESS_COLOR,
}

# %%
workspace = cloud.workspaces.get(WORKSPACE)

data = []


def iso_format(offset):
    d = datetime.utcnow().replace(tzinfo=pytz.utc) + offset
    return d.isoformat()


now = datetime.utcnow().replace(tzinfo=pytz.utc)

# https://github.dev/atlassian-api/atlassian-python-api
for repo in workspace.repositories.each(
    q=f"updated_on > {iso_format(-timedelta(days=7))}",
    sort="-updated_on",
):
    if repo.get_time("updated_on") < now - timedelta(days=7):
        break
    LOGGER.info("repo: %s", repo.name)
    last_pipelines = []

    for pipeline in repo.pipelines.each(sort="-created_on"):
        if pipeline.created_on < now - timedelta(minutes=60):
            break
        last_pipelines.append(pipeline)
        LOGGER.info("pipelines: %s, %s", pipeline.build_number, pipeline.created_on)
    LOGGER.info("pipelines size: %d", len(last_pipelines))
    data.append({"repo": repo.name, "pipelines": last_pipelines})

#%%

for repo in data:
    repo_name = repo["repo"]
    print("---")
    print(
        f"{repo_name} | href=https://bitbucket.org/{WORKSPACE}/{repo_name} |color=#D0D0D0|size=12"
    )
    for pipeline in repo["pipelines"]:
        pipeline_url = f"https://bitbucket.org/{WORKSPACE}/{repo_name}/addon/pipelines/home#!/results/{pipeline.build_number}"
        steps = list(pipeline.steps())
        current_step = steps[-1]
        target = pipeline.get_data("target")
        target_name = "-"
        if target["type"] == "pipeline_ref_target":
            target_name = target["ref_name"]
        elif target["type"] == "pipeline_pullrequest_target":
            target_name = target["source"]
        for s in steps:
            if s.state["name"] == "IN_PROGRESS":
                current_step = s
                break
        params = [
            f"#{pipeline.build_number}[{target_name}]:({pipeline.build_seconds_used or '0'}s)-{current_step.state['name']}",
            f"href={pipeline_url}",
            f"color={STEP_COLOR_MAP.get(current_step.state['name'], FAILED_COLOR)}",
        ]
        print("|".join(params))
        print(f"--created_on:{humanize_date(pipeline.created_on)}")
        for step in steps:
            step_params = [
                f"--({step.state['name']}-{step.duration_in_seconds or 0}s)-{step.get_data('name')}",
                f"color={STEP_COLOR_MAP.get(step.state['name'], FAILED_COLOR)} ",
                f"href={pipeline_url}",
            ]
            print("|".join(step_params))
            if step.state["name"] == "IN_PROGRESS":
                log_text = step.log().decode("utf-8")
                for line in log_text.split("\n"):
                    sys.stdout.write("----" + line.replace("|", "｜") + "\n")
# %%
