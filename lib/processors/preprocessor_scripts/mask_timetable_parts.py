###
# This script handles bidirectional timetables aka 2 route directions
# represented in one table (usually in a manner that one direction is read top
# to bottom and the other - bottom to top with a column with stop names in the
# middle)
# Its responsibilities are:
# 1. Getting the bounding boxes of the meaningful parts of the timetable image
#    with metadata describing each box meaning
# 2. Using the boxes coordinates to mask the image in a way that masks the data belonging
#    to other route directions or any other undesired regions (stamps etc.)
# 3. Creating the list of FileData objects (images) each containing full context for one
#    route direction (each part has to have metadata + stop list + stop times)
###

import openrouter
from visual.mask_image import compose_from_squares, mask_jpeg_img, region_to_square
from visual.pdf import pdf_to_jpg

from conf import config
from lib.llm.openrouter_utils import OpenRouterUtils as utils
from models.files import FileData, ScrRunResult
from models.preprocessors import TimetableRegions


def _check_regions_valid(regions: TimetableRegions) -> None:
    time_grids = getattr(regions, "time_grids", None)
    if time_grids is None or len(time_grids) < 2:
        raise ValueError("Timetable must contain at least 2 time grids")


async def _get_region_descriptions(data: bytes, cfg):
    # outputs the region descriptions of the image in a structured json using structured response
    model = cfg.get("llm_model")
    system_prompt = cfg.get("system_prompt")

    if not model or not system_prompt:
        raise ValueError(f"Script needs 'llm_model' and 'system_prompt' configured")

    image_url = utils._get_img_data_url(data, "image/jpeg")
    payload = {
        "model": model,
        "messages": utils.build_messages(
            utils._add_message("system", system_prompt),
            utils._add_message("user", image_url, "image_url"),
        ),
        "reasoning": {"effort": "none"},
        "response_format": utils.to_response_format_schema(TimetableRegions),
    }

    async with openrouter.OpenRouter(api_key=config.OPENROUTER_API_KEY) as client:
        response = await client.chat.send_async(**payload)

    content = response.choices[0].message.content
    if not isinstance(content, str):
        return None

    regions = TimetableRegions.model_validate_json(content)
    _check_regions_valid(regions)

    return regions


def _mask_timetable_for_direction(
    data: bytes, region_data: TimetableRegions
) -> list[FileData]:
    """Create masked images for each time_grid direction."""
    regions = region_data.regions
    time_grids = [r for r in regions if r.type == "time_grid"]
    header = next((r for r in regions if r.type == "header"), None)
    footer = next((r for r in regions if r.type == "footer"), None)
    stop_names = next((r for r in regions if r.type == "stop_names"), None)
    other_regions = [r for r in regions if r.type == "other"]

    if not header or not footer or not stop_names:
        raise ValueError(
            "Timetable must contain header, footer, and stop_names regions"
        )

    output_data: list[FileData] = []
    for time_grid in time_grids:
        masked_bytes = data
        # mask all regions except the ones we're keeping
        regions_to_keep = [header, footer, stop_names, time_grid, *other_regions]
        regions_to_mask = [r for r in regions if r not in regions_to_keep]

        for region in regions_to_mask:
            square = region_to_square(region)
            masked_bytes = mask_jpeg_img(masked_bytes, square)

        output_data.append(
            FileData(
                mime="image/jpeg",
                ext="jpg",
                bytes=masked_bytes,
            )
        )

    return output_data


def _compose_timetable_for_direction(
    data: bytes, region_data: TimetableRegions
) -> list[FileData]:
    """Compose images for each time_grid direction using cut and paste."""
    regions = region_data.regions
    time_grids = [r for r in regions if r.type == "time_grid"]
    header = next((r for r in regions if r.type == "header"), None)
    footer = next((r for r in regions if r.type == "footer"), None)
    stop_names = next((r for r in regions if r.type == "stop_names"), None)
    other_regions = [r for r in regions if r.type == "other"]

    if not header or not footer or not stop_names:
        raise ValueError(
            "Timetable must contain header, footer, and stop_names regions"
        )

    output_data: list[FileData] = []
    for time_grid in time_grids:
        kept_regions = [header, footer, stop_names, time_grid, *other_regions]
        squares = [region_to_square(r) for r in kept_regions]
        composed_bytes = compose_from_squares(data, squares)

        output_data.append(
            FileData(
                mime="image/jpeg",
                ext="jpg",
                bytes=composed_bytes,
                description=time_grid.description,
            )
        )

    return output_data


async def run(input: ScrRunResult, **kwargs) -> ScrRunResult | None:
    if len(input.data) != 1:
        raise ValueError("Input data must contain exactly one FileData object")

    data = input.data[0].bytes
    data_mime = input.data[0].mime

    match data_mime:
        case "image/jpeg":
            pass
        case "application/pdf":
            data = pdf_to_jpg(data)
        case _:
            raise ValueError(f"Filetype '{data_mime}' is not supported")

    script_config = kwargs.get("script_config")
    if not script_config:
        raise ValueError(f"Script needs a script config")

    # split image into logical parts
    region_data = await _get_region_descriptions(data, script_config)
    if not region_data:
        return None

    # assemble a list of FileData objects.
    # Each object is self sufficient piece of timetable data eg. Header, Direction1, Footer
    output_data = _compose_timetable_for_direction(data, region_data)

    return ScrRunResult(data=output_data)
