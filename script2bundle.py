# Generate an application bundle (Mac OS) from an executable
#
# Initial version 2022 Apr 22 (Andy Thomas)
# https://github.com/andythomas/script2bundle
#
# For more information on application bundle declarations, in particular UTIs, please see:
#
# https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_declare/understand_utis_declare.html
# https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html
# https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis_conc/understand_utis_conc.html

import argparse  # cmd line parser
import os
import plistlib
import shutil  # copy files
import sys  # find the python3 path
import string 

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

 
rfc1035_chars = string.ascii_lowercase + string.digits + '-.'

def is_valid_domain(domain):
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

parser.add_argument('-x', '--extension',
                    type=str,
                    help='A file extension to be opened by the app.')

parser.add_argument('--BundleTypeRole',
                    type=str,
                    choices={'Editor', 'Viewer', 'Shell', 'None'},
                    default='Viewer',
                    const='Viewer',
                    nargs='?',
                    help='The app’s role with respect to the file extension. (default: %(default)s).')

parser.add_argument('--launch', 
                     action='store_true',
                     help='Launch the app to register properly.')

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
bundle_identifier = 'org.script2bundle.' + name 
info_plist.update(CFBundleIdentifier=bundle_identifier)
info_plist.update(CFBundleName=name)

# It is an application (not, e.g., a framework)
info_plist.update(CFBundlePackageType="APPL")

# Determine the destination of the .app file
head, tail = os.path.split(executable)
app_name = name + '.app'
if (args.destination=='executable'):
    app_name = os.path.join(head, app_name)
elif (args.destination=='system'):
    app_name = os.path.join('/Applications', app_name)
elif (args.destination=='user'):
    app_name = os.path.join(os.path.expanduser("~"), 'Applications', app_name)

# Delete possible old version 
if os.path.isdir(app_name):
    shutil.rmtree(app_name)

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


# do the optional connection to a file extension
if (args.extension != None):
    UTTypeIdentifier = bundle_identifier + '.' + args.extension
    if not is_valid_domain(UTTypeIdentifier):
        print (f'{UTTypeIdentifier} is not a valid domain name as set forth in RFC 1035.')
        sys.exit()

    file_type = name + ' ' + args.extension + ' file'

    document_types = [{'LSItemContentTypes': [bundle_identifier + '.' + args.extension],
                        'CFBundleTypeName': file_type,
                        'CFBundleTypeRole': args.BundleTypeRole}]

    info_plist.update(CFBundleDocumentTypes = document_types)


    extension_info = [{'UTTypeIdentifier': UTTypeIdentifier,
          'UTTypeTagSpecification': {'public.filename-extension': [args.extension]},
          'UTTypeConformsTo': 'public.data',
          'UTTypeDescription': file_type
          }]

    info_plist.update(UTExportedTypeDeclarations = extension_info)

# write the Info.plist file
info_filename = os.path.join(contents_dir, 'Info.plist')
with open(info_filename, 'wb') as infofile:
    plistlib.dump(info_plist, infofile)

# launch if requested
if (args.launch):
    launch_cmd = 'Open ' + app_name
    print(launch_cmd)
    os.system(launch_cmd)
