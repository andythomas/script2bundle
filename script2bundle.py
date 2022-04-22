# Generate an application bundle (Mac OS) from an executable
#
# Initial version 2022 Apr 22 (Andy Thomas)
#
#

import argparse  # cmd line parser
import os  # mkdir and such
# import the required packages
import plistlib
import shutil  # copy files
import sys  # find the python3 path

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
parser.add_argument('-e', '--executable', type=str,
                    help='The existing executable.')

# initiate the parsing
args = parser.parse_args()

# use the example if no file is given
executable = args.executable

if executable == None:
    executable = 'example'
    with open(executable, 'w') as examplefile:
        examplefile.write(example)
    os.chmod(executable, 0o755)

# First, generate the directory framework
app_name = executable + '.app'
contents_dir = os.path.join(app_name, 'Contents')
macos_dir = os.path.join(contents_dir, 'MacOS')
os.makedirs(macos_dir)

# copy the executable in the correct place
shutil.copy(executable, macos_dir)

# add the Info.plist file
info_plist = dict(CFBundleExecutable=executable)
info_filename = os.path.join(contents_dir, 'Info.plist')
with open(info_filename, 'wb') as infofile:
    plistlib.dump(info_plist, infofile)
