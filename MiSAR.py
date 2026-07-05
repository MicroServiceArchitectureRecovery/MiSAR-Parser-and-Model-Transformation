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
from tkinter import filedialog, messagebox
from urllib.request import Request, urlopen
import os
from datetime import datetime
import threading

# ===============================
# ENVIRONMENT VARIABLES
# ===============================

USER_HOME_DIR = Path.home()
AIO_DIR = Path(__file__).resolve().parent

MISAR_DIR = USER_HOME_DIR / "MiSAR"
INSTALLED_PARSER_DIR = MISAR_DIR / "Parser"
REPOSITORY_PARSER_DIR = AIO_DIR
ACTIVE_PARSER_DIR = INSTALLED_PARSER_DIR
PARSER_PSM_ECORE = ACTIVE_PARSER_DIR / "TransformationEngineNecessities" / "source" / "PSM.ecore"
PARSER_GUI_PATH = ACTIVE_PARSER_DIR / "ParserNecessities" / "MisarParserGUI.py"
PARSER_METADATA_PATH = ACTIVE_PARSER_DIR / "MiSAR.parser.release.json"
PARSER_REPOSITORY_API_URL = "https://api.github.com/repos/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation"
PARSER_REPOSITORY_CLONE_URL = "https://github.com/MicroServiceArchitectureRecovery/MiSAR-Parser-and-Model-Transformation.git"

GMG_RELEASE_API_URL = "https://api.github.com/repos/MicroServiceArchitectureRecovery/misar-plantUML/releases/latest"
GMG_ASSET_NAME = "MiSAR.jar"
GMG_JAR_DIR = USER_HOME_DIR / "MISAR" / "GMG"
GMG_JAR_PATH = GMG_JAR_DIR / GMG_ASSET_NAME
GMG_METADATA_PATH = GMG_JAR_DIR / "MiSAR.release.json"
GMG_VERSION_KEY = "misar.visualiser"

MISAR_DOCUMENTATION_URL = "https://microservicearchitecturerecovery.github.io/MiSAR-Parser-and-Model-Transformation/"
LOG_DIR = AIO_DIR / "logs"
LOG_FILE_PATH = LOG_DIR / f"MiSAR-LOGGER-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

REQUIRED_MODULES = [
    ("git", "GitPython"),
    ("pyecore", "pyecore"),
    ("yaml", "PyYAML"),
    ("xmltodict", "xmltodict"),
    ("javalang", "javalang"),
    ("screeninfo", "ScreenInfo"),
]

VERSION_FILE_PATH = AIO_DIR / "MISAR.versions.json"
CONFIG_FILE_PATH = AIO_DIR / "MISAR.configs.json"
IMAGE_DIR = AIO_DIR / "img"
MISAR_LOGO_PATH = IMAGE_DIR / "MainLogo.png"
BRUNEL_LOGO_PATH = IMAGE_DIR / "brunel_Logo.png"
AUTO_UPDATE_CONFIG_KEY = "updates.auto_check"
MODULE_VERSION_KEYS = {
    "MiSAR Parser": ("misar.parser",),
    "MiSAR Transformation Engine": ("misar.transofrmer", "misar.transformer"),
    "MiSAR Graphical Model Generator": ("misar.visualiser",),
}
LAUNCHER_VERSION_KEYS = ("misar.launcher",)
MISAR_VERSIONS = {}
MISAR_CONFIGS = {}

LOGGER = logging.getLogger("MiSAR-AIO")
LOGGER.propagate = False

main_window = None
the_parser = None
the_transformation_engine = None
the_graphical_model_generator = None
the_help_button = None

# ===============================
# HELPER FUNCTIONS
# ===============================


def config_value_as_bool(value, default=False):
    """Convert config values from JSON/string form into a boolean."""
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    text_value = str(value).strip().lower()

    if text_value in {"1", "true", "yes", "y", "on", "enabled"}:
        return True

    if text_value in {"0", "false", "no", "n", "off", "disabled"}:
        return False

    return default


def read_bootstrap_configs():
    """Read minimal startup config before the logger/UI helpers are available."""
    if not CONFIG_FILE_PATH.is_file():
        return {}

    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_use_repository_parser(cli_enabled=False, configs=None):
    """Return True when the repository parser runtime should be used."""
    if cli_enabled:
        return True

    configs = configs or {}
    return config_value_as_bool(configs.get(LOCAL_RUNTIME_CONFIG_KEY), False)


def parse_arguments():
    """Parse MiSAR AIO command-line arguments without interrupting Tkinter."""
    parser = argparse.ArgumentParser(description="MiSAR All-in-One launcher")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to logs/MiSAR-AIO.log and the terminal.",
    )
    parser.add_argument(
        "--psm-path",
        "--misar-psm-path",
        default=None,
        help="Optional PSM Ecore file to pass to the MiSAR Parser when debug mode is enabled.",
    )
    parser.add_argument(
        "--use-repository-parser",
        action="store_true",
        help="Use parser and transformation files from this repository instead of the installed stable runtime.",
    )
    return parser.parse_known_args()[0]


ARGS = parse_arguments()
BOOTSTRAP_CONFIGS = read_bootstrap_configs()
DEBUG_MODE = ARGS.debug
USE_REPOSITORY_PARSER = resolve_use_repository_parser(
    bool(getattr(ARGS, "use_repository_parser", False)),
    BOOTSTRAP_CONFIGS,
)
PARSER_SELECTED_PSM_PATH = Path(ARGS.psm_path).expanduser() if getattr(ARGS, "psm_path", None) else None


def configure_parser_runtime_paths():
    """Point parser paths at either the installed runtime or this repository checkout."""
    global ACTIVE_PARSER_DIR, PARSER_PSM_ECORE, PARSER_GUI_PATH, PARSER_METADATA_PATH

    ACTIVE_PARSER_DIR = REPOSITORY_PARSER_DIR if USE_REPOSITORY_PARSER else INSTALLED_PARSER_DIR
    PARSER_PSM_ECORE = ACTIVE_PARSER_DIR / "TransformationEngineNecessities" / "source" / "PSM.ecore"
    PARSER_GUI_PATH = ACTIVE_PARSER_DIR / "ParserNecessities" / "MisarParserGUI.py"
    PARSER_METADATA_PATH = ACTIVE_PARSER_DIR / "MiSAR.parser.release.json"


configure_parser_runtime_paths()


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

    module_names = [package_name for _, package_name in missing_modules]
    module_list = "\n".join(module_names)

    if len(missing_modules) == 1:
        message = (
            "The following Python package is currently not installed:\n\n"
            + module_list
            + "\n\nThis package is required for MiSAR.\nWould you like MiSAR to install it now?"
        )
    else:
        message = (
            "The following Python packages are currently not installed:\n\n"
            + module_list
            + "\n\nThese packages are required for MiSAR.\nWould you like MiSAR to install them now?"
        )

    install_modules = messagebox.askquestion("Missing Python Packages", message)
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


def read_version_json_file(file_path):
    """Read MISAR.versions.json from the launcher root, or return empty data if absent."""
    if not file_path.is_file():
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data if isinstance(data, dict) else {}
    except Exception as error:
        log_event("version_json_file_read_failed", path=file_path, error=str(error))
        return {}


def load_misar_versions():
    """Read MiSAR versions from MISAR.versions.json, or return empty data if absent."""
    version_keys = {key for keys in MODULE_VERSION_KEYS.values() for key in keys}
    version_keys.update(LAUNCHER_VERSION_KEYS)

    data = read_version_json_file(VERSION_FILE_PATH)
    versions = {key: str(value) for key, value in data.items() if key in version_keys and value}

    if versions:
        log_event("misar_versions_loaded", path=VERSION_FILE_PATH, versions=versions)
        return versions

    log_event("misar_versions_unavailable", path=VERSION_FILE_PATH)
    return {}


def read_config_json_file(file_path):
    """Read launcher user configuration from MISAR.configs.json."""
    if not file_path.is_file():
        log_event("config_json_file_missing", path=file_path)
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        return data if isinstance(data, dict) else {}
    except Exception as error:
        log_event("config_json_file_read_failed", path=file_path, error=str(error))
        return {}


def load_misar_configs():
    """Read user-selected launcher paths/settings from MISAR.configs.json."""
    configs = read_config_json_file(CONFIG_FILE_PATH)

    if configs:
        log_event("misar_configs_loaded", path=CONFIG_FILE_PATH, configs=configs)
        return configs

    log_event("misar_configs_unavailable", path=CONFIG_FILE_PATH)
    return {}


def write_misar_config(config_key, config_value):
    """Update one launcher config entry and persist it to MISAR.configs.json."""
    global MISAR_CONFIGS

    config_value = str(config_value).strip() if config_value is not None else ""
    config_data = read_config_json_file(CONFIG_FILE_PATH)
    if not config_data and MISAR_CONFIGS:
        config_data = dict(MISAR_CONFIGS)

    if config_value:
        config_data[config_key] = config_value
        MISAR_CONFIGS[config_key] = config_value
    else:
        config_data.pop(config_key, None)
        MISAR_CONFIGS.pop(config_key, None)

    write_json_file(CONFIG_FILE_PATH, config_data)
    log_event("misar_config_updated", path=CONFIG_FILE_PATH, key=config_key, value=config_value)
    return True


def get_misar_config_bool(config_key, default=False):
    """Read one boolean launcher config from MISAR.configs.json data."""
    return config_value_as_bool(MISAR_CONFIGS.get(config_key), default)


def is_auto_update_enabled():
    """Return True when startup parser update checks are enabled."""
    return get_misar_config_bool(AUTO_UPDATE_CONFIG_KEY, True)


def bool_to_config_value(value):
    """Serialise a boolean setting for MISAR.configs.json."""
    return "true" if bool(value) else "false"


def get_configured_version(version_keys):
    """Return a configured version for the supplied keys, or an empty string when unavailable."""
    for version_key in version_keys:
        version = MISAR_VERSIONS.get(version_key)

        if version:
            return str(version)

    return ""


def get_module_version(module_name):
    """Return a configured module version, or an empty string when unavailable."""
    return get_configured_version(MODULE_VERSION_KEYS.get(module_name, ()))


