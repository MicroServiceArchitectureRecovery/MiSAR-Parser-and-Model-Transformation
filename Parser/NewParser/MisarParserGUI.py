############################
# Developed by RanaFakeeh-87
# 01/20/2020
# Updated by RanaFakeeh-87
# 11/01/2022
# Updated by kevinvahdat01
# 25/09/2023
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
from MisarParserMain import *


def window_quit():
    window.quit()
    window.destroy()
    
def select_dir(button):
    directory = filedialog.askdirectory()
    if directory:
        if button == btn_proj_dir:
            txt_proj_dir.configure(state = 'normal')
            txt_proj_dir.delete(0, 'end')
            txt_proj_dir.insert(0, directory)
            txt_proj_dir.configure(state = 'readonly', readonlybackground = 'white')
        elif button in [btn_module_build_dir_add, btn_app_config_dir_add]:
            lst = tkinter.Listbox()
            if button == btn_module_build_dir_add: 
                lst = lst_module_build_dir 
            elif button == btn_app_config_dir_add: 
                lst = lst_app_config_dir
            if directory not in lst.get(0, 'end'):
                lst.insert(lst.size(), directory) 

def select_file(button):
    if button == btn_psm_ecore:
        filename = filedialog.askopenfilename()
        if filename:
            txt_psm_ecore.configure(state = 'normal')
            txt_psm_ecore.delete(0, 'end')
            txt_psm_ecore.insert(0, filename)
            txt_psm_ecore.configure(state = 'readonly', readonlybackground = 'white')
    elif button in [btn_docker_compose_add, btn_app_build_add, btn_module_build_add]:
        files = filedialog.askopenfilenames()
        lst = tkinter.Listbox()
        if button == btn_docker_compose_add: 
            lst = lst_docker_compose 
        elif button == btn_app_build_add: 
            lst = lst_app_build
        elif button == btn_module_build_add: 
            lst = lst_module_build
        for file in files: 
            if file not in lst.get(0, 'end'):
                lst.insert('end', file) 

def delete_item(button):
    pass


def create_psm_instance():
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
        parser(txt_proj_name, txt_proj_dir, txt_psm_ecore, lst_docker_compose, lst_app_build, lst_module_build_dir, lst_module_build, lst_app_config_dir)
    
window = tkinter.Tk()
window.title('A Python application to parse YAML, XML and JAVA artifacts of a microservice architecture  project into a MiSAR PSM model. NEW!')
window.protocol("WM_DELETE_WINDOW", window_quit)

box_width = 50
padding = 2
fg_color = 'navy'

lbl_proj_name = tkinter.Label(window, text = 'Type Multi-Module Project Name (mandatory):')
lbl_proj_name.grid(row = 1, column = 0, columnspan = 2, sticky = 'W' + 'S')
txt_proj_name = tkinter.Entry(window, text = '', width = box_width, foreground = fg_color)
txt_proj_name.grid(row = 2, column = 0, padx = padding, pady = padding, sticky = 'N')

lbl_proj_dir = tkinter.Label(window, text = 'Select Multi-Module Project Build Directory (mandatory):')
lbl_proj_dir.grid(row = 3, column = 0, columnspan = 2, sticky = 'W' + 'S')
txt_proj_dir = tkinter.Entry(window, text = '', width = box_width, foreground = fg_color)
txt_proj_dir.grid(row = 4, column = 0, padx = padding, pady = padding, sticky = 'N')
txt_proj_dir.configure(state ='readonly', readonlybackground = 'white')
btn_proj_dir = tkinter.Button(window, text = 'Browse', width = 10)
btn_proj_dir.configure(command = lambda button = btn_proj_dir: select_dir(button))
btn_proj_dir.grid(row = 4, column = 1, padx = padding, pady = padding, sticky = 'N')

lbl_psm_ecore = tkinter.Label(window, text = 'Select PSM Ecore File (mandatory):')
lbl_psm_ecore.grid(row = 5, column = 0, columnspan = 2, sticky = 'W' + 'S')
txt_psm_ecore = tkinter.Entry(window, text = '', width = box_width, foreground = fg_color)
txt_psm_ecore.grid(row = 6, column = 0, padx = padding, pady = padding, sticky = 'N')
btn_psm_ecore = tkinter.Button(window, text = 'Browse', width = 10)
btn_psm_ecore.configure(command = lambda button = btn_psm_ecore : select_file(button))
btn_psm_ecore.grid(row = 6, column = 1, padx = padding, pady = padding, sticky = 'N')
txt_psm_ecore.configure(state ='readonly', readonlybackground = 'white')

