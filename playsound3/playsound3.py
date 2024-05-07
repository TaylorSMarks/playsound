import atexit
import ctypes
import logging
import os
import platform
import ssl
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from threading import Thread
from typing import Callable, Dict, Union

import certifi

logging.basicConfig(level=os.environ.get("LOGLEVEL", "WARNING"))
logger = logging.getLogger(__name__)

_PLAYSOUND_DEFAULT_BACKEND: Callable[[str], None]
_SYSTEM = platform.system()
_DOWNLOAD_CACHE = dict()


class PlaysoundException(Exception):
    pass


def playsound(sound, block: bool = True, backend: Union[str, None] = None) -> None:
    """Play a sound file using an audio backend availabile in your system.

    Args:
        sound: Path or URL to the sound file. Can be a string or pathlib.Path.
        block: If True, the function will block execution until the sound finishes playing.
               If False, sound will play in a background thread.
        backend: Name of the audio backend to use. If None, the best available backend will be selected.
    """
    if backend is None:
        _play = _PLAYSOUND_DEFAULT_BACKEND
    elif backend in _BACKEND_MAPPING:
        _play = _BACKEND_MAPPING[backend]
    else:
        raise PlaysoundException(f"Unknown backend: {backend}. Available backends: {', '.join(AVAILABLE_BACKENDS)}")

    path = _prepare_path(sound)
    if block:
        _play(path)
    else:
        Thread(target=_play, args=(path,), daemon=True).start()


def _download_sound_from_web(link, destination):
    # Identifies itself as a browser to avoid HTTP 403 errors
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
    request = urllib.request.Request(link, headers=headers)
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, context=context) as response, open(destination, "wb") as out_file:
        out_file.write(response.read())


def _prepare_path(sound) -> str:
    if sound.startswith(("http://", "https://")):
        # To play file from URL, we download the file first to a temporary location and cache it
        if sound not in _DOWNLOAD_CACHE:
            with tempfile.NamedTemporaryFile(delete=False, prefix="playsound3-") as f:
                _download_sound_from_web(sound, f.name)
                _DOWNLOAD_CACHE[sound] = f.name
        sound = _DOWNLOAD_CACHE[sound]

    path = Path(sound)

    if not path.exists():
        raise PlaysoundException(f"File not found: {sound}")
    return path.absolute().as_posix()


