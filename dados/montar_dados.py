"""
Monta os CSVs de treino do Desconfie a partir dos dados brutos.

Entradas (pasta brutos/):
  - brscamsfacebook/BrScamsFacebook.csv  BrScamsFacebook (Kaggle, brunaassisgt, MIT), 450 golpes
                      e mensagens legítimas em português do Brasil, em 6 categorias.
  - legitphish.csv    LegitPhish (Mendeley Data, DOI 10.17632/hx4m73v2sf.2), 101.219 URLs
                      com 16 features numéricas. ClassLabel: 0 = phishing, 1 = legítima.

Saídas:
  - mensagens.csv  texto,golpe,tipo,origem,pais   (modelo 1: essa mensagem é golpe?)
  - urls.csv       url, 16 features, phishing     (modelo 2: esse link é phishing?)

As mensagens brasileiras são sintéticas (origem = sintetico): geradas por modelo a partir
de modelos de frase dos golpes mais comuns no Brasil, com o mesmo volume de mensagens
legítimas brasileiras para o modelo não aprender "português do Brasil = golpe".
Telefones, CPFs e e-mails são mascarados em todas as fontes (LGPD).

Uso:  python montar_dados.py
"""
import csv
import random
import re
import sys
from pathlib import Path

AQUI = Path(__file__).parent
BRUTOS = AQUI / "brutos"
random.seed(42)

# ---------------------------------------------------------------- mascaramento (LGPD)
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RE_TEL = re.compile(r"(\+?\d{2,3}\s?)?(\(?\d{2}\)?\s?)?\b\d{4,5}[-\s]?\d{4}\b|\b8[2-7]\d{7}\b")


def mascarar(texto):
    texto = RE_EMAIL.sub("[EMAIL]", texto)
    texto = RE_CPF.sub("[CPF]", texto)
    texto = RE_TEL.sub("[TELEFONE]", texto)
    texto = re.sub(r"(?<!\d)\+?\d{9,}(?!\d)", "[TELEFONE]", texto)  # números longos, mesmo colados em letras
    return re.sub(r"\s+", " ", texto).strip()


# ---------------------------------------------------------------- vocabulário
BANCOS = [("Itaú", "itau"), ("Bradesco", "bradesco"), ("Caixa", "caixa"), ("Banco do Brasil", "bb"),
          ("Nubank", "nubank"), ("Santander", "santander"), ("Inter", "inter"), ("C6 Bank", "c6")]
LOJAS = ["Magazine", "Casas Bahia", "Americanas", "Mercado Livre", "Shopee", "Amazon"]
NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela",
         "João", "Larissa", "Marcos", "Natália", "Otávio", "Paula", "Rafael", "Sabrina", "Thiago"]
PARENTES = ["mãe", "pai", "vó", "tia", "mana", "amor"]
TLDS = ["xyz", "top", "online", "site", "info", "com", "net", "click"]
PALAVRAS_LINK = ["seguranca", "atualiza", "regulariza", "desbloqueio", "cliente", "app", "valida", "suporte"]
ENCURTADORES = ["bit.ly", "tinyurl.com", "cutt.ly", "is.gd"]


def valor():
    reais = random.choice(["89", "127", "249", "389", "499", "890", "1.250", "1.890", "2.400", "3.200", "4.750"])
    return f"R$ {reais}" + random.choice([",00", ",90", ",50"])


def link_falso(slug=None):
    if random.random() < 0.3:
        cod = "".join(random.choices("abcdefghijkmnpqrstuvwxyz23456789", k=6))
        return f"{random.choice(ENCURTADORES)}/{cod}"
    slug = slug or random.choice([b[1] for b in BANCOS] + ["correios", "gov", "receita", "pix"])
    sep = random.choice(["-", ""])
    dominio = f"{slug}{sep}{random.choice(PALAVRAS_LINK)}.{random.choice(TLDS)}"
    return random.choice(["https://", "http://", ""]) + dominio + random.choice(["", "/login", "/acesso", "/pix"])