def get_launcher_version():
    """Return the configured launcher version, or an empty string when unavailable."""
    return get_configured_version(LAUNCHER_VERSION_KEYS)


def format_version_text(version):
    """Format a version value for display while allowing empty versions to stay hidden."""
    version = str(version).strip() if version else ""

    if not version:
        return ""

    return version if version.lower().startswith("v") else "v" + version


def write_misar_version(version_key, version):
    """Update one entry inside MISAR.versions.json and the in-memory version cache."""
    global MISAR_VERSIONS

    version = str(version).strip() if version else ""

    if not version:
        log_event("misar_version_update_skipped", key=version_key, reason="empty_version")
        return False

    version_data = read_version_json_file(VERSION_FILE_PATH)
    if not version_data and MISAR_VERSIONS:
        version_data = dict(MISAR_VERSIONS)
    previous_version = version_data.get(version_key)

    if previous_version == version and MISAR_VERSIONS.get(version_key) == version:
        log_event("misar_version_update_skipped", key=version_key, reason="already_current", version=version)
        return False

    version_data[version_key] = version
    write_json_file(VERSION_FILE_PATH, version_data)
    MISAR_VERSIONS[version_key] = version

    log_event(
        "misar_version_updated",
        path=VERSION_FILE_PATH,
        key=version_key,
        previous_version=previous_version,
        version=version,
    )
    return True


def sync_gmg_visualiser_version_from_asset(asset):
    """Persist the latest GMG release tag_name into MISAR.versions.json."""
    tag_name = str(asset.get("tag_name") or "").strip()

    if not tag_name:
        log_event("gmg_version_sync_skipped", reason="missing_tag_name", asset=asset)
        return False

    try:
        updated = write_misar_version(GMG_VERSION_KEY, tag_name)
        refresh_gmg_version_display()
        log_event("gmg_version_sync_completed", updated=updated, tag_name=tag_name)
        return updated
    except Exception as error:
        log_exception("gmg_version_sync_failed", error, tag_name=tag_name, path=VERSION_FILE_PATH)
        return False


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

def stream_process_output(process, process_name):
    """Stream a child process stdout/stderr into the debug logger without blocking Tkinter."""
    if process.stdout is None:
        return

    try:
        for line in process.stdout:
            line = line.rstrip()

            if line:
                LOGGER.debug("%s output | %s", process_name, line)

        return_code = process.wait()
        log_event("subprocess_completed", process_name=process_name, return_code=return_code)
    except Exception as error:
        log_exception("subprocess_output_stream_failed", error, process_name=process_name)


def launch_logged_subprocess(command, process_name, cwd=None):
    """Launch a child process without closing or blocking the MiSAR AIO window."""
    log_event("subprocess_launch_started", process_name=process_name, command=command, cwd=cwd)

    if not DEBUG_MODE:
        process = subprocess.Popen(command, cwd=cwd)
        log_event("subprocess_launch_completed", process_name=process_name, pid=process.pid)
        return process

    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["MISAR_AIO_DEBUG"] = "1"

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_thread = threading.Thread(
        target=stream_process_output,
        args=(process, process_name),
        daemon=True,
    )
    output_thread.start()

    log_event("subprocess_launch_completed", process_name=process_name, pid=process.pid)
    return process


def run_on_ui_thread(callback, *args, **kwargs):
    """Schedule a callback on the Tkinter UI thread when the main window exists."""
    if main_window is not None and hasattr(main_window, "after"):
        main_window.after(0, lambda: callback(*args, **kwargs))
    else:
        callback(*args, **kwargs)


def show_info_on_ui_thread(title, message):
    run_on_ui_thread(messagebox.showinfo, title, message)


def show_error_on_ui_thread(title, message):
    run_on_ui_thread(messagebox.showerror, title, message)


def ask_question_on_ui_thread(title, message, default="no"):
    """Ask a Tkinter question from worker code and wait for the UI-thread response."""
    if main_window is None or not hasattr(main_window, "after"):
        return messagebox.askquestion(title, message)

    response_holder = {"response": default}
    completed = threading.Event()

    def ask():
        try:
            response_holder["response"] = messagebox.askquestion(title, message)
        finally:
            completed.set()

    main_window.after(0, ask)
    completed.wait()
    return response_holder["response"]


def ask_yesno_on_ui_thread(title, message, default=False):
    """Ask a Tkinter yes/no question from worker code and wait for the UI-thread response."""
    if main_window is None or not hasattr(main_window, "after"):
        return messagebox.askyesno(title, message)

    response_holder = {"response": default}
    completed = threading.Event()

    def ask():
        try:
            response_holder["response"] = messagebox.askyesno(title, message)
        finally:
            completed.set()

    main_window.after(0, ask)
    completed.wait()
    return response_holder["response"]

# ===============================
# INSTALLERS
# ===============================


