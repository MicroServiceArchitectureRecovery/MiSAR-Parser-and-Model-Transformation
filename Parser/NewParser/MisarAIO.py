import tkinter
from tkinter import messagebox
import os
import shutil
import stat
import subprocess
import sys
from git import Repo
import pip


"""try:
    import github
except ModuleNotFoundError:
    installGit = messagebox.askquestion("Git not installed!", "Git is a mandatory module which isn't installed. Install it now?")
    if installGit == "yes":
        os.system('pip3 install github')"""

def checkImports():
    errors = []
    try:
        import pyecore
    except ModuleNotFoundError:
        errors.append("pyecore")
    try:
        import yaml
    except ModuleNotFoundError:
        errors.append("yaml")
    try:
        import xmltodict
    except ModuleNotFoundError:
        errors.append("xmltodict")
    try:
        import javalang
    except ModuleNotFoundError:
        errors.append("javalang")
    return errors

class preRequisits:
    def __init__(self, importName, inputRow, inputColumn, status):
        self.importName = importName
        self.inputRow = inputRow
        self.inputColumn = inputColumn


def buttonStuff(inputClass):
    targetLink = ""
    if inputClass.name == "MiSAR Parser":
        if os.path.isfile((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")) == False:
            MisarChecker = messagebox.askquestion("Parser Installer", "To use the MiSAR Parser, you must first install it.\n Would you to like to install it now?")
            if MisarChecker == "yes":
                readOnly = True
                while readOnly:
                    readOnly = False
                    try:
                        os.mkdir(os.path.expanduser('~') + "\\" + "MisAR")
                    except FileExistsError:
                        try:
                            shutil.rmtree((os.path.expanduser('~') + "\\" + "MisAR"))
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
                            print(targetLink)
                            os.chmod(targetLink, stat.S_IWRITE)
                            os.unlink(targetLink)
                            shutil.rmtree(targetLink)
                            targetLink = ""
                            readOnly = True
                    if readOnly == False:
                        while MisarChecker == "yes":
                            MisarChecker = "no"
                            try:
                                Repo.clone_from(
                                    "https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation.git",
                                    (os.path.expanduser('~') + "/" + "MiSAR"))
                                if os.path.isfile((os.path.expanduser('~') + "/MisAR/MisarQVTv3/source/PSM.ecore")) == True:
                                    messagebox.showinfo("Success!", "The operation completed successfully.")
                            except Exception as fail:
                                if os.path.isfile((os.path.expanduser('~') + "/MisAR/MisarQVTv3/source/PSM.ecore")) == True:
                                    messagebox.showinfo("Success!", "The operation completed successfully.")
                                else:
                                    try:
                                        shutil.rmtree(targetLink)
                                    except Exception as fail:
                                        messagebox.showerror("Retrieval failure!", (
                                                "PSM retrieval failed!\nError code:\n" + str(
                                            fail)))

        else:
            import MisarParserGUI
class programOfChoice:
    def __init__(self, name, version, inputRow, inputColumn, targetWindow):
        self.name = name
        self.version = version
        self.inputRow = inputRow
        self.inputColumn = inputColumn
        self.moduleName = tkinter.Label(targetWindow, text = name, font = 15)
        self.moduleName.grid(row = inputRow, column = inputColumn)
        self.launchButton = tkinter.Button(targetWindow, text = "Launch", width = 10)
        self.launchButton.configure(command = lambda button = self: buttonStuff(button))
        self.launchButton.grid(row = inputRow+1, column = inputColumn)
def window_quit():
    mainWindow.quit()
    mainWindow.destroy()

mainWindow = tkinter.Tk()

mainWindow.title("MicroService Architecture Recovery")
welcome = tkinter.Label(mainWindow, text = "Hello and welcome to the MiSAR AIO!\n Please select a program you would like to use from the list below:", font = 15)
welcome.grid(row = 0, column = 0)

theParser = programOfChoice("MiSAR Parser", "V1.0", 1, 0, mainWindow)
theTransformationEngine = programOfChoice("MiSAR Transformation Engine", "V1.0", 3, 0, mainWindow)
theGraphicalModelGenerator = programOfChoice("MiSAR Graphical Model Generator", "V1.0", 5, 0, mainWindow)

mainWindow.protocol("WM_DELETE_WINDOW", window_quit)


mainWindow.mainloop()