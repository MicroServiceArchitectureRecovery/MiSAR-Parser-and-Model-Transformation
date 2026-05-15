import argparse
import hashlib
import json
import logging
import shutil
import stat
import subprocess
import sys
import tkinter
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path
from tkinter import messagebox
from urllib.request import Request, urlopen
import os
from datetime import datetime

# ===============================
# ENVIRONMENT VARIABLES
# ===============================

USER_HOME_DIR = Path.home()
AIO_DIR = Path(__file__).resolve().parent

MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
PARSER_PSM_ECORE = PARSER_DIR / "TransformationEngineNecessities" / "source" / "PSM.ecore"
PARSER_GUI_PATH = PARSER_DIR / "ParserNecessities" / "MisarParserGUI.py"
PARSER_METADATA_PATH = PARSER_DIR / "MiSAR.parser.release.json"
PARSER_REPOSITORY_API_URL = "https://api.github.com/repos/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation"
PARSER_REPOSITORY_CLONE_URL = "https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation.git"

GMG_RELEASE_API_URL = "https://api.github.com/repos/MicroServiceArchitectureRecovery/misar-plantUML/releases/latest"
GMG_ASSET_NAME = "MiSAR.jar"
GMG_JAR_DIR = USER_HOME_DIR / "MISAR" / "GMG"
GMG_JAR_PATH = GMG_JAR_DIR / GMG_ASSET_NAME
GMG_METADATA_PATH = GMG_JAR_DIR / "MiSAR.release.json"

MISAR_DOCUMENTATION_URL = "https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/"
LOG_DIR = AIO_DIR / "logs"
LOG_FILE_PATH = LOG_DIR / f"MiSAR-LOGGER-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

REQUIRED_MODULES = [
    ("git", "GitPython"),
    ("pyecore", "pyecore"),
    ("yaml", "PyYAML"),
    ("xmltodict", "xmltodict"),
    ("javalang", "javalang"),
]

LOGGER = logging.getLogger("MiSAR-AIO")
LOGGER.propagate = False

main_window = None
the_parser = None
the_graphical_model_generator = None
the_help_button = None

# ===============================
# HELPER FUNCTIONS
# ===============================


def parse_arguments():
    """Parse MiSAR AIO command-line arguments without interrupting Tkinter."""
    parser = argparse.ArgumentParser(description="MiSAR All-in-One launcher")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to logs/MiSAR-AIO.log and the terminal.",
    )
    return parser.parse_known_args()[0]


ARGS = parse_arguments()
DEBUG_MODE = ARGS.debug


def setup_logger():
    """Configure the optional debug logger, leaving logging disabled by default."""
    LOGGER.handlers.clear()

    if not DEBUG_MODE:
        LOGGER.addHandler(logging.NullHandler())
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(console_handler)
    LOGGER.debug("Logger enabled")


def serialise_log_value(value):
    """Convert log values into JSON-safe data for structured debug events."""
    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Exception):
        return str(value)

    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def log_event(event, **details):
    """Write a structured debug event when --debug is enabled."""
    if not DEBUG_MODE:
        return

    payload = {key: serialise_log_value(value) for key, value in details.items()}
    LOGGER.debug("%s | %s", event, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def log_exception(event, error, **details):
    """Write a structured debug event with exception traceback when --debug is enabled."""
    if not DEBUG_MODE:
        return

    payload = {key: serialise_log_value(value) for key, value in details.items()}
    payload["error"] = str(error)
    LOGGER.exception("%s | %s", event, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def check_internet():
    """Return True when a short internet connectivity check succeeds."""
    log_event("internet_check_started")

    try:
        request = Request("https://google.com/", headers={"User-Agent": "MiSAR-AIO"})
        urlopen(request, timeout=3)
        log_event("internet_check_success")
        return True
    except Exception as error:
        log_event("internet_check_failed", error=str(error))
        return False


def plural_check(errors):
    """Return a grammatically correct module phrase for user-facing dependency errors."""
    return "this required module." if len(errors) == 1 else "these required modules."


def get_json_from_url(url):
    """Fetch and parse JSON from a GitHub API endpoint."""
    log_event("github_api_request_started", url=url)

    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MiSAR-AIO",
        },
    )

    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    log_event("github_api_request_success", url=url)
    return payload