def _select_linux_backend() -> Callable[[str], None]:
    """Select the best available audio backend for Linux systems."""
    logging.info("Selecting the best available audio backend for Linux systems.")

    try:
        subprocess.run(["gst-play-1.0", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logging.info("Using gst-play-1.0 as the audio backend.")
        return _playsound_gst_play
    except FileNotFoundError:
        pass

    try:
        subprocess.run(["ffplay", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logging.info("Using ffplay as the audio backend.")
        return _playsound_ffplay
    except FileNotFoundError:
        pass

    try:
        subprocess.run(["aplay", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["mpg123", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logging.info("Using aplay and mpg123 as the audio backend.")
        return _playsound_alsa
    except FileNotFoundError:
        pass

    logging.info("No suitable audio backend found.")
    raise PlaysoundException("No suitable audio backend found. Install gstreamer or ffmpeg!")


def _playsound_gst_play(sound: str) -> None:
    """Uses gst-play-1.0 utility (built-in Linux)."""
    logger.debug("gst-play-1.0: starting playing %s", sound)
    try:
        subprocess.run(["gst-play-1.0", "--no-interactive", "--quiet", sound], check=True)
    except subprocess.CalledProcessError as e:
        raise PlaysoundException(f"gst-play-1.0 failed to play sound: {e}")
    logger.debug("gst-play-1.0: finishing play %s", sound)


def _playsound_ffplay(sound: str) -> None:
    """Uses ffplay utility (built-in Linux)."""
    logger.debug("ffplay: starting playing %s", sound)
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", sound],
            check=True,
            stdout=subprocess.DEVNULL,  # suppress output as ffplay prints an unwanted newline
        )
    except subprocess.CalledProcessError as e:
        raise PlaysoundException(f"ffplay failed to play sound: {e}")
    logger.debug("ffplay: finishing play %s", sound)


def _playsound_alsa(sound: str) -> None:
    """Play a sound using alsa and mpg123 (built-in Linux)."""
    if Path(sound).suffix == ".wav":
        logger.debug("alsa: starting playing %s", sound)
        try:
            subprocess.run(["aplay", "--quiet", sound], check=True)
        except subprocess.CalledProcessError as e:
            raise PlaysoundException(f"aplay failed to play sound: {e}")
        logger.debug("alsa: finishing play %s", sound)
    else:
        logger.debug("mpg123: starting playing %s", sound)
        try:
            subprocess.run(["mpg123", "-q", sound], check=True)
        except subprocess.CalledProcessError as e:
            raise PlaysoundException(f"mpg123 failed to play sound: {e}")
        logger.debug("mpg123: finishing play %s", sound)


def _playsound_gst_legacy(sound: str) -> None:
    """Play a sound using gstreamer (built-in Linux)."""

    if not sound.startswith("file://"):
        sound = "file://" + urllib.request.pathname2url(sound)

    import gi

    # Silences gi warning
    gi.require_version("Gst", "1.0")

    # GStreamer is included in all Linux distributions
    from gi.repository import Gst

    Gst.init(None)

    playbin = Gst.ElementFactory.make("playbin", "playbin")
    playbin.props.uri = sound

    logger.debug("gstreamer: starting playing %s", sound)
    set_result = playbin.set_state(Gst.State.PLAYING)
    if set_result != Gst.StateChangeReturn.ASYNC:
        raise PlaysoundException("playbin.set_state returned " + repr(set_result))
    bus = playbin.get_bus()
    try:
        bus.poll(Gst.MessageType.EOS, Gst.CLOCK_TIME_NONE)
    finally:
        playbin.set_state(Gst.State.NULL)
    logger.debug("gstreamer: finishing play %s", sound)


def _send_winmm_mci_command(command):
    winmm = ctypes.WinDLL("winmm.dll")
    buffer = ctypes.create_string_buffer(255)
    error_code = winmm.mciSendStringA(ctypes.c_char_p(command.encode()), buffer, 254, 0)
    if error_code:
        logger.error("MCI error code: %s", error_code)
    return buffer.value


def _playsound_mci_winmm(sound: str) -> None:
    """Play a sound utilizing windll.winmm."""

    # Select a unique alias for the sound
    alias = str(uuid.uuid4())
    logger.debug("winmm: starting playing %s", sound)
    _send_winmm_mci_command(f'open "{sound}" type mpegvideo alias {alias}')
    _send_winmm_mci_command(f"play {alias} wait")
    _send_winmm_mci_command(f"close {alias}")
    logger.debug("winmm: finishing play %s", sound)


def _playsound_afplay(sound: str) -> None:
    """Uses afplay utility (built-in macOS)."""
    logger.debug("afplay: starting playing %s", sound)
    try:
        subprocess.run(["afplay", sound], check=True)
    except subprocess.CalledProcessError as e:
        raise PlaysoundException(f"afplay failed to play sound: {e}")
    logger.debug("afplay: finishing play %s", sound)


def _initialize_default_backend() -> None:
    global _PLAYSOUND_DEFAULT_BACKEND

    if _SYSTEM == "Windows":
        _PLAYSOUND_DEFAULT_BACKEND = _playsound_mci_winmm
    elif _SYSTEM == "Darwin":
        _PLAYSOUND_DEFAULT_BACKEND = _playsound_afplay
    else:
        # Linux version serves as the fallback
        # because tools like gstreamer and ffmpeg could be installed on unrecognized systems
        _PLAYSOUND_DEFAULT_BACKEND = _select_linux_backend()


def _remove_cached_downloads(cache: Dict[str, str]) -> None:
    """Remove all files saved in the cache when the program ends."""
    import os

    for path in cache.values():
        os.remove(path)


# ######################## #
# PLAYSOUND INITIALIZATION #
# ######################## #

_initialize_default_backend()
atexit.register(_remove_cached_downloads, _DOWNLOAD_CACHE)

_BACKEND_MAPPING = {
    "afplay": _playsound_afplay,
    "alsa_mpg123": _playsound_alsa,
    "ffplay": _playsound_ffplay,
    "gst_play": _playsound_gst_play,
    "gst_legacy": _playsound_gst_legacy,
    "mci_wnmm": _playsound_mci_winmm,
}

AVAILABLE_BACKENDS = list(_BACKEND_MAPPING.keys())