def tel():
    return f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"


def hora():
    return f"{random.randint(8, 20)}h"


def prazo():
    return random.choice(["30 minutos", "2 horas", "hoje", "até as 23h59", "24 horas"])


# ---------------------------------------------------------------- golpes brasileiros (golpe = 1)
def g_falsa_central():
    b, s = random.choice(BANCOS)
    return random.choice([
        f"{b}: identificamos uma compra de {valor()} no seu cartão. Se não reconhece, ligue agora {tel()} para cancelar.",
        f"URGENTE {b}: seu PIX de {valor()} foi bloqueado por suspeita de fraude. Regularize em {prazo()}: {link_falso(s)}",
        f"Prezado cliente {b}, sua conta será suspensa {prazo()}. Atualize seus dados e senha em {link_falso(s)}",
        f"{b} informa: seu token expirou. Para não ter o acesso bloqueado, valide em {link_falso(s)} informando CPF e senha.",
        f"Aqui é da central de segurança do {b}. Detectamos acesso suspeito. Responda com o código que enviamos por SMS para cancelar.",
        f"Alerta {b}: transferência de {valor()} pendente de autorização. Caso não tenha sido você, acesse {link_falso(s)} imediatamente.",
        f"{b}: seu cartão foi clonado. Um atendente vai te ligar, confirme os números do cartão e a senha para o estorno.",
    ])


def g_falso_parente():
    p, n = random.choice(PARENTES), random.choice(NOMES)
    return random.choice([
        f"Oi {p}, troquei de número, salva esse. Tô sem acesso ao app do banco, consegue fazer um pix de {valor()} pra mim? Te devolvo amanhã.",
        f"{p.capitalize()}, é o {n}. Meu celular quebrou, esse é meu número novo. Preciso pagar uma conta urgente, me ajuda?",
        f"Oi {p}! Número novo aqui. Tenho que pagar um boleto hoje e o meu limite estourou. Pode mandar {valor()} nessa chave pix?",
        f"{p}, não conta pra ninguém, tô num aperto. Faz um pix de {valor()} pro meu amigo {n}, depois te explico.",
        f"Salva meu novo contato {p}. Tá dando erro no meu banco, me empresta {valor()} só até sexta?",
    ])


def g_boleto():
    return random.choice([
        f"Sua fatura de {random.choice(['energia', 'internet', 'condomínio', 'cartão'])} venceu. Evite o corte: pague a segunda via com desconto em {link_falso()}",
        f"Débito pendente em seu CPF no valor de {valor()}. Quite {prazo()} para evitar protesto: {link_falso('receita')}",
        f"Aviso de cobrança: boleto em atraso. Gere a 2ª via atualizada em {link_falso()} e evite negativação no Serasa.",
        f"Negocie sua dívida com 90% de desconto só {prazo()}! Acesse {link_falso()} e pague com boleto.",
    ])


def g_falsa_entrega():
    cod = f"BR{random.randint(10000000, 99999999)}BR"
    return random.choice([
        f"Correios: sua encomenda {cod} está retida. Pague a taxa de importação de {valor()} em {link_falso('correios')}",
        f"Sua entrega não pôde ser realizada por endereço incompleto. Atualize em {link_falso('correios')} em até {prazo()}.",
        f"Encomenda {cod} aguardando pagamento de taxa alfandegária. Após {prazo()} será devolvida ao remetente: {link_falso()}",
        f"Tentamos entregar seu pedido hoje. Reagende pelo link {link_falso()} e confirme o pagamento do frete de {valor()}.",
    ])


