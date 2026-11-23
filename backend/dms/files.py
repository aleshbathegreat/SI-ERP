import hashlib
import mimetypes


def file_facts(uploaded):
    if not uploaded:
        return {}
    name = (getattr(uploaded, "name", "") or "").replace("\\", "/").split("/")[-1][:255]
    size = int(getattr(uploaded, "size", 0) or 0)
    mime = (getattr(uploaded, "content_type", "") or "")[:120]
    if not mime:
        mime = (mimetypes.guess_type(name)[0] or "")[:120]
    if hasattr(uploaded, "seek"):
        try:
            uploaded.seek(0)
        except Exception:
            pass
    digest = hashlib.sha256()
    if hasattr(uploaded, "chunks"):
        for chunk in uploaded.chunks():
            digest.update(chunk)
    elif hasattr(uploaded, "read"):
        digest.update(uploaded.read())
    if hasattr(uploaded, "seek"):
        try:
            uploaded.seek(0)
        except Exception:
            pass
    return {
        "original_filename": name,
        "file_size": size,
        "mime_type": mime,
        "checksum": digest.hexdigest(),
    }


def apply_file_facts(obj, uploaded):
    facts = file_facts(uploaded)
    for key, value in facts.items():
        setattr(obj, key, value)
    return facts
