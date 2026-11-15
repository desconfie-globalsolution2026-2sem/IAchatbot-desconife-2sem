"""
Funções usadas igualzinho no treino (notebooks) e na API (app.py).
Se mudar algo aqui, treine os modelos de novo.
"""
import math
import re
import unicodedata
from collections import Counter
from urllib.parse import urlparse

# ---------------------------------------------------------------- texto (modelo 1)
RE_URL = re.compile(r"(https?://\S+|www\.\S+|\b[\w-]+\.(?:com|net|org|xyz|top|online|site|info|click|ly|gd|br)(?:/\S*)?)", re.I)
RE_NUM = re.compile(r"\d+")


def limpar_texto(texto):
    """Minúsculas, sem acento, links viram TOKEN_URL e números viram TOKEN_NUM."""
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = RE_URL.sub(" tokenurl ", t)
    t = t.replace("[telefone]", " tokentelefone ").replace("[cpf]", " tokencpf ").replace("[email]", " tokenemail ")
    t = RE_NUM.sub(" tokennum ", t)
    return re.sub(r"\s+", " ", t).strip()


def extrair_links(texto):
    return [m.group(0).rstrip(".,;)") for m in RE_URL.finditer(str(texto))]


# ---------------------------------------------------------------- URL (modelo 2)
TLDS_POPULARES = {"com", "org", "net", "edu", "gov"}
EXTENSOES_SUSPEITAS = (".exe", ".apk", ".zip", ".rar", ".scr", ".bat", ".js", ".msi", ".jar", ".dll")
RE_IP = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

COLUNAS_URL_LEGITPHISH = ["url_length", "has_ip_address", "dot_count", "https_flag", "url_entropy", "token_count",
               "subdomain_count", "query_param_count", "tld_length", "path_length", "has_hyphen_in_domain",
               "number_of_digits", "tld_popularity", "suspicious_file_extension", "domain_name_length",
               "percentage_numeric_chars"]

# Duas features nossas, além das 16 do LegitPhish: o golpe brasileiro usa palavras de "segurança"
# e domínios baratos (.xyz, .top…), mesmo com HTTPS.
PALAVRAS_SUSPEITAS = ("login", "signin", "secure", "seguranca", "verify", "valida", "account", "conta",
                      "update", "atualiza", "confirm", "desbloq", "regulariza", "suporte", "support",
                      "bank", "banco", "pix", "premio", "resgate", "taxa", "token", "senha", "password")
TLDS_SUSPEITOS = {"xyz", "top", "online", "site", "info", "click", "shop", "live", "store", "cc", "tk",
                  "ml", "ga", "cf", "gq", "buzz", "icu", "rest", "fun", "monster", "cyou", "sbs"}
COLUNAS_URL = COLUNAS_URL_LEGITPHISH + ["suspicious_word_count", "suspicious_tld"]


def entropia(s):
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def extrair_features(url):
    """As 16 features do LegitPhish, calculadas só a partir do texto da URL."""
    url = str(url).strip()
    alvo = url if "://" in url else "http://" + url
    p = urlparse(alvo)
    host = (p.hostname or "").lower()
    partes = [x for x in host.split(".") if x]
    tld = p.netloc.lower().split(".")[-1] if "." in p.netloc else ""  # como no LegitPhish, inclui a porta
    dominio = partes[-2] if len(partes) >= 2 else (partes[0] if partes else "")
    digitos = sum(c.isdigit() for c in url)
    return {
        "url_length": len(url),
        "has_ip_address": int(bool(RE_IP.match(host))),
        "dot_count": url.count("."),
        "https_flag": int(url.lower().startswith("https")),
        "url_entropy": entropia(url),
        "token_count": len(re.split(r"[./]", url)),
        "subdomain_count": max(0, len(partes) - 2),
        "query_param_count": len(p.query.split("&")),
        "tld_length": len(tld),
        "path_length": len(p.path),
        "has_hyphen_in_domain": int("-" in host),
        "number_of_digits": digitos,
        "tld_popularity": int(tld in TLDS_POPULARES),
        "suspicious_file_extension": int(p.path.lower().endswith(EXTENSOES_SUSPEITAS)),
        "domain_name_length": len(dominio),
        "percentage_numeric_chars": 100 * digitos / len(url) if url else 0.0,
        "suspicious_word_count": sum(w in (host + p.path.lower()) for w in PALAVRAS_SUSPEITAS),
        "suspicious_tld": int(host.split(".")[-1] in TLDS_SUSPEITOS) if host else 0,
    }
