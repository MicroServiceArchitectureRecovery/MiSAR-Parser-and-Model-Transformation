import yaml
import re
import os

def fetch_artifacts(filename_part, filepath_part, app_root_dir):
    artifact_list = []
    for (root,dirs,files) in os.walk(app_root_dir, topdown=True):
        for file in files:
            if filename_part in file:
                root = re.sub(r'\\', '/', root)
                artifact_filename = root + '/' + file
                if filepath_part in root:
                    artifact_list.append(artifact_filename)
    return artifact_list

#This function converts the YAML docker compose file into a dictionary file.
def yaml_to_dict(filename):
    yaml_dict = {}
    with open(filename, encoding='utf8') as file:
        yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
    return yaml_dict

#This function parses the contents of the YAML docker compose file into application containers
def docker_container_part1(docker_compose_files, multi_module_project_name):
    application_containers = {}
    for docker_compose_file in docker_compose_files:
        docker_compose_dict = {}
        if docker_compose_file.endswith(('.yml','.yaml')):
            docker_compose_dict = yaml_to_dict(docker_compose_file)
        if 'services' in docker_compose_dict:
            docker_compose_dict = docker_compose_dict['services']
        for container_name in docker_compose_dict:
            if 'build' in docker_compose_dict[container_name] or 'image' in docker_compose_dict[container_name]:
                if container_name not in application_containers:
                    application_containers[container_name] = {}
                    application_containers[container_name]['parent'] = multi_module_project_name
                    application_containers[container_name]['filename'] = docker_compose_file
                    application_containers[container_name]['build'] = ''
                    application_containers[container_name]['image'] = ''
                    application_containers[container_name]['logging'] = False
                    application_containers[container_name]['ports'] = []
                    application_containers[container_name]['links'] = []
                if 'image' in docker_compose_dict[container_name]:
                    if application_containers[container_name]['image'] == '':
                        application_containers[container_name]['image'] = docker_compose_dict[container_name]['image']
                if 'build' in docker_compose_dict[container_name]:
                    if application_containers[container_name]['build'] == '':
                        if isinstance(docker_compose_dict[container_name]['build'], str):
                            application_containers[container_name]['build'] = docker_compose_dict[container_name]['build']
                        elif isinstance(docker_compose_dict[container_name]['build'], dict):
                            if 'context' in docker_compose_dict[container_name]['build']:
                                application_containers[container_name]['build'] = docker_compose_dict[container_name]['build']['context']
                if 'logging' in docker_compose_dict[container_name] or 'log_opt' in docker_compose_dict[container_name]:
                     if not application_containers[container_name]['logging']:
                        application_containers[container_name]['logging'] = True
                if 'ports' in docker_compose_dict[container_name]:
                    for port in docker_compose_dict[container_name]['ports']:
                        if port not in application_containers[container_name]['ports']:
                            application_containers[container_name]['ports'].append(port)
                if 'expose' in docker_compose_dict[container_name]:
                    for port in docker_compose_dict[container_name]['expose']:
                        if port not in application_containers[container_name]['ports']:
                            application_containers[container_name]['ports'].append(port)
                if 'links' in docker_compose_dict[container_name]:
                    for link in docker_compose_dict[container_name]['links']:
                        if link not in application_containers[container_name]['links']:
                            application_containers[container_name]['links'].append(link)
                if 'depends_on' in docker_compose_dict[container_name]:
                    for link in docker_compose_dict[container_name]['depends_on']:
                        if link not in application_containers[container_name]['links']:
                            application_containers[container_name]['links'].append(link)
    return application_containers

def docker_container_part2(application_containers, app_root_dir):
    for container_name in application_containers:
        # ASSUMPTION: every container_name container that has a local project must have a 'build' value
        # that matches the root directory of the project
        dockerfile_build_dir = re.findall(r'[\.*\./]*(.+)', application_containers[container_name]['build'])
        if len(dockerfile_build_dir) > 0:
            dockerfile_build_dir = dockerfile_build_dir[0].rstrip('/')
        if dockerfile_build_dir:
            dockerfile_files = fetch_artifacts('Dockerfile', dockerfile_build_dir, app_root_dir)
            if len(dockerfile_files) > 0:
                with open(dockerfile_files[0], encoding='utf8') as dockerfile_file:
                    for line in dockerfile_file:
                        line = line.strip()
                        from_commands = re.findall(r'FROM\s+(.+)', line)
                        expose_commands = re.findall(r'EXPOSE\s+(.+)', line)
                        if len(from_commands) > 0:
                            application_containers[container_name]['image'] = from_commands[0]
                        elif len(expose_commands) > 0:
                            application_containers[container_name]['ports'].append(expose_commands[0])

def docker_container_part3(application_containers, application, metamodel):
    for container_name in application_containers:
        container = metamodel.DockerContainerDefinition()
        container.ContainerName = container_name
        container.BuildField = application_containers[container_name]['build']
        container.ImageField = application_containers[container_name]['image']
        container.GeneratesLogs = application_containers[container_name]['logging']
        container.ParentProjectName = application_containers[container_name]['parent']
        container.ArtifactFileName = application_containers[container_name]['filename']
        for port in application_containers[container_name]['ports']:
            ports = metamodel.DockerContainerPort(ExposesPortsField = port, ParentProjectName = application_containers[container_name]['parent'], ArtifactFileName = application_containers[container_name]['filename'])
            container.ports.append(ports)
        order = 0
        for link in application_containers[container_name]['links']:
            order = order + 1
            links = metamodel.DockerContainerLink(DependencyOrder = order, LinksDependsOnField = link, ParentProjectName = application_containers[container_name]['parent'], ArtifactFileName = application_containers[container_name]['filename'])
            container.links.append(links)
        application.containers.append(container)
