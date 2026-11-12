import io
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree

from platformdirs import user_data_path
from pypdf import PdfReader

from .common import require, success


async def download_resource(ucloud, resource_id: str, extension: str = "pdf"):
    require(
        extension in {"pdf", "docx", "pptx", "txt", "png", "jpg", "xlsx", "zip"},
        "不支持该文件扩展名。",
    )
    result = await ucloud.resource_url(resource_id)
    url = result["data"]["url"]
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    require(
        parsed.scheme == "https"
        and (host == "bupt.edu.cn" or host.endswith(".bupt.edu.cn"))
        and not parsed.username
        and not parsed.password
        and parsed.port in {None, 443},
        "该资源使用尚未核验的外部存储域名；可使用 resource_url 查看源链接。",
        "RESOURCE_HOST_NOT_VERIFIED",
    )
    # No school authentication headers or cookies are forwarded to file storage.
    from .transport import Transport

    transport = Transport()
    try:
        response = await transport.request("GET", url, limit=30_000_000)
    finally:
        await transport.close()
    require(response.is_success, "资源下载失败或返回重定向。", "DOWNLOAD_FAILED")
    require(
        "text/html" not in response.headers.get("content-type", ""),
        "资源返回了网页而非文件。",
        "DOWNLOAD_FAILED",
    )
    folder = user_data_path("bupt-agent", appauthor=False) / "downloads"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{resource_id}-{uuid4().hex[:8]}.{extension}"
    path.write_bytes(response.content)
    return success(
        {"resource_id": resource_id, "path": str(path.resolve()), "bytes": len(response.content)},
        "ucloud:resource_download",
    )


def read_document(path: str, max_chars: int = 30000):
    require(1 <= max_chars <= 100000, "max_chars 应为 1–100000。")
    file = Path(path).expanduser().resolve()
    folder = (user_data_path("bupt-agent", appauthor=False) / "downloads").resolve()
    require(file.is_relative_to(folder) and file.is_file(), "只能读取本工具下载目录中的文件。")
    require(file.stat().st_size <= 30_000_000, "文件超过 30MB。")
    units = []
    if file.suffix.lower() == ".pdf":
        reader = PdfReader(file)
        require(not reader.is_encrypted, "暂不支持加密 PDF。")
        for i, page in enumerate(reader.pages):
            units.append({"locator": f"page:{i + 1}", "text": page.extract_text() or ""})
            if sum(len(u["text"]) for u in units) > max_chars:
                break
        full_units = len(reader.pages)
    elif file.suffix.lower() in {".docx", ".pptx"}:
        with zipfile.ZipFile(io.BytesIO(file.read_bytes())) as archive:
            names = (
                ["word/document.xml"]
                if file.suffix.lower() == ".docx"
                else sorted(
                    n
                    for n in archive.namelist()
                    if n.startswith("ppt/slides/slide") and n.endswith(".xml")
                )
            )
            full_units = len(names)
            for name in names:
                require(archive.getinfo(name).file_size <= 8_000_000, "文档 XML 超过大小限制。")
                node = ElementTree.fromstring(archive.read(name))
                text = "\n".join(n.text for n in node.iter() if n.tag.endswith("}t") and n.text)
                units.append({"locator": name, "text": text})
                if sum(len(u["text"]) for u in units) > max_chars:
                    break
    else:
        require(file.suffix.lower() == ".txt", "正文读取目前支持 PDF、DOCX、PPTX、UTF-8 TXT。")
        units, full_units = [{"locator": "text", "text": file.read_text(encoding="utf-8")}], 1
    remaining, truncated = max_chars, len(units) < full_units
    for unit in units:
        truncated |= len(unit["text"]) > remaining
        unit["text"] = unit["text"][:remaining]
        remaining -= len(unit["text"])
    return success(
        {"path": str(file), "units": units, "truncated": truncated},
        "local:document",
        complete=not truncated,
        note="扫描 PDF 未做 OCR；无文本不代表原文无内容。",
    )
