import tkinter
from tkinter import messagebox
import os
import shutil
import stat
from urllib.request import urlopen as url
from datetime import *

def checkInternet():
    try:
        url('https://google.com/', timeout=3)
        return True
    except Exception as e:
        return False

def checkIfGitIsInstalled(inputClass):
    if checkInternet():
        try:
            from git import Repo
            return True
        except ModuleNotFoundError:
            installGit = messagebox.askquestion("Git not installed!", "GitPython and pyGit are mandatory modules which aren't installed. Install them now?")
            if installGit == "yes":
                try:
                    os.system('pip3 install pyGit')
                    os.system('pip3 install gitPython')
                    from git import Repo
                    messagebox.showinfo("Success!", "The operation completed successfully.")
                    if inputClass != None:
                        installContinue = messagebox.askquestion("Continue?",
                                                                 ("Would you like to continue with the installation of the "+ inputClass.name+"?"))
                    else:
                        installContinue = messagebox.askquestion("Continue?",
                                                                 ("Would you like to check for updates?"))
                    if installContinue == "yes":
                        return True
                    else:
                        return False
                except Exception as e:
                    messagebox.showerror("Error!",
                                         ("The installation of the GitHub modules have failed.\nError code:\n"+str(e)))
                    return False
            else:
                if inputClass != None:
                    messagebox.showerror("You said no...","MiSAR cannot install the "+ inputClass.name + " without pyGit and GitPython.")
                    return False
                else:
                    messagebox.showerror("You said no...",
                                         "MiSAR cannot check for updates without pyGit and GitPython.")
                    return False
    else:
        messagebox.showerror("No Internet Connection!",
                             "An internet connection is required to install pyGit and gitPython.")
        return False

def checkImports(inputClass):
    errors = []
    try:
        import pyecore
    except ModuleNotFoundError:
        errors.append("pyecore")
    try:
        import yaml
    except ModuleNotFoundError:
        errors.append("pyYaml")
    try:
        import xmltodict
    except ModuleNotFoundError:
        errors.append("xmltodict")
    try:
        import javalang
    except ModuleNotFoundError:
        errors.append("javalang")
    if len(errors) > 0:
        errStr = ""
        for z in range (0, len(errors)):
            errStr = errStr + errors[z]+"\n"
        if len(errors) == 1:
            strAdd = "The following import is currently not installed:\n\n"+errStr+"\nThis import is mandatory for the function of the Parser.\nWould you like to install it now?"
        else:
            strAdd = "The following imports are currently not installed:\n\n"+errStr+"\nThese imports are mandatory for the function of the Parser.\nWould you like to install it now?"
        installImports = messagebox.askquestion("Missing Imports", (strAdd))
        if installImports == "yes" and checkInternet():
            try:
                os.system('pip3 install pyecore')
                os.system('pip3 install pyYaml')
                os.system('pip3 install xmltodict')
                os.system('pip3 install javalang')
                import pyecore
                import yaml
                import xmltodict
                import javalang
                messagebox.showinfo("Success!", "The operation completed successfully.")
                return True
            except ModuleNotFoundError:
                messagebox.showerror("Error",
                                     "An unknown error occurred")
            return False
        else:
            return False
    else:
        return True

def parserInstaller(parserLocation):
    from git import Repo
    try:
        Repo.clone_from(
            "https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation.git",
            (os.path.expanduser('~') + "/" + parserLocation), branch="2123833-(Kevin's-branch)")
        if os.path.isfile(
                (os.path.expanduser('~') + "\\" + parserLocation + "\\MisarQVTv3\\source\\PSM.ecore")) == True:
            return True
    except Exception as fail:
        return False

def parserUninstaller(parserLocation):
    targetLink = ""
    readOnly = True
    while readOnly:
        readOnly = False
        try:
            os.rmdir(os.path.expanduser('~') + "\\" + parserLocation)
        except OSError:
            try:
                shutil.rmtree((os.path.expanduser('~') + "\\" + parserLocation))
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
                try:
                    shutil.rmtree(targetLink)
                except FileNotFoundError:
                    pass
                targetLink = ""
                readOnly = True



