# email_utils.py
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger("giftcard-webhook")


def _get_smtp_config():
    """Czyta konfigurację SMTP z environment variables."""
    host = os.getenv("SMTP_HOST")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_SENDER")  # adres "From:"

    if not host or not port or not sender:
        raise RuntimeError(
            "Brak konfiguracji SMTP. Ustaw SMTP_HOST, SMTP_PORT i SMTP_SENDER w zmiennych środowiskowych."
        )

    try:
        port = int(port)
    except ValueError:
        raise RuntimeError("SMTP_PORT musi być liczbą (np. 587).")

    return host, port, user, password, sender


def send_giftcard_email(
    to_email: str,
    order_id: str,
    codes: List[Dict[str, str]],
    pdf_files: List[Tuple[str, bytes]],
) -> None:
    """
    Wysyła e-mail z kartami podarunkowymi.

    :param to_email: adres klienta
    :param order_id: ID zamówienia z Idosell
    :param codes: lista słowników {"code": "...", "value": 300}
    :param pdf_files: lista (filename, pdf_bytes)
    """
    host, port, user, password, sender = _get_smtp_config()

    msg = EmailMessage()
    msg["Subject"] = f"WASSYL – karta podarunkowa (zamówienie {order_id})"
    msg["From"] = sender
    msg["To"] = to_email

    # Treść maila – możesz sobie potem ładniej wystylować :)
    lines = [
        "Dzień dobry,",
        "",
        "Dziękujemy za zakup karty podarunkowej WASSYL.",
        "Poniżej przesyłamy szczegóły:",
        "",
    ]

    for c in codes:
        lines.append(f"- wartość: {c['value']} zł, numer karty: {c['code']}")

    lines.extend(
        [
            "",
            "W załączniku znajdziesz karty w formacie PDF – gotowe do wydruku lub przesłania dalej.",
            "",
            "Pozdrawiamy,",
            "Zespół WASSYL",
        ]
    )

    msg.set_content("\n".join(lines))

    # Załączniki PDF
    for filename, pdf_bytes in pdf_files:
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=filename,
        )

    context = ssl.create_default_context()

    logger.info("Wysyłam e-mail z kartą podarunkową do %s", to_email)

    with smtplib.SMTP(host, port) as server:
        # większość providerów wymaga STARTTLS na porcie 587
        try:
            server.starttls(context=context)
        except smtplib.SMTPException:
            logger.warning("Nie udało się uruchomić STARTTLS – kontynuuję bez TLS.")

        if user and password:
            server.login(user, password)

        server.send_message(msg)

    logger.info("E-mail z kartą podarunkową wysłany do %s", to_email)
