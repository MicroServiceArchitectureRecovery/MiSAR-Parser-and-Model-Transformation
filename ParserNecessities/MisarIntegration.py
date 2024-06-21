import tkinter
from tkinter import messagebox
import os
import shutil
import stat
from urllib.request import urlopen as url
from datetime import *
import webbrowser
import subprocess

def checkInternet():
    try:
        url('https://google.com/', timeout=3)
        return True
    except Exception as e:
        return False

def pluralCheck(errors):
    if len(errors) == 1:
        return ("this required module.")
    else:
        return ("these required modules.")

def checkIfModulesAreInstalled(inputClass):
    errors = []
    try:
        from git import Repo
    except ModuleNotFoundError:
        errors.append("git")
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
        for z in range(0, len(errors)):
            errStr = errStr + errors[z] + "\n"
        if len(errors) == 1:
            strAdd = "The following import is currently not installed:\n\n" + errStr + "\nThis import is mandatory for the function of MiSAR.\nWould you like to install it now?"
        else:
            strAdd = "The following imports are currently not installed:\n\n" + errStr + "\nThese imports are mandatory for the function of MiSAR.\nWould you like to install them now?"
        installModules = messagebox.askquestion("Missing Imports", (strAdd))
        if installModules == "yes":
            if checkInternet():
                try:
                    os.system('pip3 install pyGit')
                    os.system('pip3 install gitPython')
                    os.system('pip3 install pyecore')
                    os.system('pip3 install pyYaml')
                    os.system('pip3 install xmltodict')
                    os.system('pip3 install javalang')
                    from git import Repo
                    import pyecore
                    import yaml
                    import xmltodict
                    import javalang
                    messagebox.showinfo("Success!", "The operation completed successfully!")
                    return True
                except Exception as e:
                    messagebox.showerror("Error!",
                                         ("The installation of the required modules have failed.\nError code:\n" + str(e)))
                    return False
            else:
                messagebox.showerror("Error!",
                                     ("An internet connection is required to install " + pluralCheck(
                                         errors) + " Please connect to the internet and try again."))
                return False
        else:
            messagebox.showerror("Error!",
                                 ("MiSAR cannot operate correctly without " + pluralCheck(
                                     errors) + " Please select yes and try again."))
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
            if os.path.isfile(
                    (os.path.expanduser('~') + "\\" + parserLocation + "\\Parser\\NewParser\\MisarParserGUI.py")) == True:
                return True
    except Exception as fail:
        return False

