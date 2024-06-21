############################
# Developed by RanaFakeeh-87
# 01/20/2020
############################

import tkinter
from tkinter import filedialog
from tkinter import messagebox
from pyecore.resources import ResourceSet, URI
from pyecore.utils import DynamicEPackage
import os
import yaml
import xmltodict
from collections import OrderedDict
import re
from datetime import datetime
import javalang
import tkinter.messagebox
from git import Repo
import tkinter
from tkinter import filedialog
from tkinter import messagebox
import os
import tkinter
from tkinter import messagebox
import os
import shutil
import stat
from urllib.request import urlopen as url
from datetime import *
import webbrowser
import subprocess
from MisarParserJava import *
from MisarParserDocker import *
            
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

def yaml_to_dict(filename):
    yaml_dict = {}
    with open(filename) as file:
        yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
    return yaml_dict
    
def xml_to_dict(filename):
    xml_dict = {}
    with open(filename) as file:
        xml_dict = xmltodict.parse(file.read())
    return xml_dict

def get_library_list(list0, file_n, app_root_dir):       
    list_n = list0
    if file_n.endswith('pom.xml'):
        pom_xml_dict = xml_to_dict(file_n)
        maven_transitive_scopes = {
                'COMPILE': {'COMPILE':'COMPILE', 'PROVIDED':'-', 'RUNTIME':'RUNTIME', 'TEST':'-'},
                'PROVIDED': {'COMPILE':'PROVIDED', 'PROVIDED':'-', 'RUNTIME':'PROVIDED', 'TEST':'-'},
                'RUNTIME': {'COMPILE':'RUNTIME', 'PROVIDED':'-', 'RUNTIME':'RUNTIME', 'TEST':'-'},
                'TEST': {'COMPILE':'TEST', 'PROVIDED':'-', 'RUNTIME':'TEST', 'TEST':'-'}
                }
        if 'parent' in pom_xml_dict['project']: 
            if 'artifactId' in pom_xml_dict['project']['parent']:
                parent_artifact_Id = pom_xml_dict['project']['parent']['artifactId']
                for parent_build_file in fetch_artifacts('pom.xml', '', app_root_dir):
                    parent_pom_xml_dict = xml_to_dict(parent_build_file)
                    if 'artifactId' in parent_pom_xml_dict['project']:
                        if parent_artifact_Id == parent_pom_xml_dict['project']['artifactId']:
                            list_n = get_library_list(list_n, parent_build_file, app_root_dir)
                            break        
        dependency_list = []
        if 'dependencies' in pom_xml_dict['project']:
            if 'dependency' in pom_xml_dict['project']['dependencies']:
                dependency_object = pom_xml_dict['project']['dependencies']['dependency']
                if isinstance(dependency_object, OrderedDict):
                    dependency_list.append(dependency_object)
                elif isinstance(dependency_object, list):                                       
                    dependency_list = dependency_object               
                for dependency in dependency_list:
                    library = {'filename':file_n, 'groupId':dependency['groupId'], 'artifactId':dependency['artifactId'], 'scope':'COMPILE'}
                    if 'scope' in dependency:
                        library['scope'] = dependency['scope'].upper()
                    build_file = os.path.basename(file_n)
                    artifacts = fetch_artifacts(build_file, library['artifactId'], app_root_dir)
                    if len(artifacts) > 0:
                        list_n = get_library_list(list_n, artifacts[0], app_root_dir)
                    else:
                        found_at = -1
                        index = -1
                        for library_n in list_n:
                            index += 1
                            if library_n['groupId'] == library['groupId'] and library_n['artifactId'] == library['artifactId']:
                                found_at = index
                                break
                        if found_at == -1:
                            list_n.append(library)
                        else:
                            list_n[found_at]['scope'] = maven_transitive_scopes[list_n[found_at]['scope']][library['scope']]
                            if list_n[found_at]['scope'] == '-':
                                list_n.remove(list_n[found_at])
    return list_n
                        
def yaml_to_properties(config_file):    
    with open(config_file) as file:
        properties = []
        value_section = ''
        for line in file:
            if line.strip():
                if line.strip() == '---':
                    properties.append(line.strip())
                else:
                    parts = line.strip().partition(':')
                    if '#' not in parts[0]:
                        if ':' in parts[1]:
                            line = line[:line.index(parts[0])]
                            tabs = re.findall(r'(\s\s)', line)
                            levels = len(tabs)
                            if parts[0].strip().startswith('-'):
                                levels += 1      
                            if levels == 0:
                                property_sections = [] 
                            else:
                                property_sections = property_sections[:levels]
                            property_sections.append(parts[0].strip())
                            if parts[2]:
                                if '#' in parts[2]:
                                    value_section = parts[2].partition('#')[0]
                                else:
                                    value_section = parts[2]
                        else:
                            value_section = parts[0].lstrip('-')
                        if value_section: 
                            property_line = property_sections[0]
                            for property_section in property_sections[1:]:
                                property_line += '.' + property_section  
                            property_line = property_line.lstrip('.')
                            property_line = re.sub(r'\-\s', '', property_line)
                            properties.append(property_line + '=' + value_section.strip())
                            value_section = ''
                            
    return properties

