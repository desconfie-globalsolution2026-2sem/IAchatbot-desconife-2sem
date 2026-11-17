// Servidor MCP do Desconfie: expõe a API de IA & ML (Flask) como ferramentas MCP.
// Transporte: Streamable HTTP, sem sessão. Endpoint: POST /mcp
import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const API_URL = (process.env.MCP_API_URL || "https://iachatbot-desconife-2sem.onrender.com").replace(/\/+$/, "");
const PORT = process.env.PORT || process.env.MCP_SERVER_PORT || 4000;
// O plano free do Render hiberna a API Flask; o primeiro pedido pode levar ~50 s.
const TIMEOUT_MS = 90_000;

async function chamarApi(caminho, metodo = "GET", corpo) {
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  const texto = await resposta.text();
  let dados;
  try { dados = JSON.parse(texto); } catch { dados = texto; }
  return { ok: resposta.ok, status: resposta.status, dados };
}

function resultado({ ok, status, dados }) {
  const texto = typeof dados === "string" ? dados : JSON.stringify(dados, null, 2);
  return ok
    ? { content: [{ type: "text", text: texto }] }
    : { isError: true, content: [{ type: "text", text: `A API respondeu ${status}:\n${texto}` }] };
}

async function executar(caminho, metodo, corpo) {
  try {
    return resultado(await chamarApi(caminho, metodo, corpo));
  } catch (e) {
    const motivo = e.name === "TimeoutError" ? "a API demorou demais para responder" : e.message;
    return { isError: true, content: [{ type: "text", text: `Não foi possível falar com a API: ${motivo}` }] };
  }
}

function criarServidor() {
  const server = new McpServer({ name: "desconfie-ia-ml", version: "1.0.0" });
  const leitura = { readOnlyHint: true, openWorldHint: true };

  server.registerTool("get-api-index", {
    title: "Índice da API",
    description: "Lista as rotas da API Desconfie IA & ML e o limite de caracteres.",
    inputSchema: {},
    annotations: leitura,
  }, () => executar("/"));

  server.registerTool("get-health", {
    title: "Status dos modelos",
    description: "Diz se a API está no ar e mostra versão, algoritmo e limiar de cada modelo.",
    inputSchema: {},
    annotations: leitura,
  }, () => executar("/health"));

  server.registerTool("predict-text", {
    title: "Mensagem é golpe?",
    description:
      "Calcula a probabilidade de uma mensagem (WhatsApp, SMS, e-mail) ser golpe. Devolve probabilidadeGolpe (0 a 1), " +
      "acimaDoLimiar, sinaisTexto (URGENCIA, PEDE_PIX, PEDE_DADOS…), linksEncontrados e termosMaisRelevantes.",
    inputSchema: { texto: z.string().min(1).max(5000).describe("Texto da mensagem a analisar (até 5000 caracteres)") },
    annotations: leitura,
  }, ({ texto }) => executar("/prever/texto", "POST", { texto }));

  server.registerTool("predict-url", {
    title: "Link é phishing?",
    description:
      "Calcula a probabilidade de um link ser phishing. Devolve probabilidadePhishing (0 a 1), acimaDoLimiar e " +
      "featuresMaisRelevantes (sem_https, hifen_no_dominio, dominio_de_terminacao_suspeita…).",
    inputSchema: { url: z.string().min(1).max(5000).describe("Link a analisar, com ou sem http(s)://") },
    annotations: leitura,
  }, ({ url }) => executar("/prever/url", "POST", { url }));

  return server;
}

const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/", (_req, res) => {
  res.json({ servidor: "Desconfie · MCP", endpoint: "/mcp", transporte: "streamable-http", api: API_URL });
});

app.post("/mcp", async (req, res) => {
  // Sem sessão: um servidor e um transporte novos por requisição.
  const server = criarServidor();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on("close", () => { transport.close(); server.close(); });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (e) {
    console.error("Erro no /mcp:", e);
    if (!res.headersSent) {
      res.status(500).json({ jsonrpc: "2.0", error: { code: -32603, message: "Erro interno" }, id: null });
    }
  }
});

const naoPermitido = (_req, res) =>
  res.status(405).json({ jsonrpc: "2.0", error: { code: -32000, message: "Use POST em /mcp." }, id: null });
app.get("/mcp", naoPermitido);
app.delete("/mcp", naoPermitido);

app.listen(PORT, () => console.log(`MCP do Desconfie em http://localhost:${PORT}/mcp → API ${API_URL}`));
