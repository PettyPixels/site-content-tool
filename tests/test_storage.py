import json

import pytest

import storage


class TestLoadEntries:
    def test_missing_file_returns_empty_list(self, site):
        assert storage.load_entries("art.json") == []

    def test_returns_the_saved_list(self, site):
        (site / "data" / "art.json").write_text(
            json.dumps([{"title": "Sketch"}]), encoding="utf-8"
        )
        assert storage.load_entries("art.json") == [{"title": "Sketch"}]

    def test_invalid_json_raises_JSONParseError(self, site):
        (site / "data" / "art.json").write_text("{not valid json", encoding="utf-8")
        with pytest.raises(storage.JSONParseError):
            storage.load_entries("art.json")

    def test_error_names_the_offending_file(self, site):
        (site / "data" / "art.json").write_text("{not valid json", encoding="utf-8")
        with pytest.raises(storage.JSONParseError, match="art.json"):
            storage.load_entries("art.json")


class TestSaveEntries:
    def test_round_trips_through_load(self, site):
        entries = [{"title": "Sketch"}, {"title": "Doodle"}]
        storage.save_entries("art.json", entries)
        assert storage.load_entries("art.json") == entries

    def test_creates_the_data_dir_if_it_was_removed(self, site):
        (site / "data").rmdir()
        storage.save_entries("art.json", [{"title": "Sketch"}])
        assert storage.load_entries("art.json") == [{"title": "Sketch"}]

    def test_overwrites_rather_than_appends(self, site):
        storage.save_entries("art.json", [{"title": "First"}])
        storage.save_entries("art.json", [{"title": "Second"}])
        assert storage.load_entries("art.json") == [{"title": "Second"}]

    def test_file_is_human_editable(self, site):
        storage.save_entries("art.json", [{"title": "Sketch"}])
        text = (site / "data" / "art.json").read_text(encoding="utf-8")
        assert "\n" in text  # not one unbroken line
        assert text.endswith("\n")  # trailing newline, like a hand-written file

    def test_no_leftover_temp_file_after_a_successful_save(self, site):
        storage.save_entries("art.json", [{"title": "Sketch"}])
        leftovers = list((site / "data").glob("*.tmp"))
        assert leftovers == []

    def test_a_failed_save_leaves_the_previous_file_untouched(self, site):
        """Atomicity: a save that fails partway through must not corrupt or
        truncate the existing file. A python `set` isn't valid JSON, so
        json.dump raises TypeError partway through — a real failure, not a
        mocked one, exercising the actual except-block cleanup path."""
        storage.save_entries("art.json", [{"title": "Original"}])

        with pytest.raises(TypeError):
            storage.save_entries("art.json", [{"title": "New", "bad": {1, 2, 3}}])

        assert storage.load_entries("art.json") == [{"title": "Original"}]

    def test_a_failed_save_does_not_leave_a_temp_file_behind(self, site):
        with pytest.raises(TypeError):
            storage.save_entries("art.json", [{"bad": {1, 2, 3}}])

        leftovers = list((site / "data").glob("*.tmp"))
        assert leftovers == []


class TestCopyImage:
    def _images_dir(self, site):
        return site / "media" / "images" / "art"

    def _make_source(self, tmp_path, name="cover.png", content=b"fake-image-bytes"):
        tmp_path.mkdir(parents=True, exist_ok=True)
        source = tmp_path / name
        source.write_bytes(content)
        return source

    def test_copies_the_file_into_images_dir(self, site, tmp_path):
        images_dir = self._images_dir(site)
        source = self._make_source(tmp_path)

        storage.copy_image(source, images_dir)

        assert (images_dir / "cover.png").read_bytes() == b"fake-image-bytes"

    def test_creates_images_dir_if_missing(self, site, tmp_path):
        images_dir = self._images_dir(site)
        source = self._make_source(tmp_path)

        assert not images_dir.exists()
        storage.copy_image(source, images_dir)
        assert images_dir.is_dir()

    def test_returned_path_is_relative_to_the_site_root(self, site, tmp_path):
        images_dir = self._images_dir(site)
        source = self._make_source(tmp_path)

        result = storage.copy_image(source, images_dir)

        assert result == "media/images/art/cover.png"

    def test_returned_path_always_uses_forward_slashes(self, site, tmp_path):
        """Regression test for the media\\images\\art\\... paths already sitting
        in data/art.json: on Windows, str(Path(...)) uses backslashes, which
        is not a valid path separator in an HTML src or a URL."""
        images_dir = self._images_dir(site)
        source = self._make_source(tmp_path)

        result = storage.copy_image(source, images_dir)

        assert "\\" not in result

    def test_a_name_collision_gets_a_numeric_suffix(self, site, tmp_path):
        images_dir = self._images_dir(site)
        first_source = self._make_source(tmp_path / "a", content=b"first")
        second_source = self._make_source(tmp_path / "b", content=b"second")

        first_result = storage.copy_image(first_source, images_dir)
        second_result = storage.copy_image(second_source, images_dir)

        assert first_result.endswith("cover.png")
        assert second_result.endswith("cover-2.png")
        assert (images_dir / "cover.png").read_bytes() == b"first"
        assert (images_dir / "cover-2.png").read_bytes() == b"second"

    def test_collisions_keep_counting_up(self, site, tmp_path):
        images_dir = self._images_dir(site)
        for i in range(3):
            source = self._make_source(tmp_path / str(i), content=str(i).encode())
            storage.copy_image(source, images_dir)

        assert (images_dir / "cover.png").exists()
        assert (images_dir / "cover-2.png").exists()
        assert (images_dir / "cover-3.png").exists()

    def test_reselecting_an_image_already_in_the_folder_does_not_duplicate_it(self, site, tmp_path):
        images_dir = self._images_dir(site)
        source = self._make_source(tmp_path)
        first_result = storage.copy_image(source, images_dir)

        already_there = images_dir / "cover.png"
        second_result = storage.copy_image(already_there, images_dir)

        assert second_result == first_result
        assert list(images_dir.iterdir()) == [already_there]  # no cover-2.png
