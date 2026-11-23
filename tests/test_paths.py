import os

import pytest

from m1_work import paths


def test_uri_roundtrip_plain():
    root = os.path.abspath(os.sep + "data")
    rel = "test/0_safe_walkway_violation/0_te21.mp4"
    assert paths.to_uri(os.path.join(root, *rel.split("/")), root) == \
        "saferaw://" + rel


def test_uri_encodes_spaces_in_dir_name():
    root = os.path.abspath(os.sep + "data")
    rel = "test/2_opened_panel cover/2_te12.mp4"
    uri = paths.to_uri(os.path.join(root, *rel.split("/")), root)
    assert " " not in uri
    assert uri.endswith("2_opened_panel%20cover/2_te12.mp4")


def test_to_rel_rejects_paths_outside_root():
    root = os.path.abspath(os.sep + "data")
    with pytest.raises(ValueError):
        paths.to_rel(os.path.join(os.path.dirname(root), "other.mp4"), root)


def test_resolve_invalid_uri_returns_error_not_raises():
    r = paths.resolve_uri("file:///etc/passwd")
    assert r["ok"] is False
    assert r["error"] == "invalid_uri"


def test_resolve_missing_file_returns_not_found(tmp_path):
    uri = "{}://test/0_safe_walkway_violation/none.mp4".format(paths.config.URI_SCHEME)
    r = paths.resolve_uri(uri, str(tmp_path))
    assert r["ok"] is False
    assert r["error"] == "not_found"


def test_resolve_ok(tmp_path):
    d = tmp_path / "test" / "0_safe_walkway_violation"
    d.mkdir(parents=True)
    f = d / "a.mp4"
    f.write_bytes(b"x")
    uri = paths.to_uri(str(f), str(tmp_path))
    r = paths.resolve_uri(uri, str(tmp_path))
    assert r["ok"] is True
    assert r["abs_path"] == str(f)