def calculate_sha256_digest(file_path):
    """Calculate a file SHA-256 digest using GitHub's 'sha256:<hash>' format."""
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256_hash.update(chunk)

    digest = "sha256:" + sha256_hash.hexdigest()
    log_event("sha256_calculated", file_path=file_path, digest=digest)
    return digest


def get_missing_modules():
    """Return required Python modules that are not currently importable."""
    missing_modules = []

    for import_name, package_name in REQUIRED_MODULES:
        try:
            __import__(import_name)
        except ModuleNotFoundError:
            missing_modules.append((import_name, package_name))

    log_event("dependency_check_completed", missing_modules=[name for name, _ in missing_modules])
    return missing_modules


def install_python_package(package_name):
    """Install one Python package using the same interpreter running MiSAR AIO."""
    log_event("python_package_install_started", package=package_name)
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
    log_event("python_package_install_success", package=package_name)


def check_required_modules():
    """Ensure MiSAR parser dependencies exist, optionally installing missing packages."""
    missing_modules = get_missing_modules()

    if not missing_modules:
        return True

    module_names = [import_name for import_name, _ in missing_modules]
    module_list = "\n".join(module_names)

    if len(missing_modules) == 1:
        message = (
            "The following import is currently not installed:\n\n"
            + module_list
            + "\n\nThis import is mandatory for the function of MiSAR.\nWould you like to install it now?"
        )
    else:
        message = (
            "The following imports are currently not installed:\n\n"
            + module_list
            + "\n\nThese imports are mandatory for the function of MiSAR.\nWould you like to install them now?"
        )

    install_modules = messagebox.askquestion("Missing Imports", message)
    log_event("missing_dependency_user_response", response=install_modules, modules=module_names)

    if install_modules != "yes":
        messagebox.showerror(
            "Error!",
            "MiSAR cannot operate correctly without "
            + plural_check(module_names)
            + " Please select yes and try again.",
        )
        return False

    if not check_internet():
        messagebox.showerror(
            "Error!",
            "An internet connection is required to install "
            + plural_check(module_names)
            + " Please connect to the internet and try again.",
        )
        return False

    try:
        for _, package_name in missing_modules:
            install_python_package(package_name)

        if get_missing_modules():
            raise RuntimeError("Some required modules are still missing after installation.")

        messagebox.showinfo("Success!", "The operation completed successfully!")
        return True
    except Exception as error:
        log_exception("dependency_install_failed", error, modules=module_names)
        messagebox.showerror(
            "Error!",
            "The installation of the required modules has failed.\nError code:\n" + str(error),
        )
        return False


def read_json_file(file_path):
    """Read JSON from disk, returning an empty dictionary when the file is unavailable."""
    if not file_path.is_file():
        log_event("json_file_missing", path=file_path)
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        log_event("json_file_read", path=file_path, data=data)
        return data
    except Exception as error:
        log_event("json_file_read_failed", path=file_path, error=str(error))
        return {}


def write_json_file(file_path, data):
    """Write JSON metadata to disk, creating the parent directory when required."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=2)

    log_event("json_file_written", path=file_path, data=data)


def open_documentation():
    """Open the MiSAR online documentation in the user's default browser."""
    log_event("documentation_open_requested", url=MISAR_DOCUMENTATION_URL)

    if check_internet():
        webbrowser.open(MISAR_DOCUMENTATION_URL, new=2)
        log_event("documentation_opened", url=MISAR_DOCUMENTATION_URL)
        return True

    messagebox.showerror(
        "No Internet Connection",
        "An internet connection is required to open the MiSAR documentation website.",
    )
    log_event("documentation_open_failed", reason="no_internet")
    return False


def uninstall_path(location):
    """Remove an installed MiSAR directory, including read-only files on Windows."""
    target_link = ""
    read_only = True
    location_path = USER_HOME_DIR / Path(location)
    log_event("uninstall_started", location=location_path)

    while read_only:
        read_only = False

        try:
            location_path.rmdir()
            log_event("uninstall_completed", location=location_path)
        except OSError:
            try:
                shutil.rmtree(location_path)
                log_event("uninstall_completed", location=location_path)
            except FileNotFoundError:
                log_event("uninstall_skipped_missing_path", location=location_path)
            except PermissionError as error:
                log_event("uninstall_permission_error", location=location_path, error=str(error))
                error_text = str(error)
                comma_activate = False

                for character in error_text:
                    if character == "'" and comma_activate:
                        comma_activate = False
                    elif comma_activate:
                        target_link += character
                    elif character == "'" and not comma_activate:
                        comma_activate = True

                target_path = Path(target_link)
                target_path.chmod(stat.S_IWRITE)
                target_path.unlink()

                try:
                    shutil.rmtree(target_path)
                except FileNotFoundError:
                    pass

                target_link = ""
                read_only = True

