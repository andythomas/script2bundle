"""
Generate an application bundle (Mac OS) from an executable.

Run the script without options to generate example.app in the
same directory. Run `script2bundle -h` for additional options

Initial version 2022 Apr 22 (Andy Thomas)
https://github.com/andythomas/script2bundle

For more information on application bundle declarations, in particular
UTIs, please see:

https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_declare/understand_utis_declare.html
https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html
https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_conc/understand_utis_conc.html
"""

import argparse
import os
import plistlib
import re
import shutil
import string
import sys
import time
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Union

import icnsutil

LAUNCHER_NAME = "terminallauncher"


class _FilesystemDictionary:
    """Create files and folders in a dictionary."""

    def __init__(self):
        """Create the root directory."""
        self.directory_dict = {}

    def _relative_path(self, path: Path) -> Path:
        """
        Remove the leading / from a path (if existing).

        Parameters
        ----------
        path: Path
            The path to be cleaned from a prepending slash.

        Returns
        -------
        Path
            The 'relative' path.
        """
        if path.parts[0] == "/":
            path = Path(*path.parts[1:])
        return path

    def _cd(self, path: Path) -> dict:
        """
        Change into a directory and create unexisting ones.

        Parameters
        ----------
        path : Path
            The directory to change into (starting from root).

        Returns
        -------
        dict
            The 'directory' that was changed into.
        """
        current_folder = self.directory_dict
        for subfolder in path.parts:
            if subfolder not in current_folder:
                current_folder[subfolder] = {}
            current_folder = current_folder[subfolder]
        return current_folder

    def mkdir(self, path: Path):
        """
        Create a directory.

        Parameters
        ----------
        path: Path
            The full path of the directory.
        """
        path = self._relative_path(path)
        self._cd(path)

    def save_file(self, file: Path, content: Union[str, bytes]) -> None:
        """
        Save a file with given content.

        Parameters
        ----------
        file : Path
            The file including its full path and filename.
        content : str or bytes
            The content of the file (text or binary).
        """
        file = self._relative_path(file)
        dir_ref = self._cd(file.parent)
        if isinstance(content, str):
            content = content.encode()
        dir_ref[file.name] = BytesIO(content)

    def write_all_to_disk(self, root: Path) -> None:
        """
        Write the directory structure and all files to disk.

        Parameters
        ----------
        root : Path
            The reference folder on the disk that becomes root.
        """
        self._write_recursively(root, self.directory_dict)

    def _write_recursively(self, base: Path, subdirectory: dict) -> None:
        """
        Write everything recursively to the disk.

        Parameters
        ----------
        base: Path
            The reference point on the disk.
        subdirectory : dict
            The dict with only items in this subdirectory.
        """
        Path.mkdir(base, parents=True, exist_ok=True)
        for name, obj in subdirectory.items():
            full_path = base / Path(name)
            if isinstance(obj, dict):
                self._write_recursively(full_path, obj)
            elif isinstance(obj, BytesIO):
                with open(full_path, "wb") as f:
                    f.write(obj.getvalue())


