# Image Colorspace Modifier

The Image Colorspace Modifier Program allows you to inver, offset, and change the different color channels of an image.

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