############################
# Developed by RanaFakeeh-87
# 01/20/2020
# LAST UPDATE: 02/04/2026
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
from MisarParserMain import *
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
from pathlib import Path

USER_HOME_DIR = Path.home()
MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
from MisarParserConfig import describe_psm_selection
DEPENDENCY_BUILD_FILES = ["pom.xml", "requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg", "poetry.lock"]


def yaml_to_dict(filename):
    yaml_dict = {}
    with open(filename) as file:
        yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
    return yaml_dict


def Installer(Location, targetLink):
    from git import Repo
    install_path = USER_HOME_DIR / Path(Location)
    Repo.clone_from(
        "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git",
        install_path)
    repo = Repo("https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git")
    branch_list = [r.remote_head for r in repo.remote().refs]
    print(branch_list)
    remote_refs = repo.remote().refs

    for refs in remote_refs:
        print(refs.name)
    try:
        Repo.clone_from(
            "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git",
            install_path, branch="main")
        if os.path.isfile(install_path / "Runnable Jar File" / "MiSAR.jar"):
            return True
    except Exception as fail:
        return False


def Uninstaller(Location):
    targetLink = ""
    readOnly = True
    location_path = USER_HOME_DIR / Path(Location)
    while readOnly:
        readOnly = False
        try:
            os.rmdir(location_path)
        except OSError:
            try:
                shutil.rmtree(location_path)
            except PermissionError as fail:
                failEdit = (str(fail))
                commaActivate = False
                for x in range(0, len(failEdit)):
                    if failEdit[x] == "'" and commaActivate == True:
                        commaActivate = False
                    if commaActivate == True:
                        targetLink = targetLink + failEdit[x]
                    if failEdit[x] == "'" and commaActivate == False:
                        commaActivate = True
                targetLink = Path(targetLink)
                os.chmod(targetLink, stat.S_IWRITE)
                os.unlink(targetLink)
                try:
                    shutil.rmtree(targetLink)
                except FileNotFoundError:
                    pass
                targetLink = ""
                readOnly = True


def window_quit():
    window.quit()
    window.destroy()


def select(inputClass):
    print(inputClass.fileType)
    if inputClass.fileType == "file":
        if inputClass.name in ["dockerCompose", "appBuild", "moduleBuild"]:
            files = filedialog.askopenfilenames()
            for file in files:
                if file not in inputClass.lst.get(0, 'end'):
                    inputClass.lst.insert('end', file)
                    inputClass.lst.configure(background='white')
                    if inputClass.name == "dockerCompose":
                        if proj_dir.ent.get().strip():
                            autoImporter(proj_dir.ent.get().strip())
    elif inputClass.fileType == "directory":
        directory = filedialog.askdirectory()
        if directory:
            if inputClass.name in ["projectDir", "outputDir"]:
                inputClass.ent.configure(state='normal')
                inputClass.ent.delete(0, 'end')
                inputClass.ent.insert(0, directory)
                inputClass.ent.configure(state='readonly', readonlybackground='white')
                if inputClass.name == "projectDir":
                    if docker_compose.lst.size() > 0:
                        autoImporter(directory)
                    #pomScanner(inputClass, directory)
            elif inputClass.name in ["moduleBuildDir", "appConfigDir"]:
                if directory not in inputClass.lst.get(0, 'end'):
                    inputClass.lst.insert(inputClass.lst.size(), directory)
                    inputClass.lst.configure(background='white')
                    if inputClass.name == "moduleBuildDir":
                        pomScanner(inputClass, directory)


def delete_item(inputClass):
    inputClass.lst.delete(tkinter.ANCHOR)


def folderNameCalc(inputDirectory):
    return Path(inputDirectory).name


def forbiddenFinder(projName):
    clean = True
    AYE4BIDU = ["<", ">", ":", '"', "/", '\\', "|", "?", "*"]
    for x in range(0, len(projName)):
        for y in range(0, len(AYE4BIDU)):
            if projName[x] == AYE4BIDU[y]:
                clean = False
    return clean


