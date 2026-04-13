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

# ===============================
# ENVIRONMENTS FOR THE MiSAR AIO
# ===============================

USER_HOME_DIR = Path.home()
MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
GMG_DIR = MISAR_DIR / "GMG"
MISAR_TEMP_DIR = USER_HOME_DIR / "MiSARTemp"

PARSER_PSM_ECORE = PARSER_DIR / "TransformationEngineNecessities" / "source" / "PSM.ecore"
PARSER_GUI_PATH = PARSER_DIR / "ParserNecessities" / "MisarParserGUI.py"
GMG_JAR_PATH = GMG_DIR / "Runnable Jar File" / "MiSAR.jar"

PARSER_MANUAL_PATH = MISAR_DIR / "MiSAR Parser - manualfinal.pdf"
MISAR_MANUAL_PATH = MISAR_DIR / "MiSAR Manual v1.pdf"


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
    parser_path = USER_HOME_DIR / Path(parserLocation)
    print(parser_path)
    try:
        Repo.clone_from(
            "https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation.git",
            parser_path, branch="main")
        if os.path.isfile(parser_path / "TransformationEngineNecessities" / "source" / "PSM.ecore") == True:
            if os.path.isfile(parser_path / "ParserNecessities" / "MisarParserGUI.py") == True:
                return True
    except Exception as fail:
        return False


def gmgInstaller(gmgLocation):
    from git import Repo
    gmg_path = USER_HOME_DIR / Path(gmgLocation)
    print(gmg_path)
    try:
        Repo.clone_from(
            "https://github.com/MicroServiceArchitectureRecovery/misar-plantUML.git",
            gmg_path, branch="main")
        if os.path.isfile(gmg_path / "Runnable Jar File" / "MiSAR.jar") == True:
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


def buttonStuff(inputClass):
    if inputClass.name == "MiSAR Parser":
        if os.path.isfile(PARSER_PSM_ECORE) == False:
            MisarChecker = messagebox.askquestion("Parser Installer", "To use the MiSAR Parser, you must first install it.\nWould you to like to install it now?")
            if MisarChecker == "yes":
                if checkInternet():
                    if checkIfModulesAreInstalled(inputClass):
                        messagebox.showinfo("Installation commencing!",
                                            "The Parser will now be installed.")
                        if parserInstaller(Path("MiSAR") / "Parser") == True:
                            messagebox.showinfo("Success!",
                                                "The operation completed successfully!\nThe Parser has been installed! It has been saved at: " + str(
                                                    MISAR_DIR))
                            theParser.launchButton.configure(text="Launch")
                        else:
                            Uninstaller(Path("MiSAR") / "Parser")
                            if parserInstaller(Path("MiSAR") / "Parser") == True:
                                messagebox.showinfo("Success!",
                                                    "The operation completed successfully!\nThe Parser has been installed! It has been saved at: " + str(
                                                        PARSER_DIR))
                                theParser.launchButton.configure(text="Launch")
                else:
                    messagebox.showerror("No Internet Connection!",
                                         "An internet connection is required to install the " + inputClass.name + ".")
        elif checkIfModulesAreInstalled(inputClass):
                mainWindow.destroy()
                subprocess.call(['python', str(PARSER_GUI_PATH)])

    elif inputClass.name == "MiSAR Transformation Engine":
        if checkIfModulesAreInstalled(inputClass):
            mainWindow.destroy()
            #import MisarTransformationEngine
        else:
            messagebox.showerror("Error!",
                                 "The installation has failed!\nIf 'No' was selected, please select yes and try again.\n Otherwise, check your internet connection.")

    elif inputClass.name == "MiSAR Graphical Model Generator":
        if os.path.isfile(GMG_JAR_PATH) == False:
            MisarChecker = messagebox.askquestion("Graphical Model Generator Installer", "To use the " + inputClass.name + ", you must first install it.\nWould you to like to install it now?")
            if MisarChecker == "yes":
                if checkInternet():
                    if checkIfModulesAreInstalled(inputClass):
                        if gmgInstaller(Path("MiSAR") / "GMG") == True:
                            messagebox.showinfo("Success!",
                                                "The operation completed successfully!\nThe Graphical Model Generator, and it's JAR executable has been saved at: " + str(
                                                    GMG_DIR))
                            theGraphicalModelGenerator.launchButton.configure(text="Launch")
                        else:
                            Uninstaller("GMG")
                            if gmgInstaller("GMG") == True:
                                messagebox.showinfo("Success!",
                                                    "The operation completed successfully!\nThe Graphical Model Generator, and it's JAR executable has been saved at: " + str(
                                                        GMG_DIR))
                                theGraphicalModelGenerator.launchButton.configure(text="Launch")
                else:
                    messagebox.showerror("No Internet Connection!",
                                         "An internet connection is required to install the " + inputClass.name + ".")
        else:
            mainWindow.destroy()
            subprocess.call(['java', '-jar', str(GMG_JAR_PATH)])

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
                webbrowser.open("https://www.youtube.com/watch?v=sdRDkLesyS0&ab_channel=NourAli", new=2)
            else:
                messagebox.showerror("No Internet Connection!",
                                     "An internet connection is required to view the MiSAR Demonstration Video.")
                demo = messagebox.askquestion("Need more?",
                                              "Would you instead like to view the manual for MiSAR?\n"
                                              "This does NOT requires an internet connection.")
                if demo == "yes":
                    subprocess.Popen(str(PARSER_MANUAL_PATH), shell=True)
        else:
            demo = messagebox.askquestion("Need more?",
                                          "Would you instead like to view the manual for MiSAR?\n"
                                          "This does NOT requires an internet connection.")
            if demo == "yes":
                subprocess.Popen(str(MISAR_MANUAL_PATH), shell=True)


