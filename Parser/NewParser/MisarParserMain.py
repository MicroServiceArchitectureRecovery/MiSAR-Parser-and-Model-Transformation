############################
# Developed by RanaFakeeh-87
# 01/20/2020
# Updated by RanaFakeeh-87
# 11/01/2022
# Updated by kevinvahdat01
# 05/10/2023
############################

from MisarParserDocker import *
from MisarParserJava import *
from pyecore.resources import ResourceSet, URI
from pyecore.utils import DynamicEPackage
import os
import re
from datetime import datetime
import javalang

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

def multi_module_part1(multi_module_project_name, app_build_files):
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
    return multi_module_project

def multi_module_part2(module_build_dirs, module_build_files, multi_module_project, multi_module_project_name, application_containers):
    # create modules for application project
    for module_build_dir in module_build_dirs:
        # get module name from project folder name
        module_name = os.path.basename(module_build_dir)
        # get module name from container name
        for container_name, container in application_containers.items():
            if 'build' in container:
                if module_name in container['build']:
                    module_name = container_name
            if 'image' in container:
                if module_name in container['image']:
                    module_name = container_name
        # get module name from POM build file
        build_file = ''
        for module_build_file in module_build_files:
            if module_build_file.startswith(module_build_dir):
                build_file = module_build_file
        multi_module_project['modules'][module_name] = {}
        multi_module_project['modules'][module_name]['parent'] = multi_module_project_name
        multi_module_project['modules'][module_name]['build'] = build_file
        multi_module_project['modules'][module_name]['artifactId'] = module_name
        multi_module_project['modules'][module_name]['libraries'] = []
        multi_module_project['modules'][module_name]['properties'] = []
        multi_module_project['modules'][module_name]['java_elements'] = []

def multi_module_library_part(multi_module_project, module_name, app_root_dir, metamodel):
    print('\nmodule_name = {}'.format(module_name))
    spring_boot_app = False
    spring_web_flux_app = False

    # fetch module libraries
    module_build_file = multi_module_project['modules'][module_name]['build']
    module_libraries = []
    module_libraries = get_library_list(module_libraries, module_build_file, app_root_dir)
    for library in module_libraries:
        if library['groupId'] in ['org.springframework.boot', 'org.springframework.cloud']:
            spring_boot_app = True
        if 'webflux' in library['artifactId'] or 'reactive' in library['artifactId'] or 'reactor' in library[
            'artifactId']:
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

    return([module_project, spring_boot_app])

def annotation_generator(metamodel, module_name, java_file, annotation):
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
    return (java_annotation)

def data_type_generator(input_target, metamodel, module_name, java_file, imports):
    element_identifier = get_reference_type(input_target)
    java_data_type = metamodel.JavaDataType()
    java_data_type.ParentProjectName = module_name
    java_data_type.ArtifactFileName = java_file
    java_data_type.ElementIdentifier = element_identifier
    java_data_type.ElementProfile = 'COMPILE'
    java_data_type.PackageName = 'java.lang'
    java_data_type.IsPrimitive = True
    java_data_type.JsonSchema = '{"title":"' + element_identifier + '","type":"number"}'
    if element_identifier.lower() in ['string', 'boolean']:
        java_data_type.JsonSchema = '{"title":"' + element_identifier + '","type":"' + element_identifier.lower() + '"}'
    if isinstance(input_target, javalang.tree.ReferenceType):
        java_data_type.IsPrimitive = False
        if element_identifier.lower() not in ['string', 'boolean']:
            java_data_type.JsonSchema = '{"title":"' + element_identifier + '","type":"object","properties":{}}'
        for _import in imports:
            parts = _import.split('.')
            if '<' in element_identifier:
                element_identifier = element_identifier[:element_identifier.index('<')]
            if parts[-1] == element_identifier:
                java_data_type.PackageName = _import[:(_import.index(element_identifier) - 1)]
    return java_data_type


def parser(txt_proj_name, txt_proj_dir, txt_psm_ecore, lst_docker_compose, lst_app_build, lst_module_build_dir, lst_module_build, lst_app_config_dir, txt_output_dir):
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


    psm_instance_file_name = multi_module_project_name+"-PSM"+'.xmi'
    if len(output_dir) != 0:
        psm_instance_file = output_dir+"/"+psm_instance_file_name
    else:
        psm_instance_file = psm_ecore_file.replace(os.path.basename(psm_ecore_file), psm_instance_file_name)

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
    application_containers = docker_container_part1(docker_compose_files, multi_module_project_name)

    # parse dockerfile artifacts to update image and ports information
    docker_container_part2(application_containers, app_root_dir)

    # create containers instance and append it to application instance
    docker_container_part3(application_containers, application, metamodel)

    # parse multi module project build artifacts (pom.xml / build.gradle) into application project and its module projects
    multi_module_project = multi_module_part1(multi_module_project_name, app_build_files)

    # create application project instance
    application_project = metamodel.ApplicationProject()
    application_project.ParentProjectName = multi_module_project['parent']
    application_project.ArtifactFileName = multi_module_project['build']
    application_project.ProjectArtifactId = multi_module_project['artifactId']


    # create modules for application project
    multi_module_part2(module_build_dirs, module_build_files, multi_module_project, multi_module_project_name, application_containers)

    # create libraries and properties instances for every module project
    for module_name in multi_module_project['modules']:

        project_initialiser = multi_module_library_part(multi_module_project, module_name, app_root_dir, metamodel)

        module_project = project_initialiser[0]

        # fetch module properties
        module_properties = []
        module_properties += get_property_list('application', module_name, app_root_dir, '')
        module_properties += get_property_list('bootstrap', module_name, app_root_dir, '')
        #application_name = ''
        application_name = module_name
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

        #parse java files
        java_main_parser(metamodel, module_name, module_project, multi_module_project, app_root_dir, project_initialiser[1])

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

