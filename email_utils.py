import os
import logging
import base64
import time
from typing import List, Tuple, Dict, Any, Optional

import requests

from pdf_utils import generate_giftcard_pdf

logger = logging.getLogger("giftcard-webhook")

# ------------------------------------------------------------------------------
# Konfiguracja SendGrid
# ------------------------------------------------------------------------------

SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")

# Wsparcie zarówno dla EMAIL_FROM, jak i SENDGRID_FROM_EMAIL
SENDGRID_FROM_EMAIL: str = (
    os.getenv("EMAIL_FROM")
    or os.getenv("SENDGRID_FROM_EMAIL")
    or "vouchery@wassyl.pl"
)
SENDGRID_FROM_NAME: str = os.getenv("SENDGRID_FROM_NAME", "Wassyl")

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

# Log pomocniczy, żeby w logach startowych było widać, jaki FROM faktycznie używamy
logger.info("SendGrid FROM email skonfigurowany jako: %r", SENDGRID_FROM_EMAIL)


# ------------------------------------------------------------------------------
# Niskopoziomowa funkcja do wysyłania maili przez SendGrid Web API v3
# ------------------------------------------------------------------------------


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    attachments: Optional[List[Tuple[str, bytes]]] = None,
) -> None:
    """
    Wysyła wiadomość e-mail przy użyciu SendGrid Web API v3.

    :param to_email: adres odbiorcy
    :param subject: temat wiadomości
    :param body_text: treść w formacie text/plain
    :param body_html: treść w formacie text/html (opcjonalnie)
    :param attachments: lista załączników (nazwa_pliku, zawartość_bytes)
    """
    if not SENDGRID_API_KEY:
        logger.error("Brak SENDGRID_API_KEY – nie można wysłać e-maila.")
        raise RuntimeError("SENDGRID_API_KEY is not configured")

    if body_html is None:
        body_html = f"<pre>{body_text}</pre>"

    data: Dict[str, Any] = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": SENDGRID_FROM_NAME,
        },
        "content": [
            {
                "type": "text/plain",
                "value": body_text,
            },
            {
                "type": "text/html",
                "value": body_html,
            },
        ],
    }

    if attachments:
        sg_attachments: List[Dict[str, Any]] = []
        for filename, file_bytes in attachments:
            encoded = base64.b64encode(file_bytes).decode("ascii")
            sg_attachments.append(
                {
                    "content": encoded,
                    "type": "application/pdf",
                    "filename": filename,
                    "disposition": "attachment",
                }
            )
        data["attachments"] = sg_attachments

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    logger.info("Wysyłanie e-maila do %s przez SendGrid...", to_email)

    resp = requests.post(SENDGRID_API_URL, json=data, headers=headers, timeout=15)

    if resp.status_code >= 400:
        logger.error(
            "Błąd SendGrid: %s – %s",
            resp.status_code,
            resp.text,
        )
        resp.raise_for_status()

    logger.info("E-mail do %s został pomyślnie wysłany.", to_email)


# ------------------------------------------------------------------------------
# Budowa HTML dla maila z kartą podarunkową
# ------------------------------------------------------------------------------


