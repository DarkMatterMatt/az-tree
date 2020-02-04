#!/usr/bin/env python3

import json
import os
import re
from azure.common.credentials import ServicePrincipalCredentials
from azure.common.credentials import UserPassCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.subscription import SubscriptionClient

def main():
    obj = fetch_az_obj()

    with open("az-tree.json", "w", encoding="utf-8") as f:
        f.write(obj_to_json(obj))

    with open("az-tree.dot", "w", encoding="utf-8") as f:
        f.write(obj_to_dot(obj))

def fetch_az_obj():
    if "AZ_CLIENT" in os.environ and "AZ_SECRET" in os.environ and "AZ_TENANT" in os.environ:
        credentials = ServicePrincipalCredentials(
            client_id = os.environ["AZ_CLIENT"],
            secret = os.environ["AZ_SECRET"],
            tenant = os.environ["AZ_TENANT"]
        )
    elif "AZ_USER" in os.environ and "AZ_PASS" in os.environ:
        credentials = UserPassCredentials(
            os.environ["AZ_USER"],
            os.environ["AZ_PASS"],
        )
    else:
        print("ERROR: Missing credentials in environmental variables")
        return

    subscriptions = SubscriptionClient(credentials).subscriptions

    root_obj = []

    # subscriptions
    for sub in subscriptions.list():
        client = ResourceManagementClient(credentials, sub.subscription_id)

        sub_obj = sub.as_dict()
        sub_obj["resource_groups"] = []
        root_obj.append(sub_obj)

        # resource groups
        for res_group in client.resource_groups.list():
            res_group_obj = res_group.as_dict()
            res_group_obj["resources"] = []
            sub_obj["resource_groups"].append(res_group_obj)

            # resources
            for res in client.resources.list_by_resource_group(res_group.name):
                res_group_obj["resources"].append(res.as_dict())

    return root_obj

def obj_to_dot(obj):
    # https://stackoverflow.com/questions/8382304/how-to-generate-nodes-with-customized-shape
    o = "digraph az_tree {"

    o += "\n    compound=true;"
    o += "\n    ranksep=1.25;"
    o += "\n    bgcolor=white;"

    o += "\n    node [shape=plaintext, fontsize=16, label=\"\"];"
    o += "\n    edge [arrowsize=1, color=black];"
    o += "\n    graph[penwidth=0, labelloc=\"b\"];"


    for sub in obj:
        sub_name = re.sub("\W", "_", sub["display_name"])
        o += "\n\n    /* Subscription: {} */".format(sub_name)
        o += "\n    \"root\" -> \"{}\";".format(sub_name)

        for res_group in sub["resource_groups"]:
            res_group_name = re.sub("\W", "_", res_group["name"])
            o += "\n\n        /* Resource Group: {} */".format(res_group_name)
            o += "\n        \"{}\" -> \"{}\";".format(sub_name, res_group_name)

            for res in res_group["resources"]:
                res_name = re.sub("\W", "_", res["name"])
                o += "\n            \"{}\" -> \"{}_icon\";".format(res_group_name, res_name)

                image = res["type"].lower().split("/")[1] + ".svg"
                o += "\n            subgraph cluster_{0} {{label=\"{0}\"; {0}_icon[image=\"{1}\"];}};".format(res_name, image)

    o += "\n}"
    return o

def obj_to_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
