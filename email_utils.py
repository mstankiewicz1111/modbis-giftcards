import os
import logging
import base64
import requests
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger("giftcard-webhook")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "kontakt@wowpr.pl")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Wassyl")

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


def _build_attachments(attachments: List[Tuple[str, bytes]]):
    """
    attachments: lista (filename, bytes)
    """
    result = []
    for filename, content in attachments:
        result.append(
            {
                "content": base64.b64encode(content).decode("ascii"),
                "type": "application/pdf",
                "filename": filename,
                "disposition": "attachment",
            }
        )
    return result


def send_email(
    to_email: str,
    subject: str,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    attachments: Optional[List[Tuple[str, bytes]]] = None,
):
    """
    Ogólna funkcja do wysyłki maila przez SendGrid.

    - body_text – treść tekstowa (text/plain)
    - body_html – treść HTML (text/html)
    - attachments – lista (filename, bytes) lub None
    """
    if not SENDGRID_API_KEY:
        raise RuntimeError("Brak SENDGRID_API_KEY w zmiennych środowiskowych")

    content = []
    if body_text:
        content.append({"type": "text/plain", "value": body_text})
    if body_html:
        content.append({"type": "text/html", "value": body_html})

    if not content:
        raise ValueError("Musisz podać body_text lub body_html")

    data: Dict = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": SENDGRID_FROM_NAME,
        },
        "subject": subject,
        "content": content,
    }

    if attachments:
        data["attachments"] = _build_attachments(attachments)

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(SENDGRID_API_URL, json=data, headers=headers, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as e:
        logger.error(
            "Błąd przy wysyłce maila SendGrid: %s, response=%s", e, resp.text
        )
        raise

    logger.info("Wysłano e-mail na %s (SendGrid)", to_email)


def send_giftcard_email(
    to_email: str,
    order_id: str,
    codes: List[Dict[str, str]],
    pdf_files: List[Tuple[str, bytes]],
):
    """
    Wysyła maila z kartami podarunkowymi w załącznikach.
    pdf_files: lista (filename, bytes)
    """
    subject = f"Twoja karta podarunkowa – zamówienie {order_id}"

    # Treść tekstowa
    lines = [
        "Dziękujemy za zakup karty podarunkowej w sklepie Wassyl!",
        "",
        "W załączniku znajdziesz swoje karty w formacie PDF.",
        "",
        "Podsumowanie kart:",
    ]
    for c in codes:
        lines.append(f"- {c['value']} zł – kod: {c['code']}")
    lines.append("")
    lines.append("Miłych zakupów!")
    body_text = "\n".join(lines)

    # Prosty HTML (docelowo możesz go zastąpić finalnym szablonem)
    html_lines = [
        "<p>Dziękujemy za zakup karty podarunkowej w sklepie Wassyl!</p>",
        "<p>W załączniku znajdziesz swoje karty w formacie PDF.</p>",
        "<p><strong>Podsumowanie kart:</strong></p>",
        "<ul>",
    ]
    for c in codes:
        html_lines.append(
            f"<li><strong>{c['value']} zł</strong> – kod: <code>{c['code']}</code></li>"
        )
    html_lines.append("</ul>")
    html_lines.append("<p>Miłych zakupów!</p>")
    body_html = "\n".join(html_lines)

    send_email(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        attachments=pdf_files,
    )
