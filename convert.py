# Imports
from PIL import Image
from os.path import exists
from colorsys import rgb_to_hsv, hsv_to_rgb
import numpy as np
from sys import argv

###
### Start Input
###

help_string = """

Usage: convert.py <mode> <sub_mode> [<option>...] , <image> [<image>...]

WARNING: Note the ',' between the option array and the image array! Excluding this comma will break the program!

capitalization is irrelvant in the non image arguments, as everything gets lowercased.

Special Flags:
    -h Show this menu
    -d Enable Debug Messages

Mode:
    The mode specifies the main operation to perform
    
    invert
        Invert the channel, x → 1 - x
    
    offset
        Offset the channel, x → x + y

Sub-Mode / Channels:
    The sub mode specifies the channels that the mode affects.
    The sub mode is any combination of h, s, v, r, g, b, and a, where each letter represents the corresponding channel and then followed by a ':' separated list of float values for each channel
    Ex. HSR:0.4:0.3:0.23

Option:
    The option is an operation to perform before or after the main mode operation, and can either be a min or max clamp or a channel offset.
    The option consists of the letter of the channel, (a)fter, (b)efore, and the option name. Ex. RAmin is a min clamp on the R channel after the mode operation.
    The value is separated by a ':', and is a float value. Ex: RAmin:30.21

Image:
    The image is an input image name and an output image name. This can be an absolue or relative path. The names are seperated by a ':'.
    Ex: image_red.png:image_blue.png


"""

# Check the flags

# Check if user is crying for help
if 'h' in argv or '-h' in argv or len(argv) == 1:
    print(help_string)
    quit(0)

debug = False
if '-d' in argv:
    argv.remove('-d')
    debug = True

# OPERATIONS / MODES & OPTIONS
BEFORE = 1
AFTER = BEFORE + 1

INVERT = AFTER + 1
OFFSET = INVERT + 1
MIN = OFFSET + 1
MAX = MIN + 1

string_to_mode = {
    'invert': INVERT,
    'offset': OFFSET
}

string_to_option = {
    'b': BEFORE,
    'a': AFTER,
    'offset': OFFSET,
    'min': MIN,
    'max': MAX,
    
}


# SUB-MODES / CHANNELS

# HSV / HSL
# Hue, Saturation, Value / Brightness

H = 1
S = H + 1
V = S + 1

# RGBA
# Red, Green, Blue, Alpha

R = V + 1
G = R + 1
B = G + 1
A = B + 1

string_to_channel = {
    'h': H,
    's': S,
    'v': V,
    'r': R,
    'g': G,
    'b': B,
    'a': A
}

# File Types
# This is the image encoded format
file_types = ['png', 'jpg']

# Image Types
# This is the encoded channel format
RGB = 1
RGBA = RGB + 1
HSV = RGBA + 1
ONE = HSV + 1

string_to_format = {
    'RGB': RGB,
    'RGBA': RGBA,
    'HSV': HSV
}

# Get the argument inputs
try:
    comma_index = argv[3:].index(',')
except ValueError:
    comma_index = -1

input_mode, input_channels = argv[1:3]
if comma_index > -1:
    input_options = argv[3:comma_index + 3]
    input_images = argv[comma_index + 4:]
else:
    input_options = []
    input_images = argv[3:]
# Lower all arguments except image names
input_mode = input_mode.lower()
input_channels = input_channels.lower()
input_options = [input_option.lower() for input_option in input_options]

# Check that the mode is valid
if input_mode not in string_to_mode.keys():
    print(f'Invalid Mode: {input_mode}')
    quit(1)

input_mode = string_to_mode[input_mode]
del string_to_mode

# Check that the sub-mode is valid
input_channel_dict = {}

input_channels, input_channel_values = input_channels.split(':', 1)
input_channel_values = input_channel_values.split(':')

for index, input_channel in enumerate(input_channels):
    if input_channel not in string_to_channel.keys():
        print(f'Invalid Channel: {input_channel}')
        quit(1)
    try:
        input_channel_value = float(input_channel_values[index])
    except ValueError:
        print(f'Invalid value {input_channel_value} in {input_channel}')
        quit(1)
    input_channel_dict[string_to_channel[input_channel]] = input_channel_value
input_channels = input_channel_dict
del input_channel
del index
del input_channel_dict
del input_channel_values

# Check that the options are valid
input_option_dict = {}
for input_option in input_options:
    try:
        option_info, option_value_string = input_option.split(':')
        option_channel_string = option_info[0]
        option_time_string = option_info[1]
        option_operation_string = option_info[2:]
    except ValueError:
        print('Malformed Option Input: {input_option}')
        quit(1)
    if option_channel_string not in string_to_channel.keys():
        print(f'Invalid Channel {option_channel_string} in {input_option}')
        quit(1)
    if option_time_string not in string_to_option.keys():
        print(f'Invalid Option Time {option_time_string} in {input_option}')
        quit(1)
    if option_operation_string not in string_to_option.keys():
        print(f'Invalid Option Method {option_operation_string} in {input_option}')
        quit(1)
    
    option_channel = string_to_channel[option_channel_string]
    option_time = string_to_option[option_time_string]
    option_operation = string_to_option[option_operation_string]
    option = option_time | option_operation
    
    try:
        option_value = float(option_value_string)
    except ValueError:
        print(f'Invalid Option Value {option_value_string} in {input_option}')
        quit(1)
    
    if option not in input_option_dict:
        input_option_dict[option] = []
    if (option_channel , option_value) in input_option_dict[option]:
        print(f'Duplicated Option: {input_option}')
        quit(1)
    input_option_dict[option].append((option_channel, option_value))
