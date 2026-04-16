from pathlib import Path

import cloudinary.uploader
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError


def ensure_cloudinary_configured():
    if not getattr(settings, "CLOUDINARY_URL", "").strip():
        raise ImproperlyConfigured(
            "Define la variable de entorno CLOUDINARY_URL para poder subir adjuntos."
        )


def upload_attachment(uploaded_file, *, folder, tags=None):
    ensure_cloudinary_configured()
    try:
        return cloudinary.uploader.upload(
            uploaded_file,
            folder=folder,
            resource_type="auto",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
            display_name=uploaded_file.name,
            tags=tags or [],
        )
    except Exception as exc:
        raise ValidationError(
            f"No se pudo subir el archivo '{uploaded_file.name}' a Cloudinary."
        ) from exc


def destroy_attachment(public_id, *, resource_type):
    ensure_cloudinary_configured()
    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            invalidate=True,
        )
    except Exception:
        # Si el borrado remoto falla no bloqueamos el borrado local.
        return


def extract_filename(url, fallback):
    if not url:
        return fallback
    filename = Path(url).name
    return filename or fallback