def g_falso_emprego():
    return random.choice([
        f"Olá! Vaga de meio período em casa, ganhe {valor()} por dia curtindo vídeos. Chama no WhatsApp {tel()}",
        f"Você foi selecionado para trabalho remoto. Ganhos de até {valor()} por dia. Para começar, pague a taxa de cadastro.",
        f"Oportunidade: avaliar produtos online, renda extra de {valor()} por semana. Fale com a recrutadora {random.choice(NOMES)} pelo link {link_falso()}",
        f"Vaga temporária com salário de {valor()}. Envie CPF e foto do documento para garantir sua vaga {prazo()}.",
    ])


def g_premio():
    return random.choice([
        f"Parabéns! Seu número foi sorteado e você ganhou {valor()}. Resgate em {link_falso()} {prazo()}.",
        f"Você ganhou um iPhone na promoção de aniversário da {random.choice(LOJAS)}! Pague só o frete em {link_falso()}",
        f"Seu CPF tem valores a receber do governo: {valor()}. Consulte e resgate em {link_falso('gov')}",
        f"Pontos do seu cartão expiram {prazo()}! Troque por {valor()} em dinheiro em {link_falso()}",
        f"Parabéns, cliente premiado! Para liberar seu prêmio de {valor()}, faça um pix de {valor()} de taxa.",
    ])


def g_loja_falsa():
    lj = random.choice(LOJAS)
    return random.choice([
        f"Queima de estoque {lj}: Air fryer por {valor()} só {prazo()}! Compre via pix em {link_falso()}",
        f"{lj} liquidação: tudo com 80% OFF. Últimas unidades, aproveite: {link_falso()}",
        f"Seu carrinho na {lj} tem um cupom de 70% esperando. Finalize {prazo()} no link {link_falso()}",
        f"Black Friday antecipada! TV 55 polegadas por {valor()}. Pagamento só no pix: {link_falso()}",
    ])


def g_pix_falso():
    n = random.choice(NOMES)
    return random.choice([
        f"Oi, fiz um pix de {valor()} pra você por engano. Pode devolver pra essa chave? Segue o comprovante.",
        f"Seu PIX agendado de {valor()} para {n} será processado {prazo()}. Para cancelar acesse {link_falso('pix')}",
        f"Você recebeu um PIX de {valor()}. Para liberar o valor, confirme seus dados em {link_falso('pix')}",
        f"Comprovante: transferi {valor()} a mais. Me devolve a diferença nesse pix por favor, é urgente.",
    ])


GOLPES = {"falsa_central": g_falsa_central, "falso_parente": g_falso_parente, "boleto_falso": g_boleto,
          "falsa_entrega": g_falsa_entrega, "falso_emprego": g_falso_emprego, "premio": g_premio,
          "loja_falsa": g_loja_falsa, "pix_falso": g_pix_falso}


# ---------------------------------------------------------------- mensagens legítimas brasileiras (golpe = 0)
def l_banco():
    b, _ = random.choice(BANCOS)
    return random.choice([
        f"{b}: compra aprovada de {valor()} em {random.choice(LOJAS)} no cartão final {random.randint(1000, 9999)}.",
        f"Você recebeu um PIX de {valor()} de {random.choice(NOMES)}. Confira no app {b}.",
        f"{b}: seu código de verificação é {random.randint(100000, 999999)}. Não compartilhe com ninguém, nem com funcionários do banco.",
        f"{b}: a fatura do seu cartão fecha dia {random.randint(1, 28)}. Valor parcial {valor()}. Veja os detalhes no app.",
        f"{b} lembra: nunca pedimos senha, token ou código por SMS, WhatsApp ou ligação.",
    ])


def l_entrega():
    cod = f"BR{random.randint(10000000, 99999999)}BR"
    return random.choice([
        f"Seu pedido da {random.choice(LOJAS)} saiu para entrega e chega hoje até as {hora()}. Acompanhe pelo app.",
        f"Correios: objeto {cod} entregue em {random.randint(1, 28)}/{random.randint(1, 12)} às {hora()}.",
        f"{random.choice(LOJAS)}: pedido confirmado! Previsão de entrega em {random.randint(2, 9)} dias úteis.",
        f"Seu pacote está no centro de distribuição da sua cidade. Acompanhe pelo app da {random.choice(LOJAS)}.",
    ])


