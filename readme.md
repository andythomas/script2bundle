## Short description

script2bundle is a command line Python script that bundles an executable, e.g. another (Python) script, into a MacOS application bundle. Compared to [py2app](https://py2app.readthedocs.io/en/latest/), this is a minmal wrapper and allows editable installs (PEP660), but the application bundle will only work on the computer it was created.  Script2bundle is of limited use for command line scripts, where [Platypus](https://sveinbjorn.org/platypus) might be a better option. It is intended to be used for GUI (e.g. Qt) executables.  

## How to use
Simply run the script without any options to generate an example file. Afterwards, you will find example.app in the same folder.

## General options:
- -e The filename of the (existing) executable file to be bundled.
- -f The filename of the app to be generated (without .app).
- -i The (existing) png file to be used to generate an icon.
- -d The destination of the .app file:  user (~/Applications), system (/Applications) or executable (same as -e).
- --launch Launch the app to register properly.

## Options to connect a file extension
- -x An (app specific!) file extension to be opened by the app.
- --CFBundleTypeRole The app’s role with respect to the file extension. Can be Editor, Viewer, Shell or None. 

## Additional modifier options:
The information above will be used to generate reasonable entries in `Info.plist`. However, these entries can be directly modified using the corresponding argument named according to the [Apple documentation](https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html). The implemented options are:

- --CFBundleDisplayName Specifies the display name of the bundle, visible to users and used by Siri.

## Notes
Due to the internal structure of some entries, they have to be formatted according to [RFC 1035](https://datatracker.ietf.org/doc/html/rfc1035). If neccessary, an error is raised by script2bundle, e.g. caused by two subsequent dashes in the filename. 