def properties_to_property_documents(config_file, apllication_name):    
    properties = []
    file_extension = ''
    if config_file.endswith(('.yml','.yaml')):
        file_extension = '.yml'
        if config_file.endswith('.yaml'):
            file_extension = '.yml'            
        properties = yaml_to_properties(config_file)
    elif config_file.endswith('.properties'):
        file_extension = '.properties'
        with open(config_file) as file:
            for line in file:
                line = line.strip()
                if line and '#' not in line:
                    properties.append(line)         
    property_documents = []
    property_document = []
    for property_line in properties:
        if property_line == '---':
            property_documents.append(property_document)
            property_document = []
            continue            
        delimiter = ''
        if '=' in property_line:
            delimiter = '='
        elif ':' in property_line:
            delimiter = ':' 
        parts = property_line.partition(delimiter)
        property_document.append({'filename':config_file, 'property':parts[0].strip(), 'value':parts[2].strip(), 'profile':''})
    if property_document:
        property_documents.append(property_document)              
    config_profile = 'compile'
    if apllication_name: 
        parts = os.path.basename(config_file).rstrip(file_extension).partition(apllication_name)
        if parts[2]:
            config_profile = parts[2].lstrip('-')        
    for property_document in property_documents:
        for property_dict in property_document:
            if property_dict['property'] == 'spring.profiles':
                config_profile = property_dict['value'].replace(',', ';')
            property_dict['profile'] = config_profile.upper()

    return property_documents
    
def evaluate_property_local_variable1(property_value):
    variable_terms = re.findall(r'\$\{(\w+[.\w+]*):(\w+[:\w+]*)\}', property_value.strip())
    if len(variable_terms) > 0:
        property_value = re.sub(r'\$\{(\w+[.\w+]*):(\w+[:\w+]*)\}', variable_terms[0][1], property_value)
        return evaluate_property_local_variable1(property_value)
    else:
        return property_value 
    
def evaluate_property_local_variable2(property_value, property_document, property_documents):
    property_found = False
    variable_terms = re.findall(r'\$\{(\w+[.\w+[\-\w+]*]*)\}', property_value)
    for variable_term in variable_terms:
        for config_property in property_document:
            if config_property['property'] == variable_term:
                property_found = True
                property_value = re.sub(r'\$\{'+variable_term+'\}', config_property['value'], property_value)
                if len(re.findall(r'\$\{(\w+[.\w+[\-\w+]*]*)\}', property_value)) > 0:
                    property_value = evaluate_property_local_variable2(property_value, property_document, property_documents)                    
                break
    if not property_found:
        for variable_term in variable_terms:
            for _document in property_documents:
                for config_property in _document:
                    if config_property['property'] == variable_term:
                        property_value = re.sub(r'\$\{'+variable_term+'\}', config_property['value'], property_value)
                        if len(re.findall(r'\$\{(\w+[.\w+[\-\w+]*]*)\}', property_value)) > 0:
                            property_value = evaluate_property_local_variable2(property_value, property_document, property_documents)                    
                        break   
    return property_value 
    
def get_property_list(filename_part, filepath_part, app_root_dir, application_name):
    property_list = [] 
    for config_file in fetch_artifacts(filename_part, filepath_part, app_root_dir):
        if config_file.endswith(('.yml','.yaml','.properties')):
            if '/src/test/' not in config_file:
                property_list += properties_to_property_documents(config_file, application_name)
                
    return property_list  

def resolve_hostname1(port_number, application_containers):
    hostname = ''
    for container_name in application_containers:
        for container_port in application_containers[container_name]['ports']:
            if port_number in container_port:
                hostname = container_name
                break        
    return hostname

def resolve_hostname2(port_number, application_project):
    hostname = ''
    for module_name in application_project['modules']:
        for config_property in application_project['modules'][module_name]['properties']:
            if config_property['property'] == 'server.port':
                if port_number in config_property['value']:
                    hostname = module_name
                    break
        if hostname:
            break

    return hostname

def get_annotations(element):
    annotations = []
    for _annotation in element.annotations:
        annotation = {}
        annotation['name'] = _annotation.name
        annotation['parameters'] = []
        if _annotation.element:
            if isinstance(_annotation.element, javalang.tree.Literal):
                annotation['parameters'].append({'name':'', 'value':_annotation.element.value})
            elif isinstance(_annotation.element, list):
                for _element in _annotation.element:
                    if isinstance(_element, javalang.tree.ElementValuePair):
                        if isinstance(_element.value, javalang.tree.Literal):
                            annotation['parameters'].append({'name':_element.name, 'value':_element.value.value})
                        elif isinstance(_element.value, javalang.tree.MemberReference):
                            annotation['parameters'].append({'name':_element.name, 'value':_element.value.qualifier + '.' + _element.value.member})
                            # get the literal value from referenced member
        annotations.append(annotation)
    return annotations
                      
def evaluate_member_reference(member_reference, element):
    literal_value = ''    
    if isinstance(element, javalang.tree.ClassDeclaration):
        for path, _field in element.filter(javalang.tree.FieldDeclaration):
            if _field.declarators:
                for _declarator in _field.declarators:
                    if isinstance(_declarator, javalang.tree.VariableDeclarator):
                        if _declarator.name ==  member_reference.member:
                            if _declarator.initializer:
                                if isinstance(_declarator.initializer, javalang.tree.Literal):
                                    literal_value = _declarator.initializer.value
                                    break
                if literal_value:
                    break               
    elif isinstance(element, javalang.tree.MethodDeclaration):
        for path, _variable in element.filter(javalang.tree.LocalVariableDeclaration):
            if _variable.declarators:
                for _declarator in _variable.declarators:
                    if isinstance(_declarator, javalang.tree.VariableDeclarator):
                        if _declarator.name ==  member_reference.member:
                            if _declarator.initializer:
                                if isinstance(_declarator.initializer, javalang.tree.Literal):
                                    literal_value = _declarator.initializer.value
                                    break
                if literal_value:
                    break

    return literal_value

