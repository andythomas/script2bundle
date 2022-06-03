# Generate an application bundle (Mac OS) from an executable
#
# Initial version 2022 Apr 22 (Andy Thomas)
#
#

import argparse  # cmd line parser
import os
import plistlib
import shutil  # copy files
import sys  # find the python3 path

import icnsutil

# minimal example file
example = '#!' + sys.executable + '''
# very simple qt5 executable to demonstrate script2bundle

import sys
from PyQt5.QtWidgets import QApplication, QWidget

def window():
   app = QApplication(sys.argv)
   widget = QWidget()

   widget.setWindowTitle("Simple script2bundle example")
   widget.show()
   sys.exit(app.exec_())

if __name__ == '__main__':
   window()
'''

# use a parser to allow some options
parser = argparse.ArgumentParser(
    description='Generate an application bundle (Mac OS) from an executable.')

# The options:
parser.add_argument('-e', '--executable',
                    type=str,
                    help='The existing executable file.')

parser.add_argument('-i', '--icon',
                    type=str,
                    help='The existing png icon file.')

parser.add_argument('-d', '--destination',
                    type=str,
                    choices={'user', 'system', 'executable'},
                    default='executable',
                    const='executable',
                    nargs='?',
                    help='The destination of the .app file (default: %(default)s).')

parser.add_argument('-n', '--name', type=str,
                    help='The name of the app (default: EXECUTABLE.app).')

# initiate the parsing
args = parser.parse_args()

# use the example if no file is given
executable = args.executable
if (executable == None):
    executable = 'example'
    with open(executable, 'w') as examplefile:
        examplefile.write(example)
    os.chmod(executable, 0o755)

# add the executable and the name to the Info.plist file
name = args.name
head, tail = os.path.split(executable)
info_plist = dict(CFBundleExecutable=tail)
if (name == None):
    name = tail
else:
    name = args.name
info_plist.update(CFBundleName=name)

# Determine the destination of the .app file
head, tail = os.path.split(executable)
app_name = name + '.app'
if (args.destination=='executable'):
    app_name = os.path.join(head, app_name)
elif (args.destination=='system'):
    app_name = os.path.join('/Applications', app_name)
elif (args.destination=='user'):
    app_name = os.path.join(os.path.expanduser("~"), 'Applications', app_name)

# Generate the directory framework
contents_dir = os.path.join(app_name, 'Contents')
macos_dir = os.path.join(contents_dir, 'MacOS')
resources_dir = os.path.join(contents_dir, 'Resources')
os.makedirs(macos_dir, exist_ok=True)
os.makedirs(resources_dir, exist_ok=True)

# copy the executable in the correct place
shutil.copy(executable, macos_dir)

# deal with the optional icon file
if (args.icon != None):
    icns_file = args.icon + '.icns'
    icon_img = icnsutil.IcnsFile()
    icon_img.add_media(file=args.icon)
    icon_img.write(icns_file)
    head, tail = os.path.split(icns_file)
    info_plist.update(CFBundleIconFile=tail)
    # copy the icon file in the correct place
    shutil.copy(icns_file, resources_dir)

# write the Info.plist file
info_filename = os.path.join(contents_dir, 'Info.plist')
with open(info_filename, 'wb') as infofile:
    plistlib.dump(info_plist, infofile)
