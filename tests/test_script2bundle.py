"""Test the script2bundle options for proper function."""

import os
import plistlib
import random
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import pytest

python_executable = sys.executable


def open_app(file: Path) -> None:
    """Open the application."""
    completed_process = subprocess.run(["Open", file])
    assert completed_process.returncode == 0
    time.sleep(1)


def kill_app() -> None:
    """Kill the application."""
    command_list = [
        "pkill",
        "-f",
        "example",
    ]
    completed_process = subprocess.run(command_list, check=True)
    assert completed_process.returncode == 0


def delete_bundle(file: Path) -> None:
    """Delete the bundle."""
    shutil.rmtree(file)


def get_plist(app: Path) -> dict:
    """Get the plist file from an app."""
    plist_file = Path(app) / "Contents" / "Info.plist"
    with open(plist_file, "rb") as input_file:
        plist = plistlib.load(input_file)
    assert isinstance(plist, dict)
    return plist


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


def test_without_parameters() -> None:
    """Test the bundle with the example file."""
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
    ]
    file = Path("example.app")
    bundle(command_list, file)
    open_app(file)
    kill_app()
    delete_bundle(file)


def test_launch() -> None:
    """Test the auto-open."""
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "--launch",
    ]
    file = Path("example.app")
    bundle(command_list, file)
    kill_app()
    delete_bundle(file)


def test_filename() -> None:
    """Test the bundle with a custom filename."""
    characters = string.ascii_letters + string.digits
    file = "".join(random.choices(characters, k=8))
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-f",
        file,
    ]
    file = Path(file + ".app")
    bundle(command_list, file)
    delete_bundle(file)


def test_icon() -> None:
    """Test the bundle with a custom filename."""
    file = "icon"
    icon_file = file + ".png"
    command_list = [
        python_executable,
        "-m",
        "script2bundle",
        "-f",
        file,
        "-i",
        Path("media") / Path(icon_file),
    ]
    file = Path(file + ".app")
    bundle(command_list, file)
    plist = get_plist(file)
    assert plist["CFBundleIconFile"] == icon_file + ".icns"
    icon_file = Path(file) / "Contents" / "Resources" / Path(icon_file + ".icns")
    assert icon_file.is_file()
    delete_bundle(file)


destinations = ["user", "system"]


@pytest.mark.parametrize("destination", destinations)
def test_destination(destination: str) -> None:
    """Test the bundle with different destinations."""
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
    kill_app()
    with open(file_with_extension, "w") as test_file:
        test_file.write(".")
    open_app(file_with_extension)
    kill_app()
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


@pytest.mark.parametrize("type_role", types)
def test_type_role(type_role: str) -> None:
    """Test other type role than 'viewer'."""
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