lbl_docker_compose = tkinter.Label(window, text = 'Select Docker Compose Files (mandatory):')
lbl_docker_compose.grid(row = 1, column = 2, columnspan = 2, sticky = 'W')
frame_docker_compose = tkinter.Frame(window)
frame_docker_compose.grid(row = 2, rowspan= 5, column = 2, padx = padding, pady = padding)
xscroll_docker_compose = tkinter.Scrollbar(frame_docker_compose, orient='horizontal')
yscroll_docker_compose = tkinter.Scrollbar(frame_docker_compose, orient='vertical')
lst_docker_compose = tkinter.Listbox(frame_docker_compose, width = box_width, height = 10, xscrollcommand = xscroll_docker_compose.set, yscrollcommand = yscroll_docker_compose.set, foreground = fg_color)
xscroll_docker_compose.config(command = lst_docker_compose.xview)
xscroll_docker_compose.pack(side = 'bottom', fill = 'x')
yscroll_docker_compose.config(command = lst_docker_compose.yview)
yscroll_docker_compose.pack(side = 'right', fill = 'y')
lst_docker_compose.pack(side = 'left', fill = 'both', expand = 1)
btn_docker_compose_add = tkinter.Button(window, text = 'Add Item', width = 10)
btn_docker_compose_add.configure(command = lambda button = btn_docker_compose_add: select_file(button))
btn_docker_compose_add.grid(row = 2, column = 3, padx = padding, pady = padding, sticky = 'N')
btn_docker_compose_del = tkinter.Button(window, text = 'Delete', width = 10, state='disabled')
btn_docker_compose_del.configure(command = lambda button = btn_docker_compose_del: delete_item(button))
btn_docker_compose_del.grid(row = 3, column = 3, padx = padding, pady = padding, sticky = 'N')

lbl_app_build = tkinter.Label(window, text = 'Select Multi-Module Project POM Build Files (optional):')
lbl_app_build.grid(row = 1, column = 4, columnspan = 2, sticky = 'W')
frame_app_build = tkinter.Frame(window)
frame_app_build.grid(row = 2, rowspan= 5, column = 4, padx = padding, pady = padding)
xscroll_app_build = tkinter.Scrollbar(frame_app_build, orient='horizontal')
yscroll_app_build = tkinter.Scrollbar(frame_app_build, orient='vertical')
lst_app_build = tkinter.Listbox(frame_app_build, width = box_width, height = 10, xscrollcommand = xscroll_app_build.set, yscrollcommand = yscroll_app_build.set, foreground = fg_color)
xscroll_app_build.config(command = lst_app_build.xview)
xscroll_app_build.pack(side = 'bottom', fill = 'x')
yscroll_app_build.config(command = lst_app_build.yview)
yscroll_app_build.pack(side = 'right', fill = 'y')
lst_app_build.pack(side = 'left', fill = 'both', expand = 1)
btn_app_build_add = tkinter.Button(window, text = 'Add Item', width = 10)
btn_app_build_add.configure(command = lambda button = btn_app_build_add: select_file(button))
btn_app_build_add.grid(row = 2, column = 5, padx = padding, pady = padding, sticky = 'N')
btn_app_build_del = tkinter.Button(window, text = 'Delete', width = 10, state='disabled')
btn_app_build_del.configure(command = lambda button = btn_app_build_del: delete_item(button))
btn_app_build_del.grid(row = 3, column = 5, padx = padding, pady = padding, sticky = 'N')

lbl_module_build_dir = tkinter.Label(window, text = 'Select Module Projects Build Directories (mandatory):')
lbl_module_build_dir.grid(row = 7, column = 0, columnspan = 2, sticky = 'W')
frame_module_build_dir = tkinter.Frame(window)
frame_module_build_dir.grid(row = 8, rowspan= 2, column = 0, padx = padding, pady = padding)
xscroll_module_build_dir = tkinter.Scrollbar(frame_module_build_dir, orient='horizontal')
yscroll_module_build_dir = tkinter.Scrollbar(frame_module_build_dir, orient='vertical')
lst_module_build_dir = tkinter.Listbox(frame_module_build_dir, width = box_width, height = 10, xscrollcommand = xscroll_module_build_dir.set, yscrollcommand = yscroll_module_build_dir.set, foreground = fg_color)
xscroll_module_build_dir.config(command = lst_module_build_dir.xview)
xscroll_module_build_dir.pack(side = 'bottom', fill = 'x')
yscroll_module_build_dir.config(command = lst_module_build_dir.yview)
yscroll_module_build_dir.pack(side = 'right', fill = 'y')
lst_module_build_dir.pack(side = 'left', fill = 'both', expand = 1)
btn_module_build_dir_add = tkinter.Button(window, text = 'Add Item', width = 10)
btn_module_build_dir_add.configure(command = lambda button = btn_module_build_dir_add: select_dir(button))
btn_module_build_dir_add.grid(row = 8, column = 1, padx = padding, pady = padding, sticky = 'N')
btn_module_build_dir_del = tkinter.Button(window, text = 'Delete', width = 10, state='disabled')
btn_module_build_dir_del.configure(command = lambda button = btn_module_build_dir_del: delete_item(button))
btn_module_build_dir_del.place(x = 327, y = 267)