# ===============================
# INSTALLERS
# ===============================


def install_parser():
    """Install the MiSAR parser and persist repository metadata when available."""
    repository_metadata = None

    try:
        if check_internet():
            repository_metadata = get_parser_repository_metadata()
    except Exception as error:
        log_event("parser_repository_metadata_unavailable", error=str(error))

    return clone_parser_repository(Path("MiSAR") / "Parser", repository_metadata)


def clone_parser_repository(parser_location, repository_metadata=None):
    """Clone the parser repository into the MiSAR installation directory."""
    from git import Repo

    parser_path = USER_HOME_DIR / Path(parser_location)
    log_event("parser_install_started", path=parser_path)

    try:
        Repo.clone_from(PARSER_REPOSITORY_CLONE_URL, parser_path, branch="main")

        parser_ready = (
            parser_path / "TransformationEngineNecessities" / "source" / "PSM.ecore"
        ).is_file() and (parser_path / "ParserNecessities" / "MisarParserGUI.py").is_file()

        if parser_ready:
            if repository_metadata is not None and parser_path == PARSER_DIR:
                write_parser_metadata(repository_metadata)

            log_event("parser_install_success", path=parser_path)
            return True

        log_event("parser_install_validation_failed", path=parser_path)
        return False
    except Exception as error:
        log_exception("parser_install_failed", error, path=parser_path)
        return False


def install_or_update_gmg():
    """Download or update the Graphical Model Generator JAR from the latest release."""
    log_event("gmg_install_or_update_started", jar_path=GMG_JAR_PATH)

    try:
        asset = get_latest_gmg_jar_asset()

        if not should_download_gmg_jar(asset):
            log_event("gmg_jar_already_current", jar_path=GMG_JAR_PATH)
            return True

        download_gmg_jar(asset)
        write_gmg_metadata(asset)

        installed = GMG_JAR_PATH.is_file()
        log_event("gmg_install_or_update_completed", installed=installed, jar_path=GMG_JAR_PATH)
        return installed
    except Exception as error:
        log_exception("gmg_install_or_update_failed", error, jar_path=GMG_JAR_PATH)
        return False


def get_latest_gmg_jar_asset():
    """Return release metadata for the latest valid MiSAR.jar asset."""
    release_data = get_json_from_url(GMG_RELEASE_API_URL)
    assets_url = release_data.get("assets_url")

    if not assets_url:
        raise RuntimeError("The latest GMG release does not include an assets URL.")

    assets = get_json_from_url(assets_url)
    log_event("gmg_release_assets_loaded", asset_count=len(assets))

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

            selected_asset = {
                "name": asset_name,
                "download_url": download_url,
                "digest": asset.get("digest"),
                "updated_at": asset.get("updated_at"),
                "size": asset.get("size"),
            }
            log_event("gmg_release_asset_selected", asset=selected_asset)
            return selected_asset

    raise RuntimeError("Could not find a valid MiSAR.jar release asset.")


def should_download_gmg_jar(asset):
    """Return True when the local GMG JAR is missing or differs from the release asset."""
    if not GMG_JAR_PATH.is_file():
        log_event("gmg_download_required", reason="missing_local_jar", jar_path=GMG_JAR_PATH)
        return True

    expected_digest = asset.get("digest")

    if expected_digest:
        current_digest = calculate_sha256_digest(GMG_JAR_PATH)
        should_download = current_digest != expected_digest
        log_event(
            "gmg_digest_comparison_completed",
            should_download=should_download,
            current_digest=current_digest,
            expected_digest=expected_digest,
        )
        return should_download

    metadata = read_gmg_metadata()
    should_download = metadata.get("updated_at") != asset.get("updated_at")
    log_event(
        "gmg_updated_at_comparison_completed",
        should_download=should_download,
        local_updated_at=metadata.get("updated_at"),
        remote_updated_at=asset.get("updated_at"),
    )
    return should_download