def l_cobranca():
    return random.choice([
        f"Sua conta de {random.choice(['energia', 'água', 'internet', 'celular'])} de {random.choice(['outubro', 'novembro'])} está disponível no app. Vencimento dia {random.randint(1, 28)}.",
        f"Lembrete: a mensalidade da escola vence dia {random.randint(1, 28)}. O boleto está no portal do aluno.",
        f"Recebemos o pagamento de {valor()}. Obrigado!",
        f"Débito automático programado de {valor()} para o dia {random.randint(1, 28)}.",
    ])


def l_saude():
    return random.choice([
        f"Lembrete: sua consulta com Dr(a). {random.choice(NOMES)} é amanhã às {hora()}. Responda 1 para confirmar ou 2 para remarcar.",
        f"Seu resultado de exame está disponível no site do laboratório. Use o protocolo entregue no atendimento.",
        f"Farmácia: seu pedido está pronto para retirada até as {hora()}.",
        f"Campanha de vacinação: postos abertos sábado das 8h às 17h. Leve documento e carteira de vacinação.",
    ])


def l_conversa():
    n = random.choice(NOMES)
    return random.choice([
        f"Oi {random.choice(PARENTES)}, chego aí umas {hora()}. Quer que eu leve pão?",
        f"{n}, a reunião mudou pra {hora()}, mesma sala.",
        f"Bom dia! Vai ter almoço de domingo aí? Avisa que eu levo a sobremesa.",
        f"Te mandei o pix da pizza, confere aí. Valeu!",
        f"Mãe, cheguei bem. Amanhã te ligo.",
        f"Alguém sabe se a aula de amanhã vai ser online?",
    ])


def l_servico():
    return random.choice([
        f"Seu código de acesso ao WhatsApp é {random.randint(100, 999)}-{random.randint(100, 999)}. Não compartilhe este código.",
        f"Sua corrida foi concluída. Total {valor()}. Avalie seu motorista no app.",
        f"Operadora: seu pacote de dados foi renovado. Consulte o saldo no app.",
        f"Seu agendamento no salão está confirmado para sexta às {hora()}.",
    ])


def l_governo():
    return random.choice([
        f"Gov.br: seu login foi feito em um novo dispositivo. Se não foi você, troque a senha pelo app gov.br.",
        f"Prefeitura: o IPTU está disponível para consulta no site oficial da prefeitura. Pagamento em cota única até dia {random.randint(1, 28)}.",
        f"Detran: seu agendamento para renovação da CNH está confirmado para {random.randint(1, 28)}/{random.randint(1, 12)} às {hora()}.",
        f"Defesa Civil: previsão de chuva forte nas próximas horas. Em emergência, ligue 199.",
    ])


def l_compra():
    lj = random.choice(LOJAS)
    return random.choice([
        f"{lj}: seu pagamento de {valor()} foi aprovado. Obrigado pela compra!",
        f"{lj}: a nota fiscal do seu pedido está disponível em Meus Pedidos no app.",
        f"Você tem um cupom de 10% para a próxima compra no app da {lj}. Válido até o fim do mês.",
        f"{lj}: seu estorno de {valor()} foi processado e aparece na próxima fatura.",
    ])


LEGITIMAS = {"banco_aviso": l_banco, "entrega": l_entrega, "cobranca": l_cobranca, "saude": l_saude,
             "conversa": l_conversa, "servico": l_servico, "governo": l_governo, "compra": l_compra}