def install_parser():
    """Install the MiSAR parser and persist repository metadata when available."""
    if USE_REPOSITORY_PARSER:
        log_event("parser_install_skipped", reason="use_repository_parser", path=ACTIVE_PARSER_DIR)
        return is_parser_installed()

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
            if repository_metadata is not None and parser_path == INSTALLED_PARSER_DIR:
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
            sync_gmg_visualiser_version_from_asset(asset)
            log_event("gmg_jar_already_current", jar_path=GMG_JAR_PATH)
            return True

        download_gmg_jar(asset)
        write_gmg_metadata(asset)
        sync_gmg_visualiser_version_from_asset(asset)

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
                "tag_name": release_data.get("tag_name"),
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
    updated_at = repository_data.get("updated_at")
    # NOTE: pushed_at counts pushes in all branches, whereas updated_at only detects the main branch which we're looking to get

    if updated_at is None:
        raise RuntimeError("Could not read parser repository update time from GitHub.")

    metadata = {
        "updated_at": updated_at,
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
    update_available = local_metadata.get("updated_at") != repository_metadata.get("updated_at")

    log_event(
        "parser_update_comparison_completed",
        update_available=update_available,
        local_updated_at=local_metadata.get("updated_at"),
        remote_updated_at=repository_metadata.get("updated_at"),
    )
    return update_available


def install_parser_update_from_metadata(repository_metadata):
    """Install an available parser update using repository metadata already fetched."""
    update_available = ask_question_on_ui_thread(
        "Parser Update Available",
        "An update is available for the MiSAR Parser and Transformation Engine.\n"
        "Would you like to install it now?",
    )
    log_event("parser_update_prompt_response", response=update_available)

    if update_available != "yes":
        return False

    if not check_required_modules():
        return False

    if INSTALLED_PARSER_DIR.exists():
        uninstall_path(Path("MiSAR") / "Parser")

    if clone_parser_repository(Path("MiSAR") / "Parser", repository_metadata):
        show_info_on_ui_thread("Success!", "The parser update completed successfully.")
        run_on_ui_thread(refresh_launch_buttons)
        return True

    show_error_on_ui_thread("Failure!", "The parser update has failed.")
    return False


def automatic_update_check():
    """Check for parser updates after the UI starts, without interrupting offline users."""
    log_event("automatic_update_check_started")

    if not is_auto_update_enabled():
        log_event("automatic_update_check_skipped", reason="auto_update_disabled")
        return

    if USE_REPOSITORY_PARSER:
        log_event("automatic_update_check_skipped", reason="use_repository_parser", path=ACTIVE_PARSER_DIR)
        return

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

        install_parser_update_from_metadata(repository_metadata)
    except Exception as error:
        log_exception("automatic_update_check_failed", error)
        show_error_on_ui_thread(
            "Update Check Failed",
            "MiSAR could not check for parser updates.\n\nError code:\n" + str(error),
        )


def manual_update_check():
    """Run the parser update check when the user explicitly asks for it."""
    log_event("manual_update_check_started")

    if USE_REPOSITORY_PARSER:
        show_info_on_ui_thread(
            "Repository Runtime Active",
            "MiSAR is currently using the repository parser runtime.\n\n"
            "Automatic parser updates are skipped in this mode.",
        )
        log_event("manual_update_check_skipped", reason="use_repository_parser", path=ACTIVE_PARSER_DIR)
        return False

    if not check_internet():
        show_error_on_ui_thread(
            "No Internet Connection",
            "An internet connection is required to check for MiSAR updates.",
        )
        log_event("manual_update_check_skipped", reason="no_internet")
        return False

    if not is_parser_installed():
        show_info_on_ui_thread(
            "Parser Not Installed",
            "The MiSAR Parser is not installed yet. Please use the Install button on the MiSAR Parser card first.",
        )
        log_event("manual_update_check_skipped", reason="parser_not_installed")
        return False

    try:
        repository_metadata = get_parser_repository_metadata()

        if not is_parser_update_available(repository_metadata):
            show_info_on_ui_thread("MiSAR Updates", "You are up to date.")
            log_event("manual_update_check_completed", update_available=False)
            return False

        log_event("manual_update_check_completed", update_available=True)
        return install_parser_update_from_metadata(repository_metadata)
    except Exception as error:
        log_exception("manual_update_check_failed", error)
        show_error_on_ui_thread(
            "Update Check Failed",
            "MiSAR could not check for updates.\n\nError code:\n" + str(error),
        )
        return False


def run_update_check_in_background(manual=False):
    """Run update checks in a worker thread so Tkinter does not freeze."""
    set_status("Checking MiSAR updates..." if manual else "Checking parser updates...")
    target = manual_update_check if manual else automatic_update_check

    def worker():
        try:
            target()
        finally:
            run_on_ui_thread(set_status, "Ready")

    update_thread = threading.Thread(target=worker, daemon=True)
    update_thread.start()
    log_event("update_check_background_started", manual=manual, thread_name=update_thread.name)
    return update_thread


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
    if USE_REPOSITORY_PARSER:
        messagebox.showinfo(
            "Repository Parser Active",
            "The --use-repository-parser flag is active, so MiSAR is using the parser files from:\n\n"
            + str(REPOSITORY_PARSER_DIR)
            + "\n\nRepository files are not removed from the launcher.",
        )
        log_event("parser_uninstall_skipped", reason="use_repository_parser", path=REPOSITORY_PARSER_DIR)
        return

    if not is_parser_installed():
        refresh_launch_buttons()
        return

    uninstall_choice = messagebox.askquestion(
        "Uninstall MiSAR Parser",
        "This will remove the installed MiSAR Parser from:\n\n"
        + str(INSTALLED_PARSER_DIR)
        + "\n\nDo you want to continue?",
    )
    log_event("parser_uninstall_prompt_response", response=uninstall_choice, path=INSTALLED_PARSER_DIR)

    if uninstall_choice != "yes":
        return

    try:
        uninstall_path(Path("MiSAR") / "Parser")
        messagebox.showinfo("Success!", "The MiSAR Parser has been uninstalled.")
        refresh_launch_buttons()
    except Exception as error:
        log_exception("parser_uninstall_failed", error, path=INSTALLED_PARSER_DIR)
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

import tkinter.font as tkfont
from tkinter import ttk

PALETTE = {
    "bg": "#eef2f7",
    "sidebar": "#101c36",
    "sidebar_text": "#b8c2d6",
    "sidebar_title": "#ffffff",
    "panel": "#ffffff",
    "panel_soft": "#f8fafc",
    "border": "#dbe3ef",
    "border_strong": "#cbd5e1",
    "title": "#162037",
    "text": "#334155",
    "muted": "#111827",
    "input": "#f8fafc",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_pressed": "#1e40af",
    "secondary": "#eef2f7",
    "secondary_hover": "#e2e8f0",
    "secondary_text": "#1e293b",
    "success": "#16a34a",
    "success_hover": "#15803d",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "disabled": "#d9e1ec",
    "disabled_text": "#7b8797",
    "status_bg": "#eef2f8",
}

CARD_RADIUS = 10
CARD_SHADOW_OFFSET = 5
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 850
WINDOW_MIN_HEIGHT = 650
WINDOW_VERTICAL_MARGIN = 72

# Windows VM/display scaling can make the Tkinter UI look about 1.5x larger
# than macOS. Keep macOS/Linux unchanged by default, but allow users to override
# the launcher density from Display Settings. The setting is persisted in
# MISAR.configs.json so more UI options can be added later.
WINDOWS_COMPACT_DENSITY = sys.platform.startswith("win")
DEFAULT_UI_DENSITY = 0.88 if WINDOWS_COMPACT_DENSITY else 1.0
UI_DENSITY = DEFAULT_UI_DENSITY
WINDOW_SIZE_CONFIG_KEY = "ui.window_size"
LEGACY_UI_DENSITY_CONFIG_KEY = "ui.density"
UI_DENSITY_CONFIG_KEY = WINDOW_SIZE_CONFIG_KEY
UI_DENSITY_OPTIONS = {
    "auto": ("Auto", None),
    "compact": ("Small", 0.88),
    "normal": ("Default", 1.0),
    "comfortable": ("Large", 1.08),
    "large": ("Extra large", 1.18),
}


def normalise_ui_density_choice(choice):
    """Return a supported UI density choice key."""
    choice = str(choice or "auto").strip().lower()
    return choice if choice in UI_DENSITY_OPTIONS else "auto"


def get_ui_density_choice():
    """Return the configured window size choice from MISAR.configs.json."""
    return normalise_ui_density_choice(
        MISAR_CONFIGS.get(WINDOW_SIZE_CONFIG_KEY, MISAR_CONFIGS.get(LEGACY_UI_DENSITY_CONFIG_KEY, "auto"))
    )


def resolve_ui_density(choice=None):
    """Resolve the configured UI density choice to a numeric multiplier."""
    choice = normalise_ui_density_choice(choice if choice is not None else get_ui_density_choice())
    _label, configured_density = UI_DENSITY_OPTIONS[choice]
    return DEFAULT_UI_DENSITY if configured_density is None else configured_density


def apply_configured_ui_density():
    """Refresh the in-memory UI density from MISAR.configs.json."""
    global UI_DENSITY
    UI_DENSITY = resolve_ui_density()
    log_event("ui_density_configured", choice=get_ui_density_choice(), density=UI_DENSITY)
    return UI_DENSITY


def ui_density_display_text(choice=None):
    """Return a user-facing label for a UI density choice."""
    choice = normalise_ui_density_choice(choice if choice is not None else get_ui_density_choice())
    label, _density = UI_DENSITY_OPTIONS[choice]
    return label


def ui_size(value, minimum=1):
    """Scale layout values for platform-specific UI density."""
    return max(int(round(value * UI_DENSITY)), minimum)


def ui_pad(values):
    """Scale Tkinter padding tuples/lists while preserving tuple shape."""
    if isinstance(values, tuple):
        return tuple(ui_pad(value) for value in values)
    if isinstance(values, list):
        return [ui_pad(value) for value in values]
    if isinstance(values, int):
        return ui_size(values, 0)
    return values


def ui_font(size=11, weight="normal"):
    try:
        family = tkfont.nametofont("TkDefaultFont").cget("family")
    except Exception:
        family = "Helvetica"
    scaled_size = ui_size(size, 8)
    return (family, scaled_size, weight) if weight != "normal" else (family, scaled_size)


def calculate_image_subsample_factor(width, height, max_width=None, max_height=None):
    """Return an integer PhotoImage subsample factor for the requested bounds."""
    factor = 1

    if max_width and width > max_width:
        factor = max(factor, (width + max_width - 1) // max_width)

    if max_height and height > max_height:
        factor = max(factor, (height + max_height - 1) // max_height)

    return max(int(factor), 1)


def load_ui_image(root, image_key, image_path, max_width=None, max_height=None):
    """Load and retain a Tkinter PhotoImage, returning None if the asset is absent."""
    image_path = Path(image_path)

    if not image_path.is_file():
        log_event("ui_image_missing", key=image_key, path=image_path)
        return None

    try:
        image = tkinter.PhotoImage(file=str(image_path))
        factor = calculate_image_subsample_factor(
            image.width(),
            image.height(),
            max_width=max_width,
            max_height=max_height,
        )

        if factor > 1:
            image = image.subsample(factor, factor)

        if not hasattr(root, "misar_ui_images"):
            root.misar_ui_images = {}

        root.misar_ui_images[image_key] = image
        log_event("ui_image_loaded", key=image_key, path=image_path, width=image.width(), height=image.height())
        return image
    except Exception as error:
        log_event("ui_image_load_failed", key=image_key, path=image_path, error=str(error))
        return None


def set_window_icon(root):
    """Use the MiSAR logo as the Tkinter window icon when the PNG asset is available."""
    icon_image = load_ui_image(root, "window_icon", MISAR_LOGO_PATH, max_width=64, max_height=64)

    if icon_image is None:
        return False

    try:
        root.iconphoto(True, icon_image)
        log_event("window_icon_set", path=MISAR_LOGO_PATH)
        return True
    except Exception as error:
        log_event("window_icon_set_failed", path=MISAR_LOGO_PATH, error=str(error))
        return False


def add_sidebar_logo(sidebar, root, image_key, image_path, fallback_text, max_width, max_height, pady):
    """Add one sidebar logo with a text fallback."""
    image = load_ui_image(root, image_key, image_path, max_width=max_width, max_height=max_height)

    if image is not None:
        tkinter.Label(sidebar, image=image, bg=PALETTE["sidebar"]).pack(pady=pady)
        return True

    tkinter.Label(
        sidebar,
        text=fallback_text,
        font=ui_font(11, "bold"),
        bg=PALETTE["sidebar"],
        fg=PALETTE["sidebar_title"],
        wraplength=ui_size(76),
        justify="center",
    ).pack(pady=pady)
    return False


class RoundedButton(tkinter.Canvas):
    def __init__(self, master, text, command=None, variant="primary", width=132):
        super().__init__(master, width=ui_size(width), height=ui_size(42), highlightthickness=0, bd=0, cursor="hand2")
        self.text = text
        self.command = command
        self.variant = variant
        self.enabled = True
        self.hovered = False
        self.pressed = False
        self.button_font = ui_font(11, "bold")
        super().configure(bg=PALETTE["panel"])
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self._draw()

    def configure(self, cnf=None, **kwargs):
        options = {}
        if cnf:
            options.update(cnf)
        options.update(kwargs)

        if "text" in options:
            self.text = options.pop("text")
        if "command" in options:
            self.command = options.pop("command")
        if "variant" in options:
            self.variant = options.pop("variant")
        if "state" in options:
            state = str(options.pop("state"))
            self.set_enabled(state not in {"disabled", str(tkinter.DISABLED)})
        if "font" in options:
            self.button_font = options.pop("font")
        if options:
            super().configure(**options)
        self._draw()

    def config(self, cnf=None, **kwargs):
        self.configure(cnf, **kwargs)

    def set_enabled(self, enabled):
        self.enabled = enabled
        super().configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def invoke(self):
        if self.enabled and self.command is not None:
            self.command()

    def _colours(self):
        if not self.enabled:
            return PALETTE["disabled"], PALETTE["disabled_text"], PALETTE["disabled"]
        if self.variant == "secondary":
            bg = PALETTE["secondary_hover"] if self.hovered else PALETTE["secondary"]
            return bg, PALETTE["secondary_text"], PALETTE["border_strong"]
        if self.variant == "danger":
            bg = PALETTE["danger_hover"] if self.hovered else PALETTE["danger"]
            return bg, "#ffffff", bg
        if self.variant == "success":
            bg = PALETTE["success_hover"] if self.hovered else PALETTE["success"]
            return bg, "#ffffff", bg
        bg = PALETTE["accent_hover"] if self.hovered else PALETTE["accent"]
        if self.pressed:
            bg = PALETTE["accent_pressed"]
        return bg, "#ffffff", bg

    def _draw(self):
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        bg, fg, outline = self._colours()
        if self.enabled:
            self._rounded_rect(2, 4, width - 2, height - 1, 12, fill="#dfe6f1", outline="")
        self._rounded_rect(1, 1, width - 3, height - 4, 12, fill=bg, outline=outline)
        self.create_text((width - 2) / 2, (height - 3) / 2, text=self.text, fill=fg, font=self.button_font)

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, splinesteps=18, **kwargs)

    def _on_enter(self, _event):
        self.hovered = True
        self._draw()

    def _on_leave(self, _event):
        self.hovered = False
        self.pressed = False
        self._draw()

    def _on_press(self, _event):
        if self.enabled:
            self.pressed = True
            self._draw()

    def _on_release(self, _event):
        was_pressed = self.pressed
        self.pressed = False
        self._draw()
        if was_pressed:
            self.invoke()


class BoxFrame(tkinter.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=PALETTE["bg"], **kwargs)
        self.canvas = tkinter.Canvas(self, highlightthickness=0, bd=0, bg=PALETTE["bg"])
        self.canvas.pack(fill="both", expand=True)
        self.content = tkinter.Frame(self.canvas, bg=PALETTE["panel"], padx=ui_size(18), pady=ui_size(14))
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def grid_columnconfigure(self, index, cnf=None, **kw):
        return self.content.grid_columnconfigure(index, {} if cnf is None else cnf, **kw)

    def grid_rowconfigure(self, index, cnf=None, **kw):
        return self.content.grid_rowconfigure(index, {} if cnf is None else cnf, **kw)

    def _on_content_configure(self, event):
        height = event.height + CARD_SHADOW_OFFSET + 4
        if self.canvas.winfo_height() != height:
            self.canvas.configure(height=height)
        self._draw()

    def _on_canvas_configure(self, event):
        width = max(event.width - CARD_SHADOW_OFFSET - 2, 120)
        self.canvas.itemconfigure(self.window_id, width=width)
        self._draw()

    def _draw(self):
        self.canvas.delete("card")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight() + CARD_SHADOW_OFFSET + 4)
        panel_width = max(width - CARD_SHADOW_OFFSET - 1, 1)
        panel_height = max(height - CARD_SHADOW_OFFSET - 1, 1)
        self._rounded_rect(3, 4, panel_width + 3, panel_height + 4, CARD_RADIUS, fill="#e8edf5", outline="", tags="card")
        self._rounded_rect(1, 2, panel_width + 1, panel_height + 2, CARD_RADIUS, fill="#f1f4f9", outline="", tags="card")
        self._rounded_rect(0, 0, panel_width, panel_height, CARD_RADIUS, fill=PALETTE["panel"], outline=PALETTE["border"], tags="card")
        self.canvas.tag_lower("card")

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.canvas.create_polygon(points, smooth=True, splinesteps=20, **kwargs)


class ProgramOfChoice:
    def __init__(self, name, version, input_row, input_column, target_window, supports_uninstall=False):
        self.name = name
        self.version = str(version).strip() if version else ""
        self.input_row = input_row
        self.input_column = input_column
        self.uninstall_button = None

        parent = getattr(target_window, "modules_frame", target_window)
        self.container = BoxFrame(parent)
        self.container.grid(row=input_row, column=input_column, sticky="ew", pady=ui_pad((0, 10)))
        self.container.content.grid_columnconfigure(1, weight=1)

        details = module_details(name)
        self.icon = tkinter.Label(
            self.container.content,
            text=details["icon"],
            width=ui_size(3),
            height=ui_size(2),
            font=ui_font(20, "bold"),
            bg=PALETTE["panel_soft"],
            fg=PALETTE["accent"],
            relief="flat",
        )
        self.title_frame = tkinter.Frame(self.container.content, bg=PALETTE["panel"])
        self.module_name = ttk.Label(self.title_frame, text=name, style="CardTitle.TLabel")
        self.module_name.pack(side=tkinter.LEFT)
        self.module_version = None

        if self.version:
            version_text = format_version_text(self.version)
            self.module_version = tkinter.Label(
                self.title_frame,
                text=version_text,
                font=ui_font(10, "bold"),
                bg=PALETTE["secondary"],
                fg=PALETTE["muted"],
                padx=ui_size(7),
                pady=ui_size(2),
            )
            self.module_version.pack(side=tkinter.LEFT, padx=(10, 0))

        self.module_description = ttk.Label(
            self.container.content,
            text=details["description"],
            style="MutedCard.TLabel",
            wraplength=620,
        )
        self.status_badge = tkinter.Label(
            self.container.content,
            text="Checking",
            font=ui_font(11, "bold"),
            bg=PALETTE["secondary"],
            fg=PALETTE["muted"],
            padx=ui_size(10),
            pady=ui_size(5),
        )

        self.button_frame = tkinter.Frame(self.container.content, bg=PALETTE["panel"])
        self.launch_button = RoundedButton(self.button_frame, "Install", command=lambda button=self: handle_module_button(button), width=118)

        if supports_uninstall:
            self.launch_button.pack(side=tkinter.LEFT, padx=ui_pad((0, 8)))
        else:
            self.launch_button.pack(side=tkinter.RIGHT)

        if supports_uninstall:
            self.uninstall_button = RoundedButton(
                self.button_frame,
                "Uninstall",
                command=lambda button=self: handle_uninstall_button(button),
                variant="secondary",
                width=118,
            )
            self.uninstall_button.pack(side=tkinter.LEFT)
            self.uninstall_button.configure(state=tkinter.DISABLED)

        self.icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=ui_pad((0, 14)))
        self.title_frame.grid(row=0, column=1, sticky="w")
        self.module_description.grid(row=1, column=1, sticky="ew", pady=ui_pad((4, 0)))
        self.status_badge.grid(row=0, column=2, sticky="e", padx=ui_pad((14, 0)))
        self.button_frame.grid(row=1, column=2, sticky="e", padx=ui_pad((14, 0)), pady=ui_pad((6, 0)))

        if name == "Need help or more information about this program?":
            self.status_badge.grid_remove()
            self.launch_button.configure(text="Help", variant="primary")

        log_event(
            "program_button_created",
            name=name,
            version=version,
            row=input_row,
            column=input_column,
            supports_uninstall=supports_uninstall,
        )

    def set_installed_state(self, installed):
        label = "Installed" if installed else "Not installed"
        bg = "#dcfce7" if installed else PALETTE["secondary"]
        fg = PALETTE["success"] if installed else PALETTE["muted"]
        self.status_badge.configure(text=label, bg=bg, fg=fg)


