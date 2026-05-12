import tkinter
from tkinter import messagebox
import os
import shutil
import stat
import hashlib
import json
from urllib.request import Request, urlopen
from datetime import *
import webbrowser
import subprocess
from pathlib import Path

# ===============================
# ENVIRONMENTS FOR THE MiSAR AIO
# ===============================

USER_HOME_DIR = Path.home()
AIO_DIR = Path(__file__).resolve().parent

MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
MISAR_TEMP_DIR = USER_HOME_DIR / "MiSARTemp"

GMG_RELEASE_API_URL = "https://api.github.com/repos/MicroServiceArchitectureRecovery/misar-plantUML/releases/latest"
GMG_ASSET_NAME = "MiSAR.jar"
GMG_DIR = AIO_DIR
GMG_JAR_DIR = AIO_DIR
GMG_JAR_PATH = GMG_JAR_DIR / GMG_ASSET_NAME
GMG_METADATA_PATH = GMG_JAR_DIR / "MiSAR.release.json"

PARSER_PSM_ECORE = PARSER_DIR / "TransformationEngineNecessities" / "source" / "PSM.ecore"
PARSER_GUI_PATH = PARSER_DIR / "ParserNecessities" / "MisarParserGUI.py"

MISAR_DOCUMENTATION_URL = "https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/create-psm/"

def checkInternet():
    try:
        request = Request("https://google.com/", headers={"User-Agent": "MiSAR-AIO"})
        urlopen(request, timeout=3)
        return True
    except Exception:
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


def gmgInstaller(gmgLocation=None):
    try:
        asset = get_latest_gmg_jar_asset()

        if not should_download_gmg_jar(asset):
            return True

        download_gmg_jar(asset)
        write_gmg_metadata(asset)

        return GMG_JAR_PATH.is_file()
    except Exception as fail:
        print("GMG installation failed:", fail)
        return False


def get_latest_gmg_jar_asset():
    release_data = get_json_from_url(GMG_RELEASE_API_URL)
    assets_url = release_data.get("assets_url")

    if not assets_url:
        raise RuntimeError("The latest GMG release does not include an assets URL.")

    assets = get_json_from_url(assets_url)

    for asset in assets:
        asset_name = asset.get("name", "")
        content_type = asset.get("content_type", "")

        is_expected_name = asset_name == GMG_ASSET_NAME
        is_java_archive = content_type == "application/java-archive"
        is_jar_file = asset_name.lower().endswith(".jar")

        if is_expected_name and is_jar_file and is_java_archive:
            download_url = asset.get("browser_download_url")

            if not download_url:
                raise RuntimeError("The GMG JAR asset does not include a download URL.")

            return {
                "name": asset_name,
                "download_url": download_url,
                "digest": asset.get("digest"),
                "updated_at": asset.get("updated_at"),
                "size": asset.get("size"),
            }

    raise RuntimeError("Could not find a valid MiSAR.jar release asset.")


def get_json_from_url(url):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MiSAR-AIO",
        },
    )

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def should_download_gmg_jar(asset):
    if not GMG_JAR_PATH.is_file():
        return True

    expected_digest = asset.get("digest")

    if expected_digest:
        return calculate_sha256_digest(GMG_JAR_PATH) != expected_digest

    metadata = read_gmg_metadata()
    return metadata.get("updated_at") != asset.get("updated_at")


def download_gmg_jar(asset):
    GMG_JAR_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = GMG_JAR_PATH.with_suffix(".jar.tmp")
    request = Request(asset["download_url"], headers={"User-Agent": "MiSAR-AIO"})

    with urlopen(request, timeout=120) as response:
        with open(temp_path, "wb") as output_file:
            shutil.copyfileobj(response, output_file)

    expected_digest = asset.get("digest")

    if expected_digest:
        downloaded_digest = calculate_sha256_digest(temp_path)

        if downloaded_digest != expected_digest:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError("Downloaded MiSAR.jar failed SHA-256 verification.")

    temp_path.replace(GMG_JAR_PATH)


def calculate_sha256_digest(file_path):
    """
    Calculate the SHA256 digest of a file and return it in the format "sha256:<digest>".
    (To compare with the digest provided by GitHub API, which is in the format "sha256:<digest>")
    :param file_path:
    :return:
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256_hash.update(chunk)

    return "sha256:" + sha256_hash.hexdigest()


def read_gmg_metadata():
    if not GMG_METADATA_PATH.is_file():
        return {}
    try:
        with open(GMG_METADATA_PATH, "r", encoding="utf-8") as metadata_file:
            return json.load(metadata_file)
    except Exception:
        return {}


def write_gmg_metadata(asset):
    GMG_JAR_DIR.mkdir(parents=True, exist_ok=True)
    with open(GMG_METADATA_PATH, "w", encoding="utf-8") as metadata_file:
        json.dump(asset, metadata_file, indent=2)

def openDocumentation():
    if checkInternet():
        webbrowser.open(MISAR_DOCUMENTATION_URL, new=2)
        return True

    messagebox.showerror(
        "No Internet Connection",
        "An internet connection is required to open the MiSAR documentation website."
    )
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
        if not GMG_JAR_PATH.is_file():
            MisarChecker = messagebox.askquestion(
                "Graphical Model Generator Installer",
                "To use the " + inputClass.name + ", you must first install it.\nWould you like to install it now?"
            )

            if MisarChecker == "yes":
                if checkInternet():
                    if gmgInstaller() == True:
                        messagebox.showinfo(
                            "Success!",
                            "The operation completed successfully!\nThe Graphical Model Generator JAR has been saved at: "
                            + str(GMG_JAR_PATH)
                        )
                        theGraphicalModelGenerator.launchButton.configure(text="Launch")
                    else:
                        messagebox.showerror("Failure!", "The Graphical Model Generator installation has failed.")

                else:
                    messagebox.showerror(
                        "No Internet Connection!",
                        "An internet connection is required to install the " + inputClass.name + "."
                    )
        else:
            if checkInternet():
                gmgInstaller()
            mainWindow.destroy()
            subprocess.call(['java', '-jar', str(GMG_JAR_PATH)])

    elif inputClass.name == "Need help or more information about this program?":
        messagebox.showinfo(
            "MiSAR Help",
            "Hello and welcome to MiSAR.\n\n"
            "MiSAR is an approach that follows Model Driven Architecture to semi-automatically "
            "generate architectural models of implemented microservice systems.\n\n"
            "The documentation includes guidance for the Parser, Transformation Engine, "
            "Graphical Model Generator, setup instructions, and usage examples."
        )

        open_documentation = messagebox.askquestion(
            "MiSAR Documentation",
            "Would you like to open the MiSAR documentation website?"
        )

        if open_documentation == "yes":
            openDocumentation()


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