def gerar(funcoes, golpe, por_tipo):
    linhas, vistos = [], set()
    for tipo, f in funcoes.items():
        n, tentativas = 0, 0
        while n < por_tipo and tentativas < por_tipo * 50:
            tentativas += 1
            t = mascarar(f())
            if t not in vistos:
                vistos.add(t)
                linhas.append({"texto": t, "golpe": golpe, "tipo": tipo, "origem": "sintetico", "pais": "BR"})
                n += 1
    return linhas


# ---------------------------------------------------------------- BrScamsFacebook
# "Golpes de Desinformação Digital" fica de fora: é fake news, não golpe que pede dinheiro ou dados.
CATEGORIAS_BRSCAMS = {
    "Golpes Baseados Em Relacionamento": (1, "relacionamento"),
    "Golpes de Ganho Financeiro Ilusório": (1, "ganho_ilusorio"),
    "Ataques de Phishing e Roubo de Dados": (1, "phishing"),
    "Fraudes em Lojas Virtuais Falsas": (1, "loja_falsa"),
    "Seguro": (0, "legitima"),
}


def ler_brscams():
    linhas = []
    with open(BRUTOS / "brscamsfacebook" / "BrScamsFacebook.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Categoria"] not in CATEGORIAS_BRSCAMS:
                continue
            golpe, tipo = CATEGORIAS_BRSCAMS[r["Categoria"]]
            fonte = r["Dataset"].lower().replace(" ", "")  # "Externo 4" -> "externo4"
            linhas.append({"texto": mascarar(r["Mensagem"]), "golpe": golpe, "tipo": tipo,
                           "origem": "brscams_" + fonte, "pais": "BR"})
    return linhas


