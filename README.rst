playsound
=========
*Pure Python, cross platform, single function module with no dependencies for playing sounds.*

Installation
------------
Install via pip:

.. code-block:: bash

    $ pip install playsound

Done.

If you insist on the (slightly) harder way of installing, from source,
you know how to do it already and don't need my help.

The latest version of the source code can be found at:
https://github.com/TaylorSMarks/playsound

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

On Linux, uses GStreamer. Known to work on Ubuntu 14.04 and ElementaryOS Loki. I expect any Linux distro with a standard gnome desktop experience should work.

If you'd like other Linux distros (or any other OS) to work, submit a PR adding in support for it, but please make sure it passes the tests (see below).

Testing
-------
Playsound includes a small set of tests - if you're making a PR, please ensure that you have no regressions and all the tests pass on your local system.
Also make sure that Travis-CI, which runs these tests against Windows Server 2016, macOS 10.11 (El Capitan, 2015) and 11.3 (Big Sur, 2020), Ubuntu 14 (Trusty), and Ubuntu 18 (Bionic), for both Python 2.7 and 3.9, fully passes.
You can check the Travis-CI status for Playsound here: https://travis-ci.com/github/TaylorSMarks/playsound/builds

Copyright
---------
This software is Copyright (c) 2021 Taylor Marks <taylor@marksfam.com>.

See the bundled LICENSE file for more information.
