from app.site.render import _faq, _items, _split_item, contact_links, render_site

STRATEGY = {
    "primary_action": {"label": "Book now"},
    "pages": [{"slug": "", "title": "Home"}, {"slug": "contact", "title": "Contact"}],
}
STYLE = {
    "palette": {
        "background": "#f6efe3",
        "surface": "#fbf7f0",
        "ink": "#2b1d14",
        "muted": "#6b5847",
        "accent": "#8a3b1c",
        "accent_ink": "#fff8ef",
    },
    "typography": {"heading_font": "Fraunces", "body_font": "Inter", "heading_style": "italic accents"},
    "signature_ideas": [{"name": "Library card menu"}],
}
COPY = {
    "pages": [
        {
            "slug": "",
            "seo_title": "x",
            "meta_description": "y",
            "sections": [
                {"section": "hero", "heading": "Fresh poi daily", "body": "Baked twice a day.", "cta_label": None},
                {"section": "gallery", "heading": "Inside", "body": "Our oven.", "cta_label": None},
                {
                    "section": "services",
                    "heading": "Menu",
                    "body": "- Poi: soft bread. ₹10\n- Bebinca: layered cake. ₹80",
                    "cta_label": None,
                },
            ],
        },
        {
            "slug": "contact",
            "seo_title": "x",
            "meta_description": "y",
            "sections": [{"section": "contact", "heading": "Visit", "body": "Come by.", "cta_label": None}],
        },
    ]
}
LAYOUT = {
    "pages": [{"slug": "", "blocks": ["hero_image", "gallery", "services"]}, {"slug": "contact", "blocks": ["contact"]}]
}


def render(photos, details=None):
    return render_site(
        business_name="Bakehouse",
        business_type="bakery",
        city="Panaji",
        strategy=STRATEGY,
        style=STYLE,
        copy=COPY,
        layout=LAYOUT,
        url_for=lambda s: f"/{s}",
        photos=photos,
        details=details,
    )


def test_no_photos_falls_back_gracefully():
    home = render([])[""]
    assert 'class="hero-split"' in home and "hero-image" not in home.split("<main>")[1].split("</section>")[0]
    assert 'class="gallery"' not in home
    assert "<script" not in home


def test_photos_fill_image_blocks_and_credits():
    photos = [{"url": f"https://img.test/{i}.jpg", "alt": "a", "credit": f"Photo {i}, CC BY"} for i in range(6)]
    home = render(photos)[""]
    assert 'class="hero-image"' in home and 'class="gallery"' in home
    assert "Photo 0, CC BY" in home and "Photo credits" in home


def test_contact_actions_from_details():
    page = render(
        [], {"phone number": "98765 43210", "address": "Rua de Ourem, Panaji", "email address": "hi@bake.in"}
    )["contact"]
    assert 'href="tel:+919876543210"' in page and "https://wa.me/919876543210" in page
    assert "google.com/maps/search/?api=1&amp;query=Rua+de+Ourem%2C+Panaji" in page
    assert "mailto:hi@bake.in" in page


def test_parsers():
    assert _split_item("Bridal makeup: full look with trial. ₹4,500") == {
        "title": "Bridal makeup",
        "text": "full look with trial",
        "price": "₹4,500",
    }
    assert _items("Intro\n- One\n- Two") == {"lead": "Intro", "entries": ["One", "Two"]}
    assert _faq("Do you take bookings?\nYes, on WhatsApp.\nAre you open Sunday?\nNo.") == [
        {"q": "Do you take bookings?", "a": "Yes, on WhatsApp."},
        {"q": "Are you open Sunday?", "a": "No."},
    ]
    assert contact_links({"phone": "123"}, "#c")["phone"] == ""  # too short to be a number
