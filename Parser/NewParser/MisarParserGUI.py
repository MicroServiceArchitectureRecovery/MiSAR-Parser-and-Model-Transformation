############################
# Developed by RanaFakeeh-87
# 01/20/2020
# Updated by RanaFakeeh-87
# 11/01/2022
# Updated by kevinvahdat01
# 05/10/2023
############################

from MisarParserMain import *
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

def window_quit():
    window.quit()
    window.destroy()


def select(inputClass):
    print(inputClass.fileType)
    if inputClass.fileType == "file":
        if inputClass.name == "psmEcore":
            filename = filedialog.askopenfilename()
            if filename:
                inputClass.ent.configure(state = 'normal')
                inputClass.ent.delete(0, 'end')
                inputClass.ent.insert(0, filename)
                inputClass.ent.configure(state = 'readonly', readonlybackground = 'white')
                
        elif inputClass.name in ["dockerCompose", "appBuild", "moduleBuild"]:
            files = filedialog.askopenfilenames()
            for file in files: 
                if file not in inputClass.lst.get(0, 'end'):
                    inputClass.lst.insert('end', file)
                    
    elif inputClass.fileType == "directory":
        directory = filedialog.askdirectory()
        if directory:
            if inputClass.name in ["projectDir", "outputDir"]:
                inputClass.ent.configure(state = 'normal')
                inputClass.ent.delete(0, 'end')
                inputClass.ent.insert(0, directory)
                inputClass.ent.configure(state = 'readonly', readonlybackground = 'white')
                if inputClass.name == "projectDir":
                    autoImporter(directory)
                    pomScanner(inputClass, directory)
            elif inputClass.name in ["moduleBuildDir", "appConfigDir"]:
                if directory not in inputClass.lst.get(0, 'end'):
                    inputClass.lst.insert(inputClass.lst.size(), directory)
                    if inputClass.name == "moduleBuildDir":
                        pomScanner(inputClass, directory)
                    

def delete_item(inputClass):
    inputClass.lst.delete(tkinter.ANCHOR)

def autoImporter(inputDirectory):
    automatic = messagebox.askquestion("Automatic Importer", "Would you like to try and automatically import all of the files from this micro company?", icon = "info")
    if automatic == "yes":
        for file in os.listdir(inputDirectory):
            targetDirectory = inputDirectory+"/"+file
            if os.path.isdir(targetDirectory):
                if os.path.isfile(targetDirectory+"/pom.xml"):
                    if targetDirectory not in module_build_dir.lst.get(0, 'end'):
                        module_build_dir.lst.insert('end', targetDirectory)
                    if targetDirectory+"/pom.xml" not in module_build.lst.get(0, 'end'):
                        module_build.lst.insert('end', targetDirectory+"/pom.xml")
                elif os.path.isfile(targetDirectory+"/docker-compose-v3.yml"):
                    if targetDirectory+"/docker-compose-v3.yml" not in docker_compose.lst.get(0, 'end'):
                        docker_compose.lst.insert('end', targetDirectory+"/docker-compose-v3.yml")
            if os.path.isfile(inputDirectory+"/pom.xml"):
                if inputDirectory+"/pom.xml" not in app_build.lst.get(0, 'end'):
                    app_build.lst.insert('end', inputDirectory+"/pom.xml")


def pomScanner(inputClass, inputDirectory):
    pomScan = messagebox.askquestion("POM Scanner", "Would you like to add any corresponding POM files that exist within this directory?", icon = "info")
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
    

def create_psm_instance():
    if not txt_proj_name.get().strip():
        messagebox.showerror('Missing Values', 'please provide one value for \'Application Project Name\' !')
    elif not proj_dir.ent.get().strip():
        messagebox.showerror('Missing Values', 'please provide one value for \'Application Project Build Directory\' !')
    elif not psm_ecore.ent.get().strip():
        messagebox.showerror('Missing Values', 'please provide one value for \'PSM Ecore File\' !') 
    elif psm_ecore.ent.get().lower().strip().find('.ecore') == -1:
        messagebox.showerror('Invalid File Type', 'please select an ECORE file type for \'PSM Ecore File\' !') 
    elif not docker_compose.lst.size():
        messagebox.showerror('Missing Values', 'please provide one or more value for \'Docker Compose Files\' !') 
    elif not module_build_dir.lst.size():
        messagebox.showerror('Missing Values', 'please provide one or more value for \'Microservice Projects Build Directories\' !') 
    elif not output_dir.ent.get():
        outputPrompt = messagebox.askquestion("Empty Output Box",
                                           "You have not selected any output directory. Would you like to add one? If you select no, the output metamodel will be located in the same directory as the PSM.ecore file.",
                                           icon="info")
        if outputPrompt == "no":
            parser(txt_proj_name, proj_dir.ent, psm_ecore.ent, docker_compose.lst, app_build.lst, module_build_dir.lst, module_build.lst, app_config_dir.lst, output_dir.ent)
    else:
        parser(txt_proj_name, proj_dir.ent, psm_ecore.ent, docker_compose.lst, app_build.lst, module_build_dir.lst, module_build.lst, app_config_dir.lst, output_dir.ent)


