import pytest
from pydantic import ValidationError

from app.agents.copywriting import PageCopy
from app.agents.design import Palette, Typography, contrast

GOOD = {
    "background": "#f6efe3",
    "surface": "#fbf7f0",
    "ink": "#2b1d14",
    "muted": "#6b5847",
    "accent": "#8a3b1c",
    "accent_ink": "#fff8ef",
}


def test_contrast_math():
    assert round(contrast("#000000", "#ffffff"), 1) == 21.0
    assert contrast("#777777", "#777777") == 1.0


def test_good_palette_passes():
    assert Palette(**GOOD).accent == "#8a3b1c"


@pytest.mark.parametrize(
    "change,needle",
    [
        ({"ink": "#9a8a7a"}, "ink on background"),
        ({"accent_ink": "#9b5a3a"}, "accent_ink on accent"),
        ({"accent": "#7c3aed", "accent_ink": "#ffffff"}, "purple"),
        ({"surface": "blue"}, "hex"),
    ],
)
def test_bad_palettes_are_rejected_with_reasons(change, needle):
    with pytest.raises(ValidationError, match=needle):
        Palette(**{**GOOD, **change})


def test_fonts_must_come_from_the_list():
    with pytest.raises(ValidationError, match="heading_font"):
        Typography(heading_font="Comic Sans MS", body_font="Inter", heading_style="regular", why="x")


def section(**kw):
    return {"section": "Hero", "heading": "Filter coffee", "body": "Open daily.", **kw}


def test_copy_rules():
    ok = PageCopy(slug="", seo_title="Kaapi House", meta_description="Coffee.", sections=[section()])
    assert ok.sections[0].heading == "Filter coffee"
    with pytest.raises(ValidationError, match="elevate, seamless"):
        PageCopy(
            slug="",
            seo_title="x",
            meta_description="x",
            sections=[section(body="We elevate your seamless experience.")],
        )
    with pytest.raises(ValidationError):
        PageCopy(slug="", seo_title="x" * 61, meta_description="x", sections=[section()])
    with pytest.raises(ValidationError, match="to perfection"):
        PageCopy(slug="", seo_title="x", meta_description="x", sections=[section(body="Baked to perfection")])


def test_dashes_are_rewritten_not_rejected():
    page = PageCopy(
        slug="",
        seo_title="Bakehouse – Goan bakery",
        meta_description="Fresh bread - every day",
        sections=[section(heading="Poi—baked twice daily", body="Wood-fired, family-run.")],
    )
    assert page.seo_title == "Bakehouse, Goan bakery"
    assert page.meta_description == "Fresh bread, every day"
    assert page.sections[0].heading == "Poi, baked twice daily"
    assert page.sections[0].body == "Wood-fired, family-run."


def test_bullet_lists_survive_dash_cleanup():
    body = "What we treat:\n- Back pain\n- Knee pain"
    assert (
        PageCopy(slug="", seo_title="x", meta_description="x", sections=[section(body=body)]).sections[0].body == body
    )
