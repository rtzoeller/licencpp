#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
"""
This file is part of licencpp, which is released under the MIT License.
See file LICENSE or go to https://opensource.org/licenses/MIT for full license details.
"""

# This script reads a project's vcpkg.json file to get the project name, then uses vcpkg to generate a DGML file of the project's dependencies.
# It then reads the DGML file to extract the names of the dependencies, and reads each dependency's vcpkg.json file to extract its license.

import json
import os
import subprocess
import xml.etree.ElementTree as ET
import datetime
import yaml
import argparse
from sys import exit

SCRIPT_NAME = "licencpp"
SCRIPT_VERSION = "0.2.5"
SCRIPT_LICENSE = "MIT"

# Display welcome message
print(f"Welcome to {SCRIPT_NAME} v{SCRIPT_VERSION} - Licensed under {SCRIPT_LICENSE}\n")

parser = argparse.ArgumentParser(description='Creates project_spdx_document.spdx.yaml from vcpkg.json')
parser.add_argument('--project_vcpkg_json', dest='project_vcpkg_json', default='vcpkg.json',
                    help="Path to your project's vcpkg.json", required=False)
parser.add_argument('--vcpkg_ports_dir', dest='vcpkg_ports_dir', default='../vcpkg/ports',
                    help="Path to vcpkg official registry (port folder)", required=False)
parser.add_argument('--vcpkg_additional_registry', dest='vcpkg_additional_registry', default='',
                    help="Path to additional vcpkg registry (port folder)", required=False)
parser.add_argument('--vcpkg_executable', dest='vcpkg_executable', default='..\\vcpkg\\vcpkg',
                    help="Path to vcpkg executable", required=False)
parser.add_argument('--project_features', dest='project_features', default='',
                    help="Features to enable in the project", required=False)
parser.add_argument('--dependencies_dgml', dest='dependencies_dgml', default='dependencies.dgml',
                    help="Path to vcpkg-built dependencies.dgml", required=False)
parser.add_argument('--mermaid', dest='mermaid', default=False, action='store_true',
                    help="Create the mermaid diagram in addition to the DGML document through vcpkg integration")
parser.add_argument('--dependencies_md', dest='dependencies_md', default='dependencies.md',
                    help="Path to vcpkg-built dependencies.md with the mermaid plot, if enabled", required=False)
parser.add_argument('--verbose', dest='verbose', default=False, action='store_true',
                    help="Run the program in verbose mode")
args = parser.parse_args()

project_vcpkg_json = args.project_vcpkg_json
vcpkg_ports_dir = args.vcpkg_ports_dir
vcpkg_additional_registry = args.vcpkg_additional_registry
vcpkg_executable = args.vcpkg_executable
dependencies_dgml = args.dependencies_dgml
project_features = args.project_features
enable_mermaid = args.mermaid
dependencies_md = args.dependencies_md
verbose = args.verbose

# Read project's vcpkg.json to get the project name
if not os.path.exists(project_vcpkg_json):
    print(f"Error: {project_vcpkg_json} not found")
    exit(1)

with open(project_vcpkg_json, 'r') as file:
    project_data = json.load(file)
project_name = project_data.get('name')
project_license = project_data.get('license')
project_homepage = project_data.get('homepage')
project_version = project_data.get('version')
project_description = project_data.get('description')

if project_features is not None and project_features != '':
    project_features = f'[{project_features}]'

# Generate dependencies.dgml file
command = f'"{vcpkg_executable}" depend-info --overlay-ports=. {project_name}{project_features} --format=dgml > {dependencies_dgml}'
if verbose:
    print(f"Running: {command}")
subprocess.run(command, shell=True, check=True)

if enable_mermaid:
    command = f'"{vcpkg_executable}" depend-info --overlay-ports=. {project_name}{project_features} --format=mermaid > {dependencies_md}'
    if verbose:
        print(f"Running: {command}")
    subprocess.run(command, shell=True, check=True)

# Parse the DGML file to extract dependency names
def parse_dgml(dgml_path):
    dependencies = []
    tree = ET.parse(dgml_path)
    root = tree.getroot()
    for node in root.findall('.//{http://schemas.microsoft.com/vs/2009/dgml}Node'):
        dependencies.append(node.get('Id'))
    return dependencies

