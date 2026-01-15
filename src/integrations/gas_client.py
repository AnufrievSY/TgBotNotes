from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from src.config import config, log


@dataclass(frozen=True)
class GasClient:
    deployment_id: str
    timeout: int = 15

    @property
    def url(self) -> str:
        return f"https://script.google.com/macros/s/{self.deployment_id}/exec"

    def post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = requests.post(self.url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                return {"ok": False, "error": "Bad response JSON"}
            return data
        except Exception as e:
            log.error(f"GAS request failed: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    def exists(self, *, user: str, msg_id: int) -> bool:
        resp = self.post({"action": "exists", "user": user, "id": str(msg_id)})
        return bool(resp.get("ok") and resp.get("exists") is True)

    def upsert_note(
        self,
        *,
        user: str,
        msg_id: int,
        when: str,
        what: str,
        emotions: List[str],
        tags: List[str],
    ) -> Dict[str, Any]:
        return self.post(
            {
                "action": "upsert_note",
                "user": user,
                "record": {
                    "id": str(msg_id),
                    "when": when,       # dd.mm.YYYY HH:MM:SS
                    "what": what,
                    "emotions": emotions,
                    "tags": tags,
                },
            }
        )

    def add_tracks(self, *, user: str, msg_id: int, items: List[dict[str, str]]) -> Dict[str, Any]:
        clean_items: List[dict[str, str]] = []
        for it in items:
            link = (it.get("link") or "").strip()
            text = (it.get("text") or "").strip()
            if link and text:
                clean_items.append({"link": link, "text": text})

        return self.post(
            {
                "action": "add_track",
                "user": user,
                "id": str(msg_id),
                "items": clean_items,
            }
        )

def get_gas_client() -> GasClient:
    return GasClient(deployment_id=config.gas.token)
