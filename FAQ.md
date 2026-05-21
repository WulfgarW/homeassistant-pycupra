# PyCupra - A Home Assistant custom component using the pycupra library to add integration for your Cupra or Seat car 


# Scope of this document
This faq document shall help PyCupra users to solve problems or issues they are experiencing.
You are welcome to contribute to this document.


# Table of contents

## How to contribute to the faq document

## Login problems

## Some technical background information



# Content

## How to contribute to the faq document

You can contribute to this document by sending your suggestions to the mail address you find under https://github.com/WulfgarW.
(Or for users that are familiar with the pull request procedure in github, you can fork homeassistant-pycupra, edit FAQ.md and then create a pull request.)

## Login problems

### Terms and condition error

Open seatid.vwgroup.io or cupraid.vwgroup.ioin your browser and login. Change 'Language' to English and 'Country' to United Kingdom. Then log off und relogin. 
If you get a page asking you to consent to terms and condition, then agree to it. After that, you can change language and country back.
PyCupra should work now.

### Marketing consent error

Open seatid.vwgroup.io or cupraid.vwgroup.io in your browser and login. Change 'Language' to English and 'Country' to United Kingdom. Then log off und relogin. 
If you get a page asking if you consent to marketing, then answer it (agree and disagree should both work). After that, you can change language and country back.
PyCupra should work now.

### Account locked error

An account locked error means, that there have been repeated login attempts with wrong credentials and the portal has locked the account temporarily. Please don't do any reboots of HA or reloads of the PyCupra devices. Wait, until the locking period has passed and then try to login via cupraid.vwgroup.io/seatid.vwgroup.io or via the mobile phone app first. If that works, then try to reload your PyCupra vehicle.

## Some technical background information

### What's homeassistant-pycupra? What's pycupra?

The python package 'pycupra' contains the program code that connects to the Cupra/Seat API, communicates with the API (e.g. reading information about your vehicle) and present the information gathered from the API as vehicle instruments. The 'pycupra' package is not restricted to home assistant and can also be used directly.
The package 'homeassistant-pycupra' acts as the interface between the 'pycupra' package and home assistant, making the vehicle instruments, that the pycupra package provides available as entites in home assistant.
So to use PyCupra in home assistant, you install the homeassistant-pycupra package in home assistant. The 'pycupra' package, that is required as well, is installed automatically by home assistant.

### How do I know, which version of homeassistant-pycupra and pycupra I am using?

The information, which version of homeassistant-pycupra you are currently using, can be found in HACS. Open 'HACS' in the UI, search the row for 'PyCupra' and then click on the three vertical points on the right side of this row. In the submenu choose 'Show details'.
If you want to know, which version of the 'pycupra' package is used, then open the system log (the raw log) and search for 'pycupra'. You will find a log line containing 'Init PyCupra library, version' and this line shows the version number of the pycupra package.


