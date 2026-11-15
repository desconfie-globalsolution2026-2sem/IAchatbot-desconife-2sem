# IA & ML · Desconfie

Dois modelos de **classificação** e uma API **Flask** que a API Java consome.

| # | Pergunta | Algoritmo escolhido | Comparado com | Teste (dados reais) |
|---|---|---|---|---|
| 1 | Essa mensagem é golpe? | TF-IDF + Regressão Logística | Naive Bayes | recall 1,000 · precisão 0,872 · F1 0,932 (limiar 0,655, 94 mensagens reais BR) |
| 2 | Esse link é phishing? | Random Forest (18 features da URL) | Regressão Logística | recall 0,998 · precisão 0,990 · F1 0,994 (só URLs BR: F1 0,923) |

## Estrutura

```
ia-ml/
├── dados/
│   ├── mensagens.csv        933 mensagens (BrScamsFacebook + sintéticas BR)
│   ├── urls.csv             106.218 URLs (LegitPhish + sintéticas BR)
│   ├── montar_dados.py      recria os CSVs a partir de brutos/
│   ├── brutos/              arquivos originais baixados
│   └── LEIAME.md            fontes, licenças e cuidados
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
