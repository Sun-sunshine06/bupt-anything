from zipfile import ZipFile

import pytest

from bupt_agent import files
from bupt_agent.common import AgentError


def test_docx_text_has_source_locator(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "user_data_path", lambda *a, **k: tmp_path)
    folder = tmp_path / "downloads"
    folder.mkdir()
    document = folder / "synthetic.docx"
    with ZipFile(document, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="urn:test"><w:p><w:t>合成资料正文</w:t></w:p></w:document>',
        )
    result = files.read_document(str(document))
    assert result["data"]["units"] == [{"locator": "word/document.xml", "text": "合成资料正文"}]
    assert result["meta"]["complete"]


def test_text_truncation_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "user_data_path", lambda *a, **k: tmp_path)
    folder = tmp_path / "downloads"
    folder.mkdir()
    document = folder / "synthetic.txt"
    document.write_text("合成资料正文", encoding="utf-8")
    result = files.read_document(str(document), max_chars=2)
    assert result["data"]["units"][0]["text"] == "合成"
    assert result["data"]["truncated"]
    assert not result["meta"]["complete"]


def test_unrelated_local_file_is_not_exposed(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "user_data_path", lambda *a, **k: tmp_path)
    other = tmp_path / "outside.txt"
    other.write_text("unrelated", encoding="utf-8")
    with pytest.raises(AgentError):
        files.read_document(str(other))
