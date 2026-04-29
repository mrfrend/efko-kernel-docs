from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from mkdocs.config.defaults import MkDocsConfig

log = logging.getLogger(__name__)


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def on_post_build(*, config: MkDocsConfig) -> None:
    base_dir = Path(config.config_file_path).resolve().parent
    docs_dir = _resolve_path(base_dir, config.docs_dir)
    site_dir = _resolve_path(base_dir, config.site_dir)
    archive_path = site_dir / "downloads" / "docs.zip"

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    docs_files = [
        path
        for path in sorted(docs_dir.rglob("*"))
        if path.is_file() and path.resolve() != archive_path.resolve()
    ]

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        temp_archive = Path(tmp_file.name)

    try:
        with zipfile.ZipFile(temp_archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for path in docs_files:
                zip_file.write(path, arcname=path.relative_to(docs_dir))

        shutil.move(str(temp_archive), archive_path)
        log.info("Created documentation archive at %s", archive_path)
    finally:
        if temp_archive.exists():
            temp_archive.unlink(missing_ok=True)