def autoImporter(inputDirectory):
    automatic = messagebox.askquestion("Automatic Importer",
                                       "Would you like to use the automatic importer to try and automatically import all of the required files located within " + folderNameCalc(
                                           inputDirectory) + "? If you use the automatic importer, it will save you a lot of time uploading files manually.", icon="info")
    if automatic == "yes":
        input_dir_path = Path(inputDirectory)
        candidate_directories = []
        for docker_compose_file in docker_compose.lst.get(0, 'end'):
            if not docker_compose_file.strip():
                continue
            docker_compose_dict = {}
            if docker_compose_file.endswith(('.yml', '.yaml')):
                docker_compose_dict = yaml_to_dict(docker_compose_file)
            services = docker_compose_dict.get('services', docker_compose_dict)
            for container_name, service_definition in services.items():
                service_name_dir = input_dir_path / container_name
                if service_name_dir.is_dir():
                    candidate_directories.append(service_name_dir)
                build_definition = service_definition.get('build', '') if isinstance(service_definition, dict) else ''
                build_context = ''
                if isinstance(build_definition, str):
                    build_context = build_definition
                elif isinstance(build_definition, dict):
                    build_context = build_definition.get('context', '')
                if build_context:
                    build_path = (input_dir_path / build_context).resolve()
                    if build_path.is_dir():
                        candidate_directories.append(build_path)

        for targetDirectory in candidate_directories:
            target_text = str(targetDirectory)
            if target_text not in module_build_dir.lst.get(0, 'end'):
                module_build_dir.lst.insert('end', target_text)
            add_dependency_files_for_directory(targetDirectory, module_build.lst)
        add_dependency_files_for_directory(input_dir_path, app_build.lst)


def add_dependency_files_for_directory(inputDirectory, targetList):
    input_path = Path(inputDirectory)
    for dependency_file in DEPENDENCY_BUILD_FILES:
        candidate = input_path / dependency_file
        if candidate.is_file():
            candidate_text = str(candidate)
            if candidate_text not in targetList.get(0, 'end'):
                targetList.insert('end', candidate_text)


def pomScanner(inputClass, inputDirectory):
    dependencyScan = messagebox.askquestion("Build / Dependency Scanner",
                                            "Would you like to add any corresponding build or dependency files that exist within " + folderNameCalc(
                                                inputDirectory) + "?", icon="info")
    if dependencyScan == "yes":
        if inputClass.name == "projectDir":
            add_dependency_files_for_directory(inputDirectory, app_build.lst)
        if inputClass.name == "moduleBuildDir":
            add_dependency_files_for_directory(inputDirectory, module_build.lst)
        if inputClass.name not in ["projectDir", "moduleBuildDir"]:
            add_dependency_files_for_directory(inputDirectory, module_build.lst)


def create_psm_instance_final_checks():
    missingValueGenerator = ""
    txt_proj_name.configure(background="white")
    if not txt_proj_name.get().strip():
        missingValueGenerator = missingValueGenerator + "\nApplication Project Name missing"
        txt_proj_name.configure(background="red")
    if forbiddenFinder(txt_proj_name.get().strip()) == False:
        missingValueGenerator = missingValueGenerator + '\nApplication Project Name has forbidden characters\nList of fordidden characters:\n< > : " / \ | ? * '
        txt_proj_name.configure(background="red")
    if not proj_dir.ent.get().strip():
        missingValueGenerator = missingValueGenerator + "\nApplication Project Build Directory missing"
        proj_dir.ent.configure(readonlybackground='red')
    if not docker_compose.lst.size():
        missingValueGenerator = missingValueGenerator + "\nDocker Compose Files missing"
        docker_compose.lst.configure(background='red')
    if not module_build_dir.lst.size():
        missingValueGenerator = missingValueGenerator + "\nMicroservice Projects Build Directories missing"
        module_build_dir.lst.configure(background='red')
    if not output_dir.ent.get():
        missingValueGenerator = missingValueGenerator + "\nOutput Directory missing"
        output_dir.ent.configure(readonlybackground='red')
    if len(missingValueGenerator) <= 0:

        create_psm_instance(txt_proj_name, proj_dir.ent, None, docker_compose.lst, app_build.lst, module_build_dir.lst,
               module_build.lst, app_config_dir.lst, output_dir.ent)
    else:
        messagebox.showerror('Error!', ('The following errors are present:\n' + missingValueGenerator + "\n\nThese mandatory fields will be marked in red."))


