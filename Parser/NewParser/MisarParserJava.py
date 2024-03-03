import os
import xmltodict
from collections import OrderedDict
import re
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
                    #print(files)
    return artifact_list

def xml_to_dict(filename):
    xml_dict = {}
    with open(filename, encoding='utf8') as file:
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
    with open(config_file, encoding='utf8') as file:
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
        with open(config_file, encoding='utf8') as file:
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
        if parts[2] and ('-' in parts[2]):
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


def get_annotations(element, properties=None):
    annotations = []
    for _annotation in element.annotations:
        annotation = {}
        annotation['name'] = _annotation.name
        annotation['parameters'] = []
        if _annotation.element:
            if isinstance(_annotation.element, javalang.tree.Literal):
                annotation['parameters'].append({'name':'NOT_AVAILABLE', 'value':_annotation.element.value})
                # evaluate configuration property in literal
                literal = _annotation.element.value.strip('"')
                if re.findall('\$\{([.a-z]+)\}', literal):
                    _property = re.findall('\$\{([.a-z]+)\}', literal)[0]
                    if properties:
                        for p in properties:
                            if p['property'] == _property:
                                annotation['parameters'][-1]['value'] = p['value']
            elif isinstance(_annotation.element, list):
                for _element in _annotation.element:
                    if isinstance(_element, javalang.tree.ElementValuePair):
                        if isinstance(_element.value, javalang.tree.Literal):
                            annotation['parameters'].append({'name':_element.name, 'value':_element.value.value})
                            # evaluate configuration property in literal
                            literal = _element.value.value.strip('"')
                            if re.findall('\$\{([.a-z]+)\}', literal):
                                _property = re.findall('\$\{([.a-z]+)\}', literal)[0]
                                if properties:
                                    for p in properties:
                                        if p['property'] == _property:
                                            annotation['parameters'][-1]['value'] = p['value']
                        elif isinstance(_element.value, javalang.tree.MemberReference):
                            annotation['parameters'].append({'name':_element.name, 'value':_element.value.qualifier + '.' + _element.value.member})
                            # get the literal value from referenced member
        annotations.append(annotation)
    return annotations

def get_reference_type(reference_type):
    type_name = reference_type.name
    if isinstance(reference_type, javalang.tree.ReferenceType):
        if reference_type.arguments:
            type_name += '<'
            arguments = ''
            for _argument in reference_type.arguments:
                if isinstance(_argument, javalang.tree.TypeArgument):
                    if _argument.type:
                        if isinstance(_argument.type, javalang.tree.ReferenceType):
                            arguments += get_reference_type(_argument.type) + ','
            arguments = arguments.rstrip(',')
            type_name += arguments + '>'

    return type_name

def evaluate_field(field1, type_name, properties, module_name, app_root_dir):
    # print('evaluate_field ->',field1.declarators[0].name)
    # print('in type ->',type_name)
    field_value = 'NOT_AVAILABLE'

    if field1.annotations:
        for annotation in get_annotations(field1, properties):
            if annotation['name'] == 'Value':
                if annotation['parameters']:
                    field_value = annotation['parameters'][0]['value']
                    if not field_value.strip('"'):
                        field_value = 'NOT_AVAILABLE'
                    return field_value

    if field1.declarators:
        for _declarator in field1.declarators:
            if isinstance(_declarator, javalang.tree.VariableDeclarator):
                if _declarator.initializer:
                    if isinstance(_declarator.initializer, javalang.tree.Literal):
                        field_value = _declarator.initializer.value
                        return field_value
                    if isinstance(_declarator.initializer, javalang.tree.MemberReference):
                        member = _declarator.initializer.member
                        qualifier = _declarator.initializer.qualifier
                        if not qualifier:
                            qualifier = type_name
                        # get referenced field
                        referenced_field = get_referenced_field(member, qualifier, module_name, app_root_dir)
                        if referenced_field:
                            field_value = evaluate_field(referenced_field, qualifier, properties, module_name, app_root_dir)
                            return field_value
            break
    return field_value

