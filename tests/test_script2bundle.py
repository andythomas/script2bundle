"""Test the script2bundle options for proper function."""

import os
import plistlib
import random
import re
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import pytest

python_executable = sys.executable

minimal_file = f"""#!{python_executable}
# minmal qt6 app to test scrpt2bundle

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = QMainWindow()
    ex.setWindowTitle("Example")
    ex.show()
    sys.exit(app.exec())
"""


def open_app(file: Path) -> None:
    """
    Open the application.

    Parameters
    ----------
    file : Path
        The app or file with linked extension to be opened.
    """
    completed_process = subprocess.run(["Open", file])
    assert completed_process.returncode == 0
    time.sleep(2)


def kill_app(ci: bool, name: str) -> None:
    """
    Kill the application.

    Parameters
    ----------
    name : str
        The process name to be killed.
    """
    if ci:
        result = subprocess.run("ps -ax -o pid,comm", shell=True, capture_output=True, text=True)
        processes = result.stdout
        print(processes)
        # This is a hack trying to match the sandboxed
        # process on Github Actions
        pattern = r"(\d+)(.*)\/bin\/bash(.*)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.sh$"
        match = match = re.search(pattern, processes)
        if match:
            pid = match.group(0)
        else:
            pid = None
        print(pid)
        # assert result != ""
    # command_list = [
    #     "pgrep",
    #     "-f",
    #     name,
    # ]
    # completed_process = subprocess.run(command_list, check=True)
    # print(completed_process)
    result = subprocess.run("ps aux | grep _temp", shell=True, capture_output=True, text=True)
    processes = result.stdout
    print(processes)
    # assert completed_process.returncode == 0


def delete_bundle(file: Path) -> None:
    """
    Delete the bundle.

    Parameters
    ----------
    file : Path
        The application bundle to be deleted.
    """
    shutil.rmtree(file)


def get_plist(app: Path) -> dict:
    """
    Get the plist file from an app.

    Parameters
    ----------
    app : Path
        The application from which the plist is extracted.
    """
    plist_file = Path(app) / "Contents" / "Info.plist"
    with open(plist_file, "rb") as input_file:
        plist = plistlib.load(input_file)
    assert isinstance(plist, dict)
    return plist


def count_terminal_windows() -> int:
    """Count the open Terminal windows."""
    completed_process = subprocess.run(
        ["osascript", "-e", 'tell application "Terminal" to count windows'],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return int(completed_process.stdout.strip())


def close_last_terminal_window() -> None:
    """Close the last Terminal window."""
    command_list = [
        "osascript",
        "-e",
        'tell application "Terminal" to close last window',
    ]
    subprocess.run(command_list)


def bundle(command_list: List[str], file: Path) -> None:
    """
    Generate the app and default tests.

    Generate the app, then check for successful completion and if the
    file exists.

    Parameters
    ----------
    command_list : List
        The script2bundle 'command line'.
    file : Path
        The file including '.app'.
    """
    completed_process = subprocess.run(command_list)
    assert completed_process.returncode == 0
    example_app = file
    assert example_app.exists()
    time.sleep(1)


def test_without_parameters(cirunner) -> None:
    """Test the bundle with the example file."""
    name = "example"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
    ]
    file = Path(name + ".app")
    bundle(command_list, file)
    open_app(file)
    kill_app(cirunner, name)
    delete_bundle(file)


def test_launch() -> None:
    """Test the auto-open."""
    name = "example"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "--launch",
    ]
    file = Path(name + ".app")
    bundle(command_list, file)
    kill_app(name)
    delete_bundle(file)


@pytest.mark.ci
def test_filename() -> None:
    """Test the bundle with a custom filename."""
    characters = string.ascii_letters + string.digits
    name = "".join(random.choices(characters, k=8))
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-f",
        name,
    ]
    file = Path(name + ".app")
    bundle(command_list, file)
    delete_bundle(file)