def _build_giftcard_html(order_serial_number: str) -> str:
    """
    Buduje HTML dla maila z kartą podarunkową.
    Layout prosty, ale zgodny z wymaganiami:
    - logotyp WASSYL
    - treść po polsku
    - numer zamówienia (orderSerialNumber)
    """
    return f"""
<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="UTF-8" />
    <title>Twoja karta podarunkowa – zamówienie {order_serial_number}</title>
  </head>
  <body style="margin:0; padding:0; background:#f3f4f6; font-family:system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6; padding:24px 0;">
      <tr>
        <td align="center">
          <table width="100%" cellpadding="0" cellspacing="0" style="max-width:640px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 12px 30px rgba(15,23,42,0.08);">
            <tr>
              <td align="center" style="padding:24px 24px 16px 24px; border-bottom:1px solid #e5e7eb;">
                <img src="https://wassyl.pl/data/include/cms/gfx/logo-wassyl.png" alt="WASSYL" style="display:block; max-width:180px; height:auto;" />
              </td>
            </tr>

            <tr>
              <td style="padding:24px 24px 4px 24px; font-size:16px; font-weight:600; color:#111827;">
                Dziękujemy za zakup karty podarunkowej WASSYL
              </td>
            </tr>
            <tr>
              <td style="padding:0 24px 12px 24px; font-size:14px; line-height:1.6; color:#4b5563;">
                W załączniku przesyłamy Twoją kartę (lub karty) podarunkową w formacie PDF – możesz ją wydrukować
                lub przesłać dalej osobie obdarowanej.
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 16px 24px;">
                <div style="background:#f9fafb; border-radius:10px; padding:12px 14px; border:1px solid #e5e7eb; font-size:13px; color:#374151;">
                  <div style="text-transform:uppercase; letter-spacing:0.09em; font-size:11px; color:#9ca3af; margin-bottom:4px;">
                    Numer zamówienia
                  </div>
                  <div style="font-weight:600; letter-spacing:0.02em;">{order_serial_number}</div>
                </div>
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 12px 24px; font-size:14px; line-height:1.6; color:#4b5563;">
                <strong>Jak skorzystać z karty?</strong><br/>
                Podczas składania zamówienia w sklepie <a href="https://wassyl.pl" style="color:#4f46e5; text-decoration:none;">WASSYL.pl</a>
                wybierz metodę płatności „Karta podarunkowa” i wpisz numer karty podarunkowej z załączonego PDF.
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 24px 24px; font-size:13px; line-height:1.6; color:#6b7280;">
                W razie pytań dotyczących zamówienia lub problemów z realizacją karty, skontaktuj się z nami
                odpowiadając na tę wiadomość lub poprzez formularz kontaktowy w sklepie.
              </td>
            </tr>

            <tr>
              <td style="padding:0 24px 24px 24px; font-size:13px; color:#4b5563;">
                Pozdrawiamy,<br/>
                <strong>zespół WASSYL.pl</strong>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
    """.strip()


def build_giftcard_html(order_serial_number: str) -> str:
    """
    Publiczny helper – ten HTML możesz wykorzystać również w debug/test-email,
    żeby testowy mail wyglądał identycznie jak produkcyjny.
    """
    return _build_giftcard_html(order_serial_number)


# ------------------------------------------------------------------------------
# Wysokopoziomowa funkcja do wysyłania kart podarunkowych
# ------------------------------------------------------------------------------


def send_giftcard_email(
    to_email: str,
    codes: List[Dict[str, Any]],
    order_serial_number: str,
) -> None:
    """
    Wysyła maila z kartami podarunkowymi.

    - generuje PDF dla każdej karty na bazie szablonu WASSYL-GIFTCARD.pdf
    - dołącza wszystkie PDF-y jako załączniki
    - w treści maila umieszcza listę kart + numer zamówienia (orderSerialNumber)
    - opóźnia wysyłkę o 3 minuty (żeby najpierw przyszły maile ze sklepu)
    """

    # OPÓŹNIENIE WYSYŁKI – 3 minuty
    delay_seconds = 3 * 60
    logger.info(
        "Zaplanowano wysyłkę e-maila z kartą/kartami do %s za %s sekund.",
        to_email,
        delay_seconds,
    )
    time.sleep(delay_seconds)

    subject = f"Twoja karta podarunkowa – zamówienie {order_serial_number}"

    # Tekst jako fallback (plain text)
    lines: List[str] = [
        "Cześć!",
        "",
        "Dziękujemy za zakup naszej karty podarunkowej.",
        "W załączeniu przesyłamy plik PDF z kartą (lub kartami) do samodzielnego wydruku.",
        "",
        "Podsumowanie kart:",
    ]

    attachments: List[Tuple[str, bytes]] = []

    for c in codes:
        code = str(c.get("code"))
        value = c.get("value")

        # Linia do body_text
        lines.append(f"- {value} zł – kod: {code}")

        # Generacja PDF dla każdej karty
        pdf_bytes = generate_giftcard_pdf(code=code, value=value)
        filename = f"WASSYL-GIFTCARD-{value}zl-{code}.pdf"
        attachments.append((filename, pdf_bytes))

    lines.extend(
        [
            "",
            "Jak skorzystać z karty?",
            "Wystarczy wybrać metodę płatności „Karta podarunkowa” w sklepie WASSYL.pl "
            "i podać numer karty.",
            "",
            "W celu ułatwienia komunikacji podaj numer zamówienia:",
            f"Numer zamówienia: {order_serial_number}",
            "",
            "Pozdrawiamy, zespół WASSYL.pl",
        ]
    )

    body_text = "\n".join(lines)
    body_html = _build_giftcard_html(order_serial_number)

    send_email(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        attachments=attachments,
    )