def download_gmg_jar(asset):
    """Download the GMG JAR to a temporary file and verify its SHA-256 digest."""
    GMG_JAR_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = GMG_JAR_PATH.with_suffix(".jar.tmp")

    log_event("gmg_download_started", url=asset["download_url"], temp_path=temp_path)
    request = Request(asset["download_url"], headers={"User-Agent": "MiSAR-AIO"})

    with urlopen(request, timeout=120) as response:
        with open(temp_path, "wb") as output_file:
            shutil.copyfileobj(response, output_file)

    expected_digest = asset.get("digest")

    if expected_digest:
        downloaded_digest = calculate_sha256_digest(temp_path)

        if downloaded_digest != expected_digest:
            temp_path.unlink(missing_ok=True)
            log_event(
                "gmg_download_digest_failed",
                downloaded_digest=downloaded_digest,
                expected_digest=expected_digest,
            )
            raise RuntimeError("Downloaded MiSAR.jar failed SHA-256 verification.")

        log_event("gmg_download_digest_verified", digest=downloaded_digest)

    temp_path.replace(GMG_JAR_PATH)
    log_event("gmg_download_completed", jar_path=GMG_JAR_PATH)


def read_gmg_metadata():
    """Read GMG release metadata stored beside the downloaded JAR."""
    return read_json_file(GMG_METADATA_PATH)


def write_gmg_metadata(asset):
    """Store GMG release metadata beside the downloaded JAR."""
    write_json_file(GMG_METADATA_PATH, asset)

# ===============================
# UPDATERS
# ===============================


def get_parser_repository_metadata():
    """Return update metadata from the parser repository GitHub API."""
    repository_data = get_json_from_url(PARSER_REPOSITORY_API_URL)
    pushed_at = repository_data.get("pushed_at")

    if pushed_at is None:
        raise RuntimeError("Could not read parser repository update time from GitHub.")

    metadata = {
        "pushed_at": pushed_at,
        "default_branch": repository_data.get("default_branch", "main"),
        "clone_url": repository_data.get("clone_url", PARSER_REPOSITORY_CLONE_URL),
    }

    log_event("parser_repository_metadata_loaded", metadata=metadata)
    return metadata


def read_parser_metadata():
    """Read the local parser metadata file used for update comparison."""
    return read_json_file(PARSER_METADATA_PATH)


def write_parser_metadata(metadata):
    """Store parser metadata after a successful install or update."""
    write_json_file(PARSER_METADATA_PATH, metadata)


def is_parser_installed():
    """Return True when the parser installation contains its required entry files."""
    installed = PARSER_PSM_ECORE.is_file() and PARSER_GUI_PATH.is_file()
    log_event(
        "parser_installation_checked",
        installed=installed,
        psm_ecore=PARSER_PSM_ECORE,
        parser_gui=PARSER_GUI_PATH,
    )
    return installed


def is_parser_update_available(repository_metadata):
    """Compare local parser metadata with GitHub repository metadata."""
    local_metadata = read_parser_metadata()
    update_available = local_metadata.get("pushed_at") != repository_metadata.get("pushed_at")

    log_event(
        "parser_update_comparison_completed",
        update_available=update_available,
        local_pushed_at=local_metadata.get("pushed_at"),
        remote_pushed_at=repository_metadata.get("pushed_at"),
    )
    return update_available


def automatic_update_check():
    """Check for parser updates after the UI starts, without interrupting offline users."""
    log_event("automatic_update_check_started")

    if not check_internet():
        log_event("automatic_update_check_skipped", reason="no_internet")
        return

    if not is_parser_installed():
        log_event("automatic_update_check_skipped", reason="parser_not_installed")
        return

    try:
        repository_metadata = get_parser_repository_metadata()

        if not is_parser_update_available(repository_metadata):
            log_event("automatic_update_check_completed", update_available=False)
            return

        update_available = messagebox.askquestion(
            "Parser Update Available",
            "An update is available for the MiSAR Parser and Transformation Engine.\n"
            "Would you like to install it now?",
        )
        log_event("parser_update_prompt_response", response=update_available)

        if update_available != "yes":
            return

        if not check_required_modules():
            return

        if PARSER_DIR.exists():
            uninstall_path(Path("MiSAR") / "Parser")

        if clone_parser_repository(Path("MiSAR") / "Parser", repository_metadata):
            messagebox.showinfo("Success!", "The parser update completed successfully.")
            refresh_launch_buttons()
        else:
            messagebox.showerror("Failure!", "The parser update has failed.")
    except Exception as error:
        log_exception("automatic_update_check_failed", error)
        messagebox.showerror(
            "Update Check Failed",
            "MiSAR could not check for parser updates.\n\nError code:\n" + str(error),
        )

