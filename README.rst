playsound
=========
*Pure Python, cross platform, single function module with no dependencies for playing sounds.*

Forked from TaylorSMarks/playsound - https://github.com/TaylorSMarks/playsound

Quick Start
-----------
Once you've installed, you can really quickly verified that it works with just this:

.. code-block:: python

    >>> from playsound import playsound
    >>> playsound('/path/to/a/sound/file/you/want/to/play.mp3') 

Documentation
-------------
The playsound module contains only one thing - the function (also named) playsound.

It requires one argument - the path to the file with the sound you'd like to play. This may be a local file, or a URL.

There's an optional second argument, block, which is set to True by default. Setting it to False makes the function run asynchronously.

On Windows, uses windll.winmm. WAVE and MP3 have been tested and are known to work. Other file formats may work as well.

On OS X, uses AppKit.NSSound. WAVE and MP3 have been tested and are known to work. In general, anything QuickTime can play, playsound should be able to play, for OS X.

On Linux, uses ossaudiodev. I don't have a machine with Linux, so this hasn't been tested at all. Theoretically, it plays WAVE files. Any other file format working would surprise me. The block argument is not used on Linux - I do not know whether the function blocks on Linux or not.

Requirements
------------
I've tested playsound it with Python 3.4 on Windows 7.

Copyright
---------
This software is Copyright (c) 2016 Taylor Marks <taylor@marksfam.com>.

See the bundled LICENSE file for more information.
