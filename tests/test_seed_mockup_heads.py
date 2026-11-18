"""The demo heads and signatures in scripts/seed_mockup.py (owner, 18 Nov 2026): every opinion
box of a demo request slip is signed."""

import io

from PIL import Image

from scripts.seed_mockup import HEADS, _set_heads, _signatures, draw_signature


def test_a_drawn_signature_is_a_clean_png_and_the_same_each_time():
    png = draw_signature("Ly Sophal")
    image = Image.open(io.BytesIO(png))
    assert image.format == "PNG"
    assert image.mode == "RGBA"  # cleaned like an upload: see-through paper
    assert draw_signature("Ly Sophal") == png
    assert draw_signature("Chan Malis") != png


def _org(make_department, make_division):
    """The demo staff's departments and offices, by the names the seed looks for."""
    departments, divisions = {}, {}
    for head in HEADS:
        department, division = head.division
        if department not in departments:
            departments[department] = make_department(name_en=department)
        if head.division not in divisions:
            divisions[head.division] = make_division(
                department=departments[department], name_en=division
            )
    return departments, divisions


def test_heads_are_set_only_where_none_is(db_session, make_department, make_division, make_user):
    departments, divisions = _org(make_department, make_division)
    users = {head.staff_id: make_user(name_en=head.name_en) for head in HEADS}
    admin_pick = make_user(name_en="Set by an Admin")
    departments["Statistics Department"].head_user_id = admin_pick.id
    db_session.flush()

    assert _set_heads(db_session, users) == len(HEADS) - 1
    assert departments["Statistics Department"].head_user_id == admin_pick.id  # never replaced
    assert (
        departments["Monetary Policy and Research Department"].head_user_id == users["HEAD-203"].id
    )
    assert divisions[("Monetary Policy and Research Department", "Research")].head_user_id == (
        users["HEAD-204"].id
    )
    assert _set_heads(db_session, users) == 0  # safe to run again


def test_signatures_are_drawn_only_for_who_has_none(db_session, settings, make_user):
    users = {"HEAD-201": make_user(), "DEMO-103": make_user(user_signature="users/5/mine.png")}
    assert _signatures(db_session, settings, users) == 1
    stored = users["HEAD-201"].user_signature
    assert (settings.signature_dir / stored).is_file()
    assert users["DEMO-103"].user_signature == "users/5/mine.png"