def run_logged_subprocess(command, process_name, cwd=None):
    """Run a child process and stream its stdout/stderr into the AIO debug logger."""
    log_event("subprocess_started", process_name=process_name, command=command, cwd=cwd)

    if not DEBUG_MODE:
        return subprocess.call(command, cwd=cwd)

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        if process.stdout is not None:
            for line in process.stdout:
                LOGGER.debug(
                    "%s stdout | %s",
                    process_name,
                    line.rstrip(),
                )

        return_code = process.wait()
        log_event("subprocess_completed", process_name=process_name, return_code=return_code)
        return return_code
    except Exception as error:
        process.kill()
        log_exception("subprocess_failed", error, process_name=process_name)
        raise

# ===============================
# UNINSTALLER
# ===============================

def is_gmg_installed():
    """Return True when the Graphical Model Generator JAR exists locally."""
    installed = GMG_JAR_PATH.is_file()
    log_event("gmg_installation_checked", installed=installed, jar_path=GMG_JAR_PATH)
    return installed


def set_module_button_state(module, installed):
    """Update launch/install and uninstall button states for one module."""
    module.launch_button.configure(text="Launch" if installed else "Install")

    if module.uninstall_button is not None:
        module.uninstall_button.configure(
            state=tkinter.NORMAL if installed else tkinter.DISABLED
        )

def handle_uninstall_button(module):
    """Route an uninstallation button click to the correct module uninstaller."""
    log_event("uninstall_button_clicked", button_name=module.name)

    if module.name == "MiSAR Parser":
        handle_parser_uninstall()
    elif module.name == "MiSAR Graphical Model Generator":
        handle_gmg_uninstall()


def handle_parser_uninstall():
    """Uninstall the MiSAR Parser from the user MiSAR directory."""
    if not is_parser_installed():
        refresh_launch_buttons()
        return

    uninstall_choice = messagebox.askquestion(
        "Uninstall MiSAR Parser",
        "This will remove the installed MiSAR Parser from:\n\n"
        + str(PARSER_DIR)
        + "\n\nDo you want to continue?",
    )
    log_event("parser_uninstall_prompt_response", response=uninstall_choice, path=PARSER_DIR)

    if uninstall_choice != "yes":
        return

    try:
        uninstall_path(Path("MiSAR") / "Parser")
        messagebox.showinfo("Success!", "The MiSAR Parser has been uninstalled.")
        refresh_launch_buttons()
    except Exception as error:
        log_exception("parser_uninstall_failed", error, path=PARSER_DIR)
        messagebox.showerror(
            "Uninstall Failed",
            "The MiSAR Parser could not be uninstalled.\n\nError code:\n" + str(error),
        )


def handle_gmg_uninstall():
    """Uninstall the Graphical Model Generator JAR and local metadata."""
    if not is_gmg_installed() and not GMG_METADATA_PATH.is_file():
        refresh_launch_buttons()
        return

    uninstall_choice = messagebox.askquestion(
        "Uninstall Graphical Model Generator",
        "This will remove the installed Graphical Model Generator files from:\n\n"
        + str(GMG_JAR_DIR)
        + "\n\nDo you want to continue?",
    )
    log_event(
        "gmg_uninstall_prompt_response",
        response=uninstall_choice,
        jar_path=GMG_JAR_PATH,
        metadata_path=GMG_METADATA_PATH,
    )

    if uninstall_choice != "yes":
        return

    try:
        GMG_JAR_PATH.unlink(missing_ok=True)
        GMG_METADATA_PATH.unlink(missing_ok=True)
        GMG_JAR_PATH.with_suffix(".jar.tmp").unlink(missing_ok=True)

        messagebox.showinfo("Success!", "The Graphical Model Generator has been uninstalled.")
        refresh_launch_buttons()
    except Exception as error:
        log_exception("gmg_uninstall_failed", error, jar_path=GMG_JAR_PATH)
        messagebox.showerror(
            "Uninstall Failed",
            "The Graphical Model Generator could not be uninstalled.\n\nError code:\n" + str(error),
        )