input_options = input_option_dict
del input_option_dict
del string_to_channel
del string_to_option

# Check that the image names are all valid and that each image is a valid type
input_image_dict = {}
for input_image in input_images:
    try:
        input_base_image, input_output_image = input_image.split(':')
    except ValueError:
        print('You forgot the ":" you dumbass')
        quit(1)
    
    try:
        input_file_type = input_base_image[input_base_image.index('.') + 1:]
    except ValueError:
        print(f'Malformed Image Name: {input_base_image}')
        quit(1)
    
    try:
        output_file_type = input_output_image[input_output_image.index('.') + 1:]
    except ValueError:
        print(f'Malformed Image Name: {input_output_image}')
        quit(1)
    
    if not exists(input_base_image):
        print(f'Image not found: {input_base_image}')
        quit(1)
    
    valid = True
    with Image.open(input_base_image) as image:
        if image.mode not in string_to_format.keys():
            print(f'{input_base_image} has an invalid format: {image.mode}')
            valid = False
    if not valid:
        quit(1)
    
    if input_base_image not in input_image_dict:
        input_image_dict[input_base_image] =[]
    if input_output_image in input_image_dict[input_base_image]:
        print(f'Duplicated Image: {input_base_image}')
        quit(1)
    input_image_dict[input_base_image].append(input_output_image)
input_images = input_image_dict
del input_image

print(input_options)

###
### End Input
###

class NotImplementedException(Exception):
    pass

