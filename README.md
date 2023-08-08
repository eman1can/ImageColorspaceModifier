# Image Colorspace Modifier

A program to perform various operations on the color channels of an image. Leverages PIL to make operations on the color
channels easy, and setting up a image conversion pipeline.

The input image need only be specified once if multiple commands are used. The first time the input
image is specified, no flag is needed, but subsequent input images must be preceded by the -i flag.
If no output image is specified, the input image will be overwritten. If no output image is specified
for the last operation, the last specified output image will be overwritten.

All output images will be saved in the same channel format as the input image.

Ex. cli.py invert input.png +rghl offset +r 0.5 -o output.png
This will open input.png, invert the rgbl channels, save the image to input.png, the offset the red
channel by half, then save the image to output.png.

All channel operation are performed in normal space between 0 and 1. All operation are clamped to inside
this range after the operation is performed. This means that if you offset the red channel by 0.5, all
values will be clamped to between 0 and 1 after the offset is performedm, and before any other command
is performed. This can be disabled by using the --no-clamp flag.

In the following examples, +c is the shorthand to the specified channel flag.

## Supported channels

- R - Red
- G - Green
- B - Blue
- H - Hue
- S - Saturation
- V - Value
- L - Lightness
- A - Alpha

## Supported Pixel Formats

- RGB
- RGBA
- HSV
- LA
- L

### Invert - Invert the specified color channels

x = 1 - x  
Usage: cli.py invert +c

### Offset - Offset the specified color channels by the specified amount

x = x + y
Usage: cli.py offset +c offset_value

### Threshold - Threshold the specified color channels with the given threshold

x = 0 if x < y else 1
Usage: cli.py threshold +c threshold_value | mean | median

### Scale - Scale the specified color channels by the specified amount

x = x * y
Usage: cli.py scale +c scale_factor

### Clamp - Clamp the specified color channels to between a given minimum or maximum

x = min(x, y) or max(x, y)
Usage: cli.py clamp +c {min, max} value | mean | median