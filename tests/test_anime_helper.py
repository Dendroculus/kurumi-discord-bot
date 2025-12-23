import pytest
import discord
from utils.animeHelper import (
    build_character_embed,
    build_anime_embed,
    build_character_select_options,
    build_anime_options,
    format_character_media_list,
    GenericSelectView,
)

def test_format_character_media_list_empty():
    assert format_character_media_list([]) == "`N/A`"

def test_format_character_media_list_truncates():
    nodes = [{"title": {"english": f"Title{i}"}} for i in range(6)]
    text = format_character_media_list(nodes)
    assert text.startswith("`Title0` `Title1` `Title2` `Title3`")
    assert text.endswith("...")

def test_build_character_embed_basic():
    data = {
        "id": 1,
        "name": {"full": "Kurumi", "native": "狂三"},
        "description": "Desc",
        "image": {"large": "http://img"},
        "gender": "F",
        "age": "17",
        "bloodType": "O",
        "dateOfBirth": {"year": 2000, "month": 1, "day": 2},
        "favourites": 99,
        "media": {"nodes": [{"title": {"english": "Anime1"}}]},
        "siteUrl": "http://site",
    }
    embed = build_character_embed(data)
    assert embed.title == "Kurumi"
    assert embed.url == "http://site"
    assert any(field.name == "📋 Info" for field in embed.fields)
    assert embed.footer.text == "Provided by AniList"

def test_build_anime_embed_fields():
    data = {
        "id": 1,
        "title": {"english": "Re:Zero", "romaji": "ReZero"},
        "siteUrl": "http://site",
        "description": "An isekai",
        "coverImage": {"medium": "http://cover"},
        "bannerImage": "http://banner",
        "episodes": 25,
        "status": "finished",
        "startDate": {"year": 2016, "month": 4, "day": 1},
        "endDate": {"year": 2016, "month": 9, "day": 1},
        "duration": 24,
        "studios": {"nodes": [{"name": "White Fox"}]},
        "source": "Light Novel",
        "averageScore": 90,
        "popularity": 1000,
        "favourites": 500,
        "genres": ["Fantasy", "Drama"],
    }
    embed = build_anime_embed(data)
    assert embed.title == "Re:Zero"
    names = [f.name for f in embed.fields]
    assert "Episodes" in names
    assert "Score" in names
    assert embed.thumbnail.url == "http://cover"
    assert embed.image.url == "http://banner"

def test_build_character_select_options():
    results = [
        {"id": 1, "name": {"full": "A", "native": "Aa"}},
        {"id": 2, "name": {"full": "B", "native": "Bb"}},
    ]
    opts = build_character_select_options(results)
    assert len(opts) == 2
    assert opts[0].value == "1"
    assert opts[1].label == "B"

def test_build_anime_options():
    results = [
        {"id": 10, "title": {"english": "X", "romaji": "X"}, "episodes": 12, "season": "SPRING"},
    ]
    opts = build_anime_options(results)
    assert len(opts) == 1
    assert opts[0].value == "10"

@pytest.mark.asyncio
async def test_generic_select_view_maps_entries():
    # discord.ui.View requires a running event loop; make this test async
    opts = [discord.SelectOption(label="A", value="1")]
    entries = [{"id": 1, "name": {"full": "A"}}]
    view = GenericSelectView(opts, entries, embed_builder=lambda x: discord.Embed(title="x"))
    assert view.by_id["1"]["name"]["full"] == "A"