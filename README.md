# IA & ML · Desconfie

Dois modelos de **classificação** e uma API **Flask** que a API Java consome.

| # | Pergunta | Algoritmo escolhido | Comparado com | Teste (dados reais) |
|---|---|---|---|---|
| 1 | Essa mensagem é golpe? | TF-IDF + Regressão Logística | Naive Bayes | recall 1,000 · precisão 0,872 · F1 0,932 (limiar 0,655, 94 mensagens reais BR) |
| 2 | Esse link é phishing? | Random Forest (18 features da URL) | Regressão Logística | recall 0,978 · precisão 0,999 · F1 0,988 (limiar 0,90; só URLs BR: recall 0,959 · precisão 0,992) |

## Estrutura

```
desconfie-inteligencia-artificial/
├── dados/
│   ├── brscamsfacebook.csv   original: mensagens reais (Kaggle)
│   ├── legitphish.csv        original: URLs (Mendeley Data)
│   ├── treino_mensagens.csv  gerado pelo notebook 01: base final do modelo 1
│   └── treino_urls.csv       gerado pelo notebook 02: base final do modelo 2
├── notebooks/
│   ├── 01_modelo_golpe_texto.ipynb     EDA, treino, avaliação, exportação
│   └── 02_modelo_url_phishing.ipynb    EDA, treino, avaliação, exportação
├── modelos/
│   ├── golpe_texto.joblib  + .json (limiar e métricas)
│   └── url_phishing.joblib + .json
├── features.py              limpeza de texto e features de URL (usado no treino e na API)
├── app.py                   API Flask
├── requirements.txt         dependências da API
├── requirements-notebooks.txt
├── Dockerfile               deploy no Render
└── integrantes.txt          preencher antes de entregar
```

O blueprint do deploy (`render.yaml`) fica na **raiz do repositório**, um nível acima desta pasta.

## Dados

Os arquivos originais ficam em `dados/`. Cada notebook trata os dados dele quando roda (mascara, filtra, gera as sintéticas e junta tudo) e salva a base final em `dados/treino_*.csv`. A semente é fixa (`SEMENTE = 42`), então o resultado é sempre o mesmo.

| Modelo | Fonte | Reais | Sintéticas (geradas no notebook) |
|---|---|---|---|
| 1 · mensagens | [BrScamsFacebook](https://www.kaggle.com/datasets/brunaassisgt/brscamsfacebook) (Kaggle, MIT, Bruna Assis Norões/UFF) | 298 golpes · 75 legítimas | 280 golpes · 280 legítimas |
| 2 · URLs | [LegitPhish](https://data.mendeley.com/datasets/hx4m73v2sf/2) (Mendeley Data, DOI 10.17632/hx4m73v2sf.2) | 63.678 phishing · 37.540 legítimas | 2.500 phishing · 2.500 legítimas |

- **LGPD:** telefones, CPFs, e-mails e números longos viram `[TELEFONE]`, `[CPF]` e `[EMAIL]`.
- **Cuidado:** o BrScamsFacebook tem links e telefones reais de golpistas. Não acesse.
- **O teste do modelo 1 usa só mensagens reais.** Testar com as sintéticas infla as métricas. A categoria "Desinformação Digital" fica de fora, porque é fake news e não golpe.
- **No LegitPhish original, `ClassLabel` 0 = phishing.** Nos notebooks ele vira `phishing = 1`.
- **Por que URLs sintéticas:** no LegitPhish, todo link legítimo usa HTTPS e 77% dos de phishing usam IP, então o modelo deixava passar `https://itau-seguranca-app.xyz/login`. As sintéticas trazem domínios oficiais brasileiros e golpes no formato `marca-palavra.xyz`, com HTTPS dos dois lados.

## Rodar a API

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --port 5000
```

## Rotas

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| GET | `/` | | índice da API: rotas e limites |
| GET | `/health` | | status e versão dos modelos |
| POST | `/prever/texto` | `{"texto": "..."}` | `probabilidadeGolpe`, `acimaDoLimiar`, `sinaisTexto`, `linksEncontrados`, `termosMaisRelevantes` |
| POST | `/prever/url` | `{"url": "..."}` | `probabilidadePhishing`, `acimaDoLimiar`, `featuresMaisRelevantes` |

Erros (400, 404, 405, 500) saem em JSON no mesmo formato da API Java ([contrato](../contratos/5-erro-padrao.json)).

```bash
curl -X POST localhost:5000/prever/texto -H "Content-Type: application/json" \
  -d '{"texto": "URGENTE: seu PIX foi bloqueado. Regularize em itau-seguranca.xyz"}'
```

## Rodar os notebooks

```bash
pip install -r requirements-notebooks.txt
cd notebooks && jupyter notebook
```

Os notebooks salvam os `.joblib` em `modelos/`. Se mudar `features.py`, rode os dois de novo.

## Deploy no Render (API pública)

O repositório traz `render.yaml` na raiz, então o jeito mais curto é **Blueprint**:

1. Render → **New → Blueprint** → conecta este repositório → **Apply**.
   O blueprint já define: Docker, Root Directory `ia-ml`, plano free, health check em `/health` e deploy automático a cada push.
2. No fim, o Render dá uma URL pública tipo `https://desconfie-ia-ml.onrender.com`.
3. Essa URL vai na variável de ambiente **`FLASK_URL`** da API Java.

Sem blueprint, dá no mesmo por **New → Web Service** → Root Directory `ia-ml` → Runtime **Docker**.

Conferindo que subiu:

```bash
curl https://SEU-SERVICO.onrender.com/health
curl -X POST https://SEU-SERVICO.onrender.com/prever/texto -H "Content-Type: application/json" \
  -d '{"texto": "URGENTE: seu PIX foi bloqueado. Regularize em itau-seguranca.xyz"}'
```

**Cuidado na apresentação:** no plano free o serviço **hiberna após ~15 min sem acesso** e o primeiro pedido depois disso leva ~50 s para responder. Chame `/health` alguns minutos antes de apresentar para o serviço já estar acordado.

O container usa `gunicorn --preload`, então os dois modelos carregam uma vez no processo principal e os workers compartilham a memória — cabe nos 512 MB do plano free (medido: ~266 MB no total, contra ~410 MB sem `--preload`).

Detalhes: [../docs/ml.md](../docs/ml.md) · Contratos: [../contratos/](../contratos/) · Checklist: [../docs/entregas.md](../docs/entregas.md)