def misar_updater():
    if checkInternet():
        if checkIfModulesAreInstalled(None):
            if os.path.isfile(PARSER_PSM_ECORE) == True:
                if os.path.isfile(MISAR_TEMP_DIR / "TransformationEngineNecessities" / "source" / "PSM.ecore") == True:
                    Uninstaller("MiSARTemp")
                if parserInstaller("MiSARTemp") == True:
                    previousDirectory = os.getcwd()
                    os.chdir(MISAR_TEMP_DIR)
                    newestVersion = os.popen("git log -1").read()
                    updatedDate = ""
                    colonCount = 0
                    targetCutOff = 999999
                    for x in range(0, len(newestVersion)):
                        if targetCutOff > x:
                            updatedDate = updatedDate + newestVersion[x]
                            if newestVersion[x] == ":" and colonCount < 2:
                                updatedDate = ""
                                colonCount = colonCount + 1
                            if colonCount >= 2 and newestVersion[x + 1] == "+" or newestVersion[x + 1] == "-":
                                break
                    updatedDate = updatedDate.strip()
                    onlineVersion = datetime.strptime(updatedDate, '%a %b %d %H:%M:%S %Y')
                    currentVersion = datetime.fromtimestamp(
                        os.path.getctime(PARSER_PSM_ECORE))
                    os.chdir(previousDirectory)
                    if onlineVersion > currentVersion:
                        updateAvailable = messagebox.askquestion("Update Available!",
                                                                 "An update is available! Would you like to install it now?")
                        if updateAvailable == "yes":
                            Uninstaller("MiSARTemp")
                            Uninstaller(Path("MiSAR") / "Parser")
                            if parserInstaller(Path("MiSAR") / "Parser") == True:
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
        self.moduleName = tkinter.Label(targetWindow, text=name, font=("Arial", 20))
        self.moduleName.grid(row=inputRow, column=inputColumn)
        self.launchButton = tkinter.Button(targetWindow, text="Install", font=("Arial", 20), width=10)
        self.launchButton.configure(command=lambda button=self: buttonStuff(button))
        self.launchButton.grid(row=inputRow + 1, column=inputColumn)


def window_quit():
    mainWindow.quit()
    mainWindow.destroy()


misar_updater()

mainWindow = tkinter.Tk()

mainWindow.title("MicroService Architecture Recovery")
welcome = tkinter.Label(mainWindow, text="Hello and welcome to the MiSAR AIO!\n Please select a program you would like to use from the list below:", font=("Arial", 20))
welcome.grid(row=0, column=0)

theParser = programOfChoice("MiSAR Parser", "V1.0", 1, 0, mainWindow)
#theTransformationEngine = programOfChoice("MiSAR Transformation Engine", "V1.0", 3, 0, mainWindow)
theGraphicalModelGenerator = programOfChoice("MiSAR Graphical Model Generator", "V1.0", 5, 0, mainWindow)
theHelpButton = programOfChoice("Need help or more information about this program?", "V1.0", 7, 0, mainWindow)
theHelpButton.launchButton.configure(text="Help", font=("Arial", 20))

if os.path.isfile(PARSER_PSM_ECORE) == True:
    theParser.launchButton.configure(text="Launch")

if os.path.isfile(GMG_JAR_PATH) == True:
    theGraphicalModelGenerator.launchButton.configure(text="Launch")

mainWindow.protocol("WM_DELETE_WINDOW", window_quit)

mainWindow.mainloop()