class smallFrame:
    def __init__(self, name, targetWindow, description, inputRow, inputColumn, fileType):
        self.name = name
        self.targetWindow = targetWindow
        self.description = description
        self.fileType = fileType
        self.lbl = tkinter.Label(self.targetWindow, text = self.description)
        self.lbl.grid(row = inputRow, column = inputColumn, columnspan = 2, sticky = 'W')
        self.ent = tkinter.Entry(targetWindow, text = '', width = 50, foreground = 'navy')
        self.ent.grid(row = (inputRow+1), column = inputColumn, padx = 2, pady = 2, sticky = 'N')
        self.ent.configure(state ='readonly', readonlybackground = 'white')
        self.addbutton = tkinter.Button(targetWindow, text = 'Browse', width = 10)
        self.addbutton.configure(command = lambda button = self: select(self))
        self.addbutton.grid(row = (inputRow+1), column = (inputColumn+1), padx = 2, pady = 2, sticky = 'N')
        
class largeFrame:
    def __init__(self, name, targetWindow, description, inputRow, inputColumn, fileType):
        self.name = name
        self.targetWindow = targetWindow
        self.description = description
        self.fileType = fileType
        self.lbl = tkinter.Label(self.targetWindow, text = self.description)
        self.lbl.grid(row = inputRow, column = inputColumn, columnspan = 2, sticky = 'W')
        self.frame = tkinter.Frame(targetWindow)
        self.frame.grid(row = (inputRow+1), rowspan = 2, column = inputColumn, padx = 2, pady = 2)
        self.xscroll = tkinter.Scrollbar(self.frame, orient='horizontal')
        self.yscroll = tkinter.Scrollbar(self.frame, orient='vertical')
        self.lst = tkinter.Listbox(self.frame, width = 50, height = 10, xscrollcommand = self.xscroll.set, yscrollcommand = self.yscroll.set, foreground = 'navy')
        self.xscroll.config(command = self.lst.xview)
        self.xscroll.pack(side = 'bottom', fill = 'x')
        self.yscroll.config(command = self.lst.yview)
        self.yscroll.pack(side = 'right', fill = 'y')
        self.lst.pack(side = 'left', fill = 'both', expand = 1)
        self.addbutton = tkinter.Button(targetWindow, text = 'Add Item', width = 10)
        self.addbutton.configure(command = lambda button = self: select(button))
        self.addbutton.grid(row = (inputRow+1), column = (inputColumn+1), padx = 2, pady = 2, sticky = 'N')
        self.delbutton = tkinter.Button(targetWindow, text = 'Delete', width = 10)
        self.delbutton.configure(command = lambda button = self: delete_item(button))
        self.delbutton.grid(row = (inputRow+2), column = (inputColumn+1), padx = 2, pady = 2, sticky = 'N')
    
#Generates the window instance
window = tkinter.Tk()
window.title('A Python application to parse YAML, XML and JAVA artifacts of a microservice architecture project into a MiSAR PSM model. NEW!')
window.protocol("WM_DELETE_WINDOW", window_quit)

#Generates the project name input
lbl_proj_name = tkinter.Label(window, text = 'Type Multi-Module Project Name (mandatory):')
lbl_proj_name.grid(row = 1, column = 0, columnspan = 2, sticky = 'W' + 'S')
txt_proj_name = tkinter.Entry(window, text = '', width = 50, foreground = 'navy')
txt_proj_name.grid(row = 2, column = 0, padx = 2, pady = 2, sticky = 'N')

#Generates the windows
proj_dir = smallFrame("projectDir", window,"Select Multi-Module Project Build Directory (mandatory):", 3, 0, "directory")
psm_ecore = smallFrame("psmEcore", window,"Select PSM Ecore File (mandatory):", 5, 0, "file")
docker_compose = largeFrame("dockerCompose", window,"Select Docker Compose Files (mandatory):", 1, 2, "file")
app_build = largeFrame("appBuild", window,"Select Multi-Module Project POM Build Files (optional):", 1, 4, "file")
module_build_dir = largeFrame("moduleBuildDir", window,"Select Module Projects Build Directories (mandatory):", 7, 0, "directory")
module_build = largeFrame("moduleBuild", window,"Select Module Projects POM Build Files (optional):", 7, 2, "file")
app_config_dir = largeFrame("appConfigDir", window,"Select Centralized Configuration Directories (optional):", 7, 4, "directory")

"""
#Generates the create PSM button
self.lbl = tkinter.Label(self.targetWindow, text=self.description)
self.lbl.grid(row=inputRow, column=inputColumn, columnspan=2, sticky='W')

lbl_dir_select = tkinter.Button(window, text = 'Create PSM Model', width = 30)
lbl_dir_select.configure(command = lambda button = btn_psm_instance: create_psm_instance())
lbl_dir_select.grid(row = 10, column = 0, columnspan = 6, padx = 2, pady = 10)

#Generates the create PSM button
btn_dir_select = tkinter.Button(window, text = 'Select output directory', width = 30)
btn_dir_select.configure(command = lambda button = btn_psm_instance: create_psm_instance())
btn_dir_select.grid(row = 10, column = 1, columnspan = 6, padx = 2, pady = 10)
"""

#Generates the output section
output_dir = smallFrame("outputDir", window, "Select output directory (optional)", 10, 0, "directory")

#Generates the create PSM button
btn_psm_instance = tkinter.Button(window, text = 'Create PSM Model', width = 30)
btn_psm_instance.configure(command = lambda button = btn_psm_instance: create_psm_instance())
btn_psm_instance.grid(row = 11, column = 0, columnspan = 6, padx = 2, pady = 10)


window.mainloop()



