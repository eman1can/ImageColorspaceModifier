import base64
from io import BytesIO

import requests
import uvicorn
from typing import Optional

from PIL import Image
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from src import ColorspaceModifier
from src.convert import SUPPORTED_OPERATIONS, SUPPORTED_COLOR_CHANNEL_SHORTHANDS

from PIL.Image import init
init()
from PIL.Image import EXTENSION

SUPPORTED_IMAGE_TYPES = {k: f'image/{k.lower()}' for k in EXTENSION.values()}

server = FastAPI()


@server.get('/')
def index():
    return RedirectResponse('/docs')


def parse_file(data: str) -> bytes:
    """
    Parse an input file specification. Supports:
    - data:mimetype;base64
    - url:weblink
    :param data: The input file specification
    :return: The raw byte content of the file
    """
    if ',' not in data:
        raise HTTPException(status_code=400, detail="Invalid data format; Must be prepended by type")
    content_type, content_string = data.split(',')
    if content_type.startswith('file:'):
        raise HTTPException(status_code=403, detail="Tried to access a local server resource")
    if content_type.startswith('data:'):
        mimetype = content_type[content_type.index(':') + 1:content_type.index(';')]
        if mimetype not in SUPPORTED_IMAGE_TYPES.values():
            raise HTTPException(status_code=400, detail=f"Unsupported mimetype: {mimetype}")
        if content_type.endswith(';base64'):
            return base64.b64decode(content_string)
        raise HTTPException(status_code=400, detail=f"{content_type} decoding not implemented")

    elif content_type == 'url':
        r = requests.get(content_string)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.content
    raise HTTPException(status_code=400, detail=f"Invalid data format: {content_type}")


def encode_output(output_buffer: BytesIO) -> str:
    """
    Encode a PIL image into a base64 string with mimetype specification
    :param data: The image to encode
    :return: The base64 string with type specifier
    """
    encoded = base64.b64encode(output_buffer.getvalue())
    return f"data:image/png;base64,{encoded.decode('utf-8')}"


def do_operation(handle: ColorspaceModifier, operation: str, channels: list[str], params: Optional[list[any]]):
    match operation:
        case 'invert':
            handle.invert(channels)
        case 'offset':
            handle.offset(zip(channels, [float(p) for p in params]))
        case 'scale':
            handle.scale(zip(channels, [float(p) for p in params]))
        case 'clamp':
            handle.clamp(zip(channels, [(a, b, (float(c) if c not in ['mean', 'median'] else c)) for a, b, c in params]))
        case 'threshold':
            handle.threshold(zip(channels, [(a, (float(b) if b not in ['mean', 'median'] else b)) for a, b in params]))
        case _:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")


class Operation(BaseModel):
    auto_clamp: bool = False
    action: str
    channels: list[str]
    params: Optional[list] = None
    input: Optional[list[tuple[str, str]]]
    output_format: Optional[str] = None


@server.post('/operation')
async def api_operation(data: Operation):
    """
    Perform a single operation on the given images and return the resultant images as base64 encoded images.
    :param data: The operation to perform
    :return: The resultant image from the operation
    """
    # Check for incorrect data inputs
    if data.input is None:
        raise HTTPException(status_code=400, detail="Must specify input file / files")
    if data.action not in SUPPORTED_OPERATIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {data.action}")
    for c in data.channels:
        if c not in SUPPORTED_COLOR_CHANNEL_SHORTHANDS:
            raise HTTPException(status_code=400, detail=f"Unsupported channel: {c}")

    files = {}
    for input_name, input_data in data.input:
        # Parse the input files
        raw_input = parse_file(input_data)
        input_handle = Image.open(BytesIO(raw_input))

        # Create an output buffer for this image
        output_handle = BytesIO()

        # Create the modifier and perform the operation
        convert = ColorspaceModifier(input_handle, data.auto_clamp)
        do_operation(convert, data.action, data.channels, data.params)

        # Save the output image
        convert.save_image(output_handle)

        # Close the input image
        convert.close_image()

        # Encode the output
        if data.output_format is None:
            data.output_format = 'default'
        output_data = encode_output(output_handle.getvalue(), data.output_format)
        files[input_name] = output_data
    return files


class MultiOperation(BaseModel):
    auto_clamp: bool = False
    operations: list[Operation]
    input: list[tuple[str, str]]
    output_format: str = 'default'


@server.post('/operations')
async def api_operations(data: MultiOperation):
    """
    Perform multiple operations on the given images and return the resultant images as base64 encoded images.
    :param data: The operations to perform
    :return: A list of images from the operations
    """
    files = {}
    for input_name, input_data in data.input:
        # Parse the input files
        raw_input = parse_file(input_data)
        input_handle = Image.open(BytesIO(raw_input))

        # Create an output buffer for this image
        output_handle = BytesIO()

        # Create the modifier and perform the operation
        convert = ColorspaceModifier(input_handle, data.auto_clamp)

        output_files = []
        for op in data.operations:
            do_operation(convert, op.action, op.channels, op.params)

            # Save the output image
            if op.output_format is not None:
                temp_handle = BytesIO()
                convert.save_image(temp_handle, op.output_format)
                output_data = encode_output(temp_handle.getvalue(), op.output_format)
                output_files.append(output_data)

        # Save the output image
        convert.save_image(output_handle)

        # Encode the output
        if data.output_format is None:
            data.output_format = 'default'
        output_data = encode_output(output_handle)
        output_files.append(output_data)

        # Close the input image
        convert.close_image()

        files[input_name] = output_files
    return files



    # Parse the input files
    input_name, input_data = data.input
    raw_input = parse_file(input_data)
    input_handle = Image.open(BytesIO(raw_input))
    output_name, output_format = data.output

    files = {
        input_name: input_handle,
        output_name: BytesIO()
    }

    # Create the modifier
    convert = ColorspaceModifier(input_handle, data.auto_clamp)

    for op in data.operations:
        # Load input if specified
        if op.input is not None:
            name, raw_data = op.input
            if name not in files:
                data = parse_file(raw_data)
                files[name] = handle = Image.open(BytesIO(data))
            else:
                handle = files[name]
            convert.set_handle(handle)

        # Perform the operation


    # if data.action not in SUPPORTED_OPERATIONS:
    #     raise HTTPException(status_code=400, detail=f"Unsupported operation: {data.action}")
    # for c in data.channels:
    #     if c not in SUPPORTED_COLOR_CHANNEL_SHORTHANDS:
    #         raise HTTPException(status_code=400, detail=f"Unsupported channel: {c}")


if __name__ == "__main__":
    uvicorn.run(server, host='localhost', port=8040)
