## Short description

script2bundle is a command line Python script that bundles an executable, e.g. another Python script, into a MacOS application bundle. Compared to py2app, this is a minmal wrapper and allows editable installs (PEP660), but the application bundle will (most likely) only work on the computer it was created.  

## How to use
Simply run the script without any options to generate an example file. Afterwards, you will find example.app in the same folder.

## Available options:
- -e The filename of the (existing) executable file to be bundled.
- -f The filename of the app to be generated (without .app).
- -i The (existing) png to be used as an icon file.
- -d The destination of the .app file:  user (~/Applications) or system (/Applications) or executable (same as -e).
- --launch Launch the app to register properly.
- -x An (app specific) file extension to be opened by the app.

## Additional modifier options:
The information above will be used to generate reasonable entries in `Info.plist`. However, these entries can be directly modified using the corresponding argument named according to the [Apple documentation](https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html). 

- --CFBundleTypeRole The app’s role with respect to the file extension. Can be Editor, Viewer, Shell or None. 
- --CFBundleDisplayName Specifies the display name of the bundle, visible to users and used by Siri.
- --CFBundleIdentifier An identifier string that specifies the bundle (in reverse DNS format).

# Notes
Due to the internal structure of some entries, they have to be formatted according to [RFC 1035](https://datatracker.ietf.org/doc/html/rfc1035). If neccessary, an error is raised by script2bundle, e.g. caused by an underscore in the filename. 