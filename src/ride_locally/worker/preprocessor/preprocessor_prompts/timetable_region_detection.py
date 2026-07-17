PROMPT = """
# Timetable Region Detection

Draw tight bounding boxes around regions in this transport timetable image.

Coordinates use a 0–1000 scale (0 = top/left, 1000 = bottom/right).

## Region Types

- **header**: Everything above the main table (route info, carrier, titles, stamps)
- **time_grid**: A block of scheduled times with its column headers. **One box per direction** — if stops sit between two time blocks, that's two boxes.
- **stop_names**: The stop/station name column only
- **footer**: Everything below the main table (legend, footnotes, company info)
- **other**: Anything else meaningful — set `description`

## Rules

- Tight boxes, overlap OK
- `text_sample`: short exact text visible inside the box
- `description`: empty string unless type is `other`
- No reasoning. Just output the regions.
"""