def get_member_reference_type(member_reference_name, element):
    type_value = ''    
    if isinstance(element, javalang.tree.ClassDeclaration):
        for path, _field in element.filter(javalang.tree.FieldDeclaration):
            if _field.declarators:
                for _declarator in _field.declarators:
                    if isinstance(_declarator, javalang.tree.VariableDeclarator):
                        if _declarator.name ==  member_reference_name:
                            if _field.type:
                                if isinstance(_field.type, javalang.tree.ReferenceType):
                                    type_value = _field.type.name
                                    break 
                if type_value:
                    break  
                
    elif isinstance(element, javalang.tree.MethodDeclaration):
        for path, _variable in element.filter(javalang.tree.LocalVariableDeclaration):
            if _variable.declarators:
                for _declarator in _variable.declarators:
                    if isinstance(_declarator, javalang.tree.VariableDeclarator):
                        if _declarator.name ==  member_reference_name:
                            if _variable.type:
                                if isinstance(_variable.type, javalang.tree.ReferenceType):
                                    type_value = _variable.type.name
                                    break 
                if type_value:
                    break

    return type_value

def get_member(member_reference, element):
    member = {}
    member['name'] = member_reference.member
    if member_reference.qualifier:
        member['name'] = member_reference.qualifier + '.' + member['name']
    member['value'] = evaluate_member_reference(member_reference, element)
    
    return member

def get_reference_type(reference_type):
    type_str = reference_type.name
    if reference_type.arguments:
        type_str += '<'
        arguments = ''
        for _argument in reference_type.arguments:                                        
            if isinstance(_argument, javalang.tree.TypeArgument):
                if _argument.type:
                    if isinstance(_argument.type, javalang.tree.ReferenceType): 
                        arguments += get_reference_type(_argument.type) + ','
        arguments = arguments.rstrip(',')
        type_str += arguments + '>'
    
    return type_str