def gmgInstaller(gmgLocation):
    from git import Repo
    try:
        Repo.clone_from(
            "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git",
            (os.path.expanduser('~') + "/" + gmgLocation), branch="main")
        if os.path.isfile(
                (os.path.expanduser('~') + "\\" + gmgLocation + "\\Runnable Jar File\\MiSAR.jar")) == True:
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
                #print(targetLink)
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
                    if checkIfModulesAreInstalled(inputClass):
                        messagebox.showinfo("Installation commencing!",
                                            "The Parser will now be installed.")
                        if parserInstaller("MiSAR") == True:
                            messagebox.showinfo("Success!",
                                                "The operation completed successfully!\nThe Parser, and it's PSM.ecore has been saved at: " + os.path.expanduser(
                                                    '~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")
                            theParser.launchButton.configure(text="Launch")
                        else:
                            Uninstaller("MiSAR")
                            if parserInstaller("MiSAR") == True:
                                messagebox.showinfo("Success!",
                                                    "The operation completed successfully!\nThe Parser, and it's PSM.ecore has been saved at: " + os.path.expanduser(
                                                        '~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")
                                theParser.launchButton.configure(text="Launch")
                else:
                    messagebox.showerror("No Internet Connection!",
                                         "An internet connection is required to install the "+inputClass.name+".")
        elif checkIfModulesAreInstalled(inputClass):
                mainWindow.destroy()
                subprocess.call(['python', (os.path.expanduser('~') + "\\MISARFINAL\\PROGRESS UP TO SPEED\\MisarParserGUI.py")])

    elif inputClass.name == "MiSAR Transformation Engine":
        if checkIfModulesAreInstalled(inputClass):
            mainWindow.destroy()
            #import MisarTransformationEngine
        else:
            messagebox.showerror("Error!",
                                 "The installation has failed!\nIf 'No' was selected, please select yes and try again.\n Otherwise, check your internet connection.")

    elif inputClass.name == "MiSAR Graphical Model Generator":
        if os.path.isfile((os.path.expanduser('~') + "\\GMG\\Runnable Jar File\\MiSAR.jar")) == False:
            MisarChecker = messagebox.askquestion("Graphical Model Generator Installer", "To use the "+ inputClass.name + ", you must first install it.\nWould you to like to install it now?")
            if MisarChecker == "yes":
                if checkInternet():
                    if checkIfModulesAreInstalled(inputClass):
                        if gmgInstaller("GMG") == True:
                            messagebox.showinfo("Success!",
                                                "The operation completed successfully!\nThe Graphical Model Generator, and it's JAR executable has been saved at: " + os.path.expanduser(
                                                    '~') + "\\GMG\\Runnable Jar File\\MiSAR.jar")
                            theGraphicalModelGenerator.launchButton.configure(text="Launch")
                        else:
                            Uninstaller("GMG")
                            if gmgInstaller("GMG") == True:
                                messagebox.showinfo("Success!",
                                                    "The operation completed successfully!\nThe Graphical Model Generator, and it's JAR executable has been saved at: " + os.path.expanduser(
                                                        '~') + "\\GMG\\Runnable Jar File\\MiSAR.jar")
                                theGraphicalModelGenerator.launchButton.configure(text="Launch")
                else:
                    messagebox.showerror("No Internet Connection!",
                                         "An internet connection is required to install the "+inputClass.name+".")
        else:
            mainWindow.destroy()
            subprocess.call(['java', '-jar', (os.path.expanduser('~') + "\\GMG\\Runnable Jar File\\MiSAR.jar")])


    elif inputClass.name == "Need help or more information about this program?":
        messagebox.showinfo("MiSAR Help!", "Hello! And welcome to MiSAR!\n"
                                           "\nMiSAR is an approach that follows the Model Driven Architecture to semi-automatically generate architectural models of implemented microservice systems.")
        messagebox.showinfo("MiSAR Help!", "MiSAR consists of the following components:\n"
                                           "\nA Parser, that creates a Platform Specific Model from existing systems.\n"
                                           "\nA Model Tranformation engine, that transforms platform Specifc Models into Platform Independent Model instances.\n"
                                           "An instance of a MiSAR Platform Independent Model is the recovered architectural model of the implemented microservice system.\n"
                                           "\nA Graphical Model generator, which converts the architectural model exported from the Transformation engine into a UML based format.")
        demo = messagebox.askquestion("Need more?", "Would you like to view a short demonstration for the MiSAR toolset?\n"
                                                    "This requires an internet connection.")
        if demo == "yes":
            if checkInternet():
                webbrowser.open("https://www.youtube.com/watch?v=sdRDkLesyS0&ab_channel=NourAli", new = 2)
            else:
                messagebox.showerror("No Internet Connection!",
                                     "An internet connection is required to view the MiSAR Demonstration Video.")
                demo = messagebox.askquestion("Need more?",
                                              "Would you instead like to view the manual for MiSAR?\n"
                                              "This does NOT requires an internet connection.")
                if demo == "yes":
                    subprocess.Popen((os.path.expanduser('~') + "\\MisAR\\MiSAR Parser - manualfinal.pdf"), shell=True)
        else:
            demo = messagebox.askquestion("Need more?",
                                          "Would you instead like to view the manual for MiSAR?\n"
                                          "This does NOT requires an internet connection.")
            if demo == "yes":
                subprocess.Popen((os.path.expanduser('~') + "\\MisAR\\MiSAR Manual v1.pdf"), shell=True)

def misar_updater():
    if checkInternet():
        if checkIfModulesAreInstalled(None):
            if os.path.isfile((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")) == True:
                if os.path.isfile((os.path.expanduser('~') + "\\MiSARTemp\\MisarQVTv3\\source\\PSM.ecore")) == True:
                    Uninstaller("MiSARTemp")
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
                    onlineVersion = datetime.strptime(updatedDate, '%a %b %d %H:%M:%S %Y')
                    currentVersion = datetime.fromtimestamp(
                        (os.path.getctime((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore"))))
                    os.chdir(previousDirectory)
                    if onlineVersion > currentVersion:
                        updateAvailable = messagebox.askquestion("Update Available!",
                                                                 "An update is available! Would you like to install it now?")
                        if updateAvailable == "yes":
                            Uninstaller("MiSARTemp")
                            Uninstaller("MiSAR")
                            if parserInstaller("MiSAR") == True:
                                messagebox.showinfo("Success!",
                                                    "The update completed successfully!")
                            else:
                                messagebox.showerror("Failure!",
                                                     "The update has failed.")
                    else:
                        Uninstaller("MiSARTemp")
    else:
        messagebox.showerror("No Internet", "Cannot check for updates due to a lack of internet.")

class programOfChoice:
    def __init__(self, name, version, inputRow, inputColumn, targetWindow):
        self.name = name
        self.version = version
        self.inputRow = inputRow
        self.inputColumn = inputColumn
        self.moduleName = tkinter.Label(targetWindow, text = name, font =("Arial", 20))
        self.moduleName.grid(row = inputRow, column = inputColumn)
        self.launchButton = tkinter.Button(targetWindow, text = "Install", font =("Arial", 20), width = 10)
        self.launchButton.configure(command = lambda button = self: buttonStuff(button))
        self.launchButton.grid(row = inputRow+1, column = inputColumn)
def window_quit():
    mainWindow.quit()
    mainWindow.destroy()

misar_updater()

mainWindow = tkinter.Tk()

mainWindow.title("MicroService Architecture Recovery")
welcome = tkinter.Label(mainWindow, text = "Hello and welcome to the MiSAR AIO!\n Please select a program you would like to use from the list below:", font =("Arial", 20))
welcome.grid(row = 0, column = 0)

theParser = programOfChoice("MiSAR Parser", "V1.0", 1, 0, mainWindow)
#theTransformationEngine = programOfChoice("MiSAR Transformation Engine", "V1.0", 3, 0, mainWindow)
theGraphicalModelGenerator = programOfChoice("MiSAR Graphical Model Generator", "V1.0", 5, 0, mainWindow)
theHelpButton = programOfChoice("Need help or more information about this program?", "V1.0", 7, 0, mainWindow)
theHelpButton.launchButton.configure(text = "Help", font =("Arial", 20))

if os.path.isfile((os.path.expanduser('~') + "\\MisAR\\MisarQVTv3\\source\\PSM.ecore")) == True:
    theParser.launchButton.configure(text = "Launch")

if os.path.isfile((os.path.expanduser('~') + "\\GMG\\Runnable Jar File\\MiSAR.jar")) == True:
    theGraphicalModelGenerator.launchButton.configure(text = "Launch")

mainWindow.protocol("WM_DELETE_WINDOW", window_quit)


mainWindow.mainloop()