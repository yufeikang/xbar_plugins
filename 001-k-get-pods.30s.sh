#!/usr/bin/env bash

# <xbar.title>List some running Kubernetes things</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Robert Prince</xbar.author>
# <xbar.author.github>robertp</xbar.author.github>
# <xbar.desc>Simple plugin that shows running Kubernetes pods, services, deployments, ...</xbar.desc>
# <xbar.dependencies>brew,kubectl</xbar.dependencies>
# <xbar.image>https://i.imgur.com/sH9yhBW.png</xbar.image>

export PATH=/usr/local/bin:"${PATH}"

echo "Pods"

# check network
network=$(networksetup -getinfo Wi-Fi| grep -Eo 'Router: ([0-9\.]+)')
if [ -z $network ];
then
    echo "Waiting Network"
    exit 0
# else
fi

numpods=$(kubectl get pods -A 2> /dev/null | grep -v NAME | wc -l | sed 's/ //g')
numsvc=$(kubectl get services -A 2> /dev/null | grep -v NAME | wc -l | sed 's/ //g')
numdeps=$(kubectl get deployments -A 2> /dev/null | grep -v NAME | wc -l | sed 's/ //g')

current_namespace=$(kubectl config get-contexts --no-headers | grep '*' | grep -Eo '\S+$')

all_ns=$(kubectl get namespaces --no-headers | grep -Eo '^\S+\s')

# if [[ "$numpods" -eq "0" && "$numsvc" -eq "0" && "$numdeps" -eq "0" ]]; then echo "no k8s"; exit; fi

# if [[ "$numpods" -eq "0" && "$numsvc" -eq "0" && "$numdeps" -eq "0" ]]; then exit; fi

# echo "[$numpods pods / $numsvc services / $numdeps deployments]"

switch_ns="param1=config | param2=set-context |param3=--current | param4=--namespace | param5="

echo "---"
echo "Refresh | refresh=true"
echo "==== Namesapce ===="
for ns in $all_ns; do
if [ $ns == $current_namespace ];
then
    echo $ns
else
    echo "$ns | shell=kubectl | ${switch_ns}${ns} | refresh=true "
fi
done
echo "==== PODS ===="
kubectl get pods  | while read -r line; do echo "${line} | font=Menlo"; done
# echo "---"
# echo "==== SERVICES ===="
# kubectl get services  | while read -r line; do echo "${line} | font=Menlo"; done
# echo "---"
# echo "==== DEPLOYMENTS ===="
# kubectl get deployments  | while read -r line; do echo "${line} | font=Menlo"; done