class ApplicationBundle(_FilesystemDictionary):
    """Create application bundle and manag content."""

    def __init__(self, executable: Path) -> None:
        """
        Store the executable and plist in the correct directories.

        Parameters
        ----------
        executable : Path
            The full path and name of the executable to be bundled.
        """
        super().__init__()
        self.original_path = executable.parent
        self.clean_executable = re.sub(r"[^A-Za-z0-9\.-]+", "", executable.name)
        self.set_destination("executable")
        self.set_filename(self.clean_executable)
        self.mkdir(Path("Contents") / Path("Resources"))
        script = Path(executable).read_bytes()
        self.save_file(Path("Contents") / Path("MacOS") / self.clean_executable, script)
        self.plist_dict = dict(CFBundleExecutable=self.clean_executable)
        self.plist_dict.update(CFBundlePackageType="APPL")
        self.set_CFBundleDisplayName(self.clean_executable + ".app")
        self.set_CFBundleIdentifier(self.clean_executable)
        self.CFBundleTypeRole = "Viewer"

    def set_CFBundleDisplayName(self, name: str) -> None:
        """
        Set the 'official' name of the app used by, e.g., Siri.

        Paramters
        ---------
        name : str
            The name to be given.
        """
        self.plist_dict.update(CFBundleDisplayName=name)

    def set_CFBundleIdentifier(self, identifier: str) -> None:
        """
        Set the reverse domain name identifier for the app.

        A pseudo domain identifier is used. If the identifier would be
        'myapplication' -> 'org.script2bundle.myapplication'.

        Parameters
        ----------
        identifier : str
            The last part of that identifier adhering to RFC 1035.
        """
        identifier = "org.script2bundle." + identifier
        if not self._is_valid_domain(identifier):
            print(f"{identifier} is not a valid domain name as set forth in RFC 1035.")
            sys.exit(1)
        self.plist_dict.update(CFBundleIdentifier=identifier)

    def set_filename(self, name: str) -> None:
        """
        Set the filename of the application.

        Parameters
        ----------
        name : str
            The filename without '.app'.
        """
        self.filename = name + ".app"

    def set_destination(self, destination: str) -> None:
        """
        Set the destination of the bundle.

        Parameters
        ----------
        destination : str
            Can be 'executable' (same as input file), 'user'
            (~/Applications) or 'system (/Applications).
        """
        if destination == "executable":
            self.destination = self.original_path
        elif destination == "system":
            self.destination = Path("/Applications")
        elif destination == "user":
            self.destination = Path.home() / "Applications"

    def set_icon(self, icon: Path) -> None:
        """
        Set the icon for the app.

        icon : Path
            The directory and filename of the icon in 'png' format.
        """
        # if icon.name[-4:] == ".png":
        #      iconsfile = Path(icon.name[:-4] + ".icns")
        # else:
        iconsfile = Path(icon.name + ".icns")
        icon_img = icnsutil.IcnsFile()
        icon_img.add_media(file=icon)
        with NamedTemporaryFile(suffix=".icns") as tmp:
            icon_img.write(tmp.name)
            tmp.seek(0)
            icns_bytes = tmp.read()
        self.save_file(Path("Contents") / Path("Resources") / iconsfile, icns_bytes)
        self.plist_dict.update(CFBundleIconFile=iconsfile.name)

    def set_extension(self, extension: str) -> None:
        """
        Associate a file extension with the application.

        Then, a double-click or 'open' on a file with that extension
        will subsequently launch the application. The application has to
        run at least once to 'register' the extension with the system.

        Parameters
        ----------
        extension : str
            ZThe extension with the preceeding period.
        """
        self.extension = extension
        app_CFBundleIdentifier = self.plist_dict["CFBundleIdentifier"]
        UTTypeIdentifier = app_CFBundleIdentifier + ".datafile"
        if not self._is_valid_domain(UTTypeIdentifier):
            print(f"{UTTypeIdentifier} is not a valid domain name as set forth in RFC 1035.")
            sys.exit(1)
        file_type = self.plist_dict["CFBundleDisplayName"] + " datafile"
        app_CFBundleDocumentTypes = [
            {
                "LSItemContentTypes": [UTTypeIdentifier],
                "CFBundleTypeName": file_type,
                "CFBundleTypeRole": self.CFBundleTypeRole,
            }
        ]
        self.plist_dict.update(CFBundleDocumentTypes=app_CFBundleDocumentTypes)
        app_UTExportedTypeDeclarations = [
            {
                "UTTypeIdentifier": UTTypeIdentifier,
                "UTTypeTagSpecification": {"public.filename-extension": extension},
                "UTTypeConformsTo": "public.data",
                "UTTypeDescription": file_type,
            }
        ]
        self.plist_dict.update(UTExportedTypeDeclarations=app_UTExportedTypeDeclarations)

    def set_CFBundleTypeRole(self, role: str):
        """
        Set the bundle type role.

        Parameters
        ----------
        role : str
            Can be 'Viewer','Editor','Shell', or 'None'.
        """
        self.CFBundleTypeRole = role

    def write_bundle(self) -> Path:
        """
        Write the bundle to the disk.

        Returns
        -------
        Path
            The path and filename of the application bundle.
        """
        destination = self.destination / Path(self.filename)
        if destination.exists():
            shutil.rmtree(destination)
        plist = plistlib.dumps(self.plist_dict)
        self.save_file(Path("Contents") / Path("Info.plist"), plist)
        self.write_all_to_disk(destination)
        executable = destination / Path("Contents") / Path("MacOS") / self.clean_executable
        os.chmod(executable, 0o755)
        return destination

    def _is_valid_domain(self, domain: str) -> bool:
        """
        Check the validity of the Uniform Type Identifiers.

        Parameters
        ----------
        domain : str
            The domain name to be checked.

        Returns
        -------
        bool
            True if the domain is valid (RFC1035) and False otherwise.
        """
        rfc1035_chars = string.ascii_lowercase + string.digits + "-."
        if not all(char in rfc1035_chars for char in domain.lower()):
            return False
        if len(domain) > 253:
            return False
        if "--" in domain:
            return False
        if ".." in domain:
            return False
        return True


