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
from typing import Optional

import icnsutil

LAUNCHER_NAME = "terminallauncher"


def _is_valid_domain(domain):
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

    # CFBundleExecutable: Name of the bundle’s executable file
    head, tail = os.path.split(app_executable)
    # Strip 'problematic' characters
    clean_executable = re.sub(r"[^A-Za-z0-9\.-]+", "", tail)
    if clean_executable != tail:
        print(
            f"Warning: Stripping characters from filename and duplicating executable ({clean_executable})."
        )
        clean_filename = os.path.join(head, clean_executable)
        shutil.copy2(app_executable, clean_filename)
        app_executable = clean_filename
        move_file = True
    # start the plist file with the name of the executable
    info_plist = dict(CFBundleExecutable=clean_executable)

    # The bundle needs a filename and a name to be displayed
    if app_filename is None:
        app_filename = clean_executable
    app_filename = app_filename + ".app"

    if app_CFBundleDisplayName is None:
        app_CFBundleDisplayName = app_filename
    info_plist.update(CFBundleDisplayName=app_CFBundleDisplayName)

    # A bundle identifier is strongly recommended
    app_CFBundleIdentifier = "org.script2bundle." + clean_executable
    if not _is_valid_domain(app_CFBundleIdentifier):
        print(f"{app_CFBundleIdentifier} is not a valid domain name as set forth in RFC 1035.")
        sys.exit(1)
    info_plist.update(CFBundleIdentifier=app_CFBundleIdentifier)

    # It is an application (not, e.g., a framework)
    info_plist.update(CFBundlePackageType="APPL")

    app_filename = _determine_destination(app_destination, head, app_filename)

    # Delete possible old version
    if os.path.isdir(app_filename):
        shutil.rmtree(app_filename)

    # Generate the directory framework
    contents_dir = os.path.join(app_filename, "Contents")
    macos_dir = os.path.join(contents_dir, "MacOS")
    resources_dir = os.path.join(contents_dir, "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # copy the executable in the correct place
    if move_file:
        shutil.move(app_executable, macos_dir)
    else:
        shutil.copy(app_executable, macos_dir)

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
    info_filename = os.path.join(contents_dir, "Info.plist")
    with open(info_filename, "wb") as infofile:
        plistlib.dump(info_plist, infofile)

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
    appname = do_the_bundle(
        app_executable,
        app_filename=args.filename,
        app_CFBundleDisplayName=args.CFBundleDisplayName,
        app_destination=args.destination,
        app_CFBundleIconFile=args.CFBundleIconFile,
        app_extension=args.extension,
        app_CFBundleTypeRole=args.CFBundleTypeRole,
        app_terminal=args.terminal,
    )
    # Launch if requested;
    # sleep required to allow the system to recognize the new app
    if args.launch:
        time.sleep(2)
        launch_cmd = f'Open "{appname}"'
        print(launch_cmd)
        os.system(launch_cmd)


if __name__ == "__main__":
    main()
