class PlaysoundException(Exception):
    pass

def _canonicalizePath(path):
    """
    Support passing in a pathlib.Path-like object by converting to str.
    """
    import sys
    if sys.version_info[0] >= 3:
        return str(path)
    else:
        # On earlier Python versions, str is a byte string, so attempting to
        # convert a unicode string to str will fail. Leave it alone in this case.
        return path

def _playsoundWin(sound, block = True):
    '''
    Utilizes windll.winmm. Tested and known to work with MP3 and WAVE on
    Windows 7 with Python 2.7. Probably works with more file formats.
    Probably works on Windows XP thru Windows 10. Probably works with all
    versions of Python.

    Inspired by (but not copied from) Michael Gundlach <gundlach@gmail.com>'s mp3play:
    https://github.com/michaelgundlach/mp3play

    I never would have tried using windll.winmm without seeing his code.
    '''
    from ctypes import c_buffer, windll
    from time   import sleep

    sound = _canonicalizePath(sound)

    def winCommand(*command):
        bufLen = 600
        buf = c_buffer(bufLen)
        command = ' '.join(command).encode('utf-16')
        errorCode = int(windll.winmm.mciSendStringW(command, buf, bufLen - 1, 0))  # use widestring version of the function
        if errorCode:
            errorBuffer = c_buffer(bufLen)
            windll.winmm.mciGetErrorStringW(errorCode, errorBuffer, bufLen - 1)  # use widestring version of the function
            exceptionMessage = ('\n    Error ' + str(errorCode) + ' for command:'
                                '\n        ' + command.decode('utf-16') +
                                '\n    ' + errorBuffer.raw.decode('utf-16').rstrip('\0'))
            raise PlaysoundException(exceptionMessage)
        return buf.value

    try:
        winCommand(u'open "{}"'.format(sound))
        durationInSeconds = winCommand(u'status "{}" length'.format(sound))
        winCommand(u'play "{}"'.format(sound))

        if block:
            sleep(float(durationInSeconds))
    finally:
        try:
            winCommand(u'close "{}"'.format(sound))
        except PlaysoundException:
            # If it fails, there's nothing more that can be done...
            pass

def _handlePathOSX(sound):
    sound = _canonicalizePath(sound)

    if '://' not in sound:
        if not sound.startswith('/'):
            from os import getcwd
            sound = getcwd() + '/' + sound
        sound = 'file://' + sound

    try:
        # Don't double-encode it.
        sound.encode('ascii')
        return sound.replace(' ', '%20')
    except UnicodeEncodeError:
        try:
            from urllib.parse import quote  # Try the Python 3 import first...
        except ImportError:
            from urllib import quote  # Try using the Python 2 import before giving up entirely...

        parts = sound.split('://', 1)
        return parts[0] + '://' + quote(parts[1].encode('utf-8')).replace(' ', '%20')


def _playsoundOSX(sound, block = True):
    '''
    Utilizes AppKit.NSSound. Tested and known to work with MP3 and WAVE on
    OS X 10.11 with Python 2.7. Probably works with anything QuickTime supports.
    Probably works on OS X 10.5 and newer. Probably works with all versions of
    Python.

    Inspired by (but not copied from) Aaron's Stack Overflow answer here:
    http://stackoverflow.com/a/34568298/901641

    I never would have tried using AppKit.NSSound without seeing his code.
    '''
    try:
        from AppKit import NSSound
    except ImportError:
        print("playsound could not find a copy of AppKit - falling back to using macOS's system copy.")
        sys.path.append('/System/Library/Frameworks/Python.framework/Versions/2.7/Extras/lib/python/PyObjC')
        from AppKit import NSSound

    from Foundation import NSURL
    from time       import sleep

    sound = _handlePathOSX(sound)
    url   = NSURL.URLWithString_(sound)
    if not url:
        raise PlaysoundException('Cannot find a sound with filename: ' + sound)

    for i in range(5):
        nssound = NSSound.alloc().initWithContentsOfURL_byReference_(url, True)
        if nssound:
            break
        else:
            print('Failed to load sound, although url was good... ' + sound)
    else:
        raise PlaysoundException('Could not load sound with filename, although URL was good... ' + sound)
    nssound.play()

    if block:
        sleep(nssound.duration())

def _playsoundNix(sound, block = True):
    """Play a sound using GStreamer.

    Inspired by this:
    https://gstreamer.freedesktop.org/documentation/tutorials/playback/playbin-usage.html
    """
    sound = _canonicalizePath(sound)

    if not block:
        raise NotImplementedError(
            "block=False cannot be used on this platform yet")

    # pathname2url escapes non-URL-safe characters
    import os
    try:
        from urllib.request import pathname2url
    except ImportError:
        # python 2
        from urllib import pathname2url

    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst

    Gst.init(None)

    playbin = Gst.ElementFactory.make('playbin', 'playbin')
    if sound.startswith(('http://', 'https://')):
        playbin.props.uri = sound
    else:
        playbin.props.uri = 'file://' + pathname2url(os.path.abspath(sound))

    set_result = playbin.set_state(Gst.State.PLAYING)
    if set_result != Gst.StateChangeReturn.ASYNC:
        raise PlaysoundException(
            "playbin.set_state returned " + repr(set_result))

    # FIXME: use some other bus method than poll() with block=False
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bus.html
    bus = playbin.get_bus()
    try:
        bus.poll(Gst.MessageType.EOS, Gst.CLOCK_TIME_NONE)
    finally:
        playbin.set_state(Gst.State.NULL)

def _playsoundAnotherPython(otherPython, sound, block = True):
    '''
    Mostly written so that when this is run on python3 on macOS, it can invoke
    python2 on macOS... but maybe this idea could be useful on linux, too.
    '''
    from inspect    import getsourcefile
    from os.path    import abspath, exists
    from subprocess import check_call
    from threading  import Thread

    sound = _canonicalizePath(sound)

    class PropogatingThread(Thread):
        def run(self):
            self.exc = None
            try:
                self.ret = self._target(*self._args, **self._kwargs)
            except BaseException as e:
                self.exc = e

        def join(self, timeout = None):
            super().join(timeout)
            if self.exc:
                raise self.exc
            return self.ret

    # Check if the file exists...
    if not exists(abspath(sound)):
        raise PlaysoundException('Cannot find a sound with filename: ' + sound)

    playsoundPath = abspath(getsourcefile(lambda: 0))
    t = PropogatingThread(target = lambda: check_call([otherPython, playsoundPath, _handlePathOSX(sound)]))
    t.start()
    if block:
        t.join()

from platform import system
system = system()

if system == 'Windows':
    playsound = _playsoundWin
elif system == 'Darwin':
    playsound = _playsoundOSX
    import sys
    if sys.version_info[0] > 2:
        try:
            from AppKit import NSSound
        except ImportError:
            print("playsound is relying on a python 2 subprocess. Please use `pip3 install PyObjC` if you want playsound to run more efficiently.")
            playsound = lambda sound, block = True: _playsoundAnotherPython('/System/Library/Frameworks/Python.framework/Versions/2.7/bin/python', sound, block)
else:
    playsound = _playsoundNix

del system

if __name__ == '__main__':
    # block is always True if you choose to run this from the command line.
    from sys import argv
    playsound(argv[1])
