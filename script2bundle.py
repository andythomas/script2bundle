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
from typing import Optional, Union

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
        self.mkdir(Path("Contents") / Path("Resources"))
        script = Path(executable).read_bytes()
        clean_name = re.sub(r"[^A-Za-z0-9\.-]+", "", executable.name)
        script_path = Path("Contents") / Path("MacOS") / clean_name
        self.save_file(script_path, script)
        self.plist_dict = dict(CFBundleExecutable=clean_name)
        self.plist_dict.update(CFBundlePackageType="APPL")
        self.set_CFBundleDisplayName(clean_name)
        self.set_CFBundleIdentifier(clean_name)
        self.destination = executable.parent / Path(clean_name + ".app")
        self.executable = script_path


    def set_CFBundleDisplayName(self, name: str):
        name += ".app"
        self.plist_dict.update(CFBundleDisplayName=name)

    def set_CFBundleIdentifier(self, identifier: str):
        identifier = "org.script2bundle." + identifier
        if not self._is_valid_domain(identifier):
            print(f"{identifier} is not a valid domain name as set forth in RFC 1035.")
            sys.exit(1)
        self.plist_dict.update(CFBundleIdentifier=identifier)

    def write_bundle(self) -> Path:
        # Delete possible old version
        if self.destination.exists():
            shutil.rmtree(self.destination)
        plist = plistlib.dumps(self.plist_dict)
        self.save_file(Path("Contents") / Path("Info.plist"), plist)
        self.write_all_to_disk(self.destination)
        os.chmod(self.destination / self.executable, 0o755)
        return self.destination

    def _is_valid_domain(self, domain):
        """Check the validity of the Uniform Type Identifiers."""
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


    def print(self):
        print(self.directory_dict)





def _determine_destination(destination: str, origin: str, filename: str) -> str:
    """Determine the destination of the bundle."""
    app_filename = None
    if destination == "executable":
        app_filename = os.path.join(origin, filename)
    elif destination == "system":
        app_filename = os.path.join("/Applications", filename)
    elif destination == "user":
        app_filename = os.path.join(os.path.expanduser("~"), "Applications", filename)
    assert app_filename is not None
    return app_filename


def do_the_bundle(
    app_executable: str,
    app_filename: Optional[str] = None,
    app_CFBundleDisplayName: Optional[str] = None,
    app_destination: str = "executable",
    app_CFBundleIconFile: Optional[str] = None,
    app_extension: Optional[str] = None,
    app_CFBundleTypeRole: str = "Viewer",
    app_terminal: bool = False,
) -> str:
    """
    Create the execution bundle from an executable.

    Parameters
    ----------
    app_executable : str
        The filename of the (existing) executable file to be bundled.
    app_filename : str or None, default : None
        The filename of the app to be generated (without .app). Defaults
        to app_executable + '.app'
    app_CFBundleDisplayName : str or None, default : None
        Specifies the display name of the bundle, visible to users and
        used by Siri.
    app_destination : str, default = 'executable'
        The destination of the .app file. Can be 'user'
        (~/Applications), 'system' (/Application) or 'executable'
        (same as app_executable).
    app_CFBundleIconFile : str or None, default : None
        The (existing) png to be used as an icon file.
    app_extension : str or None, default : None
        File extension(s) to be opened by the app.
    app_CFBundleTypeRole : str, default = 'Viewer'
        The app’s role with respect to the file extension. Can be
        'Editor', 'Viewer', 'Shell' or 'None'
    app_terminal : bool, default : False
        Always launch the app via a terminal.
    """
    move_file = False

    if app_terminal:
        """Write a new script to be bundled."""
        terminal_script = (
            "#!/bin/bash\n/usr/bin/open '" + os.path.abspath(app_executable) + "' -a Terminal"
        )
        terminal_filename = LAUNCHER_NAME
        if os.path.isfile(terminal_filename):
            print(f"{terminal_filename} already exists.")
            sys.exit(1)
        with open(terminal_filename, "w") as terminal_file:
            terminal_file.write(terminal_script)
        os.chmod(terminal_filename, 0o755)
        if app_filename is None:
            app_filename = app_executable
        app_executable = terminal_filename
        move_file = True


    app_filename = _determine_destination(app_destination, head, app_filename)




    # Add the optional icon file if requested
    if app_CFBundleIconFile is not None:
        iconsfile = app_CFBundleIconFile + ".icns"
        # generate the proper filetype from a png
        icon_img = icnsutil.IcnsFile()
        icon_img.add_media(file=app_CFBundleIconFile)
        icon_img.write(iconsfile)
        head, tail = os.path.split(iconsfile)
        # move the icon file in the correct place and update plist
        shutil.move(iconsfile, resources_dir)
        info_plist.update(CFBundleIconFile=tail)

    # Do the optional connection to a file extension
    if app_extension is not None:
        UTTypeIdentifier = app_CFBundleIdentifier + ".datafile"
        if not _is_valid_domain(UTTypeIdentifier):
            print(f"{UTTypeIdentifier} is not a valid domain name as set forth in RFC 1035.")
            sys.exit(1)

        file_type = app_CFBundleDisplayName + " datafile"

        app_CFBundleDocumentTypes = [
            {
                "LSItemContentTypes": [UTTypeIdentifier],
                "CFBundleTypeName": file_type,
                "CFBundleTypeRole": app_CFBundleTypeRole,
            }
        ]

        info_plist.update(CFBundleDocumentTypes=app_CFBundleDocumentTypes)

        app_UTExportedTypeDeclarations = [
            {
                "UTTypeIdentifier": UTTypeIdentifier,
                "UTTypeTagSpecification": {"public.filename-extension": app_extension},
                "UTTypeConformsTo": "public.data",
                "UTTypeDescription": file_type,
            }
        ]

        info_plist.update(UTExportedTypeDeclarations=app_UTExportedTypeDeclarations)

    # Write the Info.plist file


    return app_filename


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


def main():
    """Parse the command line and run the app."""
    args = _create_argparser()
    app_executable = args.executable
    if app_executable is None:
        app_executable = _create_example()
    # appname = do_the_bundle(
    #     app_executable,
    #     app_filename=args.filename,
    #     app_CFBundleDisplayName=args.CFBundleDisplayName,
    #     app_destination=args.destination,
    #     app_CFBundleIconFile=args.CFBundleIconFile,
    #     app_extension=args.extension,
    #     app_CFBundleTypeRole=args.CFBundleTypeRole,
    #     app_terminal=args.terminal,
    # )
    exec = Path(app_executable)

    vfs = ApplicationBundle(exec)
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
