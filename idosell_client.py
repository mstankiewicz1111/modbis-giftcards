import httpx
from typing import Optional

from .config import settings


class IdosellApiError(Exception):
    pass


class IdosellClient:
    def __init__(self):
        self.base_url = f"https://{settings.idosell_domain}/api/admin/v3"
        self.api_key = settings.idosell_api_key
        self.timeout = settings.idosell_api_timeout

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "X-API-KEY": self.api_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
        )

    # -------------------------------------------------------------------
    #  POBIERANIE orderNote → GET /orders/orders
    # -------------------------------------------------------------------

    def get_order_note(self, order_serial_number: int) -> Optional[str]:
        params = {"ordersSerialNumbers": [order_serial_number]}

        with self._get_client() as client:
            resp = client.get("/orders/orders", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results") or data.get("Results")
        if not results:
            return None

        orders = (
            results.get("orders")
            or results.get("Orders")
            or []
        )
        if not orders:
            return None

        return orders[0].get("orderNote")

    # -------------------------------------------------------------------
    #  NADPISYWANIE orderNote → PUT /orders/orders
    # -------------------------------------------------------------------

    def set_order_note(self, order_serial_number: int, note: str) -> None:
        payload = {
            "params": {
                "orders": [
                    {
                        "orderSerialNumber": order_serial_number,
                        "orderNote": note,
                    }
                ]
            }
        }

        with self._get_client() as client:
            resp = client.put("/orders/orders", json=payload)

        if resp.status_code not in (200, 207):
            raise IdosellApiError(
                f"HTTP {resp.status_code}: {resp.text}"
            )

        data = resp.json()
        results = data.get("results") or {}

        # Sprawdzenie błędów per zamówienie
        for r in results.get("ordersResults", []):
            fault = r.get("faultCode")
            if fault not in (None, 0):
                raise IdosellApiError(
                    f"Idosell error {fault}: {r.get('faultString')}"
                )

    # -------------------------------------------------------------------
    #  DOPISYWANIE VOUCHERA DO orderNote
    # -------------------------------------------------------------------

    def append_order_note_with_voucher(
        self,
        order_serial_number: int,
        voucher_code: str,
        value: float,
        currency: str,
        pdf_url: Optional[str] = None,
    ) -> None:

        existing = self.get_order_note(order_serial_number) or ""

        voucher_lines = [
            "KARTA PODARUNKOWA:",
            f"– Kod: {voucher_code}",
            f"– Wartość: {value:.2f} {currency}",
        ]
        if pdf_url:
            voucher_lines.append(f"– Link do PDF: {pdf_url}")

        voucher_block = "\n".join(voucher_lines)

        if existing.strip():
            new_note = f"{existing.rstrip()}\n\n---\n{voucher_block}"
        else:
            new_note = voucher_block

        self.set_order_note(order_serial_number, new_note)
