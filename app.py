"""
API Flask do Desconfie: serve os dois modelos treinados nos notebooks.

    POST /prever/texto   {"texto": "..."}  -> probabilidade de golpe + sinais + termos que pesaram
    POST /prever/url     {"url": "..."}    -> probabilidade de phishing + motivos
    GET  /health                           -> status e versões dos modelos

Rodar:  flask --app app run --port 5000
Quem chama é a API Java. A decisão final (veredito) é dela, não desta API.
"""
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from features import COLUNAS_URL, extrair_features, extrair_links

PASTA = Path(__file__).parent / "modelos"
MODELO_TEXTO = joblib.load(PASTA / "golpe_texto.joblib")
MODELO_URL = joblib.load(PASTA / "url_phishing.joblib")
META_TEXTO = json.loads((PASTA / "golpe_texto.json").read_text(encoding="utf-8"))
META_URL = json.loads((PASTA / "url_phishing.json").read_text(encoding="utf-8"))
LIMITE_CARACTERES = 5000

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False
app.json.mimetype = "application/json; charset=utf-8"
CORS(app)


# ---------------------------------------------------------------- erros no mesmo formato da API Java
def erro(status, titulo, mensagem, campos=None):
    return jsonify(status=status, erro=titulo, mensagem=mensagem, caminho=request.path,
                   timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"), campos=campos or []), status


@app.errorhandler(HTTPException)
def http_erro(e):
    textos = {404: ("Não encontrado", "Rota não encontrada. Use /, /health, /prever/texto ou /prever/url."),
              405: ("Método não permitido", "Use POST nesta rota, com JSON no corpo.")}
    titulo, mensagem = textos.get(e.code, (e.name, e.description))
    return erro(e.code, titulo, mensagem)


@app.errorhandler(Exception)
def erro_interno(e):
    app.logger.exception(e)
    return erro(500, "Erro interno", "Não foi possível analisar agora. Tente de novo em instantes.")


def campo_texto(nome):
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict):
        return None, erro(400, "Requisição inválida", "Envie um JSON no corpo da requisição.")
    valor = corpo.get(nome)
    if not isinstance(valor, str) or not valor.strip():
        return None, erro(400, "Requisição inválida", f"O campo '{nome}' é obrigatório.",
                          [{"campo": nome, "mensagem": "não pode ficar vazio"}])
    if len(valor) > LIMITE_CARACTERES:
        return None, erro(400, "Requisição inválida", f"O campo '{nome}' passa de {LIMITE_CARACTERES} caracteres.",
                          [{"campo": nome, "mensagem": f"máximo de {LIMITE_CARACTERES} caracteres"}])
    return valor.strip(), None


# ---------------------------------------------------------------- sinais de texto (explicam o veredito)
SINAIS = [
    ("URGENCIA", r"urgente|imediatamente|agora|so hoje|hoje|ultimas horas|em ate \d+ ?(min|minutos|horas?)|prazo|expira"),
    ("PEDE_PIX", r"\bpix\b|transfer\w*|deposit\w*|manda\w* o valor|envia\w* o valor"),
    ("PEDE_DADOS", r"senha|\bcpf\b|codigo|token|numero do cartao|dados (pessoais|bancarios)|foto do documento"),
    ("AMEACA_BLOQUEIO", r"bloquead\w*|bloqueio|suspens\w*|cancelad\w*|irregular|negativa\w*|protesto"),
    ("PREMIO", r"premio|premiad\w*|sorteado|sorteio|ganhou|parabens|resgat\w*"),
    ("FINGE_PARENTE", r"troquei de numero|numero novo|novo numero|meu novo|celular quebrou|esse e o novo"),
    ("LINK_ENCURTADO", r"bit\.ly|tinyurl|cutt\.ly|is\.gd|encurta"),
]


def sem_acento(texto):
    """Devolve o texto sem acento, em minúsculas, e o índice de cada caractere no original."""
    saida, indices = [], []
    for i, c in enumerate(texto):
        for d in unicodedata.normalize("NFD", c.lower()):
            if unicodedata.category(d) != "Mn":
                saida.append(d)
                indices.append(i)
    return "".join(saida), indices