class ImageEditor:
    def __init__(self):
        self.mode = None
        self.channels = None
        self.options = None
        self.images = None
        
        self.current_format = None
        self.current_image = None
        
        self.colorspace_transitions = {
            RGB: {
                HSV: self.hsv_colorspace_in_rgb
            },
            RGBA: {
                HSV: self.hsv_colorspace_in_rgba
            },
            HSV: {
                RGBA: self.rgba_colorspace_in_hsv
            }
        }
    
    def transform_images(self):
        for input_image in self.images.keys():
            
            with Image.open(input_image) as image:
                print(f'Load {input_image}')
                self.current_format = string_to_format[image.mode]
                self.current_image = image.load()
                self.width, self.height = image.size
                
                self.perform_pre_operations()
                self.perform_operations()
                self.perform_post_operations()
                
                image.pixels = self.current_image
                
                for output_name in self.images[input_image]:
                    print(f'Save {input_image} as {output_name}')
                    image.save(output_name)
    
    ##
    ## Image space operations
    ##
    
    def normalize_colorspace(self, pixel_color):
        if self.current_format == RGBA:
            return self.normalize_rgba(*pixel_color)
        elif self.current_format == RGB:
            r, g, b = pixel_color
            return self.normalize_rgba(r, g, b, 1)
        elif self.current_format == HSV:
            return self.normalize_hsv(*pixel_color)
        raise NotImplementedException(self.current_format)
    
    def denormalize_colorspace(self, pixel_color):
        if self.current_format == RGBA:
            return self.denormalize_rgba(*pixel_color)
        elif self.current_format == RGB:
            r, g, b = pixel_color
            return self.denormalize_rgba(r, g, b, 1)
        elif self.current_format == HSV:
            return self.denormalize_hsv(*pixel_color)
    
    def transform_pixels(self, value_method, channel, values):
        channel_colorspace = self.get_colorspace(channel)
        for x in range(self.width):
            for y in range(self.height):
                pixel_color = self.normalize_colorspace(self.current_image[x, y])
                pixel_color = self.colorspace(channel_colorspace, value_method, channel, values, pixel_color)
                pixel_color = self.denormalize_colorspace(pixel_color)
                self.current_image[x, y] = self.float_to_int_number_space(*pixel_color)
    
    ##
    ## Imagespace operation functions
    ## These functions call color space functions for the image
    ##
    
    def perform_pre_operations(self):
        for option in self.options.keys():
            if option & B != B:
                continue
            for (channel, value) in self.options[option]:
                self.perform_operation(option, channel, [value])
    
    def perform_operations(self):
        for channel, value in self.channels.items():
            self.perform_operation(self.mode, channel, [value])
    
    def perform_post_operations(self):
        for option in self.options.keys():
            if option & A != A:
                continue
            for (channel, value) in self.options[option]:
                self.perform_operation(option, channel, [value])
    
    def perform_operation(self, operation, channel, value):
        if operation & OFFSET == OFFSET:
            value_method = self.offset_value
        elif operation & INVERT == INVERT:
            value_method = self.invert_value
        elif operation & MIN == MIN:
            value_method = self.min_clamp_value
        elif operation & MAX == MAX:
            value_method = self.max_clamp_value
        else:
            raise NotImplementedException()
        
        self.transform_pixels(value_method, channel, [value])
    
    ##
    ## Color Space operation functions
    ## These functions transfrom from RGBA to a colorspace, perform a method and then transform back
    ##
    
    def get_colorspace(self, channel):
        if channel in (R, G, B, A):
            return RGBA
        elif channel in (H, S, V):
            return HSV
        else:
            raise NotImplementedException()
    
    def colorspace(self, colorspace, value_method, channel, values, pixel_color):
        if self.current_format == colorspace:
            return self.same_colorspace(value_method, channel, values, pixel_color)
        if self.current_format not in self.colorspace_transitions:
            raise NotImplementedException()
        if colorspace not in self.colorspace_transitions[self.current_format]:
            raise NotImplementedException()
        return self.colorspace_transitions[self.current_format][colorspace](value_method, channel, values, pixel_color)
    
    def same_colorspace(self, value_method, channel, values, pixel_color):
        return self.channel(value_method, channel, values, *pixel_color)
    
    def rgba_colorspace_in_rgb(self, value_method, channel, values, pixel_color):
        rgba = self.channel(value_method, channel, values, self.rgb_to_rgba(*pixel_color))
        return self.rgba_to_rgb(*rgba)
    
    def rgba_colorspace_in_hsv(self, value_method, channel, values, pixel_color):
        rgba = self.channel(value_method, channel, values, *self.hsv_to_rgba(*pixel_color))
        return self.rgba_to_hsv(*rgba)
    
    def hsv_colorspace_in_rgb(self, value_method, channel, values, pixel_color):
        hsv = self.channel(value_method, channel, values, *rgb_to_hsv(*pixel_color))
        return hsv_to_rgb(*hsv)
    
    def hsv_colorspace_in_rgba(self, value_method, channel, values, pixel_color):
        r, g, b, a = pixel_color
        hsv = self.channel(value_method, channel, values, *rgb_to_hsv(r, g, b))
        r, g, b = hsv_to_rgb(*hsv)
        return r, g, b, a
    
    ##
    ## Channel space operations
    ## These methods operate on their respective colorspaces
    ## 
    
    def get_starting_channel(self, channel):
        if channel in (R, G, B, A):
            return R
        elif channel in (H, S, V):
            return H
        else:
            raise NotImplementedException()
    
    def channel(self, value_method, channel, operative_values, *values):
        channel_index = channel - self.get_starting_channel(channel)
        values = list(values)
        v = values[channel_index]
        v = value_method(*operative_values, v)
        values[channel_index] = v
        return values
    
    def normalize_rgba(self, r, g, b, a):
        return r / 255, g / 255, b / 255, a / 255
    
    def denormalize_rgba(self, r, g, b, a):
        return r * 255, g * 255, b * 255, a * 255
    
    def normalize_hsv(self, h, s, v):
        return h / 360, s / 100, v / 100
    
    def denormalize_hsv(self, h, s, v):
        return h * 360, s * 100, v * 100
    
    def rgb_to_rgba(self, r, g, b):
        return r, g, b, 1
    
    def rgba_to_rgb(self, r, g, b, a):
        return r, g, b
    
    def hsv_to_rgba(self, h, s, v):
        r, g, b = hsv_to_rgb(h, s, v)
        if debug:
            print(f'HSV ({h}, {s}, {v}) → RGBA ({r}, {g}, {b}, {1})')

        return r, g, b, 1
    
    def rgba_to_hsv(self, r, g, b, a):
        if debug:
            print(f'RGBA ({r}, {g}, {b}, {a}) → HSV {rgb_to_hsv(r, g, b)}')
        return rgb_to_hsv(r, g, b)
    
    ##
    ## Common operations
    ## These methods operate independent of colorspace and channelspace
    ## 
    
    def offset_value(self, offset, value):
        return value + offset[0]
    
    def invert_value(self, blank, value):
        if debug:
            print(f'Invert {value} → {1 - value}')
        return 1 - value
        
    
    def min_clamp_value(self, minimum, value):
        if debug:
            print(f'Clamp {value} → {max(minimum, value)}')
        return max(minimum, value)
    
    def max_clamp_value(self, maximum, value):
        return min(maximum, value)
    
    def clamp_value(self, minimum, maximum, value):
        return min(maximum, max(minimum, value))
    
    def float_to_int_number_space(self, *args):
        return tuple([int(arg) for arg in args])
    


###
### Start Output
###

editor = ImageEditor()
editor.mode = input_mode
editor.channels = input_channels
editor.options = input_options
editor.images = input_images

del input_mode
del input_channels
del input_options
del input_images

editor.transform_images()

print('All Images Processed.')
quit(0)