def get_referenced_field(field_name, type_name, module_name, app_root_dir):
    for java_file in fetch_artifacts(type_name+'.java', module_name, app_root_dir):
        if '/src/test/' not in java_file:
            try:
                with open(java_file, encoding='utf8') as file:
                    tree = javalang.parse.parse(file.read())
                    for _type in tree.types:
                        if isinstance(_type, javalang.tree.ClassDeclaration):
                            if _type.body:
                                for _declaration in _type.body:
                                    for path, field in _declaration.filter(javalang.tree.FieldDeclaration):
                                        if field.declarators:
                                            for _declarator in field.declarators:
                                                if isinstance(_declarator, javalang.tree.VariableDeclarator):
                                                    if field_name == _declarator.name:
                                                        return(field)
            except:
                continue
    return None

def evaluate_method_field(field1, method1, type_name, properties, module_name, app_root_dir):
    # print('evaluate_method_field ->',field1.declarators[0].name)
    # print('in type ->',type_name)
    field_value = 'NOT_AVAILABLE'

    if field1.declarators:
        for _declarator in field1.declarators:
            if isinstance(_declarator, javalang.tree.VariableDeclarator):
                if _declarator.initializer:
                    if isinstance(_declarator.initializer, javalang.tree.Literal):
                        field_value = _declarator.initializer.value
                        return field_value

    return field_value

def java_data_type_generator(java_data_type, module_name, java_file, element_identifier, data_instance_type, imports):
    java_data_type.ParentProjectName = module_name
    java_data_type.ArtifactFileName = java_file
    java_data_type.ElementIdentifier = element_identifier
    java_data_type.ElementProfile = 'COMPILE'
    java_data_type.PackageName = 'java.lang'
    java_data_type.IsPrimitive = True
    java_data_type.JsonSchema = '{"title":"' + element_identifier + '","type":"number"}'
    if element_identifier.lower() in ['string', 'boolean']:
        java_data_type.JsonSchema = '{"title":"' + element_identifier + '","type":"' + element_identifier.lower() + '"}'
    if isinstance(data_instance_type, javalang.tree.ReferenceType):
        java_data_type.IsPrimitive = False
        if element_identifier.lower() not in ['string', 'boolean']:
            java_data_type.JsonSchema = '{"title":"' + element_identifier + '","type":"object","properties":{}}'
        for _import in imports:
            parts = _import.split('.')
            if '<' in element_identifier:
                element_identifier = element_identifier[
                                     :element_identifier.index('<')]
            if parts[-1] == element_identifier:
                java_data_type.PackageName = _import[:(
                        _import.index(element_identifier) - 1)]
    return java_data_type

def java_annotation_generator(java_annotation, module_name, java_file, annotation, metamodel):
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
    return java_annotation

def java_interface_generator(java_interface, module_name, java_file, element_identifier, imports):
    java_interface.ParentProjectName = module_name
    java_interface.ArtifactFileName = java_file
    java_interface.ElementIdentifier = element_identifier
    java_interface.ElementProfile = 'COMPILE'
    java_interface.JsonSchema = ''
    for _import in imports:
        parts = _import.split('.')
        if '<' in element_identifier:
            element_identifier = element_identifier[
                                 :element_identifier.index('<')]
        if parts[-1] == element_identifier:
            java_interface.PackageName = _import[:(
                    _import.index(element_identifier) - 1)]
    return java_interface

def java_user_defined_type_generator(java_user_defined_type, module_name, java_file, element_identifier, imports):
    java_user_defined_type.ParentProjectName = module_name
    java_user_defined_type.ArtifactFileName = java_file
    java_user_defined_type.ElementIdentifier = element_identifier
    java_user_defined_type.ElementProfile = 'COMPILE'
    java_user_defined_type.JsonSchema = ''
    for _import in imports:
        parts = _import.split('.')
        if '<' in element_identifier:
            element_identifier = element_identifier[
                                 :element_identifier.index('<')]
        if parts[-1] == element_identifier:
            java_user_defined_type.PackageName = _import[:(
                    _import.index(element_identifier) - 1)]
    return java_user_defined_type


