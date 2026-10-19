from app.site.qa import check_site, score

GOOD = """<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width">
<title>Kaapi House, filter coffee in Pune</title>
<meta name="description" content="Filter coffee, a reading corner and slow breakfasts in Pune. Reserve a table.">
</head><body><a href="/">Home</a><a href="/menu">Menu</a><h1>Kaapi House</h1><h2>Menu</h2><h3>Coffee</h3>
<p>Open <span class="ph">[opening hours]</span></p></body></html>"""


def by_check(findings, page="home"):
    return {f.check: f for f in findings if f.page == page}


def test_clean_page_passes():
    pages = {"": GOOD, "menu": GOOD}
    f = by_check(check_site(pages, lambda s: f"/{s}"))
    assert all(x.severity == "pass" for k, x in f.items() if k != "details needed")
    assert f["details needed"].severity == "warn" and "1 [placeholders]" in f["details needed"].message
    assert score(check_site(pages, lambda s: f"/{s}")) == 100  # placeholders do not cost points


def test_problems_are_caught():
    bad = (
        GOOD.replace("<h2>Menu</h2><h3>Coffee</h3>", "<h1>Two</h1><h4>Coffee</h4>")
        .replace('href="/menu"', 'href="/missing"')
        .replace("</body>", "<script>x()</script>TODO</body>")
        .replace('<meta name="viewport" content="width=device-width">', "")
    )
    f = by_check(check_site({"": bad}, lambda s: f"/{s}"))
    assert f["one h1"].severity == "fail"
    assert f["heading order"].severity == "warn"
    assert f["internal links"].severity == "fail" and "/missing" in f["internal links"].message
    assert f["no scripts"].severity == "fail"
    assert f["mobile ready"].severity == "fail"
    assert f["leftover text"].severity == "fail"
    assert score(check_site({"": bad}, lambda s: f"/{s}")) < 40
