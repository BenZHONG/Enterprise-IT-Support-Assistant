import re

import pytest

from assistant_app.rag.documents import (
    KnowledgeBaseError,
    load_documents,
    parse_document,
)
from assistant_app.roles import ROLE_EMPLOYEE

VALID = """---
id: KB-900
title: Test Document
version: 1.0
topic: wifi
allowed_roles: employee, it_support_agent
---
# Heading

Some body text.
"""


def test_default_knowledge_base_loads():
    documents = load_documents()
    assert len(documents) >= 5


def test_every_required_topic_is_covered():
    topics = {d.topic for d in load_documents()}
    assert {"wifi", "vpn", "password", "microsoft365", "hardware", "outage"} <= topics


def test_ids_and_versions_have_the_expected_format():
    for d in load_documents():
        assert re.fullmatch(r"KB-\d{3}", d.doc_id)
        assert re.fullmatch(r"\d+\.\d+", d.version)


def test_restricted_document_is_not_visible_to_employees():
    documents = load_documents()
    visible = [d for d in documents if ROLE_EMPLOYEE in d.allowed_roles]
    restricted = [d for d in documents if ROLE_EMPLOYEE not in d.allowed_roles]
    assert len(visible) >= 5
    assert restricted
    secret = "network-ops@example.com"
    assert any(secret in d.body for d in restricted)
    assert not any(secret in d.body for d in visible)


def test_bodies_only_use_example_domains():
    for d in load_documents():
        hosts = re.findall(r"https?://([^/\s)]+)", d.body)
        hosts += re.findall(r"[\w.+-]+@([\w.-]+)", d.body)
        hosts = [h.rstrip(".,;:") for h in hosts]  # drop sentence punctuation
        assert all(h == "example.com" or h.endswith(".example.com") for h in hosts), (
            d.doc_id
        )


def test_parse_valid_document():
    doc = parse_document(VALID)
    assert doc.doc_id == "KB-900"
    assert doc.title == "Test Document"
    assert doc.version == "1.0"
    assert doc.topic == "wifi"
    assert doc.allowed_roles == ("employee", "it_support_agent")
    assert doc.body.startswith("# Heading")


def test_crlf_line_endings_are_accepted():
    doc = parse_document(VALID.replace("\n", "\r\n"))
    assert doc.doc_id == "KB-900"


def test_missing_front_matter_is_rejected():
    with pytest.raises(KnowledgeBaseError, match="front matter"):
        parse_document("# Just text, no header")


def test_missing_key_is_rejected():
    with pytest.raises(KnowledgeBaseError, match="topic"):
        parse_document(VALID.replace("topic: wifi\n", ""))


def test_unknown_key_is_rejected():
    with pytest.raises(KnowledgeBaseError, match="unknown"):
        parse_document(VALID.replace("topic: wifi\n", "topic: wifi\ncolour: blue\n"))


def test_bad_version_is_rejected():
    with pytest.raises(KnowledgeBaseError, match="version"):
        parse_document(VALID.replace("version: 1.0", "version: one"))


def test_unknown_role_is_rejected():
    with pytest.raises(KnowledgeBaseError, match="role"):
        parse_document(VALID.replace("it_support_agent", "wizard"))


def test_empty_body_is_rejected():
    header_only = VALID.split("# Heading")[0]
    with pytest.raises(KnowledgeBaseError, match="empty"):
        parse_document(header_only)


def test_duplicate_ids_across_files_are_rejected(tmp_path):
    (tmp_path / "a.md").write_text(VALID, encoding="utf-8")
    (tmp_path / "b.md").write_text(VALID, encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="duplicate"):
        load_documents(tmp_path)


def test_missing_directory_is_rejected(tmp_path):
    with pytest.raises(KnowledgeBaseError, match="not found"):
        load_documents(tmp_path / "nope")


def test_empty_directory_is_rejected(tmp_path):
    with pytest.raises(KnowledgeBaseError, match="no .md"):
        load_documents(tmp_path)
