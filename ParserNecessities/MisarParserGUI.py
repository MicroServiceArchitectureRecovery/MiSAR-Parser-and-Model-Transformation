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

def yaml_to_dict(filename):
    yaml_dict = {}
    with open(filename) as file:
        yaml_dict = yaml.load(file, Loader=yaml.FullLoader)
    return yaml_dict

def Installer(Location, targetLink):
    from git import Repo
    Repo.clone_from(
        "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git",
        (os.path.expanduser('~') + "/" + Location))
    repo = Repo("https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git")
    branch_list = [r.remote_head for r in repo.remote().refs]
    print(branch_list)
    remote_refs = repo.remote().refs

    for refs in remote_refs:
        print(refs.name)
    try:
        Repo.clone_from(
            "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git",
            (os.path.expanduser('~') + "/" + Location), branch="main")
        if os.path.isfile(
                (os.path.expanduser('~') + "\\" + Location + "\\Runnable Jar File\\MiSAR.jar")):
            return True
    except Exception as fail:
        return False


def Uninstaller(Location):
    targetLink = ""
    readOnly = True
    while readOnly:
        readOnly = False
        try:
            os.rmdir(os.path.expanduser('~') + "\\" + Location)
        except OSError:
            try:
                shutil.rmtree((os.path.expanduser('~') + "\\" + Location))
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
                # print(targetLink)
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
        if inputClass.name == "psmEcore":
            filename = filedialog.askopenfilename()
            if filename:
                inputClass.ent.configure(state='normal')
                inputClass.ent.delete(0, 'end')
                inputClass.ent.insert(0, filename)
                inputClass.ent.configure(state='readonly', readonlybackground='white')

        elif inputClass.name in ["dockerCompose", "appBuild", "moduleBuild"]:
            files = filedialog.askopenfilenames()
            for file in files:
                if file not in inputClass.lst.get(0, 'end'):
                    inputClass.lst.insert('end', file)
                    inputClass.lst.configure(background='white')
                    if inputClass.name == "dockerCompose":
                        if proj_dir.ent.get().strip():
                            autoImporter(proj_dir.ent.get().strip())
                        else:
                            messagebox.showinfo("Automatic Importer", "Would you like to save time by automatically importing the required files? Simply import the master folder's directory! The area to import it to will be marked in green.")
                            proj_dir.ent.configure(readonlybackground='lime')
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
                    else:
                        messagebox.showinfo("Automatic Importer",
                                            "Would you like to save time by automatically importing the required files? Simply import the docker compose file within the master folder's directory! The area to import it to will be marked in green.")
                        docker_compose.lst.configure(background='lime')
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
    target = ""
    for x in range(0, len(inputDirectory)):
        target = target + inputDirectory[x]
        if inputDirectory[x] == "/":
            target = ""
    return target


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
                                       "Would you like to try and automatically import all of the required files located within " + folderNameCalc(
                                           inputDirectory) + "?", icon="info")
    if automatic == "yes":
        docker_compose_files = []
        for docker_compose_file in docker_compose.lst.get(0, 'end'):
            if docker_compose_file.strip():
                docker_compose_files.append(docker_compose_file)
                application_containers = {}
                for docker_compose_file in docker_compose_files:
                    docker_compose_dict = {}
                    if docker_compose_file.endswith(('.yml', '.yaml')):
                        docker_compose_dict = yaml_to_dict(docker_compose_file)
                    if 'services' in docker_compose_dict:
                        docker_compose_dict = docker_compose_dict['services']
                    for container_name in docker_compose_dict:
                        if 'build' in docker_compose_dict[container_name] or 'image' in docker_compose_dict[container_name]:
                            if container_name not in application_containers:
                                application_containers[container_name] = {}
        dockerList = list(application_containers.keys())
        print(dockerList)

        for file in os.listdir(inputDirectory):
            targetDirectory = inputDirectory + "/" + file
            if file in dockerList:
                if os.path.isdir(targetDirectory):
                    if targetDirectory not in module_build_dir.lst.get(0, 'end'):
                        module_build_dir.lst.insert('end', targetDirectory)
                    if os.path.isfile(targetDirectory + "/pom.xml"):
                        if targetDirectory + "/pom.xml" not in module_build.lst.get(0, 'end'):
                            module_build.lst.insert('end', targetDirectory + "/pom.xml")
            if os.path.isfile(inputDirectory + "/pom.xml"):
                if inputDirectory + "/pom.xml" not in app_build.lst.get(0, 'end'):
                    app_build.lst.insert('end', inputDirectory + "/pom.xml")


def pomScanner(inputClass, inputDirectory):
    pomScan = messagebox.askquestion("POM Scanner",
                                     "Would you like to add any corresponding POM files that exist within " + folderNameCalc(
                                         inputDirectory) + "?", icon="info")
    if pomScan == "yes":
        inputDirectory = inputDirectory + "/pom.xml"
        print(inputDirectory)
        print(os.path.isfile(inputDirectory))
        if os.path.isfile(inputDirectory):
            if inputClass.name == "projectDir":
                if inputDirectory not in app_build.lst.get(0, 'end'):
                    app_build.lst.insert('end', inputDirectory)
            if inputClass.name == "moduleBuildDir":
                if inputDirectory not in module_build.lst.get(0, 'end'):
                    module_build.lst.insert('end', inputDirectory)
        else:
            messagebox.showerror('POM Scanner', 'This folder does not have a corresponding POM file.')

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

        create_psm_instance(txt_proj_name, proj_dir.ent, psm_ecore, docker_compose.lst, app_build.lst, module_build_dir.lst,
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
    'A Python application to parse YAML, XML and JAVA artifacts of a microservice architecture project into a MiSAR PSM model. NEW!')
window.protocol("WM_DELETE_WINDOW", window_quit)

# Generates the project name input
lbl_proj_name = tkinter.Label(window, text='Type Multi-Module Project Name (mandatory):')
lbl_proj_name.grid(row=1, column=0, columnspan=2, sticky='W' + 'S')
txt_proj_name = tkinter.Entry(window, text='', width=50, foreground='navy')
txt_proj_name.grid(row=2, column=0, padx=2, pady=2, sticky='N')

# Generates the windows
proj_dir = smallFrame("projectDir", window, "Select Multi-Module Project Build Directory (mandatory):", 2, 0,
                      "directory")
psm_ecore = tkinter.Entry(window, text='', width=50, foreground='navy')
psm_ecore.configure(state='normal')
psm_ecore.delete(0, 'end')
psm_ecore.insert(0, str(os.path.expanduser('~') + "\MiSAR\Parser\TransformationEngineNecessities\source\PSM.ecore"))
psm_ecore.configure(state='readonly', readonlybackground='white')
docker_compose = largeFrame("dockerCompose", window, "Select Docker Compose Files (mandatory):", 1, 2, "file")
app_build = largeFrame("appBuild", window, "Select Multi-Module Project POM Build Files (optional):", 1, 4, "file")
module_build_dir = largeFrame("moduleBuildDir", window, "Select Module Projects Build Directories (mandatory):", 7, 0,
                              "directory")
module_build = largeFrame("moduleBuild", window, "Select Module Projects POM Build Files (optional):", 7, 2, "file")
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