def java_main_parser(metamodel, module_name, module_project, multi_module_project, app_root_dir, spring_boot_app):
    # parse java files
    if spring_boot_app:
        java_layer = metamodel.SpringWebApplicationLayer()
        java_layer.ParentProjectName = module_name
        java_layer.LayerName = 'SpringWebApplicationLayer'
        module_project.layers.append(java_layer)

    for java_file in fetch_artifacts('.java', module_name, app_root_dir):
        print('java_file = {}'.format(os.path.basename(java_file)))
        try:
            with open(java_file, encoding='utf8') as file:
                tree = javalang.parse.parse(file.read())
                # if 'RabbitConfiguration' in java_file:
                ## print(tree)
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
                                    java_element.implements.append(java_interface_generator(java_interface, module_name, java_file, element_identifier, imports))
                                elif isinstance(_type.implements, list):
                                    for _interface in _type.implements:
                                        if isinstance(_interface, javalang.tree.ReferenceType):
                                            element_identifier = get_reference_type(_interface)
                                            java_interface = metamodel.JavaInterfaceType()
                                            java_element.implements.append(java_interface_generator(java_interface, module_name, java_file, element_identifier, imports))
                        elif isinstance(_type, javalang.tree.InterfaceDeclaration):
                            java_element = metamodel.JavaInterfaceType()

                        java_element.ParentProjectName = module_name
                        java_element.ArtifactFileName = java_file
                        java_element.ElementIdentifier = _type.name
                        java_element.ElementProfile = 'COMPILE'
                        java_element.JsonSchema = ''
                        java_element.PackageName = package_name

                        # add import list
                        for _import in imports:
                            parts = _import.split('.')
                            java_imported_user_defined_type = metamodel.JavaUserDefinedType()
                            java_imported_user_defined_type.ParentProjectName = module_name
                            java_imported_user_defined_type.ArtifactFileName = java_file
                            java_imported_user_defined_type.ElementIdentifier = parts[-1]
                            java_imported_user_defined_type.ElementProfile = 'COMPILE'
                            java_imported_user_defined_type.IsPrimitive = False
                            java_imported_user_defined_type.JsonSchema = ''
                            java_imported_user_defined_type.PackageName = '.'.join(parts[:-1])
                            java_element.imports.append(java_imported_user_defined_type)

                        if _type.extends:
                            if isinstance(_type.extends, javalang.tree.ReferenceType):
                                element_identifier = get_reference_type(_type.extends)
                                java_user_defined_type = metamodel.JavaUserDefinedType()
                                java_element.extends.append(java_user_defined_type_generator(java_user_defined_type, module_name, java_file, element_identifier, imports))
                            elif isinstance(_type.extends, list):
                                for _super in _type.extends:
                                    if isinstance(_super, javalang.tree.ReferenceType):
                                        element_identifier = get_reference_type(_super)
                                        java_user_defined_type = metamodel.JavaUserDefinedType()
                                        java_element.extends.append(java_user_defined_type_generator(java_user_defined_type, module_name, java_file, element_identifier, imports))

                        if _type.annotations:
                            for annotation in get_annotations(_type,
                                                              multi_module_project['modules'][module_name][
                                                                  'properties']):
                                java_annotation = metamodel.JavaAnnotation()
                                java_element.annotations.append(java_annotation_generator(java_annotation, module_name, java_file, annotation, metamodel))
                        # parse type body
                        if _type.body:
                            for _declaration in _type.body:
                                # parse type fields
                                for path, _field_declaration in _declaration.filter(
                                        javalang.tree.FieldDeclaration):
                                    # if 'AdminBasicInfoServiceImpl' in java_file:
                                    # print('_field_declaration ->',_field_declaration)
                                    java_field = metamodel.JavaDataField()

                                    java_field.ParentProjectName = module_name
                                    java_field.ArtifactFileName = java_file
                                    java_field.ElementIdentifier = ''
                                    java_field.ElementProfile = 'COMPILE'
                                    java_field.FieldValue = 'NOT_AVAILABLE'
                                    if _field_declaration.declarators:
                                        for _declarator in _field_declaration.declarators:
                                            if isinstance(_declarator, javalang.tree.VariableDeclarator):
                                                java_field.ElementIdentifier = _declarator.name
                                                break

                                    # parse field annotations
                                    if _field_declaration.annotations:
                                        for annotation in get_annotations(_field_declaration,
                                                                          multi_module_project['modules'][
                                                                              module_name]['properties']):
                                            java_annotation = metamodel.JavaAnnotation()
                                            java_field.annotations.append(java_annotation_generator(java_annotation, module_name, java_file, annotation, metamodel))
                                            # parse field value
                                    java_field.FieldValue = evaluate_field(_field_declaration, _type.name,
                                                                           multi_module_project['modules'][
                                                                               module_name]['properties'],
                                                                           module_name, app_root_dir)
                                    # print('field value ->', java_field.FieldValue)
                                    # parse field type
                                    if _field_declaration.type:
                                        element_identifier = get_reference_type(_field_declaration.type)
                                        java_data_type = metamodel.JavaDataType()
                                        java_field.type = java_data_type_generator(java_data_type, module_name, java_file, element_identifier, _field_declaration.type, imports)

                                    java_element.fields.append(java_field)
                                # parse type methods
                                for path, _method_declaration in _declaration.filter(
                                        javalang.tree.MethodDeclaration):
                                    # if 'AdminBasicInfoServiceImpl' in java_file:
                                    # print('_method_declaration ->',_method_declaration)
                                    java_method = metamodel.JavaMethod()
                                    java_method.ParentProjectName = module_name
                                    java_method.ArtifactFileName = java_file
                                    java_method.ElementIdentifier = _method_declaration.name
                                    java_method.ElementProfile = 'COMPILE'
                                    java_method.RootCallingMethod = ''
                                    # parse method parent
                                    java_user_defined_data_type = metamodel.JavaUserDefinedType()
                                    java_user_defined_data_type.ParentProjectName = java_element.ParentProjectName
                                    java_user_defined_data_type.ArtifactFileName = java_element.ArtifactFileName
                                    java_user_defined_data_type.ElementIdentifier = java_element.ElementIdentifier
                                    java_user_defined_data_type.ElementProfile = java_element.ElementProfile
                                    java_user_defined_data_type.JsonSchema = java_element.JsonSchema
                                    java_user_defined_data_type.PackageName = java_element.PackageName
                                    java_method.parent = java_user_defined_data_type
                                    # parse method annotations
                                    if _method_declaration.annotations:
                                        for annotation in get_annotations(_method_declaration,
                                                                          multi_module_project['modules'][
                                                                              module_name]['properties']):
                                            java_annotation = metamodel.JavaAnnotation()
                                            java_method.annotations.append(java_annotation_generator(java_annotation, module_name, java_file, annotation, metamodel))
                                    # parse method returns
                                    if _method_declaration.return_type:
                                        element_identifier = get_reference_type(
                                            _method_declaration.return_type)
                                        java_data_type = metamodel.JavaDataType()
                                        java_method.returns = java_data_type_generator(java_data_type, module_name, java_file, element_identifier, _method_declaration.return_type, imports)
                                        # parse method parameters
                                    if _method_declaration.parameters:
                                        parameter_order = 0
                                        for _parameter in _method_declaration.parameters:
                                            if isinstance(_parameter, javalang.tree.FormalParameter):
                                                parameter_order += 1
                                                java_method_parameter = metamodel.JavaMethodParameter()
                                                java_method_parameter.ParentProjectName = module_name
                                                java_method_parameter.ArtifactFileName = java_file
                                                java_method_parameter.ElementIdentifier = _parameter.name
                                                java_method_parameter.ElementProfile = 'COMPILE'
                                                java_method_parameter.FieldValue = 'NOT_AVAILABLE'
                                                java_method_parameter.ParameterOrder = parameter_order
                                                # parse method parameter annotations
                                                if _parameter.annotations:
                                                    for annotation in get_annotations(_parameter,
                                                                                      multi_module_project[
                                                                                          'modules'][
                                                                                          module_name][
                                                                                          'properties']):
                                                        java_annotation = metamodel.JavaAnnotation()
                                                        java_method_parameter.annotations.append(java_annotation_generator(java_annotation, module_name, java_file, annotation, metamodel))
                                                # parse method parameter type
                                                if _parameter.type:
                                                    element_identifier = get_reference_type(_parameter.type)
                                                    java_data_type = metamodel.JavaDataType()
                                                    java_method_parameter.type = java_data_type_generator(java_data_type, module_name, java_file, element_identifier, _parameter.type, imports)
                                                java_method.parameters.append(java_method_parameter)

                                    if _method_declaration.body:
                                        for _element in _method_declaration.body:
                                            # parse method fields
                                            for path, _local_variable in _element.filter(
                                                    javalang.tree.LocalVariableDeclaration):
                                                # if 'AdminBasicInfoServiceImpl' in java_file:
                                                # print('_local_variable ->',_local_variable)

                                                java_field = metamodel.JavaDataField()

                                                java_field.ParentProjectName = module_name
                                                java_field.ArtifactFileName = java_file
                                                java_field.ElementIdentifier = 'NOT_AVAILABLE'
                                                java_field.ElementProfile = 'COMPILE'
                                                java_field.FieldValue = 'NOT_AVAILABLE'
                                                if _local_variable.declarators:
                                                    for _declarator in _local_variable.declarators:
                                                        if isinstance(_declarator,
                                                                      javalang.tree.VariableDeclarator):
                                                            java_field.ElementIdentifier = _declarator.name
                                                            break

                                                # parse field value
                                                java_field.FieldValue = evaluate_method_field(
                                                    _local_variable, _method_declaration, _type.name,
                                                    multi_module_project['modules'][module_name][
                                                        'properties'], module_name, app_root_dir)
                                                # print('method field value ->', java_field.FieldValue)

                                                # parse field type
                                                if _local_variable.type:
                                                    element_identifier = get_reference_type(
                                                        _local_variable.type)
                                                    java_data_type = metamodel.JavaDataType()
                                                    java_field.type = java_data_type_generator(java_data_type, module_name, java_file, element_identifier, _local_variable.type, imports)

                                                java_method.fields.append(java_field)

                                            # parse method invokes
                                            for path, _invocation in _element.filter(
                                                    javalang.tree.MethodInvocation):
                                                # if 'AdminBasicInfoServiceImpl' in java_file:
                                                # print('_invocation ->',_invocation)
                                                element_identifier = _invocation.member
                                                java_invoked_method = metamodel.JavaMethod()
                                                java_invoked_method.ParentProjectName = module_name
                                                java_invoked_method.ArtifactFileName = java_file
                                                java_invoked_method.ElementIdentifier = element_identifier
                                                java_invoked_method.ElementProfile = 'COMPILE'
                                                java_invoked_method.RootCallingMethod = _method_declaration.name

                                                # parse invoked method parameters
                                                if _invocation.arguments:
                                                    argument_order = 0
                                                    for _argument in _invocation.arguments:
                                                        argument_order += 1
                                                        argument_value = 'NOT_AVAILABLE'
                                                        argument_name = 'NOT_AVAILABLE'
                                                        if isinstance(_argument,
                                                                      javalang.tree.MemberReference):
                                                            argument_name = _argument.member

                                                        # argument_value = evaluate_method_field(_argument)

                                                        java_method_argument = metamodel.JavaMethodParameter()
                                                        java_method_argument.ParentProjectName = module_name
                                                        java_method_argument.ArtifactFileName = java_file
                                                        java_method_argument.ElementIdentifier = argument_name
                                                        java_method_argument.ElementProfile = 'COMPILE'
                                                        java_method_argument.FieldValue = argument_value
                                                        java_method_argument.ParameterOrder = argument_order

                                                        # parse type of invoked method parameter

                                                        java_invoked_method.parameters.append(
                                                            java_method_argument)

                                                    # endfor _argument in _invocation.arguments:
                                                # endif _invocation.arguments:

                                                java_method.invokes.append(java_invoked_method)

                                    java_element.methods.append(java_method)

                        if spring_boot_app:
                            module_project.layers[-1].elements.append(java_element)

        except Exception as e:
            print('---ERROR---')
            print(str(e))
            continue
