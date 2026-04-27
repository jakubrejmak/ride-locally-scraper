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

from logging import getLogger

import openrouter
from visual.image_utils import (
    crop_image_to_square,
    region_to_square,
    stack_images_horizontal,
    stack_images_vertical,
)
from visual.pdf import pdf_to_jpg

from conf import config
from lib.llm.openrouter_utils import OpenRouterUtils as utils
from models.files import FileData, ScrRunResult
from models.preprocessors import REGION_TYPES, Region, TimetableRegions

log = getLogger(__name__)


type RegionData = dict[bytes, TimetableRegions | None]


async def _get_region_descriptions(data: bytes, cfg):
    """Extract region descriptions from a timetable image using LLM.

    Sends the image to an LLM with structured output to identify and describe
    meaningful regions (header, footer, stop_names, time_grids, other).

    Args:
        data: JPEG image bytes of a timetable page
        cfg: Script configuration containing 'llm_model' and 'system_prompt'

    Returns:
        TimetableRegions object with validated region descriptions, or None on parse failure

    Raises:
        ValueError: If required config values are missing
    """
    # outputs the region descriptions of the image in a structured json using structured response
    model = cfg.get("llm_model")
    system_prompt = cfg.get("system_prompt")

    if not model or not system_prompt:
        raise ValueError("Script needs 'llm_model' and 'system_prompt' configured")

    image_url = utils._get_img_data_url(data, "image/jpeg")
    payload = {
        "model": model,
        "messages": utils.build_messages(
            utils.add_message("system", system_prompt),
            utils.add_message("user", image_url, "image_url"),
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

    return regions


def _validate_region_data(region_data: RegionData):
    """Check region_data is valid:
    - every image has one or two time_grid regions
    - every region type (footer, header, stop_names) has one region
    """
    REQUIRED_REGION_COUNTS = {
        "1": ["footer", "header", "stop_names"],
        "1-2": ["time_grid"],
    }
    # build region type -> count in region_data map
    regions_by_type: dict[str, int] = {}  # type -> type count in region_data
    for tt_region in region_data.values():
        if not tt_region:
            continue
        for region in tt_region.regions:
            regions_by_type[region.type] = regions_by_type.get(region.type, 0) + 1

    def _cmp_int(rule: str, value: int) -> bool:
        """Supports operators:
        `-` range
        `no special chars in rule` exact match
        """
        if "-" in rule:
            parts = rule.split("-")
            if len(parts) == 2:
                min_val, max_val = parts
                return int(min_val) <= value <= int(max_val)
        else:
            return value == int(rule)
        return False

    # validate against the REQUIRED_REGION_COUNTS map
    for rule, types in REQUIRED_REGION_COUNTS.items():
        for k, v in regions_by_type.items():
            if k in types:
                res = _cmp_int(rule, v)
                if not res:
                    return {
                        "ok": False,
                        "err": f"Type {type} failed validation against rule {rule}",
                    }
            else:
                return {"ok": False, "err": f"Type {k} not found in region_data"}

    return {"ok": True, "err": None}


def _get_imgs_by_type(type: str, region_data: RegionData):
    result: list[tuple[bytes, Region]] = []
    for i1, d1 in region_data.items():
        if not d1:
            continue
        for r1 in d1.regions:
            if r1.type == type:
                result.append((i1, r1))
    return result


type DirectionImage = tuple[str, bytes]
type DirectionsData = dict[int, list[DirectionImage]]


def _compose_timetable_for_direction(
    region_data: RegionData,
) -> list[FileData]:
    """Compose images for each time_grid direction using cut-and-paste.
    Region data is keyed like:
    image bytes -> `region_data` describing it
    """
    DIRECTION_TYPE = "time_grid"
    TYPES_REST = tuple(type for type in REGION_TYPES if type != DIRECTION_TYPE)

    valid = _validate_region_data(region_data)
    if not valid["ok"]:
        raise Exception(f"Invalid region data: {valid['err']}")

    ###
    # IMPORTANT:
    # the order in which the image types will be appended is derived from the
    # order of region types defined in REGION_TYPES.
    ###
    data_per_direction: DirectionsData = {}
    direction_count = 0
    for i1, d1 in region_data.items():
        if not d1:
            continue
        for region in d1.regions:
            if region.type == DIRECTION_TYPE:
                direction_image = crop_image_to_square(i1, region_to_square(region))
                data_per_direction[direction_count].append(
                    (region.type, direction_image)
                )
                for type in TYPES_REST:
                    images_w_type = _get_imgs_by_type(type, region_data)
                    # assemble image by joining multiple images labeled as a ``type``
                    visual_data: list[bytes] = []
                    for i2, r2 in images_w_type:
                        visual_data.append(
                            crop_image_to_square(i2, region_to_square(r2))
                        )
                    joined_type_image = stack_images_vertical(visual_data)
                    data_per_direction[direction_count].append(
                        (type, joined_type_image)
                    )
                direction_count += 1

    # for every direction compose image from list[bytes] in `data_per_direction`
    # and transform to FileData
    output_data: list[FileData] = []

    def _get_image_from_list(type: str, list: list[DirectionImage]) -> bytes | None:
        for t, i in list:
            if t == type:
                return i
        return None

    for i, images in data_per_direction.items():
        # TODO
        PARTS = {"header", "stop_names", "time_grid", "footer", "other"}

        for part in PARTS:
            PARTS[part] = _get_image_from_list(part, images)

        header_img = _get_image_from_list("header", images)
        stop_names_img = _get_image_from_list("stop_names", images)
        time_grid_img = _get_image_from_list("time_grid", images)
        footer_img = _get_image_from_list("footer", images)
        other_img = _get_image_from_list("other", images)

        main_area_horizontal = stack_images_horizontal([stop_names_img, time_grid_img])
        stacked_img = stack_images_vertical(
            [header_img, main_area_horizontal, footer_img, other_img]
        )
        if not stacked_img:
            raise ValueError(
                f"Failed to stack images for direction {i} out of {len(data_per_direction.keys())}"
            )
        output_data.append(
            FileData(
                mime="image/jpeg",
                ext="jpg",
                bytes=stacked_img,
                description=f"Direction {i}",
            )
        )

    return output_data


async def run(input: ScrRunResult, **kwargs) -> ScrRunResult | None:
    """Process a timetable document and extract route directions as separate images.

    Accepts a PDF or JPEG timetable, uses an LLM to identify region bounding boxes
    (header, footer, stop_names, time_grids, other), then composes individual images
    for each route direction by assembling the relevant squares from source pages.

    Args:
        input: ScrRunResult containing a single FileData object (PDF or JPEG)
        **kwargs: keyword arguments including 'script_config' for LLM settings

    Returns:
        ScrRunResult with list of FileData objects, one per time_grid direction,
        or None if no valid regions found

    Raises:
        ValueError: If input doesn't contain exactly one FileData, or config is missing
    """
    if len(input.data) != 1:
        raise ValueError("Input data must contain exactly one FileData object")
    data = input.data[0].bytes
    data_mime = input.data[0].mime

    match data_mime:
        case "image/jpeg":
            pass
        case "application/pdf":
            data = pdf_to_jpg(data, prune_empty=True)
        case _:
            raise ValueError(f"Filetype '{data_mime}' is not supported")

    script_config = kwargs.get("script_config")
    if not script_config:
        raise ValueError("Script needs a script config")

    # split image into logical parts
    region_data: RegionData = {}  # mapping: image bytes to regions extracted from them
    if isinstance(data, list):
        for page in data:
            region_data[page] = await _get_region_descriptions(page, script_config)
    else:
        region_data[data] = await _get_region_descriptions(data, script_config)

    # assemble a list of FileData objects.
    # Each object is self sufficient piece of timetable data eg. a collection of:
    # header, direction (aka time_grid), footer
    output_data: list[FileData] = _compose_timetable_for_direction(region_data)

    return ScrRunResult(data=output_data)
