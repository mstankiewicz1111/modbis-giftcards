import os
import logging
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger("giftcard-webhook")

# Konfiguracja z env
IDOSELL_DOMAIN = os.getenv("IDOSELL_DOMAIN")  # np. "client5056.idosell.com"
IDOSELL_API_KEY = os.getenv("IDOSELL_API_KEY")
IDOSELL_TIMEOUT = float(os.getenv("IDOSELL_TIMEOUT", "10.0"))


class IdosellApiError(Exception):
    """Błąd przy komunikacji z Idosell Admin API."""
    pass


class IdosellClient:
    """
    Klient do Idosell Admin API (v3) – obsługa notatki do zamówienia (orderNote).

    Wymagane zmienne środowiskowe:
    - IDOSELL_DOMAIN   (np. client5056.idosell.com)
    - IDOSELL_API_KEY  (klucz API z panelu, używany w nagłówku X-API-KEY)
    """

    def __init__(self) -> None:
        if not IDOSELL_DOMAIN or not IDOSELL_API_KEY:
            # NIE podnosimy tego w module, tylko dopiero przy konstruktorze
            raise RuntimeError(
                "Brak IDOSELL_DOMAIN lub IDOSELL_API_KEY w zmiennych środowiskowych"
            )

        self.base_url = f"https://{IDOSELL_DOMAIN}/api/admin/v3"
        self.timeout = IDOSELL_TIMEOUT

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "X-API-KEY": IDOSELL_API_KEY,
                "accept": "application/json",
                "content-type": "application/json",
            },
        )

    # -------------------------------------------------------------------
    #  POBIERANIE orderNote → GET /orders/orders
    # -------------------------------------------------------------------

    def get_order_note(self, order_serial_number: int) -> Optional[str]:
        """
        Pobiera aktualną notatkę (orderNote) dla wskazanego zamówienia.
        """
        params = {"ordersSerialNumbers": [order_serial_number]}

        with self._client() as c:
            resp = c.get("/orders/orders", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results") or data.get("Results") or {}
        orders = results.get("orders") or results.get("Orders") or []
        if not orders:
            return None

        return orders[0].get("orderNote")

    # -------------------------------------------------------------------
    #  NADPISYWANIE orderNote → PUT /orders/orders
    # -------------------------------------------------------------------

    def set_order_note(self, order_serial_number: int, note: str) -> None:
        """
        Ustawia nową notatkę dla zamówienia (nadpisuje poprzednią).
        """
        payload: Dict[str, Any] = {
            "params": {
                "orders": [
                    {
                        "orderSerialNumber": order_serial_number,
                        "orderNote": note,
                    }
                ]
            }
        }

        with self._client() as c:
            resp = c.put("/orders/orders", json=payload)

        if resp.status_code not in (200, 207):
            raise IdosellApiError(
                f"HTTP {resp.status_code} przy aktualizacji orderNote: {resp.text}"
            )

        data = resp.json()
        results = data.get("results") or {}
        for r in results.get("ordersResults", []):
            fault_code = r.get("faultCode")
            if fault_code not in (None, 0):
                raise IdosellApiError(
                    f"Idosell error {fault_code}: {r.get('faultString')}"
                )

    # -------------------------------------------------------------------
    #  DOPISYWANIE (append) VOUCHERÓW DO orderNote
    # -------------------------------------------------------------------

    def append_order_note_with_vouchers(
        self,
        order_serial_number: int,
        vouchers: List[Dict[str, Any]],
        pdf_url: Optional[str] = None,
    ) -> None:
        """
        Dokleja do istniejącej notatki blok z informacją o kartach podarunkowych.

        vouchers: lista słowników np. {"code": "...", "value": 100}
        """
        existing = self.get_order_note(order_serial_number) or ""

        lines: List[str] = ["KARTY PODARUNKOWE:"]
        for v in vouchers:
            lines.append(f"- {v['value']} zł – kod: {v['code']}")
        if pdf_url:
            lines.append(f"- Link do kart (PDF): {pdf_url}")

        voucher_block = "\n".join(lines)

        if existing.strip():
            new_note = f"{existing.rstrip()}\n\n---\n{voucher_block}"
        else:
            new_note = voucher_block

        self.set_order_note(order_serial_number, new_note)