def create_psm_instance(txt_proj_name, txt_proj_dir, txt_psm_ecore, lst_docker_compose, lst_app_build, lst_module_build_dir, lst_module_build, lst_app_config_dir, txt_output_dir):
    if not txt_proj_name.get().strip():
        messagebox.showerror('Missing Values', 'please provide one value for \'Application Project Name\' !')
    elif not txt_proj_dir.get().strip():
        messagebox.showerror('Missing Values', 'please provide one value for \'Application Project Build Directory\' !')
    elif not txt_psm_ecore.get().strip():
        messagebox.showerror('Missing Values', 'please provide one value for \'PSM Ecore File\' !') 
    elif txt_psm_ecore.get().lower().strip().find('.ecore') == -1:
        messagebox.showerror('Invalid File Type', 'please select an ECORE file type for \'PSM Ecore File\' !') 
    elif not lst_docker_compose.size():
        messagebox.showerror('Missing Values', 'please provide one or more value for \'Docker Compose Files\' !') 
    elif not lst_module_build_dir.size():
        messagebox.showerror('Missing Values', 'please provide one or more value for \'Microservice Projects Build Directories\' !') 
    else:
        start_time = datetime.now().strftime("%H:%M:%S")
        docker_compose_files = []
        app_build_files = []
        module_build_dirs = []
        module_build_files = []
        app_config_dirs = []
        
        multi_module_project_name = txt_proj_name.get().strip()
        app_root_dir = txt_proj_dir.get().strip()
        psm_ecore_file = txt_psm_ecore.get().strip()
        output_dir = txt_output_dir.get().strip()
        for docker_compose_file in lst_docker_compose.get(0, 'end'):
            if docker_compose_file.strip():
                docker_compose_files.append(docker_compose_file)
        for app_build_file in lst_app_build.get(0, 'end'):
            if app_build_file.strip():
                app_build_files.append(app_build_file)
        for module_build_dir in lst_module_build_dir.get(0, 'end'):
            if module_build_dir.strip():
                module_build_dirs.append(module_build_dir)
        for module_build_file in lst_module_build.get(0, 'end'):
            if module_build_file.strip():
                module_build_files.append(module_build_file)
        for app_config_dir in lst_app_config_dir.get(0, 'end'):
            if app_config_dir.strip():
                app_config_dirs.append(app_config_dir)

        psm_instance_file_name = multi_module_project_name + "-PSM" + '.xmi'
        psm_instance_file = output_dir + "/" + psm_instance_file_name

        # load metamodel from XMI file
        metamodel_resource_set = ResourceSet()
        metamodel_resource = metamodel_resource_set.get_resource(URI(psm_ecore_file))
        metamodel_root = metamodel_resource.contents[0]
        metamodel_resource_set.metamodel_registry[metamodel_root.nsURI] = metamodel_root
        metamodel = DynamicEPackage(metamodel_root)
        
        # create instance model
        model = metamodel.RootPSM()
        
        # create application instance
        application = metamodel.DistributedApplicationProject() 
        application.ApplicationName = multi_module_project_name
        application.ProjectPackageURL = app_root_dir
        
        # parse docker compose artifacts into containers
        application_containers = dockerComposeAnalysis(docker_compose_files, multi_module_project_name)
        """
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
        """
        # parse dockerfile artifacts to update image and ports information
        mergeDockerfileAnalysisDockerCompose(application_containers, app_root_dir)
        """
        for container_name in application_containers:
            # ASSUMPTION: every container_name container that has a local project must have a 'build' value 
            # that matches the root directory of the project 
            dockerfile_build_dir = re.findall(r'[\.*\./]*(.+)', application_containers[container_name]['build'])
            if len(dockerfile_build_dir) > 0:
                dockerfile_build_dir = dockerfile_build_dir[0].rstrip('/')
            if dockerfile_build_dir:
                dockerfile_files = fetch_artifacts('Dockerfile', dockerfile_build_dir, app_root_dir)
                if len(dockerfile_files) > 0:
                    with open(dockerfile_files[0]) as dockerfile_file:
                        for line in dockerfile_file:
                            line = line.strip()
                            from_commands = re.findall(r'FROM\s+(.+)', line)
                            expose_commands = re.findall(r'EXPOSE\s+(.+)', line)
                            if len(from_commands) > 0:
                                application_containers[container_name]['image'] = from_commands[0]
                            elif len(expose_commands) > 0:
                                application_containers[container_name]['ports'].append(expose_commands[0])
        """

        # create containers instance and append it to application instance
        createDockerPSMElements(application_containers, application, metamodel)
        """
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
        """
        # parse multi module project build artifacts (pom.xml / build.gradle) into application project and its module projects 
        multi_module_project = {}
        multi_module_project['parent'] = multi_module_project_name
        multi_module_project['build'] = ''  
        for app_build_file in app_build_files:
            multi_module_project['build'] += app_build_file + ';'
        multi_module_project['build'] = multi_module_project['build'].rstrip(';') 
        multi_module_project_artifact_Id = multi_module_project_name
        if len(app_build_files) == 1: 
            pom_xml = xml_to_dict(app_build_files[0])
            if 'project' in pom_xml:
                if 'artifactId' in pom_xml['project']:
                    multi_module_project_artifact_Id = pom_xml['project']['artifactId']
        multi_module_project['artifactId'] = multi_module_project_artifact_Id
        multi_module_project['modules'] = {}
        
        # create application project instance
        application_project = metamodel.ApplicationProject()
        application_project.ParentProjectName = multi_module_project['parent']
        application_project.ArtifactFileName = multi_module_project['build']
        application_project.ProjectArtifactId = multi_module_project['artifactId']
        
        # create modules for application project
        for module_build_dir in module_build_dirs:
            module_name = os.path.basename(module_build_dir)
            build_file = ''
            for module_build_file in module_build_files:
                if module_build_file.startswith(module_build_dir):
                    build_file = module_build_file
                    pom_xml = xml_to_dict(module_build_file)
                    if 'project' in pom_xml:
                        if 'artifactId' in pom_xml['project']:
                            module_name = pom_xml['project']['artifactId']
                    break 
            multi_module_project['modules'][module_name] = {}
            multi_module_project['modules'][module_name]['parent'] = multi_module_project_name 
            multi_module_project['modules'][module_name]['build'] = build_file                   
            multi_module_project['modules'][module_name]['artifactId'] = module_name 
            multi_module_project['modules'][module_name]['libraries'] = [] 
            multi_module_project['modules'][module_name]['properties'] = []
            multi_module_project['modules'][module_name]['java_elements'] = []
            
        # create libraries and properties instances for every module project
        for module_name in multi_module_project['modules']:
            print('\nmodule_name = {}'.format(module_name))
            spring_boot_app = True
            spring_web_flux_app = False
            
            # fetch module libraries
            module_build_file = multi_module_project['modules'][module_name]['build']
            module_libraries = []
            module_libraries = get_library_list(module_libraries, module_build_file, app_root_dir)
            for library in module_libraries:
                if library['groupId'] in ['org.springframework.boot', 'org.springframework.cloud']:
                    spring_boot_app = True
                if 'webflux' in library['artifactId'] or 'reactive' in library['artifactId'] or 'reactor' in library['artifactId']:
                    spring_web_flux_app = True
                multi_module_project['modules'][module_name]['libraries'].append(library)
            
            # create microservice project instance
            module_project = metamodel.MicroserviceProject()
            if spring_boot_app:                
                if spring_web_flux_app:
                    module_project = metamodel.JavaSpringWebFluxApplicationProject()
                else:
                    module_project = metamodel.JavaSpringMVCApplicationProject()
            module_project.ParentProjectName = multi_module_project['modules'][module_name]['parent']
            module_project.ArtifactFileName = multi_module_project['modules'][module_name]['build']
            module_project.ProjectArtifactId = module_name
    
            # create dependency library instance and append it to module project
            for library in module_libraries:
                dependency_library = metamodel.DependencyLibrary()
                dependency_library.ParentProjectName = module_name
                dependency_library.ArtifactFileName = library['filename']
                dependency_library.LibraryGroupName = library['groupId']
                dependency_library.LibraryName = library['artifactId']
                dependency_library.LibraryScope = library['scope']
                module_project.libraries.append(dependency_library)

            java_main_parser(metamodel, module_name, module_project, multi_module_project, app_root_dir, app_config_dirs, spring_boot_app, application_containers)
            """
            # fetch module properties
            if spring_boot_app:
                module_properties = []
                module_properties += get_property_list('application', module_name, app_root_dir, '')
                module_properties += get_property_list('bootstrap', module_name, app_root_dir, '') 
                application_name = ''
                for property_document in module_properties:               
                    for config_property in property_document:
                        if config_property['property'] == 'spring.application.name':
                            application_name = config_property['value']
                            break
                for app_config_dir in app_config_dirs:
                    module_properties += get_property_list('application', app_config_dir, app_root_dir, '')
                    if application_name:
                        module_properties += get_property_list(application_name, app_config_dir, app_root_dir, application_name)                                                
                for property_document in module_properties:
                    for config_property in property_document:
                        config_property['value'] = evaluate_property_local_variable1(config_property['value'])                
                        config_property['value'] = evaluate_property_local_variable2(config_property['value'], property_document, module_properties)                
                        localhost_terms = re.findall(r'localhost:(\d+)', config_property['value'])
                        if len(localhost_terms) > 0:
                            port_number = localhost_terms[0]
                            hostname = resolve_hostname1(port_number, application_containers)
                            if hostname:
                                config_property['value'] = re.sub(r'localhost:\d+', hostname, config_property['value'])
                for property_document in module_properties:
                    for config_property in property_document:
                        multi_module_project['modules'][module_name]['properties'].append(config_property)
                        
                # create configuration property instance and append it to module project
                for module_property in multi_module_project['modules'][module_name]['properties']:
                    configuration_property = metamodel.ConfigurationProperty()
                    configuration_property.ParentProjectName = module_name
                    configuration_property.ArtifactFileName = module_property['filename']
                    configuration_property.FullyQualifiedPropertyName = module_property['property']
                    configuration_property.PropertyValue = module_property['value']
                    configuration_property.ConfigurationProfile = module_property['profile']
                    module_project.properties.append(configuration_property) 
                    
                # parse java files
                java_layer = metamodel.SpringWebApplicationLayer()
                java_layer.ParentProjectName = module_name
                java_layer.LayerName = 'SpringWebApplicationLayer'
                module_project.layers.append(java_layer)
                
                for java_file in fetch_artifacts('.java', module_name, app_root_dir):
                    if '/src/test/' not in java_file:
                        print('java_file = {}'.format(os.path.basename(java_file)))
                        try:
                            with open(java_file) as file:
                                tree = javalang.parse.parse(file.read())
                                java_element = metamodel.JavaUserDefinedType()
                                imports = []
                                if tree.imports:
                                    for _import in tree.imports:
                                        imports.append(_import.path)
                                package_name = ''
                                if tree.package:
                                    package_name = tree.package.name                                
                                for _type in tree.types:
                                    if isinstance(_type, javalang.tree.ClassDeclaration) or isinstance(_type, javalang.tree.InterfaceDeclaration):
                                        if isinstance(_type, javalang.tree.ClassDeclaration):
                                            java_element = metamodel.JavaClassType()
                                            if _type.implements:
                                                if isinstance(_type.implements, javalang.tree.ReferenceType): 
                                                    element_identifier = get_reference_type(_type.implements)
                                                    java_interface = metamodel.JavaInterfaceType()
                                                    java_interface.ParentProjectName = module_name
                                                    java_interface.ArtifactFileName = java_file
                                                    java_interface.ElementIdentifier = element_identifier
                                                    java_interface.ElementProtry:file = 'COMPILE'
                                                    java_interface.JsonSchema = ''
                                                    for _import in imports:
                                                        parts = _import.split('.')
                                                        if '<' in element_identifier:
                                                            element_identifier = element_identifier[:element_identifier.index('<')]
                                                        if parts[-1] == element_identifier:
                                                            java_interface.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                    java_element.implements.append(java_interface)
                                                elif isinstance(_type.implements, list): 
                                                    for _interface in _type.implements:
                                                        if isinstance(_interface, javalang.tree.ReferenceType):
                                                            element_identifier = get_reference_type(_interface)
                                                            java_interface = metamodel.JavaInterfaceType()
                                                            java_interface.ParentProjectName = module_name
                                                            java_interface.ArtifactFileName = java_file
                                                            java_interface.ElementIdentifier = element_identifier
                                                            java_interface.ElementProfile = 'COMPILE'
                                                            java_interface.JsonSchema = ''
                                                            for _import in imports:
                                                                parts = _import.split('.')
                                                                if '<' in element_identifier:
                                                                    element_identifier = element_identifier[:element_identifier.index('<')]
                                                                if parts[-1] == element_identifier:
                                                                    java_interface.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                            java_element.implements.append(java_interface)               
                                        elif isinstance(_type, javalang.tree.InterfaceDeclaration):
                                            java_element = metamodel.JavaInterfaceType()

                                        java_element.ParentProjectName = module_name
                                        java_element.ArtifactFileName = java_file
                                        java_element.ElementIdentifier = _type.name
                                        java_element.ElementProfile = 'COMPILE'
                                        java_element.JsonSchema = ''
                                        java_element.PackageName = package_name
    
                                        if _type.extends:
                                            if isinstance(_type.extends, javalang.tree.ReferenceType):
                                                element_identifier = get_reference_type(_type.extends)
                                                java_user_defined_type = metamodel.JavaUserDefinedType()
                                                java_user_defined_type.ParentProjectName = module_name
                                                java_user_defined_type.ArtifactFileName = java_file
                                                java_user_defined_type.ElementIdentifier = element_identifier
                                                java_user_defined_type.ElementProfile = 'COMPILE'
                                                java_user_defined_type.JsonSchema = ''
                                                for _import in imports:
                                                    parts = _import.split('.')
                                                    if '<' in element_identifier:
                                                        element_identifier = element_identifier[:element_identifier.index('<')]
                                                    if parts[-1] == element_identifier:
                                                        java_user_defined_type.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                java_element.extends.append(java_user_defined_type)               
                                            elif isinstance(_type.extends, list): 
                                                for _super in _type.extends:
                                                    if isinstance(_super, javalang.tree.ReferenceType):
                                                        element_identifier = get_reference_type(_super)
                                                        java_user_defined_type = metamodel.JavaUserDefinedType()
                                                        java_user_defined_type.ParentProjectName = module_name
                                                        java_user_defined_type.ArtifactFileName = java_file
                                                        java_user_defined_type.ElementIdentifier = element_identifier
                                                        java_user_defined_type.ElementProfile = 'COMPILE'
                                                        java_user_defined_type.JsonSchema = ''
                                                        for _import in imports:
                                                            parts = _import.split('.')
                                                            if '<' in element_identifier:
                                                                element_identifier = element_identifier[:element_identifier.index('<')]
                                                            if parts[-1] == element_identifier:
                                                                java_user_defined_type.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                        java_element.extends.append(java_user_defined_type)

                                        if _type.annotations:
                                            for annotation in get_annotations(_type):
                                                java_annotation = metamodel.JavaAnnotation()
                                                java_annotation.ParentProjectName = module_name
                                                java_annotation.ArtifactFileName = java_file
                                                java_annotation.AnnotationName = annotation['name']
                                                for parameter in annotation['parameters']:
                                                    annotation_parameter = metamodel.JavaAnnotationParameter()
                                                    annotation_parameter.ParentProjectName = module_name
                                                    annotation_parameter.ArtifactFileName = java_file
                                                    annotation_parameter.ParameterName = parameter['name']
                                                    if not annotation_parameter.ParameterName:
                                                        annotation_parameter.ParameterName = 'NOT_AVAILABLE'
                                                    annotation_parameter.ParameterValue = parameter['value']
                                                    if not annotation_parameter.ParameterValue:
                                                        annotation_parameter.ParameterValue = 'NOT_AVAILABLE'
                                                    java_annotation.parameters.append(annotation_parameter)
                                                java_element.annotations.append(java_annotation)

                                        if _type.body:
                                            for _declaration in _type.body:
                                                if isinstance(_declaration, javalang.tree.MethodDeclaration):
                                                    java_method = metamodel.JavaMethod()
                                                    java_method.ParentProjectName = module_name
                                                    java_method.ArtifactFileName = java_file
                                                    java_method.ElementIdentifier = _declaration.name
                                                    java_method.ElementProfile = 'COMPILE'
                                                    if _declaration.annotations:
                                                        for annotation in get_annotations(_declaration):
                                                            java_annotation = metamodel.JavaAnnotation()
                                                            java_annotation.ParentProjectName = module_name
                                                            java_annotation.ArtifactFileName = java_file
                                                            java_annotation.AnnotationName = annotation['name']
                                                            for parameter in annotation['parameters']:
                                                                annotation_parameter = metamodel.JavaAnnotationParameter()
                                                                annotation_parameter.ParentProjectName = module_name
                                                                annotation_parameter.ArtifactFileName = java_file
                                                                annotation_parameter.ParameterName = parameter['name']
                                                                if not annotation_parameter.ParameterName:
                                                                    annotation_parameter.ParameterName = 'NOT_AVAILABLE'
                                                                annotation_parameter.ParameterValue = parameter['value']
                                                                if not annotation_parameter.ParameterValue:
                                                                    annotation_parameter.ParameterValue = 'NOT_AVAILABLE'
                                                                java_annotation.parameters.append(annotation_parameter)
                                                            java_method.annotations.append(java_annotation)

                                                    if _declaration.return_type:
                                                        if isinstance(_declaration.return_type, javalang.tree.ReferenceType):
                                                            element_identifier = get_reference_type(_declaration.return_type)
                                                            java_data_type = metamodel.JavaDataType()
                                                            java_data_type.ParentProjectName = module_name
                                                            java_data_type.ArtifactFileName = java_file
                                                            java_data_type.ElementIdentifier = element_identifier
                                                            java_data_type.ElementProfile = 'COMPILE'
                                                            java_data_type.JsonSchema = ''
                                                            for _import in imports:
                                                                parts = _import.split('.')
                                                                if '<' in element_identifier:
                                                                    element_identifier = element_identifier[:element_identifier.index('<')]
                                                                if parts[-1] == element_identifier:
                                                                    java_data_type.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                            java_method.returns = java_data_type

                                                    if _declaration.parameters:
                                                        parameter_order = 0
                                                        for _parameter in _declaration.parameters:
                                                            if isinstance(_parameter, javalang.tree.FormalParameter):
                                                                parameter_order += 1
                                                                java_method_parameter = metamodel.JavaMethodParameter()
                                                                java_method_parameter.ParentProjectName = module_name
                                                                java_method_parameter.ArtifactFileName = java_file
                                                                java_method_parameter.ElementIdentifier = _parameter.name
                                                                java_method_parameter.ElementProfile = 'COMPILE'
                                                                java_method_parameter.FieldValue = 'NOT_AVAILABLE'
                                                                java_method_parameter.ParameterOrder = parameter_order                                                                
                                                                
                                                                if _parameter.annotations:
                                                                    for annotation in get_annotations(_parameter):
                                                                        java_annotation = metamodel.JavaAnnotation()
                                                                        java_annotation.ParentProjectName = module_name
                                                                        java_annotation.ArtifactFileName = java_file
                                                                        java_annotation.AnnotationName = annotation['name']
                                                                        for parameter in annotation['parameters']:
                                                                            annotation_parameter = metamodel.JavaAnnotationParameter()
                                                                            annotation_parameter.ParentProjectName = module_name
                                                                            annotation_parameter.ArtifactFileName = java_file
                                                                            annotation_parameter.ParameterName = parameter['name']
                                                                            if not annotation_parameter.ParameterName:
                                                                                annotation_parameter.ParameterName = 'NOT_AVAILABLE'
                                                                            annotation_parameter.ParameterValue = parameter['value']
                                                                            if not annotation_parameter.ParameterValue:
                                                                                annotation_parameter.ParameterValue = 'NOT_AVAILABLE'
                                                                            java_annotation.parameters.append(annotation_parameter)
                                                                        java_method_parameter.annotations.append(java_annotation)
                                                                
                                                                if _parameter.type:
                                                                    if isinstance(_parameter.type, javalang.tree.ReferenceType): 
                                                                        element_identifier = get_reference_type(_parameter.type)
                                                                        java_data_type = metamodel.JavaDataType()
                                                                        java_data_type.ParentProjectName = module_name
                                                                        java_data_type.ArtifactFileName = java_file
                                                                        java_data_type.ElementIdentifier = element_identifier
                                                                        java_data_type.ElementProfile = 'COMPILE'
                                                                        java_data_type.JsonSchema = ''
                                                                        for _import in imports:
                                                                            parts = _import.split('.')
                                                                            if '<' in element_identifier:
                                                                                element_identifier = element_identifier[:element_identifier.index('<')]
                                                                            if parts[-1] == element_identifier:
                                                                                java_data_type.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                                        java_method_parameter.type = java_data_type
                                                                java_method.parameters.append(java_method_parameter)
                                                    
                                                    if _declaration.body:
                                                        for body_element in _declaration.body:
                                                            for path, _invocation in body_element.filter(javalang.tree.MethodInvocation):
                                                                element_identifier = _invocation.member
                                                                java_invoked_method = metamodel.JavaMethod()
                                                                java_invoked_method.ParentProjectName = module_name
                                                                java_invoked_method.ArtifactFileName = java_file
                                                                java_invoked_method.ElementIdentifier = element_identifier
                                                                java_invoked_method.ElementProfile = 'COMPILE'
                                                                java_invoked_method.RootCallingMethod = _declaration.name + '()'
                                                                
                                                                if _invocation.qualifier: 
                                                                    element_identifier = _invocation.qualifier
                                                                    java_user_defined_type = metamodel.JavaUserDefinedType()
                                                                    java_user_defined_type.ParentProjectName = module_name
                                                                    java_user_defined_type.ArtifactFileName = java_file
                                                                    java_user_defined_type.ElementIdentifier = element_identifier
                                                                    java_user_defined_type.ElementProfile = 'COMPILE'
                                                                    java_user_defined_type.JsonSchema = ''
                                                                    java_user_defined_type.PackageName = ''
                                                                    for _import in imports:
                                                                        parts = _import.split('.')
                                                                        if '<' in element_identifier:
                                                                            element_identifier = element_identifier[:element_identifier.index('<')]
                                                                        if parts[-1] == element_identifier:
                                                                            java_user_defined_type.PackageName = _import[:(_import.index(element_identifier)-1)]
                                                                        
                                                                    if not java_user_defined_type.PackageName:
                                                                        if _declaration.parameters:
                                                                            for _parameter in _declaration.parameters:
                                                                                if isinstance(_parameter, javalang.tree.FormalParameter):
                                                                                    if _invocation.qualifier == _parameter.name:
                                                                                        if _parameter.type:
                                                                                            if isinstance(_parameter.type, javalang.tree.ReferenceType):
                                                                                                type_identifier = _parameter.type.name 
                                                                                                java_user_defined_type.ElementIdentifier = type_identifier
                                                                                                for _import in imports:
                                                                                                    parts = _import.split('.')
                                                                                                    if '<' in type_identifier:
                                                                                                        type_identifier = type_identifier[:type_identifier.index('<')]
                                                                                                    if parts[-1] == type_identifier:
                                                                                                        java_user_defined_type.PackageName = _import[:(_import.index(type_identifier)-1)]
                                                                                                        break
                                                                    
                                                                    if not java_user_defined_type.PackageName:
                                                                        type_identifier = get_member_reference_type(_invocation.qualifier, _declaration)
                                                                        if type_identifier:
                                                                            java_user_defined_type.ElementIdentifier = type_identifier
                                                                        for _import in imports:
                                                                            parts = _import.split('.')
                                                                            if '<' in type_identifier:
                                                                                type_identifier = type_identifier[:type_identifier.index('<')]
                                                                            if parts[-1] == type_identifier:
                                                                                java_user_defined_type.PackageName = _import[:(_import.index(type_identifier)-1)]
                                                                                break
                                                                    
                                                                    if not java_user_defined_type.PackageName:
                                                                        type_identifier = get_member_reference_type(_invocation.qualifier, _type)
                                                                        if type_identifier:
                                                                            java_user_defined_type.ElementIdentifier = type_identifier
                                                                        for _import in imports:
                                                                            parts = _import.split('.')
                                                                            if '<' in type_identifier:
                                                                                type_identifier = type_identifier[:type_identifier.index('<')]
                                                                            if parts[-1] == type_identifier:
                                                                                java_user_defined_type.PackageName = _import[:(_import.index(type_identifier)-1)]
                                                                                break
                                                                            
                                                                    if java_user_defined_type.ElementIdentifier in ['String', 'Boolean', 'Integer', 'Float', 'Object']:
                                                                        java_user_defined_type.PackageName = 'java.lang'
                                                                        
                                                                    if java_user_defined_type.PackageName:
                                                                        java_invoked_method.parent = java_user_defined_type
                                                                        
                                                                if _invocation.arguments:
                                                                    if isinstance(_invocation.arguments, list):
                                                                        argument_order = 0
                                                                        for _argument in _invocation.arguments:
                                                                            argument = None
                                                                            if isinstance(_argument, javalang.tree.Literal):
                                                                                argument = {'name':'', 'value':_argument.value}
                                                                            elif isinstance(_argument, javalang.tree.ClassReference):
                                                                                if isinstance(_argument.type, javalang.tree.ReferenceType):
                                                                                    argument = {'name':get_reference_type(_argument.type) , 'value':''}
                                                                            elif isinstance(_argument, javalang.tree.MemberReference):
                                                                                argument = get_member(_argument, _declaration)
                                                                                if not argument['value']:
                                                                                    argument = get_member(_argument, _type)
                                                                            elif isinstance(_argument, javalang.tree.BinaryOperation):
                                                                                literal_value = ''
                                                                                if isinstance(_argument.operandl, javalang.tree.Literal):
                                                                                    literal_value = _argument.operandl.value
                                                                                elif isinstance(_argument.operandl, javalang.tree.MemberReference):
                                                                                    literal_value = get_member(_argument.operandl, _declaration)['value']
                                                                                    if not literal_value:
                                                                                        literal_value = get_member(_argument.operandl, _type)['value']
                                                                                if isinstance(_argument.operandr, javalang.tree.Literal):
                                                                                    literal_value += _argument.operandr.value
                                                                                elif isinstance(_argument.operandr, javalang.tree.MemberReference):
                                                                                    literal_value += get_member(_argument.operandr, _declaration)['value']
                                                                                    if not literal_value:
                                                                                        literal_value += get_member(_argument.operandr, _type)['value']        
                                                                                argument = {'name':'', 'value':re.sub(r'\"', '', literal_value)}                                                          
                                                                            
                                                                            if argument:
                                                                                argument_order += 1
                                                                                if not argument['name']:
                                                                                    argument['name'] = 'NOT_AVAILABLE'
                                                                                if not argument['value']:
                                                                                    argument['value'] = 'NOT_AVAILABLE'
                                                                                java_method_argument = metamodel.JavaMethodParameter()
                                                                                java_method_argument.ParentProjectName = module_name
                                                                                java_method_argument.ArtifactFileName = java_file
                                                                                java_method_argument.ElementIdentifier = argument['name']
                                                                                java_method_argument.ElementProfile = 'COMPILE'
                                                                                java_method_argument.FieldValue = argument['value']
                                                                                java_method_argument.ParameterOrder = argument_order 
                                                                                java_invoked_method.parameters.append(java_method_argument)
                                                                            
                                                                java_method.invokes.append(java_invoked_method)
                                                                
                                                    java_element.methods.append(java_method)
                                        
                                        module_project.layers[-1].elements.append(java_element)

                        except Exception as e:
                            print('---ERROR---')
                            print(str(e))
                            continue
            """
            # append module to application project
            application_project.modules.append(module_project)                
                
        # append application project instance to application
        application.application_project = application_project          

        # append application instance to model
        model.application = application
        
        # export instance model to XMI file
        model_resource_set = ResourceSet()
        model_resource = model_resource_set.create_resource(URI(psm_instance_file))
        model_resource.append(model)
        model_resource.save()
        
        # edit PSM:RootPSM element
        xmlns_xsi = ''
        xsi_schemaLocation = ''
        psm_ecore_dict = xml_to_dict(psm_ecore_file)
        if 'ecore:EPackage' in psm_ecore_dict: 
            if '@xmlns:xsi' in psm_ecore_dict['ecore:EPackage']:
                xmlns_xsi = psm_ecore_dict['ecore:EPackage']['@xmlns:xsi']
            if '@nsURI' in psm_ecore_dict['ecore:EPackage'] and '@name' in psm_ecore_dict['ecore:EPackage']:
                xsi_schemaLocation = psm_ecore_dict['ecore:EPackage']['@nsURI'] + ' ' + psm_ecore_dict['ecore:EPackage']['@name'] + '.ecore'

        if xmlns_xsi and xsi_schemaLocation:
            file_lines = [line.rstrip() for line in open(psm_instance_file, encoding='utf8')]
            file_lines[1] = file_lines[1].rstrip('>') + ' xsi:schemaLocation="' + xsi_schemaLocation + '" >'
            """
            if xmlns_xsi:
                file_lines[1] = file_lines[1].rstrip('>') + ' xmlns:xsi="' + xmlns_xsi + '" >'
            """
            with open(psm_instance_file, 'w') as file:
                file.writelines("%s\n" % line for line in file_lines)

        end_time = datetime.now().strftime("%H:%M:%S")
        print(start_time)
        print(end_time)