def generate_spdx_document(dependencies_info):
    spdx_document = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "spdxVersion": "SPDX-2.2",
        "creationInfo": {
            "created": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "creators": [f"Tool: {SCRIPT_NAME}.py {SCRIPT_VERSION}", "Organization: none", "Person: Stefano Sinigardi"],
            "licenseListVersion": "3.9"
        },
        "name": f"{project_name}",
        "dataLicense": "CC0-1.0",
        "documentNamespace": f"http://spdx.org/spdxdocs/{project_name}-{datetime.datetime.now().timestamp()}",
        "documentDescribes": ["SPDXRef-Package-{}".format(project_name)],
        "packages": [],
        "relationships": []  # Include relationships if needed
    }

    package_spdx_id = "SPDXRef-Package-{}".format(project_name)
    package = {
        "SPDXID": "SPDXRef-Package-{}".format(project_name),
        "name": project_name,
        "downloadLocation": project_homepage or "NOASSERTION",
        "homepage": project_homepage or "NOASSERTION",
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": project_license or "NOASSERTION",
        "description": project_description or "NOASSERTION",
        "versionInfo": project_version or "NOASSERTION",
    }
    spdx_document["packages"].append(package)

    for dep, info in dependencies_info.items():
        package_spdx_id = f"SPDXRef-Package-{dep}"
        if package_spdx_id == "SPDXRef-Package-{}".format(project_name):
            continue
        package = {
            "SPDXID": f"{package_spdx_id}",
            "name": dep,
            "downloadLocation": info['homepage'] or "NOASSERTION",
            "homepage": info['homepage'] or "NOASSERTION",
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": info['license'] or "NOASSERTION",
            "description": info['description'] or "NOASSERTION",
            "versionInfo": info['version'] or "NOASSERTION",
        }
        spdx_document["packages"].append(package)

        # Optional: Define a relationship of type 'DESCRIBES' for each package
        relationship = {
            "spdxElementId": "SPDXRef-Package-{}".format(project_name),
            "relationshipType": "DEPENDS_ON",
            "relatedSpdxElement": package_spdx_id
        }
        spdx_document["relationships"].append(relationship)

    with open("project_spdx_document.spdx.yaml", "w") as spdx_file:
        yaml.dump(spdx_document, spdx_file,
                  sort_keys=False, default_flow_style=False)

def get_version_from_dep_data(dep_data):
    # The version can be stored under one of several keys
    # https://learn.microsoft.com/en-us/vcpkg/users/versioning#version-schemes
    keys = ['version', 'version-semver', 'version-date', 'version-string']
    for key in keys:
        version = dep_data.get(key)
        if version is not None:
            return version
    return None

def get_data_from_vcpkg_json(dep_name):
    if verbose:
        print(f"Analyzing {dep_name}")
    vcpkg_json_paths = []
    # First check the additional registry, then the official registry (so that if there's an overlay, the additional registry takes precedence)
    if vcpkg_additional_registry != '':
        vcpkg_json_paths.append(os.path.join(vcpkg_additional_registry, dep_name, 'vcpkg.json'))
    vcpkg_json_paths.append(os.path.join(vcpkg_ports_dir, dep_name, 'vcpkg.json'))
    for vcpkg_json_path in vcpkg_json_paths:
        if os.path.exists(vcpkg_json_path):
            with open(vcpkg_json_path, 'r') as file:
                dep_data = json.load(file)
                license = dep_data.get('license')
                homepage = dep_data.get('homepage')
                version = get_version_from_dep_data(dep_data)
                description = dep_data.get('description')
                # if description is a list of strings, we need to join them into a single string
                if isinstance(description, list):
                    description = ' '.join(description)
                if verbose:
                    print(
                        f"Using {vcpkg_json_path} as a source for {dep_name} ({version}:{license})")
            return license, homepage, version, description
    return None, None, None, None

dependencies = parse_dgml(dependencies_dgml)
dependencies_info = {}

for dep in dependencies:
    license, homepage, version, description = get_data_from_vcpkg_json(dep)
    dependencies_info[dep] = {'license': license, 'homepage': homepage, 'version': version, 'description': description}

generate_spdx_document(dependencies_info)