def montar_mensagens():
    linhas = ler_brscams() + gerar(GOLPES, 1, 35) + gerar(LEGITIMAS, 0, 35)
    unicas, vistos = [], set()
    for l in linhas:
        if l["texto"] and l["texto"].lower() not in vistos:
            vistos.add(l["texto"].lower())
            unicas.append(l)
    random.shuffle(unicas)
    with open(AQUI / "mensagens.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["texto", "golpe", "tipo", "origem", "pais"])
        w.writeheader()
        w.writerows(unicas)
    return unicas


# ---------------------------------------------------------------- URLs brasileiras sintéticas
# O LegitPhish tem um viés forte: 100% dos links legítimos usam HTTPS e 77% dos de phishing usam
# IP no lugar do domínio. Um modelo treinado só nele deixa passar o golpe brasileiro típico
# (https://itau-seguranca-app.xyz/login). Estas URLs cobrem esse caso, dos dois lados.
DOMINIOS_OFICIAIS = ["itau.com.br", "bb.com.br", "caixa.gov.br", "bradesco.com.br", "nubank.com.br",
                     "santander.com.br", "bancointer.com.br", "c6bank.com.br", "gov.br", "correios.com.br",
                     "mercadolivre.com.br", "magazineluiza.com.br", "casasbahia.com.br", "americanas.com.br",
                     "amazon.com.br", "shopee.com.br", "picpay.com", "serasa.com.br", "detran.sp.gov.br",
                     "prefeitura.sp.gov.br", "receita.fazenda.gov.br", "uol.com.br", "globo.com", "ifood.com.br"]
CAMINHOS_LEGITIMOS = ["", "/", "/para-voce", "/cartoes", "/ajuda", "/atendimento", "/rastreamento",
                      "/ofertas", "/conta", "/pt-br/servicos", "/noticias/2026/11", "/produto/MLB-{n}",
                      "/p/{n}", "/busca?q=geladeira", "/institucional/seguranca", "/app"]
MARCAS_URL = ["itau", "bradesco", "caixa", "bb", "nubank", "santander", "inter", "correios", "gov",
              "receita", "mercadolivre", "magalu", "shopee", "pix", "serasa", "detran", "c6"]
PALAVRAS_GOLPE = ["seguranca", "atualiza", "atualizacao", "regulariza", "desbloqueio", "cliente", "app",
                  "valida", "suporte", "acesso", "login", "premio", "taxa", "rastreio", "resgate", "cadastro"]
TLDS_GOLPE = ["xyz", "top", "online", "site", "info", "click", "shop", "live", "com", "net", "store", "cc"]
CAMINHOS_GOLPE = ["", "/", "/login", "/acesso", "/pix", "/pagar?id={n}", "/validar", "/cliente/atualizar",
                  "/index.php", "/br/seguranca", "/token?c={n}"]


def gerar_urls_br(qtd):
    sys.path.insert(0, str(AQUI.parent))
    from features import extrair_features, COLUNAS_URL_LEGITPHISH  # mesma função do notebook e da API

    linhas, vistos = [], set()

    def add(url, phishing):
        if url not in vistos:
            vistos.add(url)
            f = extrair_features(url)
            linhas.append({"url": url, **{c: f[c] for c in COLUNAS_URL_LEGITPHISH}, "phishing": phishing, "origem": "sintetico_br"})

    while sum(l["phishing"] == 0 for l in linhas) < qtd:
        dom = random.choice(DOMINIOS_OFICIAIS)
        sub = random.choice(["www.", "www.", "", "app.", "ajuda.", "conta."])
        caminho = random.choice(CAMINHOS_LEGITIMOS).format(n=random.randint(1000000, 99999999))
        add(f"{random.choice(['https://'] * 9 + ['http://', ''])}{sub}{dom}{caminho}", 0)

    while sum(l["phishing"] == 1 for l in linhas) < qtd:
        marca, palavra = random.choice(MARCAS_URL), random.choice(PALAVRAS_GOLPE)
        tld = random.choice(TLDS_GOLPE)
        forma = random.random()
        if forma < 0.45:
            host = f"{marca}-{palavra}.{tld}"
        elif forma < 0.65:
            host = f"{marca}{palavra}{random.randint(1, 99)}.{tld}"
        elif forma < 0.80:
            host = f"{marca}.com.br.{palavra}-{random.choice(['br', 'online', 'app'])}.{tld}"  # marca no subdomínio
        elif forma < 0.92:
            host = f"{palavra}-{marca}-{random.choice(['br', 'brasil', 'oficial'])}.{tld}"
        else:
            host = f"www.{marca}{random.choice(['', '-'])}{palavra}.{random.choice(['com', 'com.br', 'net'])}"
        caminho = random.choice(CAMINHOS_GOLPE).format(n=random.randint(1000, 999999))
        add(f"{random.choice(['https://'] * 7 + ['http://'] * 2 + [''])}{host}{caminho}", 1)
    return linhas


# ---------------------------------------------------------------- LegitPhish + sintéticas
def montar_urls():
    linhas = []
    with open(BRUTOS / "legitphish.csv", encoding="utf-8") as fin:
        r = csv.DictReader(fin)
        colunas = [c for c in r.fieldnames if c not in ("URL", "ClassLabel")]
        for linha in r:
            if linha["ClassLabel"] not in ("0", "1"):
                continue  # 1 linha sem rótulo no original
            saida = {k: v for k, v in linha.items() if k not in ("URL", "ClassLabel")}
            saida["url"] = linha["URL"]
            saida["phishing"] = 1 if linha["ClassLabel"] == "0" else 0  # no original, 0 = phishing
            saida["origem"] = "legitphish"
            linhas.append(saida)
    linhas += gerar_urls_br(2500)
    random.shuffle(linhas)
    with open(AQUI / "urls.csv", "w", newline="", encoding="utf-8") as fout:
        w = csv.DictWriter(fout, fieldnames=["url"] + colunas + ["phishing", "origem"])
        w.writeheader()
        w.writerows(linhas)
    return len(linhas)


if __name__ == "__main__":
    msgs = montar_mensagens()
    print(f"mensagens.csv: {len(msgs)} linhas")
    print(f"urls.csv: {montar_urls()} linhas")
