import argparse
import textwrap

from os.path import exists
from sys import argv
from argparse import ArgumentParser

from convert import SUPPORTED_COLOR_CHANNELS, SUPPORTED_OPERATIONS, ColorspaceModifier


def first_index(input_list, iterable, start=0):
    input_list = list(map(str.lower, input_list[start:]))
    first = len(input_list)
    for item in iterable:
        try:
            first = min(first, input_list.index(item))
        except ValueError:
            continue
    return first + start


def parse_operation(args):
    arg_parser = ArgumentParser(
        prefix_chars='-',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
                A program to perform various operation on the color channels of an image. Channels will applied in the order given,
                regardless of the base image format. This means that if you passed in -rghl to invert and the image was a grayscale
                image, the image would first be converted to RGB, then HSV, then back to grayscale.
                
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
                
                Invert: Invert the specified color channels
                    x = 1 - x  
                    Usage: cli.py invert +c

                Offset: Offset the specified color channels by the specified amount
                    x = x + y
                    Usage: cli.py offset +c offset_value

                Threshold: Threshold the specified color channels with the given threshold
                    x = 0 if x < y else 1
                    Usage: cli.py threshold +c threshold_value

                Scale: Scale the specified color channels by the specified amount
                    x = x * y
                    Usage: cli.py scale +c scale_factor
                
                Clamp: Clamp the specified color channels to between a given minimum or maximum
                    x = min(x, y) or max(x, y)
                    Usage: cli.py clamp +c {min, max} value
            """),
        usage='%(prog)s [options] command [command options] [command [command options]] ...')
    arg_parser.add_argument('command', choices=SUPPORTED_OPERATIONS, help='The operation to perform')
    arg_parser.add_argument('--debug', help='Print debug information', action='store_true')
    arg_parser.add_argument('-no', '--no-clamp',
                            help='Disabled the default normalization clamping of channels between operations',
                            action='store_true')
    return arg_parser.parse_args(args)


def parse_command(command, args, need_input=True):
    program = argv[0].split('/' if '/' in argv[0] else '\\')[-1]
    arg_parser = ArgumentParser(prefix_chars='-+', prog=program + ' ' + command)
    if need_input:
        arg_parser.add_argument('input', help='The input image')
    else:
        arg_parser.add_argument('-i', '--input', help='The input image')
    arg_parser.add_argument('-o', '--output',
                            help='The output image; If not specified, output will be written to the input image')
    arg_parser.add_argument('-no', '--no-clamp',
                            help='Disabled the default normalization clamping of channels between operations',
                            action='store_true')
    arg_parser.add_argument('--debug', help='Print debug information', action='store_true')

    if command == 'invert':
        for shorthand, channel, description in SUPPORTED_COLOR_CHANNELS:
            arg_parser.add_argument(f'+{shorthand}', f'--{channel}', action='store_true', help=description, default=argparse.SUPPRESS)
    elif command == 'offset':
        for shorthand, channel, description in SUPPORTED_COLOR_CHANNELS:
            arg_parser.add_argument(f'+{shorthand}', f'--{channel}', nargs=1, metavar='offset value', help=description, default=argparse.SUPPRESS)
    elif command == 'scale':
        for shorthand, channel, description in SUPPORTED_COLOR_CHANNELS:
            arg_parser.add_argument(f'+{shorthand}', f'--{channel}', nargs=1, metavar='scale value', help=description, default=argparse.SUPPRESS)
    elif command == 'threshold':
        for shorthand, channel, description in SUPPORTED_COLOR_CHANNELS:
            arg_parser.add_argument(f'+{shorthand}', f'--{channel}', nargs=1, metavar='threshold value', help=description, default=argparse.SUPPRESS)
    elif command == 'clamp':
        for shorthand, channel, description in SUPPORTED_COLOR_CHANNELS:
            arg_parser.add_argument(f'+{shorthand}', f'--{channel}', nargs=2, metavar='clamp mode value', help=description, default=argparse.SUPPRESS)
    else:
        raise ValueError(f'Unsupported command {command}')
    return arg_parser.parse_args(args)


def run_commands(commands, debug, clamp=True):
    image = {'input_name': None, 'output_name': None, 'handle': None}
    for command_ix, (name, values) in enumerate(commands):
        # Parse command arguments
        for k, v in vars(values).items():
            if k in ('debug', 'no_clamp'):
                continue
            if k == 'input':
                if v is None:
                    continue
                if exists(v):
                    image['input_name'] = v
                    if image['handle'] is None:
                        image['handle'] = ColorspaceModifier.from_image(v, debug)
                        image['handle'].set_clamp(clamp)
                    else:
                        image['handle'].load_image(v)
                else:
                    raise ValueError(f'Input file {v} does not exist!')
            elif k == 'output':
                if v is None:
                    continue
                image['output_name'] = v
            elif name == 'invert':
                image['handle'].invert([k])
            elif name == 'offset':
                image['handle'].offset([tuple([k, float(v[0])])])
            elif name == 'scale':
                image['handle'].scale([tuple([k, float(v[0])])])
            elif name == 'threshold':
                image['handle'].threshold([tuple([k, float(v[0]) if v[0] not in ('mean', 'median') else v[0]])])
            elif name == 'clamp':
                image['handle'].clamp([tuple([k, v[0], float(v[1]) if v[1] not in ('mean', 'median') else v[1]])])
        if image['output_name'] is not None and command_ix != len(commands) - 1:
            with open(image['output_name'], 'rb') as f:
                image['handle'].save_image(f)
    if image['output_name'] is None:
        image['output_name'] = image['input_name']
    with open(image['output_name'], 'rb') as f:
        image['handle'].save_image(f)


def main():
    end = 1
    need_input = True

    if len(argv) == 1:
        parse_operation(['-h'])
        return

    debug = False
    no_clamp = False
    commands = []
    while end < len(argv):
        start = end
        end = first_index(argv, SUPPORTED_OPERATIONS, start + 1)

        parsed = parse_operation(argv[start:start + 1])
        values = parse_command(parsed.command, argv[start + 1:end], need_input)
        debug |= values.debug or parsed.debug
        no_clamp |= values.no_clamp or parsed.no_clamp
        need_input = False
        commands.append((parsed.command, values))

    run_commands(commands, debug, not no_clamp)


if __name__ == '__main__':
    main()