# ===============================
# MAIN
# ===============================


class ProgramOfChoice:
    """Represent one selectable MiSAR module in the launcher UI."""

    def __init__(self, name, version, input_row, input_column, target_window, supports_uninstall=False):
        """Create the module label, action button, and optional uninstall button."""
        self.name = name
        self.version = version
        self.input_row = input_row
        self.input_column = input_column
        self.uninstall_button = None

        self.container = tkinter.Frame(target_window)
        self.container.grid(row=input_row, column=input_column, pady=8)

        self.module_name = tkinter.Label(self.container, text=name, font=("Arial", 20))
        self.module_name.pack()

        self.button_frame = tkinter.Frame(self.container)
        self.button_frame.pack(pady=6)

        self.launch_button = tkinter.Button(self.button_frame, text="Install", font=("Arial", 20), width=10)
        self.launch_button.configure(command=lambda button=self: handle_module_button(button))
        self.launch_button.pack(side=tkinter.LEFT, padx=8)

        if supports_uninstall:
            self.uninstall_button = tkinter.Button(
                self.button_frame,
                text="Uninstall",
                font=("Arial", 20),
                width=10,
                state=tkinter.DISABLED,
            )
            self.uninstall_button.configure(command=lambda button=self: handle_uninstall_button(button))
            self.uninstall_button.pack(side=tkinter.LEFT, padx=8)

        log_event(
            "program_button_created",
            name=name,
            version=version,
            row=input_row,
            column=input_column,
            supports_uninstall=supports_uninstall,
        )


def handle_parser_button():
    """Install or launch the MiSAR Parser depending on the local installation state."""
    if not PARSER_PSM_ECORE.is_file():
        install_parser_choice = messagebox.askquestion(
            "Parser Installer",
            "To use the MiSAR Parser, you must first install it.\nWould you like to install it now?",
        )
        log_event("parser_install_prompt_response", response=install_parser_choice)

        if install_parser_choice != "yes":
            return

        if not check_internet():
            messagebox.showerror(
                "No Internet Connection!",
                "An internet connection is required to install the MiSAR Parser.",
            )
            return

        if not check_required_modules():
            return

        messagebox.showinfo("Installation commencing!", "The Parser will now be installed.")

        if install_parser():
            messagebox.showinfo(
                "Success!",
                "The operation completed successfully!\nThe Parser has been installed! It has been saved at: "
                + str(MISAR_DIR),
            )
            refresh_launch_buttons()
            return

        uninstall_path(Path("MiSAR") / "Parser")

        if install_parser():
            messagebox.showinfo(
                "Success!",
                "The operation completed successfully!\nThe Parser has been installed! It has been saved at: "
                + str(PARSER_DIR),
            )
            refresh_launch_buttons()
        else:
            messagebox.showerror("Failure!", "The Parser installation has failed.")

        return

    if check_required_modules():
        log_event("parser_launch_started", path=PARSER_GUI_PATH)
        main_window.destroy()
        run_logged_subprocess([sys.executable, "-u", str(PARSER_GUI_PATH)],"MiSAR Parser GUI",cwd=PARSER_GUI_PATH.parent)
        log_event("parser_launch_completed", path=PARSER_GUI_PATH)


def handle_transformation_engine_button():
    """Handle the placeholder Transformation Engine selection."""
    if check_required_modules():
        log_event("transformation_engine_selected")
        main_window.destroy()
    else:
        messagebox.showerror(
            "Error!",
            "The installation has failed!\nIf 'No' was selected, please select yes and try again.\n Otherwise, check your internet connection.",
        )


def handle_gmg_button():
    """Install, update, or launch the Graphical Model Generator JAR."""
    if not GMG_JAR_PATH.is_file():
        install_gmg = messagebox.askquestion(
            "Graphical Model Generator Installer",
            "To use the MiSAR Graphical Model Generator, you must first install it.\nWould you like to install it now?",
        )
        log_event("gmg_install_prompt_response", response=install_gmg)

        if install_gmg != "yes":
            return

        if not check_internet():
            messagebox.showerror(
                "No Internet Connection!",
                "An internet connection is required to install the MiSAR Graphical Model Generator.",
            )
            return

        if install_or_update_gmg():
            messagebox.showinfo(
                "Success!",
                "The operation completed successfully!\nThe Graphical Model Generator JAR has been saved at: "
                + str(GMG_JAR_PATH),
            )
            refresh_launch_buttons()
        else:
            messagebox.showerror("Failure!", "The Graphical Model Generator installation has failed.")

        return

    if check_internet():
        install_or_update_gmg()

    log_event("gmg_launch_started", jar_path=GMG_JAR_PATH)
    main_window.destroy()
    run_logged_subprocess(["java", "-jar", str(GMG_JAR_PATH)],"MiSAR Graphical Model Generator",cwd=GMG_JAR_PATH.parent)
    log_event("gmg_launch_completed", jar_path=GMG_JAR_PATH)


