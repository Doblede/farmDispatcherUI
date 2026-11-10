"""Shared names used across the tool."""

ROOT_SHOT = "Shot"
ROOT_STACKS = "Stacks"
ROOT_RENDERS = "Renders"

# Attribute types understood by the property editor and the exporter.
ATTR_BOOL = "bool"
ATTR_INT = "int"
ATTR_FLOAT = "float"
ATTR_STRING = "string"
ATTR_LIST = "list"
ATTR_PATH = "path"
ATTR_HAIR_COMPONENTS = "hair_component_list"

# Attributes with special meaning.
ENABLE = "enable"
START_FRAME = "startFrame"
END_FRAME = "endFrame"
SUBMIT_RENDER = "submitRender"
RIG_CHAR_VAR = "rigCharVar"

# Step groups (the "group" key in node definitions).
GROUP_CLOTH = "cloth"
GROUP_HAIR = "hair"
GROUP_RENDER = "render"

# A render setup whose "input" contains this gets every character on shot load.
ALL_CHARACTERS = "ALL CHARACTERS"

# Farm label shown to the user -> queue server written to the submission.
FARMS = {
    "DEV": "dev",
    "STAGING": "staging",
    "PROD": "prod",
    "NONE": "none",
}
DEFAULT_FARM = "DEV"
