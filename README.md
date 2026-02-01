# App: Imagem → Sticker → WhatsApp

O usuário envia uma imagem e informa o número de WhatsApp; a aplicação gera um sticker (WebP 512×512, &lt;100 KB) e envia para esse número via **WhatsApp Cloud API**.

## Fluxo

1. **Upload**: usuário acessa a interface web, escolhe uma imagem e informa o número (ex: `5511999999999`).
2. **Conversão**: a imagem é convertida para o formato de sticker do WhatsApp (WebP 512×512, com transparência, até 100 KB).
3. **Envio**: o sticker é enviado para o número informado usando a WhatsApp Cloud API.

## Requisitos

- **Conta Meta for Developers** e um app com **WhatsApp** configurado (Cloud API).
- **Número de telefone do negócio** e **token de acesso** da API.

## Configuração

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Copie o exemplo de variáveis de ambiente e preencha:

   ```bash
   cp .env.example .env
   ```

   No `.env`:

   - `WHATSAPP_PHONE_ID`: ID do número de telefone do negócio (em API Setup do WhatsApp).
   - `WHATSAPP_TOKEN`: token de acesso permanente ou temporário.

3. (Opcional) Para debug local: `FLASK_DEBUG=true`.

## Como rodar

```bash
 python app.py
```

Acesse `http://localhost:5000`, envie uma imagem e o número no formato internacional (ex: `5511999999999`). O sticker será enviado para esse número no WhatsApp.

## Estrutura do projeto

| Arquivo | Função |
|--------|--------|
| `app.py` | Servidor Flask: página de upload e endpoint `/api/criar-sticker`. |
| `sticker_converter.py` | Converte imagem → WebP 512×512 (&lt;100 KB) para sticker. |
| `whatsapp_sender.py` | Upload do sticker na API e envio da mensagem tipo `sticker`. |
| `templates/index.html` | Interface para upload da imagem e número. |

## Segurança e boas práticas

- **Rate limiting**: 10 requisições por minuto por IP (evita abuso e spam).
- **Validação de entrada**: telefone em formato E.164 (10–15 dígitos); imagem validada por magic bytes (JPEG, PNG, GIF, WebP).
- **Decompression bomb**: limite de 50 megapixels no Pillow para evitar imagens maliciosas que explodem em memória.
- **Erros**: mensagens da API não são repassadas ao cliente (evita vazamento de detalhes sensíveis); debug desativado quando `FLASK_ENV=production`.

Para produção, considere: **autenticação** (login ou API key), **HTTPS** (proxy reverso com TLS) e **limite de destinatários** (ex.: só números autorizados).

## Referências

- [Requisitos de stickers do WhatsApp](https://faq.whatsapp.com/4148445205479237)
- [Sticker messages – WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/messages/sticker-messages/)