def handle_help_button():
    """Show MiSAR help information and optionally open the online documentation."""
    log_event("help_button_clicked")

    messagebox.showinfo(
        "MiSAR Help",
        "Hello and welcome to MiSAR.\n\n"
        "MiSAR is an approach that follows Model Driven Architecture to semi-automatically "
        "generate architectural models of implemented microservice systems.\n\n"
        "The documentation includes guidance for the Parser, Transformation Engine, "
        "Graphical Model Generator, setup instructions, and usage examples.",
    )

    open_documentation_choice = messagebox.askquestion(
        "MiSAR Documentation",
        "Would you like to open the MiSAR documentation website?",
    )
    log_event("documentation_prompt_response", response=open_documentation_choice)

    if open_documentation_choice == "yes":
        open_documentation()


def handle_module_button(module):
    """Route a launcher button click to the correct module handler."""
    log_event("button_clicked", button_name=module.name)

    if module.name == "MiSAR Parser":
        handle_parser_button()
    elif module.name == "MiSAR Transformation Engine":
        handle_transformation_engine_button()
    elif module.name == "MiSAR Graphical Model Generator":
        handle_gmg_button()
    elif module.name == "Need help or more information about this program?":
        handle_help_button()


def window_quit():
    """Close the Tkinter window and record the shutdown event."""
    log_event("window_quit_requested")
    main_window.quit()
    main_window.destroy()


def refresh_launch_buttons():
    """Set launcher buttons to match each module's installed/uninstalled state."""
    log_event("launch_button_refresh_started")

    parser_installed = is_parser_installed()
    gmg_installed = is_gmg_installed()

    set_module_button_state(the_parser, parser_installed)
    set_module_button_state(the_graphical_model_generator, gmg_installed)

    log_event(
        "launch_button_refresh_completed",
        parser_installed=parser_installed,
        gmg_installed=gmg_installed,
    )

def initialise_ui():
    """Create and return the MiSAR AIO Tkinter main window."""
    log_event("ui_initialisation_started")

    root = tkinter.Tk()
    root.title("MicroService Architecture Recovery")
    root.grid_columnconfigure(0, weight=1)

    welcome = tkinter.Label(
        root,
        text="Hello and welcome to the MiSAR AIO!\nPlease select a program you would like to use from the list below:",
        font=("Arial", 20),
        justify="center",
    )
    welcome.grid(row=0, column=0, pady=(12, 8))

    log_event("ui_initialisation_completed")
    return root


def run_application():
    """Initialise the MiSAR AIO UI, schedule update checks, and start Tkinter."""
    global main_window, the_parser, the_graphical_model_generator, the_help_button

    log_event(
        "application_startup",
        debug_enabled=DEBUG_MODE,
        log_file=LOG_FILE_PATH if DEBUG_MODE else None,
        aio_dir=AIO_DIR,
        parser_dir=PARSER_DIR,
        gmg_jar_path=GMG_JAR_PATH,
    )

    main_window = initialise_ui()

    the_parser = ProgramOfChoice("MiSAR Parser", "V1.0", 1, 0, main_window, supports_uninstall=True)
    the_graphical_model_generator = ProgramOfChoice(
        "MiSAR Graphical Model Generator","V1.0",5,0, main_window, supports_uninstall=True,)
    the_help_button = ProgramOfChoice("Need help or more information about this program?", "V1.0", 7, 0, main_window)
    the_help_button.launch_button.configure(text="Help", font=("Arial", 20))

    refresh_launch_buttons()

    main_window.after(500, automatic_update_check)
    main_window.protocol("WM_DELETE_WINDOW", window_quit)

    log_event("tkinter_mainloop_started")
    main_window.mainloop()
    log_event("application_shutdown")


setup_logger()

if __name__ == "__main__":
    run_application()
