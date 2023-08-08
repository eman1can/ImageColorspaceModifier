from __future__ import annotations

from typing import BinaryIO

import numpy as np
from PIL import Image
from numpy import fmax, fmin

__all__ = ["ColorspaceModifier"]


SUPPORTED_COLOR_CHANNELS = [
    ('h', 'hue', 'The hue channel in HSV'),
    ('s', 'saturation', 'The saturation channel in HSV'),
    ('v', 'value', 'The value channel in HSV'),
    ('r', 'red', 'The red channel in RGB'),
    ('g', 'green', 'The green channel in RGB'),
    ('b', 'blue', 'The blue channel in RGB'),
    ('a', 'alpha', 'The alpha channel in RGBA/LA, and other formats that support alpha'),
    ('l', 'luminance', 'The luminance channel in L'),
]

SUPPORTED_COLOR_CHANNEL_SHORTHANDS = [shorthand for shorthand, _, _ in SUPPORTED_COLOR_CHANNELS]

COLOR_CHANNEL_TO_SHORTHAND = {
    'hue': 'h',
    'saturation': 's',
    'value': 'v',
    'red': 'r',
    'green': 'g',
    'blue': 'b',
    'alpha': 'a',
    'luminance': 'l',
}

SUPPORTED_PIL_MODES = {
    'RGB': ['red', 'green', 'blue'],
    'RGBA': ['red', 'green', 'blue', 'alpha'],
    'L': ['luminance'],
    'LA': ['luminance', 'alpha'],
    'HSV': ['hue', 'saturation', 'value'],
}
SUPPORTED_OPERATIONS = ['invert', 'offset', 'clamp', 'scale', 'threshold']

SUPPORTED_KEYWORD_PARAMS = {
    'mean': np.mean,
    'median': np.median,
    'min': np.min,
    'max': np.max,
    'sum': np.sum,
    'std': np.std,
}

SUPPORTED_CLAMP_MODES = {
    'min': fmin,
    'max': fmax
}


def _get_format(current: str, k: str) -> str:
    """
    Return the closet format to the current format that supports the given channel
    :param current: The current format
    :param k: The requested channel
    :return: The closest supported format
    """

    supported = {
        'RGB': {
            'RGBA': ['A'],
            'HSV': ['H', 'S', 'V'],
            'L': ['L'],
        },
        'RGBA': {
            'HSV': ['H', 'S', 'V'],
            'L': ['L'],
        },
        'HSV': {
            'RGBA': ['R', 'G', 'B', 'A'],
            'LA': ['L'],
        },
        'L': {
            'RGB': ['R', 'G', 'B'],
            'RGBA': ['A'],
            'HSV': ['H', 'S', 'V'],
        },
        'LA': {
            'RGBA': ['R', 'G', 'B'],
            'HSV': ['H', 'S', 'V'],
        }
    }

    for mode, channels in supported[current].items():
        if k in channels:
            return mode
    raise ValueError(f'No format supports the channel {k}')


def _clamp(v: np.ndarray) -> np.ndarray:
    """
    Clamp a float value between 0 and 1.
    :param v: The value to clamp
    :return: A new value between 0 and 1
    """
    return fmax(fmin(v, 1.0), 0.0)


