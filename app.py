"""
App web: usuário envia uma imagem e o número de WhatsApp;
um sticker é gerado e enviado para esse número.
"""
import os
import time
from collections import defaultdict

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from PIL.Image import DecompressionBombError

from sticker_converter import image_to_sticker
from whatsapp_sender import send_sticker_to_whatsapp

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB para upload

# Rate limit simples por IP: máx. 10 requisições por minuto
_RATE_LIMIT_WINDOW = 60  # segundos
_RATE_LIMIT_MAX = 10
_rate_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    now = time.monotonic()
    times = _rate_store[ip]
    times[:] = [t for t in times if now - t < _RATE_LIMIT_WINDOW]
    if len(times) >= _RATE_LIMIT_MAX:
        return False
    times.append(now)
    return True


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())


def _is_valid_phone(phone: str) -> bool:
    """E.164: só dígitos, 10 a 15 caracteres."""
    p = _normalize_phone(phone)
    return 10 <= len(p) <= 15


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/criar-sticker", methods=["POST"])
def criar_sticker():
    """
    Formato esperado: multipart/form-data
    - file: imagem (jpeg, png, webp, etc.)
    - phone: número WhatsApp (ex: 5511999999999)
    """
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"ok": False, "error": "Muitas requisições. Tente de novo em 1 minuto."}), 429

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Nenhuma imagem enviada"}), 400

    file = request.files["file"]
    phone_raw = (request.form.get("phone") or "").strip()
    phone = _normalize_phone(phone_raw.replace("+", "").replace(" ", ""))

    if not file.filename:
        return jsonify({"ok": False, "error": "Arquivo sem nome"}), 400
    if not phone:
        return jsonify({"ok": False, "error": "Número de WhatsApp é obrigatório"}), 400
    if not _is_valid_phone(phone):
        return jsonify({"ok": False, "error": "Número inválido. Use formato internacional (ex: 5511999999999)."}), 400

    try:
        image_bytes = file.read()
        sticker_bytes = image_to_sticker(
            image_bytes,
            add_transparent_bg=request.form.get("transparent_bg", "true").lower() == "true",
            crop_mode=request.form.get("crop_mode", "contain"),
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except DecompressionBombError:
        return jsonify({"ok": False, "error": "Imagem muito grande. Use uma imagem menor."}), 400
    except Exception:
        # Não expor detalhes internos (ex.: stack) ao cliente
        return jsonify({"ok": False, "error": "Erro ao processar a imagem. Verifique o formato."}), 400

    result = send_sticker_to_whatsapp(sticker_bytes, phone)

    if "error" in result:
        err = result["error"]
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        # Não repassar mensagens brutas da API (podem conter detalhes sensíveis)
        if "CONFIG_MISSING" in str(err.get("code", "")):
            msg = "Serviço temporariamente indisponível."
        elif not msg or "token" in msg.lower() or "access" in msg.lower():
            msg = "Erro ao enviar para o WhatsApp. Tente mais tarde."
        return jsonify({"ok": False, "error": msg}), 400

    return jsonify({"ok": True, "message": "Sticker enviado para o WhatsApp!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    if debug and os.environ.get("FLASK_ENV", "").lower() == "production":
        debug = False  # Nunca ativar debug em produção
    app.run(host="0.0.0.0", port=port, debug=debug)
