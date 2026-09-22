import pytest

import blog_logic


class TestSlugify:
    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Hello, World", "hello-world"),
            ("  Leading and trailing  ", "leading-and-trailing"),
            ("Lots   of   spaces", "lots-of-spaces"),
            ("dash--soup - here", "dash-soup-here"),
            ("C++ & Godot!", "c-godot"),
            ("Already-a-slug", "already-a-slug"),
        ],
    )
    def test_normalizes_titles(self, title, expected):
        assert blog_logic.slugify(title) == expected

    @pytest.mark.parametrize("title", ["", "   ", "!!!", "---"])
    def test_falls_back_when_nothing_usable_is_left(self, title):
        assert blog_logic.slugify(title) == "post"


class TestUniqueSlug:
    def test_returns_base_when_free(self, site):
        assert blog_logic.unique_slug("my-post", set()) == "my-post"

    def test_skips_slugs_already_in_the_index(self, site):
        assert blog_logic.unique_slug("my-post", {"my-post.html"}) == "my-post-2"

    def test_skips_slugs_that_exist_on_disk_but_not_in_the_index(self, site):
        (site / "blog" / "my-post.html").write_text("x", encoding="utf-8")
        assert blog_logic.unique_slug("my-post", set()) == "my-post-2"

    def test_keeps_counting_past_collisions(self, site):
        taken = {"my-post.html", "my-post-2.html", "my-post-3.html"}
        assert blog_logic.unique_slug("my-post", taken) == "my-post-4"


class TestExcerpt:
    def test_takes_the_first_sentence(self):
        assert blog_logic.strip_tags_and_excerpt("One. Two. Three.") == "One."

    @pytest.mark.parametrize("end", [".", "!", "?"])
    def test_recognizes_all_sentence_terminators(self, end):
        assert blog_logic.strip_tags_and_excerpt(f"First{end} Second.") == f"First{end}"

    def test_strips_html_tags(self):
        html = "<p>Today, in my <i>overwhelming</i> desire to ship. More.</p>"
        assert blog_logic.strip_tags_and_excerpt(html) == "Today, in my overwhelming desire to ship."

    def test_does_not_leave_a_space_before_punctuation_after_a_closing_tag(self):
        assert blog_logic.strip_tags_and_excerpt("<p>It was <b>fun</b>. Really.</p>") == "It was fun."

    def test_collapses_whitespace_across_lines(self):
        assert blog_logic.strip_tags_and_excerpt("<p>Line one\n   still one.</p>\n<p>Two.</p>") == "Line one still one."

    def test_without_a_terminator_uses_the_whole_text(self):
        assert blog_logic.strip_tags_and_excerpt("No punctuation here") == "No punctuation here"

    def test_truncates_long_sentences_with_an_ellipsis(self):
        result = blog_logic.strip_tags_and_excerpt("word " * 100)
        assert result.endswith("…")
        assert len(result) <= 151  # 150 chars + the ellipsis

    def test_max_len_is_configurable(self):
        assert blog_logic.strip_tags_and_excerpt("abcdefghij", max_len=4) == "abcd…"

    def test_empty_body(self):
        assert blog_logic.strip_tags_and_excerpt("") == ""


class TestIndentBody:
    def test_wraps_plain_lines_in_paragraphs(self):
        assert blog_logic.indent_body("hello") == "            <p>hello</p>"

    def test_passes_html_lines_through_untouched(self):
        assert blog_logic.indent_body('<img src="x.png">') == '            <img src="x.png">'

    def test_drops_blank_lines_and_indents_every_line(self):
        out = blog_logic.indent_body("one\n\n   \n<p>two</p>")
        assert out == "            <p>one</p>\n            <p>two</p>"

    def test_empty_body_becomes_an_empty_paragraph(self):
        assert blog_logic.indent_body("") == "            <p></p>"
        assert blog_logic.indent_body("  \n \n") == "            <p></p>"


class TestRenderAndExtract:
    def test_rendered_page_contains_the_pieces(self):
        html = blog_logic.render_post_html("My Title", "Devlog", "2026-01-02", "<p>Body.</p>")
        assert "<title>My Title - PettyPixels</title>" in html
        assert '<h1 class="panel-title">My Title</h1>' in html
        assert '<p class="copyright">Devlog | 2026-01-02</p>' in html
        assert "<p>Body.</p>" in html

    def test_extract_returns_the_body_that_was_rendered(self):
        body = "<p>First.</p>\n<img src=\"x.png\">\n<p>Second.</p>"
        html = blog_logic.render_post_html("T", "Devlog", "2026-01-02", body)
        assert blog_logic.extract_body(html) == body

    def test_plain_lines_come_back_as_paragraphs(self):
        html = blog_logic.render_post_html("T", "Devlog", "2026-01-02", "just text")
        assert blog_logic.extract_body(html) == "<p>just text</p>"

    def test_editing_without_changes_is_stable(self):
        """Open a post, save it untouched, repeat: the page must not drift."""
        first = blog_logic.render_post_html("T", "Devlog", "2026-01-02", "line one\n<p>line two</p>")
        second = blog_logic.render_post_html("T", "Devlog", "2026-01-02", blog_logic.extract_body(first))
        assert second == first

    def test_extract_returns_empty_string_when_markers_are_missing(self):
        assert blog_logic.extract_body("<html><body>not a generated post</body></html>") == ""
