import io
import os

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# Ścieżka do szablonu PDF (pusty wzór karty)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "WASSYL-GIFTCARD.pdf")


def generate_giftcard_pdf(code: str, value: int) -> bytes:
    """
    Generuje pojedynczy plik PDF z kartą podarunkową:
    - jako tło używa WASSYL-GIFTCARD.pdf
    - w białym polu wpisuje:
        * wartość, np. "100 zł"
        * numer karty (code)
    Zwraca gotowy PDF jako bytes (do wysłania mailem / zapisania).
    """

    # 1. Wczytujemy szablon
    with open(TEMPLATE_PATH, "rb") as f:
        template_bytes = f.read()

    template_reader = PdfReader(io.BytesIO(template_bytes))
    base_page = template_reader.pages[0]

    width = float(base_page.mediabox.width)
    height = float(base_page.mediabox.height)

    # 2. Tworzymy nakładkę z tekstem, o takim samym rozmiarze jak szablon
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))

    # --- WSPÓŁRZĘDNE TEKSTU (procentowo od wysokości strony) ---
    # 0,0 = lewy dolny róg
    #
    # Wysokości dobrane "na oko" jako procent wysokości strony:
    value_y = height * 0.27   # trochę powyżej środka białego pola
    code_y = height * 0.19    # niżej – przy „Numer karty:”

    # X zostawiamy mniej więcej jak wcześniej – możesz potem skorygować
    value_x = width * 0.18
    code_x = width * 0.26

    # 3. Rysujemy wartość i kod
    value_text = f"{value} zł"
    code_text = str(code)

    # Wartość – trochę większą czcionką
    c.setFont("Helvetica-Bold", 22)
    c.drawString(value_x, value_y, value_text)

    # Numer karty
    c.setFont("Helvetica", 18)
    c.drawString(code_x, code_y, code_text)

    c.save()

    # 4. Łączymy nakładkę z szablonem
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    overlay_page = overlay_reader.pages[0]

    base_page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(base_page)

    output_stream = io.BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()
