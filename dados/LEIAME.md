# Dados de treino

Gerados por `python montar_dados.py` a partir de `brutos/`.

## mensagens.csv (modelo 1: essa mensagem é golpe?)

`texto,golpe,tipo,origem,pais`: 933 mensagens, todas em português do Brasil, golpe = 1.

| Origem | Golpe | Não golpe | Observação |
|---|---|---|---|
| BrScamsFacebook (`brscams_*`) | 298 | 75 | Golpes reais: relacionamento, ganho ilusório, phishing, loja falsa. Legítimas = categoria `Seguro` |
| Sintético (`sintetico`) | 280 | 280 | 8 tipos de golpe × 35 e 8 tipos de mensagem legítima × 35 |

- Telefones, CPFs, e-mails e números longos foram trocados por `[TELEFONE]`, `[CPF]` e `[EMAIL]`.
- A categoria "Golpes de Desinformação Digital" do BrScamsFacebook ficou de fora: é fake news, não golpe que pede dinheiro ou dados.
- O sufixo de `origem` diz a fonte original no BrScamsFacebook: `interno` (coleta no Facebook), `externo3` e `externo4` (nativos em PT-BR), os demais traduzidos automaticamente do inglês.
- As mensagens sintéticas foram geradas por modelos de frase. Há o mesmo número de golpes e de legítimas.
- **Teste o modelo só com `origem` começando por `brscams`** (dados reais). Avaliar com os sintéticos infla as métricas.
- O MOZ-Smishing (português de Moçambique) foi usado antes e saiu. O arquivo foi removido do repositório.
- O ideal é cada integrante acrescentar algumas mensagens reais do próprio celular, já mascaradas, com `origem = real`. Faltam principalmente **mensagens legítimas**.

Fonte: [BrScamsFacebook, Kaggle](https://www.kaggle.com/datasets/brunaassisgt/brscamsfacebook) (licença MIT), de Bruna Assis Norões (UFF), artigo VeritaPlugin, SBSeg 2026. Contém links e telefones reais de golpistas: não acesse.

## urls.csv (modelo 2: esse link é phishing?)

`url`, 16 features calculadas a partir do próprio endereço, `phishing`, `origem`: 106.218 URLs.

| Origem | Phishing | Legítimo |
|---|---|---|
| LegitPhish | 63.678 | 37.540 |
| Sintético BR (`sintetico_br`) | 2.500 | 2.500 |

- **No original, `ClassLabel` 0 = phishing.** Aqui virou `phishing = 1` para ficar intuitivo. Uma linha sem rótulo foi removida.
- **Por que as URLs brasileiras sintéticas:** no LegitPhish, 100% dos links legítimos usam HTTPS e 77% dos de phishing usam IP. Treinado só nele, o modelo deixava passar `https://itau-seguranca-app.xyz/login` (14%). As sintéticas trazem domínios oficiais brasileiros e golpes no formato `marca-palavra.xyz`, com HTTPS dos dois lados.
- Todas as features saem da URL (tamanho, pontos, subdomínios, HTTPS, entropia…), então o Flask consegue recalcular a partir do link recebido.
- Na análise exploratória, vale mostrar que alguns domínios de phishing se repetem centenas de vezes. Para não vazar o mesmo domínio entre treino e teste, separe por domínio (`GroupShuffleSplit`).

Fonte: [LegitPhish, Mendeley Data](https://data.mendeley.com/datasets/hx4m73v2sf/2), DOI 10.17632/hx4m73v2sf.2. Artigo: [PMC12538017](https://pmc.ncbi.nlm.nih.gov/articles/PMC12538017/).