class smallFrame:
    def __init__(self, name, targetWindow, description, inputRow, inputColumn, fileType):
        self.name = name
        self.targetWindow = targetWindow
        self.description = description
        self.fileType = fileType
        self.lbl = tkinter.Label(self.targetWindow, text=self.description)
        self.lbl.grid(row=inputRow, column=inputColumn, columnspan=2, sticky='W')
        self.ent = tkinter.Entry(targetWindow, text='', width=50, foreground='navy')
        self.ent.grid(row=(inputRow + 1), column=inputColumn, padx=2, pady=2, sticky='N')
        self.ent.configure(state='readonly', readonlybackground='white')
        self.addbutton = tkinter.Button(targetWindow, text='Browse', width=10)
        self.addbutton.configure(command=lambda button=self: select(self))
        self.addbutton.grid(row=(inputRow + 1), column=(inputColumn + 1), padx=2, pady=2, sticky='N')


class largeFrame:
    def __init__(self, name, targetWindow, description, inputRow, inputColumn, fileType):
        self.name = name
        self.targetWindow = targetWindow
        self.description = description
        self.fileType = fileType
        self.lbl = tkinter.Label(self.targetWindow, text=self.description)
        self.lbl.grid(row=inputRow, column=inputColumn, columnspan=2, sticky='W')
        self.frame = tkinter.Frame(targetWindow)
        self.frame.grid(row=(inputRow + 1), rowspan=2, column=inputColumn, padx=2, pady=2)
        self.xscroll = tkinter.Scrollbar(self.frame, orient='horizontal')
        self.yscroll = tkinter.Scrollbar(self.frame, orient='vertical')
        self.lst = tkinter.Listbox(self.frame, width=50, height=10, xscrollcommand=self.xscroll.set,
                                   yscrollcommand=self.yscroll.set, foreground='navy')
        self.xscroll.config(command=self.lst.xview)
        self.xscroll.pack(side='bottom', fill='x')
        self.yscroll.config(command=self.lst.yview)
        self.yscroll.pack(side='right', fill='y')
        self.lst.pack(side='left', fill='both', expand=1)
        self.addbutton = tkinter.Button(targetWindow, text='Add Item', width=10)
        self.addbutton.configure(command=lambda button=self: select(button))
        self.addbutton.grid(row=(inputRow + 1), column=(inputColumn + 1), padx=2, pady=2, sticky='N')
        self.delbutton = tkinter.Button(targetWindow, text='Delete', width=10)
        self.delbutton.configure(command=lambda button=self: delete_item(button))
        self.delbutton.grid(row=(inputRow + 2), column=(inputColumn + 1), padx=2, pady=2, sticky='N')


# Generates the window instance
window = tkinter.Tk()
window.title(
    'A Python application to parse YAML, XML, Java and Python artifacts of a microservice architecture project into a MiSAR PSM model. NEW!')
window.protocol("WM_DELETE_WINDOW", window_quit)
print('MiSAR parser startup PSM selection = {}'.format(describe_psm_selection()))

# Generates the project name input
lbl_proj_name = tkinter.Label(window, text='Type Multi-Module Project Name (mandatory):')
lbl_proj_name.grid(row=1, column=0, columnspan=2, sticky='W' + 'S')
txt_proj_name = tkinter.Entry(window, text='', width=50, foreground='navy')
txt_proj_name.grid(row=2, column=0, padx=2, pady=2, sticky='N')

# Generates the windows
proj_dir = smallFrame("projectDir", window, "Select Multi-Module Project Build Directory (mandatory):", 2, 0,
                      "directory")
docker_compose = largeFrame("dockerCompose", window, "Select Docker Compose Files (mandatory):", 1, 2, "file")
app_build = largeFrame("appBuild", window, "Select Multi-Module Project Build / Dependency Files (optional):", 1, 4, "file")
module_build_dir = largeFrame("moduleBuildDir", window, "Select Module Projects Build Directories (mandatory):", 7, 0,
                              "directory")
module_build = largeFrame("moduleBuild", window, "Select Module Projects Build / Dependency Files (optional):", 7, 2, "file")
app_config_dir = largeFrame("appConfigDir", window, "Select Centralized Configuration Directories (optional):", 7, 4,
                            "directory")

# Generates the output section
output_dir = smallFrame("outputDir", window, "Select Directory where the PSM will be saved (mandatory)", 3, 0,
                        "directory")

# Generates the create PSM button
btn_psm_instance = tkinter.Button(window, text='Create PSM Model', width=22, font=("Arial", 18))
btn_psm_instance.configure(command=lambda button=btn_psm_instance: create_psm_instance_final_checks())
btn_psm_instance.grid(row=11, column=0, columnspan=6, padx=2, pady=10)

# Installer("lol", "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git")

window.mainloop()