def module_details(name):
    details = {
        "MiSAR Parser": {
            "icon": "P",
            "description": "Install or open the parser used to recover MiSAR PSM models from microservice artefacts.",
        },
        "MiSAR Transformation Engine": {
            "icon": "E",
            "description": "Open Eclipse to import and run the Transformation Engine Necessities project.",
        },
        "MiSAR Graphical Model Generator": {
            "icon": "G",
            "description": "Install, update or open the graphical model generator JAR for visualising recovered models.",
        },
        "Need help or more information about this program?": {
            "icon": "?",
            "description": "Open the MiSAR help message and online documentation in your browser.",
        },
    }
    return details.get(name, {"icon": "M", "description": "Select this MiSAR module to continue."})


def set_status(message):
    if main_window is not None and hasattr(main_window, "status_label"):
        main_window.status_label.configure(text=message)


def set_busy_status(message=None, active=True):
    """Show or hide a small indeterminate status loader in the launcher footer."""
    if message:
        set_status(message)

    if main_window is None or not hasattr(main_window, "status_progress"):
        return

    if active:
        if not getattr(main_window, "status_progress_visible", False):
            main_window.status_progress.pack(side="left", padx=ui_pad((10, 0)))
            main_window.status_progress_visible = True
        main_window.status_progress.start(12)
    else:
        main_window.status_progress.stop()
        if getattr(main_window, "status_progress_visible", False):
            main_window.status_progress.pack_forget()
            main_window.status_progress_visible = False


def refresh_ui_now():
    """Flush pending Tk updates so progress/status text is visible before long work."""
    if main_window is not None:
        try:
            main_window.update_idletasks()
        except tkinter.TclError:
            pass


def set_module_actions_enabled(enabled):
    """Enable/disable module action buttons while install/update work is running."""
    for module in (the_parser, the_transformation_engine, the_graphical_model_generator, the_help_button):
        if module is None:
            continue
        if getattr(module, "launch_button", None) is not None:
            module.launch_button.configure(state=tkinter.NORMAL if enabled else tkinter.DISABLED)
        if getattr(module, "uninstall_button", None) is not None:
            module.uninstall_button.configure(state=tkinter.NORMAL if enabled else tkinter.DISABLED)


def set_module_button_state(module, installed):
    module.launch_button.configure(text="Launch" if installed else "Install")
    if hasattr(module, "set_installed_state"):
        module.set_installed_state(installed)
    if module.uninstall_button is not None:
        module.uninstall_button.configure(state=tkinter.NORMAL if installed else tkinter.DISABLED)


def set_module_version_badge(module, version):
    """Refresh a module version badge after a runtime version sync."""
    if module is None:
        return

    version_text = format_version_text(version)
    module.version = str(version).strip() if version else ""

    if not version_text:
        return

    if getattr(module, "module_version", None) is not None:
        module.module_version.configure(text=version_text)
        return

    if hasattr(module, "title_frame"):
        module.module_version = tkinter.Label(
            module.title_frame,
            text=version_text,
            font=ui_font(10, "bold"),
            bg=PALETTE["secondary"],
            fg=PALETTE["muted"],
            padx=ui_size(7),
            pady=ui_size(2),
        )
        module.module_version.pack(side=tkinter.LEFT, padx=(10, 0))


def refresh_gmg_version_display():
    """Refresh the visible GMG version badge when the latest release tag is persisted."""
    set_module_version_badge(
        the_graphical_model_generator,
        get_module_version("MiSAR Graphical Model Generator"),
    )




def set_transformation_engine_button_state():
    """Update the Transformation Engine card state based only on Eclipse availability."""
    if the_transformation_engine is None:
        return

    eclipse_executable = find_eclipse_executable()

    if eclipse_executable is not None:
        the_transformation_engine.launch_button.configure(text="Open Eclipse", state=tkinter.NORMAL)
        the_transformation_engine.status_badge.configure(
            text="Eclipse ready",
            bg="#dcfce7",
            fg=PALETTE["success"],
        )
    else:
        the_transformation_engine.launch_button.configure(text="Choose Eclipse", state=tkinter.NORMAL)
        the_transformation_engine.status_badge.configure(
            text="Eclipse missing",
            bg=PALETTE["secondary"],
            fg=PALETTE["muted"],
        )