@pytest.mark.ci
def test_icon() -> None:
    """Test the bundle with a custom filename."""
    name = "icon"
    icon_file = name + ".png"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-f",
        name,
        "-i",
        Path("media") / Path(icon_file),
    ]
    file = Path(name + ".app")
    bundle(command_list, file)
    plist = get_plist(file)
    assert plist["CFBundleIconFile"] == icon_file + ".icns"
    icon_file = Path(file) / "Contents" / "Resources" / Path(icon_file + ".icns")
    assert icon_file.is_file()
    delete_bundle(file)


destinations = ["user", "system"]


@pytest.mark.ci
@pytest.mark.parametrize("destination", destinations)
def test_destination(destination: str) -> None:
    """
    Test the bundle with different destinations.

    Parameters
    ----------
    destination : str
        Can be either 'executable' (some as script), 'user'
        (~/Applications) or 'system' (/Applications).
    """
    # ~/Applications
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-d",
        destination,
    ]
    if destination == "user":
        prefix = Path.home()
    elif destination == "system":
        prefix = Path("/")
    else:
        prefix = None
    assert isinstance(prefix, Path)
    file = prefix / "Applications" / "example.app"
    bundle(command_list, file)
    delete_bundle(file)


@pytest.mark.ci
def test_displayname() -> None:
    """Test the bundle with a custom display name."""
    file = Path("example.app")
    name = "Not Example"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "--CFBundleDisplayName",
        name,
    ]
    bundle(command_list, file)
    plist = get_plist(file)
    assert plist["CFBundleDisplayName"] == name
    delete_bundle(file)


def test_extension() -> None:
    """Test the bundle with a connected file extension."""
    name = "example"
    file = Path(name + ".app")
    extension = "s2bfile"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-x",
        extension,
    ]
    file_with_extension = Path(name + "." + extension)
    bundle(command_list, file)
    open_app(file)
    kill_app(name)
    with open(file_with_extension, "w") as test_file:
        test_file.write(".")
    open_app(file_with_extension)
    kill_app(name)
    plist = get_plist(file)
    entry1 = plist["CFBundleDocumentTypes"][0]
    datafile = str(file) + " datafile"
    identifier = str("org.script2bundle." + name + ".datafile")
    assert entry1["CFBundleTypeName"] == datafile
    assert entry1["CFBundleTypeRole"] == "Viewer"
    assert entry1["LSItemContentTypes"] == [identifier]
    entry2 = plist["UTExportedTypeDeclarations"][0]
    assert entry2["UTTypeConformsTo"] == "public.data"
    assert entry2["UTTypeDescription"] == datafile
    assert entry2["UTTypeIdentifier"] == identifier
    delete_bundle(file)
    os.remove(file_with_extension)


types = ["Editor", "Shell", "None"]


@pytest.mark.ci
@pytest.mark.parametrize("type_role", types)
def test_type_role(type_role: str) -> None:
    """
    Test other type role than 'viewer'.

    Parameters
    ----------
    type_role : str
        Can either be 'Viewer', 'Editor', 'Shell' or 'None'.
    """
    name = "example"
    file = Path(name + ".app")
    extension = "s2bfile"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-x",
        extension,
        "--CFBundleTypeRole",
        type_role,
    ]
    bundle(command_list, file)
    plist = get_plist(file)
    assert plist["CFBundleDocumentTypes"][0]["CFBundleTypeRole"] == type_role
    delete_bundle(file)


def test_terminal() -> None:
    """Test the launch via a terminal."""
    name = "example"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "--terminal",
    ]
    file = Path(name + ".app")
    bundle(command_list, file)
    before = count_terminal_windows()
    open_app(file)
    after = count_terminal_windows()
    assert after == before + 1
    kill_app(name)
    # close_last_terminal_window()
    # This does not work if pytest is also called via the command line
    delete_bundle(file)


def test_executable() -> None:
    """Test to wrap another executable."""
    name = "s2btest"
    with open(name, "w") as examplefile:
        examplefile.write(minimal_file)
    os.chmod(name, 0o755)
    file = Path(name + ".app")
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-e",
        name,
    ]
    bundle(command_list, file)
    open_app(file)
    kill_app(name)
    delete_bundle(file)
    os.remove(name)
