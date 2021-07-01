# -*- coding: utf-8 -*-=

from os      import listdir
from os.path import join
from sys     import version
from time    import time

from playsound import playsound, PlaysoundException
import unittest 

durationMarginLow  = 0.2
duratingMarginHigh = 1.5

class PlaysoundTests(unittest.TestCase):
    def helper(self, file, approximateDuration, block = True):
        startTime = time()
        playsound(join('test_media', file), block = block)
        duration = time() - startTime
        self.assertTrue(approximateDuration - durationMarginLow <= duration <= approximateDuration + duratingMarginHigh, 'File "{}" took an unexpected amount of time: {}'.format(file, duration))

    testBlockingASCII_MP3 = lambda self: self.helper('Damonte.mp3', 1.1)
    testBlockingASCII_WAV = lambda self: self.helper('Sound4.wav',  1.3)
    testBlockingCYRIL_WAV = lambda self: self.helper(u'Буква_Я.wav', 1.6)
    testBlockingSPACE_MP3 = lambda self: self.helper('Discovery - Go at throttle up (2).mp3', 2.3)
    testNonBlockingRepeat = lambda self: self.helper(u'Буква_Я.wav', 0.0, block = False)

    def testMissing(self):
        with self.assertRaises(PlaysoundException) as context:
            playsound('notarealfile.wav')

            message = context.exception.message.lower()

            for sub in ['cannot', 'find', 'filename', 'notarealfile.wav']:
                self.assertIn(sub, message.lower(), '"{}" was expected in the exception message, but instead got: "{}"'.format(sub, message))

if __name__ == '__main__':
    print(version)
    unittest.main()