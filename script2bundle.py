'''
Generate an application bundle (Mac OS) from an executable

Run the script without options to generate example.app in the same directory.
Run `script2bundle -h` for additional options

Initial version 2022 Apr 22 (Andy Thomas)
https://github.com/andythomas/script2bundle

For more information on application bundle declarations, in particular UTIs, please see:

https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_declare/understand_utis_declare.html
https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html
https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_conc/understand_utis_conc.html
'''

import argparse  # cmd line parser
import os
import plistlib
import re
import shutil  # copy files
import string
import sys  # find the python3 path
import time

import icnsutil


def do_the_bundle():
    # minimal example file
    example = '#!' + sys.executable + '''\n
# very simple Qt executable to demonstrate script2bundle
import sys

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QMessageBox
    from PyQt6.QtCore import QEvent, Qt
except ImportError:
    from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QMessageBox
    from PyQt5.QtCore import QEvent, Qt


class MyApplication (QApplication):
    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            filename = event.file()
            msg = QMessageBox()
            msg.setText(f"Opened by {filename}")
            msg.exec()
        return QApplication.event(self, event)


class MyMainWindow (QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Example")


def window():
    app = MyApplication(sys.argv)
    ex = MyMainWindow()
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    window()
'''

    def is_valid_domain(domain):
        # helper to check the validity of the Uniform Type Identifiers
        rfc1035_chars = string.ascii_lowercase + string.digits + '-.'
        if not all(char in rfc1035_chars for char in domain.lower()):
            return False
        if len(domain) > 253:
            return False
        if '--' in domain:
            return False
        if '..' in domain:
            return False
        return True

    # use a parser to allow some options
    parser = argparse.ArgumentParser(
        description='Generate an application bundle (Mac OS) from an executable.')

    # The options:
    parser.add_argument('-e', '--executable',
                        type=str,
                        help='The filename of the (existing) executable file to be bundled.')

    parser.add_argument('-f', '--filename',
                        type=str,
                        help='The filename of the app to be generated (without .app)')

    parser.add_argument('-i', '--CFBundleIconFile',
                        type=str,
                        help='The (existing) png to be used as an icon file.')

    parser.add_argument('-d', '--destination',
                        type=str,
                        choices={'user', 'system', 'executable'},
                        default='executable',
                        const='executable',
                        nargs='?',
                        help='The destination of the .app file (default: %(default)s).')

    parser.add_argument('--launch',
                        action='store_true',
                        help='Launch the app to register properly.')

    parser.add_argument('-x', '--extension',
                        type=str,
                        nargs='*',
                        help='File extension(s) to be opened by the app.')

    parser.add_argument('--CFBundleTypeRole',
                        type=str,
                        choices={'Editor', 'Viewer', 'Shell', 'None'},
                        default='Viewer',
                        const='Viewer',
                        nargs='?',
                        help='The app’s role with respect to the file extension. (default: %(default)s).')

    parser.add_argument('--CFBundleDisplayName',
                        type=str,
                        help='Specifies the display name of the bundle, visible to users and used by Siri.')

    # initiate the parsing
    args = parser.parse_args()

    # First, generate the keys and overwrite if explicit key is given
    # app_ precedes most variables to not confuse variables, arguments and plist keys

    # CFBundleExecutable: Name of the bundle’s executable file
    app_executable = args.executable
    if app_executable is None:
        app_executable = 'example'
        with open(app_executable, 'w') as examplefile:
            examplefile.write(example)
        os.chmod(app_executable, 0o755)
    head, tail = os.path.split(app_executable)
    # Strip 'problematic' characters
    move_file = False
    clean_executable = re.sub(r'[^A-Za-z0-9\.-]+', '', tail)
    if clean_executable != tail:
        print(
            f'Warning: Stripping characters from filename and duplicating executable ({clean_executable}).')
        clean_filename = os.path.join(head, clean_executable)
        shutil.copy2(app_executable, clean_filename)
        app_executable = clean_filename
        move_file = True

    # start the plist file with the name of the executable
    info_plist = dict(CFBundleExecutable=clean_executable)

    # The bundle needs a filename and a name to be displayed
    app_filename = args.filename
    if app_filename is None:
        app_filename = clean_executable
    app_CFBundleDisplayName = app_filename
    app_filename = app_filename + '.app'
    if args.CFBundleDisplayName is not None:
        app_CFBundleDisplayName = args.CFBundleDisplayName
    info_plist.update(CFBundleDisplayName=app_CFBundleDisplayName)

    # A bundle identifier is strongly recommended
    app_CFBundleIdentifier = 'org.script2bundle.' + clean_executable
    if not is_valid_domain(app_CFBundleIdentifier):
        print(
            f'{app_CFBundleIdentifier} is not a valid domain name as set forth in RFC 1035.')
        sys.exit(1)
    info_plist.update(CFBundleIdentifier=app_CFBundleIdentifier)

    # It is an application (not, e.g., a framework)
    info_plist.update(CFBundlePackageType="APPL")

    # Determine the destination of the .app file
    if args.destination == 'executable':
        app_filename = os.path.join(head, app_filename)
    elif args.destination == 'system':
        app_filename = os.path.join('/Applications', app_filename)
    elif args.destination == 'user':
        app_filename = os.path.join(os.path.expanduser(
            "~"), 'Applications', app_filename)

    # Delete possible old version
    if os.path.isdir(app_filename):
        shutil.rmtree(app_filename)

    # Generate the directory framework
    contents_dir = os.path.join(app_filename, 'Contents')
    macos_dir = os.path.join(contents_dir, 'MacOS')
    resources_dir = os.path.join(contents_dir, 'Resources')
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # copy the executable in the correct place
    if move_file:
        shutil.move(app_executable, macos_dir)
    else:
        shutil.copy(app_executable, macos_dir)

    # Add the optional icon file if requested
    if args.CFBundleIconFile is not None:
        app_CFBundleIconFile = args.CFBundleIconFile + '.icns'
        # generate the proper filetype from a png
        icon_img = icnsutil.IcnsFile()
        icon_img.add_media(file=args.CFBundleIconFile)
        icon_img.write(app_CFBundleIconFile)
        head, tail = os.path.split(app_CFBundleIconFile)
        # copy the icon file in the correct place and update plist
        shutil.copy(app_CFBundleIconFile, resources_dir)
        info_plist.update(CFBundleIconFile=tail)

    # Do the optional connection to a file extension
    if args.extension is not None:
        UTTypeIdentifier = app_CFBundleIdentifier + '.datafile'
        if not is_valid_domain(UTTypeIdentifier):
            print(
                f'{UTTypeIdentifier} is not a valid domain name as set forth in RFC 1035.')
            sys.exit(1)

        file_type = app_CFBundleDisplayName + ' datafile'

        app_CFBundleDocumentTypes = [{'LSItemContentTypes': [UTTypeIdentifier],
                                      'CFBundleTypeName': file_type,
                                      'CFBundleTypeRole': args.CFBundleTypeRole}]

        info_plist.update(CFBundleDocumentTypes=app_CFBundleDocumentTypes)

        app_UTExportedTypeDeclarations = [{'UTTypeIdentifier': UTTypeIdentifier,
                                           'UTTypeTagSpecification': {'public.filename-extension': args.extension},
                                           'UTTypeConformsTo': 'public.data',
                                           'UTTypeDescription': file_type
                                           }]

        info_plist.update(
            UTExportedTypeDeclarations=app_UTExportedTypeDeclarations)

    # Write the Info.plist file
    info_filename = os.path.join(contents_dir, 'Info.plist')
    with open(info_filename, 'wb') as infofile:
        plistlib.dump(info_plist, infofile)

    # Launch if requested; sleep required to allow the system to recognize the new app
    if args.launch:
        time.sleep(2)
        launch_cmd = 'Open ' + '"' + app_filename + '"'
        print(launch_cmd)
        os.system(launch_cmd)


if __name__ == '__main__':
    do_the_bundle()