def _create_argparser():
    """Create the command line parser."""
    parser = argparse.ArgumentParser(
        description="Generate an application bundle (Mac OS) from an executable."
    )
    parser.add_argument(
        "-e",
        "--executable",
        type=str,
        help="The filename of the (existing) executable file to be bundled.",
    )
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        help="The filename of the app to be generated (without .app)",
    )
    parser.add_argument(
        "-i",
        "--CFBundleIconFile",
        type=str,
        help="The (existing) png to be used as an icon file.",
    )
    parser.add_argument(
        "-d",
        "--destination",
        type=str,
        choices={"user", "system", "executable"},
        default="executable",
        const="executable",
        nargs="?",
        help="The destination of the .app file (default: %(default)s).",
    )
    parser.add_argument(
        "--launch", action="store_true", help="Launch the app to register properly."
    )
    parser.add_argument(
        "-x",
        "--extension",
        type=str,
        nargs="*",
        help="File extension(s) to be opened by the app.",
    )
    parser.add_argument(
        "--CFBundleTypeRole",
        type=str,
        choices={"Editor", "Viewer", "Shell", "None"},
        default="Viewer",
        const="Viewer",
        nargs="?",
        help="The app’s role with respect to the file extension. (default: %(default)s).",
    )
    parser.add_argument(
        "--CFBundleDisplayName",
        type=str,
        help="Specifies the display name of the bundle, visible to users and used by Siri.",
    )
    parser.add_argument(
        "--terminal", action="store_true", help="Always launch the app via a terminal."
    )
    return parser.parse_args()


_example_content = f"""#!{sys.executable}
# very simple Qt executable to demonstrate script2bundle
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QEvent
from AppKit import NSApplication
from Foundation import NSBundle

class MyApplication(QApplication):
    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            filename = event.file()
            msg = QMessageBox()
            msg.setText(f"Opened by {{filename}}")
            msg.exec()
        return QApplication.event(self, event)

def set_correct_appname(name):
    # Correct the title
    bundle = NSBundle.mainBundle()
    if bundle:
        info_dict = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        info_dict["CFBundleName"] = name
    # Correct the menu
    app = NSApplication.sharedApplication()
    mainMenu = app.mainMenu()
    # Get left-most menu with app-specific items
    app_menu = mainMenu.itemAtIndex_(0).submenu()
    for i in range(app_menu.numberOfItems()):
        item = app_menu.itemAtIndex_(i)
        item.setTitle_(item.title().replace("Python", name))

def main():
    app = MyApplication(sys.argv)
    set_correct_appname("Example")
    ex = QMainWindow()
    ex.setWindowTitle("Example")
    ex.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
"""


def _create_example() -> str:
    """Create an examplefile and return its filename."""
    executable = "example"
    try:
        from AppKit import NSApplication  # noqa: F401
        from Foundation import NSBundle  # noqa: F401
        from PyQt6.QtCore import QEvent  # noqa: F401
        from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox  # noqa: F401
    except ImportError:
        print("Please install 'PyQt6' and 'pyobjc' to run the example. Exiting.")
        sys.exit(1)
    with open(executable, "w") as examplefile:
        examplefile.write(_example_content)
    os.chmod(executable, 0o755)
    return executable


def _create_launcher(executable: Path) -> Path:
    """Create an launcher file and return its filename."""
    terminal_script = f"#!/bin/bash\n/usr/bin/open '{executable.resolve()}' -a Terminal"
    terminal_filename = LAUNCHER_NAME
    with open(terminal_filename, "w") as terminal_file:
        terminal_file.write(terminal_script)
    os.chmod(terminal_filename, 0o755)
    executable = Path(terminal_filename)
    return executable


def main():
    """Parse the command line and run the app."""
    args = _create_argparser()
    app_executable = args.executable
    if app_executable is None:
        app_executable = _create_example()
    executable = Path(app_executable)
    if args.terminal:
        executable = _create_launcher(executable)
    vfs = ApplicationBundle(executable)
    if args.destination:
        vfs.set_destination(args.destination)
    if args.filename:
        vfs.set_filename(args.filename)
    else:
        vfs.set_filename(app_executable)
    if args.CFBundleDisplayName:
        vfs.set_CFBundleDisplayName(args.CFBundleDisplayName)
    if args.CFBundleIconFile:
        vfs.set_icon(Path(args.CFBundleIconFile))
    if args.CFBundleTypeRole:
        vfs.set_CFBundleTypeRole(args.CFBundleTypeRole)
    if args.extension:
        vfs.set_extension(args.extension)
    appname = vfs.write_bundle()
    # Launch if requested;
    # sleep required to allow the system to recognize the new app
    if args.launch:
        time.sleep(2)
        launch_cmd = f'Open "{appname}"'
        print(launch_cmd)
        os.system(launch_cmd)


if __name__ == "__main__":
    main()
