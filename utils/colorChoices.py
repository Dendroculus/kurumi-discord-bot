"""
This module defines a list of color choices for role color selection in Discord.
Each color choice is represented as an instance of discord.app_commands.Choice with a name and a hex value.
"""

from discord import app_commands
def get_color_choices(colorname: str, value: str) -> list[app_commands.Choice[str]]:
    """Return a list of color choices for role color selection."""
    if value[0] != "#" or len(value) != 7:
        raise ValueError("Color value must be a hex string like #RRGGBB")
    
    return app_commands.Choice(name=colorname, value=value)

colors = {
    "Red": "#FF0000",
    "Green": "#00FF00",
    "Blue": "#0000FF",
    "Yellow": "#FFFF00",
    "Purple": "#800080",
    "Orange": "#FFA500",
    "Pink": "#FFC0CB",
    "Cyan": "#00FFFF",
    "White": "#FFFFFF",
    "Black": "#000000",
    "Teal": "#008080",
    "Lime": "#32CD32",
    "Magenta": "#FF00FF",
    "Indigo": "#4B0082",
    "Turquoise": "#40E0D0",
    "Gold": "#FFD700",
    "Silver": "#C0C0C0",
    "Brown": "#8B4513",
    "Lavender": "#E6E6FA",
    "Navy": "#000080",
}
color_choices = [get_color_choices(name, value) for name, value in colors.items()]