lbl_module_build = tkinter.Label(window, text = 'Select Module Projects POM Build Files (optional):')
lbl_module_build.grid(row = 7, column = 2, columnspan = 2, sticky = 'W')
frame_module_build = tkinter.Frame(window)
frame_module_build.grid(row = 8, rowspan= 2, column = 2, padx = padding, pady = padding)
xscroll_module_build = tkinter.Scrollbar(frame_module_build, orient='horizontal')
yscroll_module_build = tkinter.Scrollbar(frame_module_build, orient='vertical')
lst_module_build = tkinter.Listbox(frame_module_build, width = box_width, height = 10, xscrollcommand = xscroll_module_build.set, yscrollcommand = yscroll_module_build.set, foreground = fg_color)
xscroll_module_build.config(command = lst_module_build.xview)
xscroll_module_build.pack(side = 'bottom', fill = 'x')
yscroll_module_build.config(command = lst_module_build.yview)
yscroll_module_build.pack(side = 'right', fill = 'y')
lst_module_build.pack(side = 'left', fill = 'both', expand = 1)
btn_module_build_add = tkinter.Button(window, text = 'Add Item', width = 10)
btn_module_build_add.configure(command = lambda button = btn_module_build_add: select_file(button))
btn_module_build_add.grid(row = 8, column = 3, padx = padding, pady = padding, sticky = 'N')
btn_module_build_del = tkinter.Button(window, text = 'Delete', width = 10, state='disabled')
btn_module_build_del.configure(command = lambda button = btn_module_build_del: delete_item(button))
btn_module_build_del.place(x = 736, y = 267)

lbl_app_config_dir = tkinter.Label(window, text = 'Select Centralized Configuration Directories (optional):')
lbl_app_config_dir.grid(row = 7, column = 4, columnspan = 2, sticky = 'W')
frame_app_config_dir = tkinter.Frame(window)
frame_app_config_dir.grid(row = 8, rowspan = 2, column = 4, padx = padding, pady = padding)
xscroll_app_config_dir = tkinter.Scrollbar(frame_app_config_dir, orient='horizontal')
yscroll_app_config_dir = tkinter.Scrollbar(frame_app_config_dir, orient='vertical')
lst_app_config_dir = tkinter.Listbox(frame_app_config_dir, width = box_width, height = 10, xscrollcommand = xscroll_app_config_dir.set, yscrollcommand = yscroll_app_config_dir.set, foreground = fg_color)
xscroll_app_config_dir.config(command = lst_app_config_dir.xview)
xscroll_app_config_dir.pack(side = 'bottom', fill = 'x')
yscroll_app_config_dir.config(command = lst_app_config_dir.yview)
yscroll_app_config_dir.pack(side = 'right', fill = 'y')
lst_app_config_dir.pack(side = 'left', fill = 'both', expand = 1)
btn_app_config_dir_add = tkinter.Button(window, text = 'Add Item', width = 10)
btn_app_config_dir_add.configure(command = lambda button = btn_app_config_dir_add: select_dir(button))
btn_app_config_dir_add.grid(row = 8, column = 5, padx = padding, pady = padding, sticky = 'N')
btn_app_config_dir_del = tkinter.Button(window, text = 'Delete', width = 10, state='disabled')
btn_app_config_dir_del.configure(command = lambda button = btn_app_config_dir_del: delete_item(button))
btn_app_config_dir_del.place(x = 1145, y = 267)

btn_psm_instance = tkinter.Button(window, text = 'Create PSM Model', width = 30)
btn_psm_instance.configure(command = lambda button = btn_psm_instance: create_psm_instance())
btn_psm_instance.grid(row = 10, column = 0, columnspan = 6, padx = padding, pady = padding*5)

window.mainloop()