def parser_psm_path_display():
    if PARSER_SELECTED_PSM_PATH is None:
        return str(PARSER_PSM_ECORE)
    return str(PARSER_SELECTED_PSM_PATH)


def set_entry_value(entry, value):
    entry.configure(state="normal")
    entry.delete(0, tkinter.END)
    entry.insert(0, value)
    entry.configure(state="readonly")


def update_psm_path_entry():
    if main_window is None or not hasattr(main_window, "debug_psm_entry"):
        return
    set_entry_value(main_window.debug_psm_entry, parser_psm_path_display())


def update_debug_ui():
    if main_window is None:
        return

    if hasattr(main_window, "debug_status_label"):
        main_window.debug_status_label.configure(
            text="Debug mode: Active" if DEBUG_MODE else "Debug mode: Inactive",
            bg="#dcfce7" if DEBUG_MODE else PALETTE["secondary"],
            fg=PALETTE["success"] if DEBUG_MODE else PALETTE["muted"],
        )

    if hasattr(main_window, "debug_toggle_button"):
        main_window.debug_toggle_button.configure(text="Deactivate Debug" if DEBUG_MODE else "Activate Debug")

    if hasattr(main_window, "debug_panel"):
        if DEBUG_MODE:
            main_window.debug_panel.grid()
        else:
            main_window.debug_panel.grid_remove()

    update_psm_path_entry()

    if hasattr(main_window, "after"):
        main_window.after(40, lambda: resize_window_to_visible_content(main_window, keep_position=True))


def toggle_debug_mode():
    global DEBUG_MODE

    if not DEBUG_MODE:
        accepted = messagebox.askyesno(
            "Enable Debug Mode",
            "Debug mode writes diagnostic logs to a local logs folder on this computer.\n\n"
            "It does not send anything to MiSAR, Brunel University London, GitHub, or anyone else automatically.\n\n"
            "Enable debug mode for this session?",
        )
        if not accepted:
            return
        DEBUG_MODE = True
        setup_logger()
        log_event("debug_mode_enabled_from_ui", log_file=LOG_FILE_PATH)
        set_status("Debug mode enabled.")
    else:
        log_event("debug_mode_disabled_from_ui")
        DEBUG_MODE = False
        setup_logger()
        set_status("Debug mode disabled.")

    update_debug_ui()


def browse_parser_psm_path():
    global PARSER_SELECTED_PSM_PATH

    initial_dir = PARSER_PSM_ECORE.parent if PARSER_PSM_ECORE.parent.exists() else USER_HOME_DIR
    selected_file = filedialog.askopenfilename(
        title="Select parser PSM Ecore file",
        initialdir=str(initial_dir),
        filetypes=(
            ("Ecore files", "*.ecore"),
            ("All files", "*.*"),
        ),
    )
    if not selected_file:
        return

    selected_path = Path(selected_file).expanduser()
    if not selected_path.is_file():
        messagebox.showerror("Invalid PSM Path", "Please select an existing PSM Ecore file.")
        return

    PARSER_SELECTED_PSM_PATH = selected_path
    update_psm_path_entry()
    set_status("Parser PSM path selected.")
    log_event("parser_psm_path_selected", psm_path=selected_path)


def reset_parser_psm_path():
    global PARSER_SELECTED_PSM_PATH
    PARSER_SELECTED_PSM_PATH = None
    update_psm_path_entry()
    set_status("Parser PSM path reset to the installed default.")
    log_event("parser_psm_path_reset", psm_path=PARSER_PSM_ECORE)



def restart_launcher():
    """Restart the launcher so display-density changes are applied consistently."""
    log_event("launcher_restart_requested")

    try:
        if main_window is not None:
            main_window.destroy()

        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as error:
        log_exception("launcher_restart_failed", error)
        messagebox.showinfo(
            "Restart MiSAR",
            "Display settings were saved. Please close and reopen MiSAR to apply them fully.",
        )