def sinais_texto(texto):
    norm, idx = sem_acento(texto)
    achados = []
    for codigo, padrao in SINAIS:
        m = re.search(padrao, norm)
        if m:
            achados.append({"codigo": codigo, "evidencia": texto[idx[m.start()]:idx[m.end() - 1] + 1]})
    return achados


def termos_relevantes(texto, n=5):
    """Termos da mensagem que mais empurraram a Regressão Logística para 'golpe'."""
    tfidf, clf = MODELO_TEXTO.named_steps["tfidf"], MODELO_TEXTO.named_steps["clf"]
    if not hasattr(clf, "coef_"):
        return []
    x = tfidf.transform([texto])
    contrib = x.multiply(clf.coef_[0]).toarray()[0]
    nomes = tfidf.get_feature_names_out()
    ordem = [i for i in np.argsort(contrib)[::-1] if contrib[i] > 0][:n]
    legivel = {"tokenurl": "[link]", "tokennum": "[número]", "tokentelefone": "[telefone]",
               "tokencpf": "[cpf]", "tokenemail": "[e-mail]"}
    return [" ".join(legivel.get(p, p) for p in nomes[i].split()) for i in ordem]


# ---------------------------------------------------------------- motivos de URL
def motivos_url(f, url):
    motivos = []
    if re.search(r"bit\.ly|tinyurl|cutt\.ly|is\.gd", url, re.I):
        motivos.append("encurtador")
    if f["has_ip_address"]:
        motivos.append("ip_no_lugar_do_dominio")
    if f["suspicious_tld"]:
        motivos.append("dominio_de_terminacao_suspeita")
    if f["suspicious_word_count"]:
        motivos.append("palavra_de_seguranca_ou_pagamento")
    if f["has_hyphen_in_domain"]:
        motivos.append("hifen_no_dominio")
    if not f["https_flag"]:
        motivos.append("sem_https")
    if f["subdomain_count"] >= 3:
        motivos.append("muitos_subdominios")
    if f["suspicious_file_extension"]:
        motivos.append("arquivo_executavel")
    if f["percentage_numeric_chars"] >= 15:
        motivos.append("muitos_numeros")
    return motivos


# ---------------------------------------------------------------- rotas
@app.get("/")
def raiz():
    """Índice da API, para quem abre a URL pública no navegador."""
    return jsonify(
        api="Desconfie · IA & ML",
        descricao="Probabilidade de golpe em mensagens e de phishing em links. O veredito final é da API Java.",
        rotas={
            "GET /health": "status e versão dos modelos",
            "POST /prever/texto": '{"texto": "..."} -> probabilidadeGolpe, sinaisTexto, linksEncontrados, termosMaisRelevantes',
            "POST /prever/url": '{"url": "..."} -> probabilidadePhishing, featuresMaisRelevantes',
        },
        limiteDeCaracteres=LIMITE_CARACTERES)


@app.get("/health")
def health():
    return jsonify(status="ok",
                   modelos={"texto": {"versao": "golpe_texto_v1", "algoritmo": META_TEXTO["modelo"], "limiar": META_TEXTO["limiar"]},
                            "url": {"versao": "url_phishing_v1", "algoritmo": META_URL["modelo"], "limiar": META_URL["limiar"]}})


@app.post("/prever/texto")
def prever_texto():
    texto, falha = campo_texto("texto")
    if falha:
        return falha
    prob = float(MODELO_TEXTO.predict_proba([texto])[0][1])
    return jsonify(modelo="golpe_texto_v1",
                   probabilidadeGolpe=round(prob, 4),
                   acimaDoLimiar=prob >= META_TEXTO["limiar"],
                   sinaisTexto=sinais_texto(texto),
                   linksEncontrados=extrair_links(texto),
                   termosMaisRelevantes=termos_relevantes(texto))


@app.post("/prever/url")
def prever_url():
    url, falha = campo_texto("url")
    if falha:
        return falha
    f = extrair_features(url)
    prob = float(MODELO_URL.predict_proba(pd.DataFrame([f])[COLUNAS_URL])[0][1])
    return jsonify(modelo="url_phishing_v1",
                   probabilidadePhishing=round(prob, 4),
                   acimaDoLimiar=prob >= META_URL["limiar"],
                   featuresMaisRelevantes=motivos_url(f, url))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
