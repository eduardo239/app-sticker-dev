"""
Envio de sticker para WhatsApp via Cloud API.
Documentação: https://developers.facebook.com/docs/whatsapp/cloud-api/messages/sticker-messages/
"""
import io
import os

import requests


def send_sticker_to_whatsapp(
    sticker_bytes: bytes,
    to_phone: str,
    *,
    phone_id: str | None = None,
    token: str | None = None,
) -> dict:
    """
    Envia um sticker (WebP) para um número via WhatsApp Cloud API.

    Args:
        sticker_bytes: Conteúdo do arquivo WebP do sticker.
        to_phone: Número no formato internacional sem + (ex: 5511999999999).
        phone_id: ID do número de telefone do negócio (ou env WHATSAPP_PHONE_ID).
        token: Token de acesso da API (ou env WHATSAPP_TOKEN).

    Returns:
        Resposta JSON da API (com 'messages' em sucesso, 'error' em falha).
    """
    phone_id = phone_id or os.environ.get("WHATSAPP_PHONE_ID")
    token = token or os.environ.get("WHATSAPP_TOKEN")
    if not phone_id or not token:
        return {
            "error": {
                "message": "WHATSAPP_PHONE_ID e WHATSAPP_TOKEN devem estar definidos",
                "code": "CONFIG_MISSING",
            }
        }

    base_url = "https://graph.facebook.com/v21.0"
    headers = {"Authorization": f"Bearer {token}"}

    # 1) Upload do sticker
    upload_url = f"{base_url}/{phone_id}/media"
    files = {
        "file": ("sticker.webp", io.BytesIO(sticker_bytes), "image/webp"),
    }
    data = {"type": "image/webp", "messaging_product": "whatsapp"}
    r = requests.post(upload_url, headers=headers, files=files, data=data, timeout=30)
    upload_result = r.json()

    if "id" not in upload_result:
        return {"error": upload_result.get("error", upload_result)}

    media_id = upload_result["id"]

    # 2) Enviar mensagem do tipo sticker
    send_url = f"{base_url}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone.strip().replace("+", "").replace(" ", ""),
        "type": "sticker",
        "sticker": {"id": media_id},
    }
    r2 = requests.post(send_url, headers=headers, json=payload, timeout=30)
    return r2.json()
