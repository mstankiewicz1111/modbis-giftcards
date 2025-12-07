import os
import smtplib
import ssl
import logging
from typing import List, Tuple, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger("giftcard-email")

# Typ: lista załączników: (nazwa_pliku, bajty)
AttachmentList = Optional[List[Tuple[str, bytes]]]


def _get_smtp_config():
    """Pobiera konfigurację SMTP ze zmiennych środowiskowych."""
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_SENDER")

    if not all([host, port, user, password, sender]):
        missing = [
            name
            for name, value in [
                ("SMTP_HOST", host),
                ("SMTP_PORT", port),
                ("SMTP_USER", user),
                ("SMTP_PASSWORD", password),
                ("SMTP_SENDER", sender),
            ]
            if not value
        ]
        msg = f"Brak wymaganych zmiennych SMTP: {', '.join(missing)}"
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        port_int = int(port)
    except ValueError:
        raise RuntimeError(f"SMTP_PORT musi być liczbą, aktualnie: {port!r}")

    return host, port_int, user, password, sender


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    attachments: AttachmentList = None,
) -> None:
    """
    Wysyła prostego maila tekstowego z opcjonalnymi załącznikami.
    """
    host, port, user, password, sender = _get_smtp_config()

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject

    # Treść w UTF-8, żeby np. 'ł' działało
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # Załączniki
    if attachments:
        for filename, file_bytes in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"',
            )
            msg.attach(part)

    context = ssl.create_default_context()

    logger.info("Łączenie z serwerem SMTP %s:%s jako %s", host, port, user)
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(user, password)
        server.sendmail(sender, [to_email], msg.as_string())
    logger.info("Wysłano e-mail do %s", to_email)


def send_giftcard_email(
    to_email: str,
    order_id: str,
    codes: List[dict],
    pdf_files: AttachmentList,
) -> None:
    """
    Wysyła maila z kartami podarunkowymi (PDF-y w załączniku).
    `codes` – lista słowników np. {"code": "...", "value": 300}
    """
    subject = f"Wassyl – Twoja karta podarunkowa (zamówienie {order_id})"

    # Prosta treść maila z wypisanymi kodami
    lines = [
        "Dziękujemy za zakup karty podarunkowej WASSYL!",
        "",
        "Poniżej znajdują się kody kart podarunkowych:",
    ]
    for c in codes:
        lines.append(f"- {c['value']} zł : {c['code']}")

    lines += [
        "",
        "W załączniku znajdziesz pliki PDF z kartami.",
        "",
        "Pozdrawiamy,",
        "Zespół WASSYL",
    ]

    body_text = "\n".join(lines)

    send_email(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        attachments=pdf_files,
    )
