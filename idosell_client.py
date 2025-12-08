# idosell_client.py

import logging
from typing import Any

import requests

logger = logging.getLogger("giftcard-webhook")


class IdosellApiError(Exception):
    """Błąd zwrócony przez Idosell WebAPI."""


class IdosellClient:
    """
    Prosty klient do Idosell WebAPI – aktualnie używany tylko do ustawiania
    notatki do zamówienia (orderNote) po numerze seryjnym zamówienia.
    """

    def __init__(self, domain: str, api_key: str, timeout: float = 10.0) -> None:
        """
        :param domain: np. "client5056.idosell.com" (może być też z https:// – zostanie obcięte)
        :param api_key: klucz API (X-API-KEY) z panelu Idosell
        :param timeout: timeout dla zapytań HTTP w sekundach
        """
        # Pozwalamy podać domenę z protokołem albo bez.
        if domain.startswith("http://") or domain.startswith("https://"):
            domain = domain.split("://", 1)[1]
        self.base_url = f"https://{domain.strip('/')}/api/admin/v6/orders/orders"
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": "application/json",
                "content-type": "application/json",
                "X-API-KEY": api_key,
            }
        )

        logger.info("IdosellClient zainicjalizowany dla domeny %s", domain)

    def _parse_json_safely(self, resp: requests.Response) -> Any:
        """
        Pomocniczo: próba sparsowania JSON-a; w razie problemów zwracamy None.
        """
        try:
            return resp.json()
        except ValueError:
            return None

    def update_order_note(self, order_serial_number: int | str, note: str) -> None:
        """
        Ustawia notatkę do zamówienia (orderNote) dla danego zamówienia.

        Zgodnie z działającym przykładem z Idosell, używamy:
        - endpointu: /api/admin/v6/orders/orders
        - pola: orderSerialNumber
        - pola: orderNote
        i składni:

        {
          "params": {
            "orders": [
              {
                "orderSerialNumber": 1836855,
                "orderNote": "test"
              }
            ]
          }
        }
        """
        # Spróbujmy zrzutować na int – zgodnie z przykładem API.
        try:
            serial_value: int | str = int(order_serial_number)
        except (TypeError, ValueError):
            # Gdyby kiedyś numer był alfanumeryczny – wyślemy jako string.
            serial_value = str(order_serial_number)

        payload = {
            "params": {
                "orders": [
                    {
                        "orderSerialNumber": serial_value,
                        "orderNote": note,
                    }
                ]
            }
        }

        logger.info(
            "Aktualizuję notatkę zamówienia w Idosell: "
            "orderSerialNumber=%s, url=%s",
            order_serial_number,
            self.base_url,
        )

        resp = self.session.put(self.base_url, json=payload, timeout=self.timeout)

        if resp.status_code >= 400:
            # Błąd HTTP – logujemy pełną treść odpowiedzi, żeby łatwo debugować.
            logger.error(
                "Idosell API zwrócił błąd HTTP %s dla orderSerialNumber=%s: %s",
                resp.status_code,
                order_serial_number,
                resp.text,
            )
            raise IdosellApiError(
                f"HTTP {resp.status_code} podczas aktualizacji notatki: {resp.text}"
            )

        data = self._parse_json_safely(resp)

        # Jeżeli API zwraca strukturę z polami errors – spróbujmy ją wychwycić,
        # ale nie zakładamy konkretnego kształtu (może być dict, lista itd.).
        if isinstance(data, dict) and data.get("errors"):
            logger.error(
                "Idosell API zwrócił błąd logiczny (dict) dla orderSerialNumber=%s: %s",
                order_serial_number,
                data["errors"],
            )
            raise IdosellApiError(f"API error: {data['errors']}")

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("errors"):
                    logger.error(
                        "Idosell API zwrócił błąd logiczny (list) dla "
                        "orderSerialNumber=%s: %s",
                        order_serial_number,
                        item["errors"],
                    )
                    raise IdosellApiError(f"API error: {item['errors']}")

        logger.info(
            "Pomyślnie zaktualizowano notatkę zamówienia %s w Idosell.",
            order_serial_number,
        )