def buttonStuff(inputClass):
    if inputClass.name == "MiSAR Parser":
        if os.path.isfile((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")) == False:
            MisarChecker = messagebox.askquestion("Parser Installer", "To use the MiSAR Parser, you must first install it.\nWould you to like to install it now?")
            if MisarChecker == "yes":
                if checkInternet():
                    if checkIfGitIsInstalled(inputClass):
                        if parserInstaller("MiSAR") == True:
                            messagebox.showinfo("Success!",
                                                "The operation completed successfully!\nThe Parser, and it's PSM.ecore has been saved at: " + os.path.expanduser(
                                                    '~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")
                            theParser.launchButton.configure(text="Launch")
                        else:
                            parserUninstaller("MiSAR")
                            if parserInstaller("MiSAR") == True:
                                messagebox.showinfo("Success!",
                                                    "The operation completed successfully!\nThe Parser, and it's PSM.ecore has been saved at: " + os.path.expanduser(
                                                        '~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")
                                theParser.launchButton.configure(text="Launch")
                else:
                    messagebox.showerror("No Internet Connection!",
                                         "An internet connection is required to install the "+inputClass.name+".")
                    return False
        else:
            if checkImports(inputClass):
                import MisarParserGUI

def misar_updater():
    if checkInternet():
        if os.path.isfile((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")) == True:
            if os.path.isfile(
                    (os.path.expanduser('~') + "\\MiSARTemp\\MisarQVTv3\\source\\PSM.ecore")) == True:
                parserUninstaller("MiSARTemp")

            if checkIfGitIsInstalled(None):
                if parserInstaller("MiSARTemp") == True:
                    previousDirectory = os.getcwd()
                    os.chdir((os.path.expanduser('~') + "\\MisARTemp"))
                    newestVersion = os.popen("git log -1").read()
                    updatedDate = ""
                    colonCount = 0
                    targetCutOff = 999999
                    for x in range(0, len(newestVersion)):
                        if targetCutOff > x:
                            updatedDate = updatedDate + newestVersion[x]
                            # print(updatedDate)
                            if newestVersion[x] == ":" and colonCount < 2:
                                updatedDate = ""
                                colonCount = colonCount + 1
                            if colonCount >= 2 and newestVersion[x + 1] == "+" or newestVersion[x + 1] == "-":
                                break
                    updatedDate = updatedDate.strip()
                    #updatedDate = "Fri Oct 31 16:45:46 2023"
                    print(updatedDate)
                    onlineVersion = datetime.strptime(updatedDate, '%a %b %d %H:%M:%S %Y')
                    currentVersion = datetime.fromtimestamp(
                        (os.path.getctime((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore"))))
                    if onlineVersion > currentVersion:
                        print(onlineVersion)
                        print(currentVersion)
                        os.chdir(previousDirectory)
                        updateAvailable = messagebox.askquestion("Update Available!",
                                                                 "An update is available! Would you like to install it now?")
                        if updateAvailable == "yes":
                            parserUninstaller("MiSARTemp")
                            parserUninstaller("MiSAR")
                            if parserInstaller("MiSAR") == True:
                                messagebox.showinfo("Success!",
                                                    "The update completed successfully!")
                            else:
                                messagebox.showerror("Failure!",
                                                     "The update has failed.")
                """
                #parserUninstaller("MiSARTemp")
                        MisarChecker = "yes"
                        while MisarChecker == "yes":
                            MisarChecker = "no"
                            try:
                                Repo.clone_from(
                                    "https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation.git",
                                    (os.path.expanduser('~') + "/" + "MiSARTemp"), branch="2123833-(Kevin's-branch)")
                                if os.path.isfile(
                                        (os.path.expanduser('~') + "\\MiSARTemp\\MisarQVTv3\\source\\PSM.ecore")) == True:
                                    os.chdir((os.path.expanduser('~') + "\\MisARTemp"))
                                    newestVersion = os.popen("git log -1").read()
                                    updatedDate = ""
                                    colonCount = 0
                                    targetCutOff = 999999
                                    for x in range (0, len(newestVersion)):
                                        if targetCutOff > x:
                                            updatedDate = updatedDate + newestVersion[x]
                                            #print(updatedDate)
                                            if newestVersion[x] == ":" and colonCount < 2:
                                                updatedDate = ""
                                                colonCount = colonCount + 1
                                            if colonCount >= 2 and newestVersion[x+1] == "+" or newestVersion[x+1] == "-":
                                                break
                                    updatedDate = updatedDate.strip()
                                    print(updatedDate)
                                    onlineVersion = datetime.strptime(updatedDate, '%a %b %d %H:%M:%S %Y')
                                    currentVersion = datetime.fromtimestamp((os.path.getctime((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore"))))
                                    if onlineVersion > currentVersion:
                                        print(onlineVersion)
                                        print(currentVersion)
                                        updateAvailable = messagebox.askquestion("Update Available!", "An update is available! Would you like to install it now?")
                                        if updateAvailable == "yes":
                                            parserInstaller(updateAvailable)

                            except Exception as fail:
                                print(str(fail))
                                print(fail)
                                if os.path.isfile(
                                        (os.path.expanduser('~') + "\\MisARTemp\\MisarQVTv3\\source\\PSM.ecore")) == True:
                                    messagebox.showinfo("Success!",
                                                        "The operation completed successfully!\nThe Parser, and it's PSM.ecore has been saved at: " + os.path.expanduser(
                                                            '~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")
                                else:
                                    try:
                                        shutil.rmtree(targetLink)
                                    except Exception as fail:
                                        messagebox.showerror("Retrieval failure!", (
                                            "PSM retrieval failed!\nNo internet connection found!"))
                """
    else:
        messagebox.showerror("No Internet", "Cannot check for updates due to a lack of internet.")


class programOfChoice:
    def __init__(self, name, version, inputRow, inputColumn, targetWindow):
        self.name = name
        self.version = version
        self.inputRow = inputRow
        self.inputColumn = inputColumn
        self.moduleName = tkinter.Label(targetWindow, text = name, font = 15)
        self.moduleName.grid(row = inputRow, column = inputColumn)
        self.launchButton = tkinter.Button(targetWindow, text = "Install", width = 10)
        self.launchButton.configure(command = lambda button = self: buttonStuff(button))
        self.launchButton.grid(row = inputRow+1, column = inputColumn)
def window_quit():
    mainWindow.quit()
    mainWindow.destroy()

misar_updater()

mainWindow = tkinter.Tk()

mainWindow.title("MicroService Architecture Recovery")
welcome = tkinter.Label(mainWindow, text = "Hello and welcome to the MiSAR AIO!\n Please select a program you would like to use from the list below:", font = 15)
welcome.grid(row = 0, column = 0)

theParser = programOfChoice("MiSAR Parser", "V1.0", 1, 0, mainWindow)
theTransformationEngine = programOfChoice("MiSAR Transformation Engine", "V1.0", 3, 0, mainWindow)
theGraphicalModelGenerator = programOfChoice("MiSAR Graphical Model Generator", "V1.0", 5, 0, mainWindow)
theUpdater = programOfChoice = programOfChoice("Check for Updates", "V1.0", 7, 0, mainWindow)

if os.path.isfile((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")) == True:
    theParser.launchButton.configure(text = "Launch")


mainWindow.protocol("WM_DELETE_WINDOW", window_quit)


mainWindow.mainloop()