def open_launcher_settings():
    """Open launcher options for display and update preferences."""
    if main_window is None:
        return

    settings_window = tkinter.Toplevel(main_window)
    settings_window.title("MiSAR Options")
    settings_window.transient(main_window)
    settings_window.resizable(False, False)
    settings_window.configure(bg=PALETTE["panel"])
    settings_window.grab_set()

    tkinter.Label(
        settings_window,
        text="MiSAR Options",
        font=ui_font(14, "bold"),
        bg=PALETTE["panel"],
        fg=PALETTE["title"],
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 4))

    tkinter.Label(
        settings_window,
        text="Configure display and update options. These settings are saved locally.",
        font=ui_font(11),
        bg=PALETTE["panel"],
        fg=PALETTE["muted"],
        wraplength=420,
        justify="left",
    ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 14))

    tkinter.Label(
        settings_window,
        text="Window size",
        font=ui_font(11, "bold"),
        bg=PALETTE["panel"],
        fg=PALETTE["text"],
    ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 10))

    label_to_key = {label: key for key, (label, _density) in UI_DENSITY_OPTIONS.items()}
    current_label = ui_density_display_text()
    density_var = tkinter.StringVar(value=current_label)
    density_selector = ttk.Combobox(
        settings_window,
        textvariable=density_var,
        values=[label for label, _density in UI_DENSITY_OPTIONS.values()],
        state="readonly",
        width=22,
    )
    density_selector.grid(row=2, column=1, sticky="ew", padx=18, pady=(0, 10))

    tkinter.Label(
        settings_window,
        text=(
            "Auto chooses a suitable size for the current screen. "
        ),
        font=ui_font(10),
        bg=PALETTE["panel"],
        fg=PALETTE["muted"],
        wraplength=420,
        justify="left",
    ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

    auto_update_var = tkinter.BooleanVar(value=is_auto_update_enabled())
    auto_update_check = tkinter.Checkbutton(
        settings_window,
        text="Automatically check parser updates on startup",
        variable=auto_update_var,
        bg=PALETTE["panel"],
        fg=PALETTE["text"],
        activebackground=PALETTE["panel"],
        font=ui_font(11),
    )
    auto_update_check.grid(row=4, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 10))

    update_button_frame = tkinter.Frame(settings_window, bg=PALETTE["panel"])
    update_button_frame.grid(row=5, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))
    check_updates_button = RoundedButton(
        update_button_frame,
        "Check Updates",
        command=lambda: run_update_check_in_background(manual=True),
        variant="secondary",
        width=128,
    )
    check_updates_button.pack(side=tkinter.LEFT)

    button_frame = tkinter.Frame(settings_window, bg=PALETTE["panel"])
    button_frame.grid(row=6, column=0, columnspan=2, sticky="e", padx=18, pady=(0, 16))

    def save_launcher_settings():
        selected_key = label_to_key.get(density_var.get(), "auto")
        old_density_choice = get_ui_density_choice()

        write_misar_config(WINDOW_SIZE_CONFIG_KEY, selected_key)
        # Repository-runtime mode is only intended for development/PR testing.
        # Keep --use-repository-parser and MISAR.configs.json support, but do
        # not expose this developer switch in the normal Options UI.
        write_misar_config(AUTO_UPDATE_CONFIG_KEY, bool_to_config_value(auto_update_var.get()))
        apply_configured_ui_density()

        restart_required = selected_key != old_density_choice

        log_event(
            "launcher_settings_saved",
            ui_density_choice=selected_key,
            density=UI_DENSITY,
            auto_update_enabled=auto_update_var.get(),
            restart_required=restart_required,
        )
        settings_window.destroy()

        if restart_required:
            restart_now = messagebox.askyesno(
                "Apply MiSAR Options",
                "Settings were saved. Restart MiSAR now to apply the runtime/layout changes cleanly?",
            )

            if restart_now:
                restart_launcher()
            else:
                set_status("Settings saved. Restart MiSAR to apply all changes.")
            return

        set_status("Settings saved.")

    save_button = RoundedButton(button_frame, "Apply", command=save_launcher_settings, width=96)
    save_button.pack(side=tkinter.RIGHT, padx=(8, 0))

    cancel_button = RoundedButton(button_frame, "Cancel", command=settings_window.destroy, variant="secondary", width=96)
    cancel_button.pack(side=tkinter.RIGHT)

    settings_window.update_idletasks()
    x = main_window.winfo_x() + max((main_window.winfo_width() - settings_window.winfo_reqwidth()) // 2, 0)
    y = main_window.winfo_y() + max((main_window.winfo_height() - settings_window.winfo_reqheight()) // 2, 0)
    settings_window.geometry(f"+{x}+{y}")



def resolve_eclipse_executable(path):
    """Resolve an Eclipse file, folder or macOS .app bundle to the executable file."""
    if not path:
        return None

    candidate = Path(path).expanduser()

    if candidate.is_file():
        file_name = candidate.name.lower()
        if file_name in {"eclipse", "eclipse.exe"} or "eclipse" in file_name:
            return candidate
        return None

    if candidate.is_dir():
        possible_executables = []

        if candidate.suffix == ".app":
            possible_executables.extend(
                [
                    candidate / "Contents" / "Eclipse" / "eclipse",
                    candidate / "Contents" / "MacOS" / "eclipse",
                ]
            )

        possible_executables.extend(
            [
                candidate / "Eclipse.app" / "Contents" / "Eclipse" / "eclipse",
                candidate / "Eclipse.app" / "Contents" / "MacOS" / "eclipse",
                candidate / "eclipse",
                candidate / "eclipse.exe",
            ]
        )

        for executable in possible_executables:
            if executable.is_file():
                return executable

    return None


def get_eclipse_configured_path():
    """Return the raw Eclipse path saved in MISAR.configs.json, if available."""
    eclipse_path = str(MISAR_CONFIGS.get("eclipse.executable", "")).strip()
    return Path(eclipse_path).expanduser() if eclipse_path else None


def get_configured_eclipse_executable():
    """Return a saved Eclipse path resolved to its executable when valid."""
    configured_path = get_eclipse_configured_path()

    if configured_path is None:
        return None

    executable = resolve_eclipse_executable(configured_path)

    if executable is not None:
        return executable

    log_event("configured_eclipse_missing", path=configured_path)
    return None


def is_valid_eclipse_executable(path):
    """Return True for Eclipse executable files, install folders, or macOS .app bundles."""
    return resolve_eclipse_executable(path) is not None


def select_eclipse_executable():
    """Let the user manually select Eclipse and persist the selected path."""
    initial_dir = USER_HOME_DIR
    configured_path = get_eclipse_configured_path()

    if configured_path is not None:
        initial_dir = configured_path.parent if configured_path.is_file() else configured_path

    if sys.platform == "darwin":
        selected_file = filedialog.askdirectory(
            title="Select Eclipse.app or Eclipse installation folder",
            initialdir=str(initial_dir),
        )
    else:
        selected_file = filedialog.askopenfilename(
            title="Select Eclipse executable",
            initialdir=str(initial_dir),
            filetypes=(
                ("Eclipse executable", "eclipse.exe eclipse"),
                ("All files", "*.*"),
            ),
        )

    if not selected_file:
        set_status("Eclipse selection cancelled.")
        return None

    selected_path = Path(selected_file).expanduser()
    eclipse_executable = resolve_eclipse_executable(selected_path)

    if eclipse_executable is None:
        message = "Please select a valid Eclipse installation."
        if sys.platform == "darwin":
            message += "\n\nOn macOS, select the Eclipse.app application bundle."
        elif sys.platform.startswith("win"):
            message += "\n\nOn Windows, select eclipse.exe."

        messagebox.showerror("Invalid Eclipse Selection", message)
        log_event("eclipse_manual_selection_invalid", path=selected_path)
        return None

    # Save the user's selected path. On macOS this can be the .app bundle, while
    # get_configured_eclipse_executable() resolves it to Contents/Eclipse/eclipse.
    write_misar_config("eclipse.executable", str(selected_path))
    set_status("Eclipse executable selected.")
    log_event("eclipse_manual_selection_saved", selected_path=selected_path, executable=eclipse_executable)
    refresh_launch_buttons()
    return eclipse_executable



def append_existing_eclipse_candidate(candidates, candidate):
    """Append one Eclipse executable candidate if it exists and is not already listed."""
    if not candidate:
        return

    candidate_path = Path(candidate).expanduser()

    if candidate_path.is_file() and candidate_path not in candidates:
        candidates.append(candidate_path)


def append_globbed_eclipse_candidates(candidates, base_dir, pattern):
    """Append Eclipse executable candidates discovered by globbing a base directory."""
    base_path = Path(base_dir).expanduser()

    if not base_path.exists():
        return

    for candidate in base_path.glob(pattern):
        append_existing_eclipse_candidate(candidates, candidate)


def get_eclipse_candidates():
    """Return likely Eclipse executable paths for macOS, Windows and Linux."""
    candidates = []

    for executable_name in ("eclipse", "eclipse.exe"):
        append_existing_eclipse_candidate(candidates, shutil.which(executable_name))

    if sys.platform == "darwin":
        mac_bases = (
            Path("/Applications"),
            USER_HOME_DIR / "Applications",
            USER_HOME_DIR / "eclipse",
            USER_HOME_DIR / "Eclipse",
        )

        for base_dir in mac_bases:
            append_globbed_eclipse_candidates(candidates, base_dir, "Eclipse*.app/Contents/Eclipse/eclipse")
            append_globbed_eclipse_candidates(candidates, base_dir, "*Eclipse*.app/Contents/Eclipse/eclipse")
            append_globbed_eclipse_candidates(candidates, base_dir, "Eclipse.app/Contents/Eclipse/eclipse")
            append_globbed_eclipse_candidates(candidates, base_dir, "Eclipse.app/Contents/MacOS/eclipse")
            append_globbed_eclipse_candidates(candidates, base_dir, "*/Eclipse.app/Contents/Eclipse/eclipse")
            append_globbed_eclipse_candidates(candidates, base_dir, "*/Eclipse.app/Contents/MacOS/eclipse")

    elif sys.platform.startswith("win"):
        windows_bases = (
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            USER_HOME_DIR / "eclipse",
            USER_HOME_DIR / "Eclipse",
            Path("C:/eclipse"),
        )

        for base_dir in windows_bases:
            if not base_dir:
                continue

            append_existing_eclipse_candidate(candidates, Path(base_dir) / "eclipse.exe")
            append_globbed_eclipse_candidates(candidates, base_dir, "Eclipse*/eclipse.exe")
            append_globbed_eclipse_candidates(candidates, base_dir, "Eclipse Foundation/*/eclipse.exe")
            append_globbed_eclipse_candidates(candidates, base_dir, "Programs/Eclipse*/eclipse.exe")
            append_globbed_eclipse_candidates(candidates, base_dir, "*/eclipse.exe")

    else:
        for candidate in (
            "/usr/bin/eclipse",
            "/usr/local/bin/eclipse",
            "/snap/bin/eclipse",
            "/opt/eclipse/eclipse",
        ):
            append_existing_eclipse_candidate(candidates, candidate)

        append_globbed_eclipse_candidates(candidates, Path("/opt"), "eclipse*/eclipse")
        append_globbed_eclipse_candidates(candidates, USER_HOME_DIR / "eclipse", "*/eclipse")
        append_globbed_eclipse_candidates(candidates, USER_HOME_DIR / "Eclipse", "*/eclipse")
        append_globbed_eclipse_candidates(candidates, USER_HOME_DIR / ".local", "share/eclipse*/eclipse")

    return candidates


def get_macos_eclipse_app_bundle(eclipse_executable):
    """Return the containing Eclipse .app bundle for a macOS Eclipse executable."""
    if sys.platform != "darwin":
        return None

    current_path = Path(eclipse_executable).expanduser()

    for parent in (current_path, *current_path.parents):
        if parent.suffix == ".app" and parent.is_dir():
            return parent

    return None


def build_eclipse_launch_command(eclipse_executable):
    """Build a platform-safe command that only opens Eclipse."""
    if sys.platform == "darwin":
        app_bundle = get_macos_eclipse_app_bundle(eclipse_executable)

        if app_bundle is not None:
            return ["open", str(app_bundle)]

    return [str(eclipse_executable)]


def find_eclipse_executable():
    """Return the configured or first auto-detected Eclipse executable, caching detections."""
    configured_eclipse = get_configured_eclipse_executable()

    if configured_eclipse is not None:
        return configured_eclipse

    candidates = get_eclipse_candidates()

    if not candidates:
        return None

    selected_candidate = candidates[0]

    # Cache the first auto-detected executable so future launches avoid repeated globbing.
    # If the path later becomes invalid, get_configured_eclipse_executable() ignores it
    # and auto-detection can run again.
    try:
        write_misar_config("eclipse.executable", str(selected_candidate))
        log_event("eclipse_auto_detection_cached", path=selected_candidate)
    except Exception as error:
        log_event("eclipse_auto_detection_cache_failed", path=selected_candidate, error=str(error))

    return selected_candidate


def open_eclipse_transformation_workspace():
    """Open Eclipse if it is installed; otherwise show a clear notification."""
    eclipse_executable = find_eclipse_executable()

    if eclipse_executable is None:
        chooser_message = "Eclipse could not be found automatically.\n\n"
        if sys.platform == "darwin":
            chooser_message += "Please select the Eclipse.app application bundle."
        else:
            chooser_message += "Please select the Eclipse executable file. On Windows this is usually eclipse.exe."

        messagebox.showinfo("Choose Eclipse", chooser_message)
        log_event("eclipse_executable_not_found")
        eclipse_executable = select_eclipse_executable()

        if eclipse_executable is None:
            set_status("Eclipse executable was not selected.")
            return False

    command = build_eclipse_launch_command(eclipse_executable)

    try:
        set_status("Opening Eclipse...")
        launch_logged_subprocess(command, "Eclipse", cwd=USER_HOME_DIR)
        log_event("eclipse_launch_requested", executable=eclipse_executable, command=command)
        set_status("Eclipse launch requested.")
        return True
    except Exception as error:
        log_exception("eclipse_launch_failed", error, executable=eclipse_executable, command=command)
        messagebox.showerror(
            "Eclipse Launch Failed",
            "I found Eclipse, but could not open it.\n\n"
            "Eclipse path:\n"
            + str(eclipse_executable)
            + "\n\nPlease open Eclipse manually.",
        )
        set_status("Eclipse launch failed.")
        return False


def build_parser_launch_command():
    command = [sys.executable, "-u", str(PARSER_GUI_PATH)]

    if DEBUG_MODE:
        selected_path = Path(PARSER_SELECTED_PSM_PATH or PARSER_PSM_ECORE).expanduser()
        if not selected_path.is_file():
            messagebox.showerror(
                "Missing PSM Path",
                "The selected PSM Ecore file no longer exists:\n\n" + str(selected_path),
            )
            return None
        command.extend(["--psm-path", str(selected_path)])

    return command


def build_gmg_launch_command():
    """Build the GMG launch command using the current visualiser version when available."""
    command = ["java", "-jar", str(GMG_JAR_PATH)]
    visualiser_version = get_module_version("MiSAR Graphical Model Generator")

    if visualiser_version:
        command.extend(["--version", visualiser_version])

    return command


def handle_keyboard_shortcut(event):
    widget_class = getattr(event.widget, "winfo_class", lambda: "")()
    if widget_class in {"Entry", "Text", "TEntry"}:
        return None

    key = getattr(event, "char", "")
    if not key:
        return None

    key = key.lower()
    if key == "p":
        handle_parser_button()
        return "break"
    if key == "e":
        handle_transformation_engine_button()
        return "break"
    if key == "g":
        handle_gmg_button()
        return "break"
    if key == "?":
        handle_help_button()
        return "break"
    return None


def active_monitor_bounds(root):
    pointer_x = root.winfo_pointerx()
    pointer_y = root.winfo_pointery()

    try:
        from screeninfo import get_monitors

        for monitor in get_monitors():
            if monitor.x <= pointer_x < monitor.x + monitor.width and monitor.y <= pointer_y < monitor.y + monitor.height:
                return monitor.x, monitor.y, monitor.width, monitor.height
    except Exception:
        pass

    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def should_maximise_for_small_screen(monitor_width, monitor_height):
    """Return True when the current screen is small enough to benefit from maximising."""
    return monitor_width <= 1366 or monitor_height <= 800


def maximise_window_if_supported(root):
    """Best-effort maximise/zoom for small screens such as 1280x720 laptops."""
    try:
        if sys.platform.startswith("win"):
            root.state("zoomed")
            return True
        root.attributes("-zoomed", True)
        return True
    except Exception:
        return False


def calculate_dynamic_window_height(root):
    """Return a compact height that fits visible launcher content without leaving a large gap."""
    root.update_idletasks()
    _monitor_x, _monitor_y, _monitor_width, monitor_height = active_monitor_bounds(root)

    requested_height = root.winfo_reqheight() + 12
    available_height = max(WINDOW_MIN_HEIGHT, monitor_height - WINDOW_VERTICAL_MARGIN)

    return min(max(requested_height, WINDOW_MIN_HEIGHT), available_height)


def resize_window_to_visible_content(root, width=None, keep_position=False):
    """Resize the launcher when optional panels are shown/hidden, such as Debug mode."""
    if root is None:
        return

    root.update_idletasks()

    current_width = width or max(root.winfo_width(), WINDOW_WIDTH)
    target_height = calculate_dynamic_window_height(root)

    if keep_position and root.winfo_ismapped():
        x = root.winfo_x()
        y = root.winfo_y()
    else:
        monitor_x, monitor_y, monitor_width, monitor_height = active_monitor_bounds(root)
        x = monitor_x + max((monitor_width - current_width) // 2, 0)
        y = monitor_y + max((monitor_height - target_height) // 2, 0)

    root.geometry(f"{current_width}x{target_height}+{x}+{y}")


def build_launcher_layout_decision(monitor_width, monitor_height, requested_width=WINDOW_WIDTH, requested_height=None):
    """Build a testable layout decision for the current launcher screen."""
    small_screen = should_maximise_for_small_screen(monitor_width, monitor_height)

    if small_screen:
        target_width = max(monitor_width - 16, 960)
        target_height = max(monitor_height - 56, WINDOW_MIN_HEIGHT)
        x = 0
        y = 0
        maximise = True
    else:
        target_height = requested_height or min(max(WINDOW_MIN_HEIGHT, monitor_height - WINDOW_VERTICAL_MARGIN), WINDOW_HEIGHT)
        target_width = min(requested_width, max(monitor_width - 40, 960))
        x = max((monitor_width - target_width) // 2, 0)
        y = max((monitor_height - target_height) // 2, 0)
        maximise = False

    return {
        "component": "aio",
        "screen_width": int(monitor_width),
        "screen_height": int(monitor_height),
        "window_size_option": get_ui_density_choice(),
        "resolved_ui_density": float(UI_DENSITY),
        "small_screen": small_screen,
        "target_width": int(target_width),
        "target_height": int(target_height),
        "x": int(x),
        "y": int(y),
        "maximised": maximise,
    }


def log_launcher_layout_decision(decision):
    """Log the launcher layout decision when debug logging is active."""
    log_event("ui_layout_decision", **decision)


def centre_and_focus_window(root, width=WINDOW_WIDTH, height=None):
    root.update_idletasks()
    monitor_x, monitor_y, monitor_width, monitor_height = active_monitor_bounds(root)
    target_height = height or calculate_dynamic_window_height(root)
    decision = build_launcher_layout_decision(
        monitor_width,
        monitor_height,
        requested_width=width,
        requested_height=target_height,
    )
    log_launcher_layout_decision(decision)

    x = monitor_x + decision["x"]
    y = monitor_y + decision["y"]
    root.geometry(f'{decision["target_width"]}x{decision["target_height"]}+{x}+{y}')
    root.deiconify()

    if decision["maximised"]:
        maximise_window_if_supported(root)

    root.lift()
    root.focus_force()

    if decision["maximised"]:
        return

    try:
        root.attributes("-topmost", True)
        root.after(450, lambda: root.attributes("-topmost", False))
    except tkinter.TclError:
        pass


def handle_parser_button():
    if not PARSER_PSM_ECORE.is_file():
        if USE_REPOSITORY_PARSER:
            messagebox.showerror(
                "Repository Parser Missing",
                "The --use-repository-parser flag is active, but the required parser files were not found in:\n\n"
                + str(REPOSITORY_PARSER_DIR)
                + "\n\nPlease run MiSAR.py from the root of the parser repository.",
            )
            log_event("repository_parser_missing", path=REPOSITORY_PARSER_DIR, psm_ecore=PARSER_PSM_ECORE)
            set_status("Repository parser files are missing.")
            return

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
        set_module_actions_enabled(False)
        set_busy_status("Installing MiSAR Parser. Please wait...", active=True)
        refresh_ui_now()

        if install_parser():
            messagebox.showinfo(
                "Success!",
                "The operation completed successfully!\nThe Parser has been installed! It has been saved at: "
                + str(MISAR_DIR),
            )
            refresh_launch_buttons()
            set_busy_status("MiSAR Parser installed successfully.", active=False)
            set_module_actions_enabled(True)
            return

        uninstall_path(Path("MiSAR") / "Parser")

        if install_parser():
            messagebox.showinfo(
                "Success!",
                "The operation completed successfully!\nThe Parser has been installed! It has been saved at: "
                + str(INSTALLED_PARSER_DIR),
            )
            refresh_launch_buttons()
            set_busy_status("MiSAR Parser installed successfully.", active=False)
        else:
            messagebox.showerror("Failure!", "The Parser installation has failed.")
            set_busy_status("Parser installation failed.", active=False)

        set_module_actions_enabled(True)
        return

    if check_required_modules():
        command = build_parser_launch_command()
        if command is None:
            set_status("Parser launch cancelled because the selected PSM file is missing.")
            return

        set_status("Launching MiSAR Parser...")
        log_event("parser_launch_started", path=PARSER_GUI_PATH, command=command)
        launch_logged_subprocess(command, "MiSAR Parser GUI", cwd=PARSER_GUI_PATH.parent)
        log_event("parser_launch_requested", path=PARSER_GUI_PATH)
        set_status("MiSAR Parser launch requested.")


def handle_transformation_engine_button():
    open_eclipse_transformation_workspace()


def handle_gmg_button():
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

        set_status("Installing MiSAR Graphical Model Generator...")

        if install_or_update_gmg():
            messagebox.showinfo(
                "Success!",
                "The operation completed successfully!\nThe Graphical Model Generator JAR has been saved at: "
                + str(GMG_JAR_PATH),
            )
            refresh_launch_buttons()
            set_status("Graphical Model Generator installed successfully.")
        else:
            messagebox.showerror("Failure!", "The Graphical Model Generator installation has failed.")
            set_status("Graphical Model Generator installation failed.")

        return

    if check_internet():
        set_status("Checking Graphical Model Generator updates...")
        install_or_update_gmg()

    set_status("Launching MiSAR Graphical Model Generator...")
    gmg_command = build_gmg_launch_command()
    log_event("gmg_launch_started", jar_path=GMG_JAR_PATH, command=gmg_command)
    run_logged_subprocess(gmg_command, "MiSAR Graphical Model Generator", cwd=GMG_JAR_PATH.parent)
    log_event("gmg_launch_completed", jar_path=GMG_JAR_PATH)


def handle_help_button():
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
        set_status("Opening MiSAR documentation...")
        open_documentation()


def handle_module_button(module):
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
    log_event("window_quit_requested")
    main_window.quit()
    main_window.destroy()


def refresh_launch_buttons():
    log_event("launch_button_refresh_started")

    parser_installed = is_parser_installed()
    gmg_installed = is_gmg_installed()

    set_module_button_state(the_parser, parser_installed)

    if USE_REPOSITORY_PARSER and the_parser is not None:
        the_parser.launch_button.configure(text="Launch" if parser_installed else "Unavailable")
        if the_parser.uninstall_button is not None:
            the_parser.uninstall_button.configure(state=tkinter.DISABLED)
        if hasattr(the_parser, "status_badge"):
            if parser_installed:
                the_parser.status_badge.configure(
                    text="Repository runtime",
                    bg="#dcfce7",
                    fg=PALETTE["success"],
                )
            else:
                the_parser.status_badge.configure(
                    text="Repository missing",
                    bg=PALETTE["secondary"],
                    fg=PALETTE["muted"],
                )

    set_transformation_engine_button_state()
    set_module_button_state(the_graphical_model_generator, gmg_installed)
    set_status("Ready")

    log_event(
        "launch_button_refresh_completed",
        parser_installed=parser_installed,
        gmg_installed=gmg_installed,
        use_repository_parser=USE_REPOSITORY_PARSER,
        active_parser_dir=ACTIVE_PARSER_DIR,
    )


def configure_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tkinter.TclError:
        pass
    for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(font_name).configure(size=ui_size(11, 8))
        except Exception:
            pass
    style.configure("Root.TFrame", background=PALETTE["bg"])
    style.configure("Header.TFrame", background=PALETTE["bg"])
    style.configure("AppTitle.TLabel", background=PALETTE["bg"], foreground=PALETTE["title"], font=ui_font(22, "bold"))
    style.configure("SectionTitle.TLabel", background=PALETTE["bg"], foreground=PALETTE["title"], font=ui_font(13, "bold"))
    style.configure("CardTitle.TLabel", background=PALETTE["panel"], foreground=PALETTE["title"], font=ui_font(14, "bold"))
    style.configure("MutedRoot.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"], font=ui_font(11))
    style.configure("MutedCard.TLabel", background=PALETTE["panel"], foreground=PALETTE["muted"], font=ui_font(11))


def initialise_ui():
    log_event("ui_initialisation_started")

    root = tkinter.Tk()
    root.withdraw()
    root.misar_ui_images = {}
    set_window_icon(root)
    launcher_version = get_launcher_version()
    launcher_version_text = format_version_text(launcher_version)
    root.title("MicroService Architecture Recovery" + (" " + launcher_version_text if launcher_version_text else ""))
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    root.minsize(960, WINDOW_MIN_HEIGHT)
    root.configure(bg=PALETTE["bg"])
    configure_styles(root)

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    sidebar = tkinter.Frame(root, width=ui_size(88), bg=PALETTE["sidebar"])
    sidebar.grid(row=0, column=0, sticky="ns")
    sidebar.grid_propagate(False)

    add_sidebar_logo(
        sidebar,
        root,
        "sidebar_brunel_logo",
        BRUNEL_LOGO_PATH,
        "Brunel",
        max_width=ui_size(68),
        max_height=ui_size(34),
        pady=ui_pad((16, 4)),
    )
    add_sidebar_logo(
        sidebar,
        root,
        "sidebar_misar_logo",
        MISAR_LOGO_PATH,
        "MiSAR",
        max_width=ui_size(62),
        max_height=ui_size(46),
        pady=ui_pad((4, 3)),
    )
    tkinter.Frame(sidebar, height=1, bg="#243454").pack(fill="x", padx=ui_size(16), pady=ui_size(14))
    sidebar_footer_text = "AIO" + ("\n" + launcher_version_text if launcher_version_text else "")
    root.sidebar_footer_label = tkinter.Label(
        sidebar,
        text=sidebar_footer_text,
        font=ui_font(10, "bold"),
        justify="center",
        bg=PALETTE["sidebar"],
        fg=PALETTE["sidebar_text"],
    )
    root.sidebar_footer_label.pack(side="bottom", pady=ui_size(14))

    main = ttk.Frame(root, style="Root.TFrame")
    main.grid(row=0, column=1, sticky="nsew")
    main.grid_rowconfigure(1, weight=1)
    main.grid_columnconfigure(0, weight=1)

    header = ttk.Frame(main, padding=ui_pad((24, 20, 24, 6)), style="Header.TFrame")
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1)

    app_title = "MiSAR All-in-One launcher" + (" " + launcher_version_text if launcher_version_text else "")
    ttk.Label(header, text=app_title, style="AppTitle.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(
        header,
        text="Install, update and launch the MiSAR Parser, Transformation Engine and Graphical Model Generator from one guided dashboard.",
        style="MutedRoot.TLabel",
        wraplength=760,
    ).grid(row=1, column=0, sticky="w", pady=ui_pad((5, 0)))
    ttk.Label(
        header,
        text="Tip: keyboard shortcuts are available - P for Parser, E for Eclipse, G for Graphical Model Generator, ? for Help.",
        style="MutedRoot.TLabel",
        wraplength=760,
    ).grid(row=2, column=0, sticky="w", pady=ui_pad((3, 0)))

    root.debug_header = tkinter.Frame(header, bg=PALETTE["bg"])
    root.debug_header.grid(row=0, column=1, rowspan=3, sticky="ne", padx=ui_pad((14, 0)))
    root.debug_status_label = tkinter.Label(
        root.debug_header,
        text="Debug mode: OFF",
        font=ui_font(10, "bold"),
        bg=PALETTE["secondary"],
        fg=PALETTE["muted"],
        padx=ui_size(10),
        pady=ui_size(5),
    )
    root.debug_status_label.pack(anchor="e", pady=ui_pad((0, 6)))
    root.debug_toggle_button = RoundedButton(root.debug_header, "Activate Debug", command=toggle_debug_mode, variant="secondary", width=130)
    root.debug_toggle_button.configure(bg=PALETTE["bg"])
    root.debug_toggle_button.pack(anchor="e")
    root.settings_button = RoundedButton(root.debug_header, "Options", command=open_launcher_settings, variant="secondary", width=110)
    root.settings_button.configure(bg=PALETTE["bg"])
    root.settings_button.pack(anchor="e", pady=ui_pad((6, 0)))

    body = ttk.Frame(main, padding=ui_pad((24, 10, 24, 14)), style="Root.TFrame")
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=1)

    root.debug_panel = BoxFrame(body)
    root.debug_panel.grid(row=0, column=0, sticky="ew", pady=ui_pad((0, 10)))
    root.debug_panel.content.grid_columnconfigure(0, weight=1)
    tkinter.Label(
        root.debug_panel.content,
        text="Debug parser options",
        font=ui_font(12, "bold"),
        bg=PALETTE["panel"],
        fg=PALETTE["title"],
    ).grid(row=0, column=0, sticky="w", columnspan=3)
    tkinter.Label(
        root.debug_panel.content,
        text="Choose the PSM Ecore file passed to the parser with --psm-path. Leave it as default unless you are testing parser configuration.",
        font=ui_font(11),
        bg=PALETTE["panel"],
        fg=PALETTE["muted"],
        wraplength=760,
    ).grid(row=1, column=0, sticky="w", columnspan=3, pady=(4, 12))
    root.debug_psm_entry = tkinter.Entry(
        root.debug_panel.content,
        relief="flat",
        font=ui_font(10),
        readonlybackground=PALETTE["input"],
        fg=PALETTE["text"],
        bg=PALETTE["input"],
        highlightthickness=1,
        highlightbackground=PALETTE["border"],
        highlightcolor=PALETTE["accent"],
    )
    root.debug_psm_entry.grid(row=2, column=0, sticky="ew", ipady=ui_size(6), padx=ui_pad((0, 8)))
    root.debug_psm_entry.configure(state="readonly")
    root.debug_browse_button = RoundedButton(root.debug_panel.content, "Browse", command=browse_parser_psm_path, width=104)
    root.debug_browse_button.grid(row=2, column=1, sticky="e", padx=ui_pad((0, 6)))
    root.debug_reset_button = RoundedButton(root.debug_panel.content, "Reset", command=reset_parser_psm_path, variant="secondary", width=96)
    root.debug_reset_button.grid(row=2, column=2, sticky="e")

    ttk.Label(body, text="Available modules", style="SectionTitle.TLabel").grid(row=1, column=0, sticky="w", pady=ui_pad((0, 8)))
    root.modules_frame = ttk.Frame(body, style="Root.TFrame")
    root.modules_frame.grid(row=2, column=0, sticky="nsew")
    root.modules_frame.grid_columnconfigure(0, weight=1)

    update_debug_ui()
    # Keyboard shortcuts are available if preferred: P for Parser, E for Eclipse, G for Graphical Model Generator, ? for Help.
    root.bind_all("<KeyPress>", handle_keyboard_shortcut)

    root.status_bar = tkinter.Frame(root, height=42, bg=PALETTE["status_bg"])
    root.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
    root.status_label = tkinter.Label(root.status_bar, text="Ready", anchor="w", font=ui_font(11), bg=PALETTE["status_bg"], fg=PALETTE["text"])
    root.status_label.pack(side="left", padx=ui_size(16))
    root.status_progress = ttk.Progressbar(root.status_bar, mode="indeterminate", length=ui_size(150))
    root.status_progress_visible = False
    root.footer_label = tkinter.Label(root.status_bar, text="Brunel University London", anchor="e", font=ui_font(11), bg=PALETTE["status_bg"], fg=PALETTE["muted"])
    root.footer_label.pack(side="right", padx=ui_size(16))

    log_event("ui_initialisation_completed")
    return root


def run_application():
    global main_window, the_parser, the_transformation_engine, the_graphical_model_generator, the_help_button, MISAR_VERSIONS, MISAR_CONFIGS, USE_REPOSITORY_PARSER

    MISAR_VERSIONS = load_misar_versions()
    MISAR_CONFIGS = load_misar_configs()
    USE_REPOSITORY_PARSER = resolve_use_repository_parser(
        bool(getattr(ARGS, "use_repository_parser", False)),
        MISAR_CONFIGS,
    )
    configure_parser_runtime_paths()
    apply_configured_ui_density()
    log_event(
        "ui_density_startup",
        component="aio",
        window_size_option=get_ui_density_choice(),
        resolved_ui_density=UI_DENSITY,
        config_path=CONFIG_FILE_PATH,
    )

    log_event(
        "application_startup",
        debug_enabled=DEBUG_MODE,
        use_repository_parser=USE_REPOSITORY_PARSER,
        log_file=LOG_FILE_PATH if DEBUG_MODE else None,
        aio_dir=AIO_DIR,
        installed_parser_dir=INSTALLED_PARSER_DIR,
        repository_parser_dir=REPOSITORY_PARSER_DIR,
        active_parser_dir=ACTIVE_PARSER_DIR,
        gmg_jar_path=GMG_JAR_PATH,
    )

    main_window = initialise_ui()

    the_parser = ProgramOfChoice("MiSAR Parser", get_module_version("MiSAR Parser"), 1, 0, main_window, supports_uninstall=True)

    the_transformation_engine = ProgramOfChoice(
        "MiSAR Transformation Engine",
        get_module_version("MiSAR Transformation Engine"),
        2,
        0,
        main_window,
    )
    the_transformation_engine.launch_button.configure(text="Open Eclipse", font=ui_font(11, "bold"))

    the_graphical_model_generator = ProgramOfChoice(
        "MiSAR Graphical Model Generator",
        get_module_version("MiSAR Graphical Model Generator"),
        3,
        0,
        main_window,
        supports_uninstall=True,
    )

    the_help_button = ProgramOfChoice("Need help or more information about this program?", "", 4, 0, main_window)
    the_help_button.launch_button.configure(text="Help", font=ui_font(11, "bold"))

    refresh_launch_buttons()
    update_debug_ui()
    main_window.after(80, lambda: centre_and_focus_window(main_window))

    if is_auto_update_enabled() and not USE_REPOSITORY_PARSER:
        main_window.after(500, lambda: run_update_check_in_background(manual=False))
    else:
        log_event(
            "startup_update_check_not_scheduled",
            auto_update_enabled=is_auto_update_enabled(),
            use_repository_parser=USE_REPOSITORY_PARSER,
        )
    main_window.protocol("WM_DELETE_WINDOW", window_quit)

    log_event("tkinter_mainloop_started")
    main_window.mainloop()
    log_event("application_shutdown")


setup_logger()

if __name__ == "__main__":
    run_application()