class ColorspaceModifier:
    def __init__(self, image_handle: Image, auto_clamp: bool = True, debug: bool = False):
        self._image_handle = image_handle
        self._image_handle.load()
        self._loaded_channels = None
        self._auto_clamp = auto_clamp
        self._debug = debug

        self._image_format = self._image_handle.format
        self._current_format = self._image_handle.mode
        self._output_format = self._image_handle.mode
        if self._current_format not in SUPPORTED_PIL_MODES:
            raise ValueError(f'Unsupported image format {self._current_format}')

    def set_clamp(self, auto_clamp: bool) -> None:
        """
        Set the auto clamp flag. If true, the image will be clamped to normalization range after every operation.
        :param auto_clamp: The new value of the auto clamp flag
        """
        self._auto_clamp = auto_clamp

    @staticmethod
    def from_image(filename, debug=False) -> ColorspaceModifier:
        """
        Return a colorspace modifier object, with the image loaded from the given filename
        :param filename: The image to load
        :param debug: Enable debugging
        """
        return ColorspaceModifier(Image.open(filename), debug=debug)

    def close_image(self) -> None:
        """
        Close the currently loaded image
        """
        self._image_handle.close()

    def load_image(self, filename: str) -> None:
        """
        Load an image from a file
        :param filename: The path to the image file
        """
        self._image_handle = Image.open(filename)
        self._current_format = self._image_handle.mode
        self._output_format = self._image_handle.mode
        if self._image_format not in SUPPORTED_PIL_MODES:
            raise ValueError(f'Unsupported image format {self._image_format}')

    def set_handle(self, image_handle: Image) -> None:
        """
        Set a new image handle
        :param image_handle: The image handle to use
        """
        self._image_handle = image_handle
        self._current_format = self._image_handle.mode
        self._output_format = self._image_handle.mode
        if self._image_format not in SUPPORTED_PIL_MODES:
            raise ValueError(f'Unsupported image format {self._image_format}')

    def _convert_image(self, new_format: str) -> None:
        """
        Convert the currently loaded image into a new format, replacing the image handle.
        :param new_format: The PIL image format to convert to
        """
        if new_format not in SUPPORTED_PIL_MODES:
            raise ValueError(f'Unsupported image format {new_format}')
        self._close_channels()
        self._image_handle = self._image_handle.convert(new_format)
        self._current_format = new_format

    def _close_channels(self):
        """
        Close the image channels and commit them to the image
        """
        if self._loaded_channels is not None:
            self._image_handle = Image.merge(self._current_format, self._loaded_channels)
            self._loaded_channels = None

    def _get_channel(self, channel: str) -> np.ndarray:
        """
        Get the colorspace channel in a normalized format
        :return: The normalized channel value
        """
        if self._loaded_channels is None:
            self._loaded_channels = list(self._image_handle.split())
        ix = self._current_format.index(channel.upper())
        return np.asarray(self._loaded_channels[ix]) / 255.0

    def _set_channel(self, channel: str, value: np.ndarray):
        """
        Set the colorspace channel in a normalized format
        :param channel: The channel to set
        :param value: The value to set the channel to
        """
        ix = self._current_format.index(channel.upper())
        self._loaded_channels[ix] = Image.fromarray((value * 255.0).astype(np.uint8))

    def save_image(self, output_handle: BinaryIO, output_format: str = 'default') -> None:
        """
        Save the currently loaded image to a file
        :param output_handle: The file object to save to
        :param output_format: The format to save the image in
        """
        if output_format == 'default':
            output_format = self._output_format
        else:
            if output_format not in SUPPORTED_PIL_MODES:
                raise ValueError(f"Unsupported output format: {output_format}")

        if self._current_format != output_format:
            self._convert_image(output_format)
        self._close_channels()
        self._image_handle.save(output_handle, self._image_format)

    def _pre(self, channel: str) -> tuple[np.ndarray, str]:
        """
        Do pre-operation checks
        :param channel: The image channel in operation
        """
        if len(channel) != 1:
            channel = COLOR_CHANNEL_TO_SHORTHAND[channel.lower()]
        if channel.upper() not in self._current_format:
            self._convert_image(_get_format(self._current_format, channel.upper()))
        return self._get_channel(channel.upper()), channel.upper()

    def _post(self, channel: str, value: np.ndarray):
        """
        Do post-operation checks
        :param channel: The image channel in operation
        :param value: The value of the channel
        """

        if self._auto_clamp:
            value = _clamp(value)
        self._set_channel(channel, value)

    def convert(self, new_format: str) -> ColorspaceModifier:
        """
        Convert the currently loaded image to a new format; Will set the output format to the new format.
        :param new_format: The PIL image format to convert to
        """
        self._convert_image(new_format)
        self._output_format = new_format
        return self

    def invert(self, channels: list) -> ColorspaceModifier:
        """
        Invert the currently loaded image on the supplied channels
        :param channels: The channel name to invert
        """
        for channel in channels:
            v, c = self._pre(channel)
            v = 1.0 - v

            self._post(c, v)
        return self

    def threshold(self, channels: list[tuple[str, float | str]]) -> ColorspaceModifier:
        """
        Threshold the currently loaded image on the supplied channels
        :param channels: The channels to threshold
        :return: The current colorspace modifier object
        """
        for channel, color in channels:
            v, c = self._pre(channel)

            color = SUPPORTED_KEYWORD_PARAMS[color](v)

            v[v < color] = 0
            v[v >= color] = 1

            self._post(c, v)
        return self

    def clamp(self, channels: list[tuple[str, str, float | str]]):
        """
        Clamp the currently loaded image on the supplied channels
        :param channels: The channel name, clamp mode, and clamp color
        :return: The current colorspace modifier object
        """
        for channel, mode, color in channels:
            v, c = self._pre(channel)

            if color not in SUPPORTED_KEYWORD_PARAMS:
                raise ValueError(f'Invalid clamp color {color}')
            color = SUPPORTED_KEYWORD_PARAMS[color](v)

            if mode not in SUPPORTED_CLAMP_MODES:
                raise ValueError(f'Invalid clamp mode {mode}')
            v = SUPPORTED_CLAMP_MODES[mode](v, color)

            self._post(c, v)
        return self

    def scale(self, channels: list[tuple[str, float]]) -> ColorspaceModifier:
        """
        Scale the currently loaded image on the supplied channels
        :param channels: The channel name, and scale factor
        :return: The current colorspace modifier object
        """
        for channel, factor in channels:
            v, c = self._pre(channel)
            v *= factor
            self._post(c, v)
        return self

    def offset(self, channels: list[tuple[str, float]]) -> ColorspaceModifier:
        """
        Offset the currently loaded image on the supplied channels
        :param channels: The channel name, and offset value
        :return: The current colorspace modifier object
        """
        for channel, offset in channels:
            v, c = self._pre(channel)
            v += offset
            self._post(c, v)
        return self

