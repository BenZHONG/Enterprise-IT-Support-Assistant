"""Load and validate knowledge base documents.

Each file is Markdown with a front matter block at the top:

    ---
    id: KB-001
    title: Wi-Fi Troubleshooting
    version: 1.2
    topic: wifi
    allowed_roles: employee, it_support_agent, it_administrator
    ---
    (document body)

Stage 9 adds chunking and embeddings on top of this loader. The
metadata (id, title, version, allowed_roles) is validated now so it
can travel with every chunk later.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from assistant_app.roles import ALL_ROLES

# documents.py -> rag -> assistant_app -> project root
DEFAULT_KB_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge_base"

_KEYS = frozenset({"id", "title", "version", "topic", "allowed_roles"})
_ID_RE = re.compile(r"^KB-\d{3}$")
_VERSION_RE = re.compile(r"^\d+\.\d+$")
_TOPIC_RE = re.compile(r"^[a-z0-9]+$")


class KnowledgeBaseError(Exception):
    """A knowledge document or folder is invalid."""


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    version: str
    topic: str
    allowed_roles: tuple[str, ...]
    body: str
    source_file: str


def parse_document(text: str, source_file: str = "<text>") -> KnowledgeDocument:
    """Parse one document. Raises KnowledgeBaseError if anything is wrong."""
    # Windows tools may add a BOM or CRLF line endings. Accept both.
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise KnowledgeBaseError(f"{source_file}: missing front matter")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise KnowledgeBaseError(f"{source_file}: front matter is not closed")
    header, body = text[4:end], text[end + 5 :].strip()

    fields: dict[str, str] = {}
    for line in header.split("\n"):
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator:
            raise KnowledgeBaseError(f"{source_file}: malformed front matter line")
        if key not in _KEYS:
            raise KnowledgeBaseError(f"{source_file}: unknown front matter key '{key}'")
        if key in fields:
            raise KnowledgeBaseError(
                f"{source_file}: duplicate front matter key '{key}'"
            )
        fields[key] = value

    missing = _KEYS - fields.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise KnowledgeBaseError(f"{source_file}: missing front matter keys: {names}")

    if not _ID_RE.match(fields["id"]):
        raise KnowledgeBaseError(f"{source_file}: id must look like KB-001")
    if not _VERSION_RE.match(fields["version"]):
        raise KnowledgeBaseError(f"{source_file}: version must look like 1.0")
    if not _TOPIC_RE.match(fields["topic"]):
        raise KnowledgeBaseError(
            f"{source_file}: topic must be lowercase letters or digits"
        )
    if not 1 <= len(fields["title"]) <= 100:
        raise KnowledgeBaseError(f"{source_file}: title must be 1-100 characters")

    roles = tuple(r.strip() for r in fields["allowed_roles"].split(",") if r.strip())
    if not roles:
        raise KnowledgeBaseError(f"{source_file}: allowed_roles must not be empty")
    unknown = [r for r in roles if r not in ALL_ROLES]
    if unknown:
        raise KnowledgeBaseError(f"{source_file}: unknown role {unknown[0]!r}")

    if not body:
        raise KnowledgeBaseError(f"{source_file}: empty body")

    return KnowledgeDocument(
        doc_id=fields["id"],
        title=fields["title"],
        version=fields["version"],
        topic=fields["topic"],
        allowed_roles=roles,
        body=body,
        source_file=source_file,
    )


def load_documents(
    directory: str | Path | None = None,
) -> tuple[KnowledgeDocument, ...]:
    """Load every .md file in the folder, sorted by file name."""
    folder = Path(directory) if directory is not None else DEFAULT_KB_DIR
    if not folder.is_dir():
        raise KnowledgeBaseError(f"knowledge base directory not found: {folder}")
    files = sorted(folder.glob("*.md"))
    if not files:
        raise KnowledgeBaseError(f"no .md documents found in {folder}")

    documents: list[KnowledgeDocument] = []
    seen: set[str] = set()
    for path in files:
        document = parse_document(path.read_text(encoding="utf-8-sig"), path.name)
        if document.doc_id in seen:
            raise KnowledgeBaseError(f"duplicate document id {document.doc_id}")
        seen.add(document.doc_id)
        documents.append(document)
    return tuple(documents)
