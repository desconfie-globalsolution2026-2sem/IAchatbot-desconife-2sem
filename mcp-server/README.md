# Servidor MCP · Desconfie

Expõe a API de IA & ML (Flask) como ferramentas MCP, por Streamable HTTP em `POST /mcp`.
Gerado no SwaggerHub a partir de [`../swagger.yaml`](../swagger.yaml) (sincronizado pelo SwaggerHub) e corrigido à mão.

| Ferramenta | Chama | Entrada |
|---|---|---|
| `predict-text` | `POST /prever/texto` | `texto` |
| `predict-url` | `POST /prever/url` | `url` |
| `get-health` | `GET /health` | |
| `get-api-index` | `GET /` | |

## Rodar local

```bash
npm install
npm start          # http://localhost:4000/mcp
```

Variáveis (todas opcionais): `MCP_API_URL` (padrão: `https://iachatbot-desconife-2sem.onrender.com`), `PORT` ou `MCP_SERVER_PORT` (padrão: 4000).

## Deploy no Render

New → **Web Service** → este repositório, com:

- Root Directory: `mcp-server`
- Language: **Node**
- Build Command: `npm install`
- Start Command: `npm start`
- Health Check Path: `/`
- Plano: Free

O link para compartilhar é `https://<nome-do-servico>.onrender.com/mcp`.

## Conectar

- **Claude (claude.ai / desktop):** Settings → Connectors → Add custom connector → cole o link `/mcp`.
- **Claude Code:** `claude mcp add --transport http desconfie https://<nome-do-servico>.onrender.com/mcp`
- **MCP Inspector:** `npx @modelcontextprotocol/inspector` → transporte Streamable HTTP → link `/mcp`.

No plano free, tanto este serviço quanto a API Flask hibernam após ~15 min sem uso. A primeira chamada pode levar ~1 min.
