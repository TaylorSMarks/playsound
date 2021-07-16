# -*- coding: utf-8 -*-=

# On Mac, ignoring the issue of not having AppKit if it's not the stock version of Python, it's working for all but Cyrllic...
# Just need to find out how to properly escape the name so that it works...

from os       import environ, listdir
from os.path  import join
from platform import system
from sys      import version
from time     import time

system = system()
isTravis = environ.get('TRAVIS', 'false') == 'true'

if isTravis and system == 'Windows':
    try:
        from unittest.mock import patch
    except ImportError:
        try:
            from pip import main as pipmain
        except ImportError:
            from pip._internal import main as pipmain

        # Before python 3.3 (including python 2.7.20 and earlier),
        # mocking/patching wasn't part of the standard library. So you need
        # to get those via pip. You specifically need version 2.0.0 - newer
        # versions require python 3.3, utterly defeating the purpose of making
        # the library available on pypi.
        pipmain(['install', 'mock==2.0.0'])
        from mock import patch

from playsound import playsound, PlaysoundException
import unittest

durationMarginLow  = 0.3
duratingMarginHigh = 2.0
sawClose = False

def mockMciSendStringW(command, buf, bufLen, bufStart):
    if command.startswith('close '.encode('utf-16')):
        global sawClose
        sawClose = True
    buf.value = b'2.1' # This is what it'll get for the duration in seconds for the file - it's close enough for all 4 of the test files.
    return 0

class PlaysoundTests(unittest.TestCase):
    def get_full_path(self, file):
        path = join('test_media', file)
        print(path.encode('utf-8'))
        return path

    def helper(self, file, approximateDuration, block = True):
        startTime = time()
        path = self.get_full_path(file)

        if isTravis and system == 'Windows':
            with patch('ctypes.windll.winmm.mciSendStringW', side_effect = mockMciSendStringW):
                global sawClose
                sawClose = False
                playsound(path, block = block)
                self.assertTrue(sawClose)
        else:
            playsound(path, block = block)
        duration = time() - startTime
        self.assertTrue(approximateDuration - durationMarginLow <= duration <= approximateDuration + duratingMarginHigh, 'File "{}" took an unexpected amount of time: {}'.format(file.encode('utf-8'), duration))

    testBlockingASCII_MP3 = lambda self: self.helper('Damonte.mp3', 1.1)
    testBlockingASCII_WAV = lambda self: self.helper('Sound4.wav',  1.3)
    testBlockingCYRIL_WAV = lambda self: self.helper(u'Буква_Я.wav', 1.6)
    testBlockingSPACE_MP3 = lambda self: self.helper('Discovery - Go at throttle up (2).mp3', 2.3)
    testNonBlockingRepeat = lambda self: self.helper(u'Буква_Я.wav', 0.0, block = False)

    def testMissing(self):
        with self.assertRaises(PlaysoundException) as context:
            playsound(self.get_full_path('notarealfile.wav'))

            message = context.exception.message.lower()

            for sub in ['cannot', 'find', 'filename', 'notarealfile.wav']:
                self.assertIn(sub, message.lower(), '"{}" was expected in the exception message, but instead got: "{}"'.format(sub, message))

# Run the same tests as above, but pass pathlib.Path objects to playsound instead of strings.
try:
    from pathlib import Path
except ImportError:
    pass
else:
    class PlaysoundTestsWithPathlib(PlaysoundTests):
        def get_full_path(self, file):
            return Path('test_media') / file

if __name__ == '__main__':
    print(version)
    import sys
    print(sys.executable)
    print(sys.path)
    unittest.main()
