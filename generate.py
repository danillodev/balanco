import os, json, html, datetime, feedparser
from anthropic import Anthropic

# (nome do site, categoria, endereço do feed RSS). Feeds que falharem são ignorados.
FEEDS = [
    ("g1", "Economia", "https://g1.globo.com/rss/g1/economia/"),
    ("g1", "Política", "https://g1.globo.com/rss/g1/politica/"),
    ("Folha", "Economia", "https://feeds.folha.uol.com.br/mercado/rss091.xml"),
    ("Folha", "Política", "https://feeds.folha.uol.com.br/poder/rss091.xml"),
    ("InfoMoney", "Economia", "https://www.infomoney.com.br/feed/"),
    ("Exame", "Economia", "https://exame.com/feed/"),
    ("BBC Brasil", "Geral", "https://feeds.bbci.co.uk/portuguese/rss.xml"),
    ("Agência Brasil", "Economia", "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml"),
    ("Agência Brasil", "Política", "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml"),
    ("CNN Brasil", "Economia", "https://www.cnnbrasil.com.br/economia/feed/"),
    ("CNN Brasil", "Política", "https://www.cnnbrasil.com.br/politica/feed/"),
]
MODELO = "claude-sonnet-5-5"


def coletar():
    itens = []
    for fonte, cat, url in FEEDS:
        try:
            for e in feedparser.parse(url).entries[:8]:
                itens.append({"fonte": fonte, "cat": cat,
                              "titulo": e.get("title", "").strip(),
                              "link": e.get("link", "")})
        except Exception as ex:
            print("Feed falhou:", fonte, ex)
    for i, it in enumerate(itens):
        it["id"] = i
    print(len(itens), "manchetes coletadas")
    return itens


def curar(itens):
    prompt = (
        "Você é editor de um site brasileiro de notícias de economia e política. "
        "Abaixo estão as manchetes coletadas hoje (JSON). Escolha de 8 a 10 assuntos "
        "mais relevantes, equilibrando economia e política. Se um assunto aparece em "
        "mais de uma fonte, junte e liste todos os ids. Em política, prefira assuntos "
        "cobertos por 2 ou mais fontes e use tom neutro e factual, sem adjetivos de opinião. "
        "Para cada assunto devolva: titulo (reescrito, factual), resumo (1 a 2 frases em "
        "palavras próprias, sem copiar trechos), categoria ('Economia' ou 'Política'), "
        "tags (lista com valores entre: juros, inflacao, dolar, bolsa, eleicao, governo, geral) "
        "e ids (lista de ids das manchetes). Responda SOMENTE com uma lista JSON.\n\n"
        + json.dumps(itens, ensure_ascii=False)
    )
    r = Anthropic().messages.create(
        model=MODELO, max_tokens=4000,
        messages=[{"role": "user", "content": prompt}])
    txt = r.content[0].text.strip().strip("`").strip()
    if txt.lower().startswith("json"):
        txt = txt[4:]
    return json.loads(txt)


def escolher_produtos(assuntos):
    produtos = json.load(open("produtos.json", encoding="utf-8"))
    tags = {t for a in assuntos for t in a.get("tags", [])}
    certos = [p for p in produtos if tags & set(p["tags"])]
    resto = [p for p in produtos if p not in certos]
    return (certos + resto)[:4]


def pagina(assuntos, produtos, itens):
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    por_id = {i["id"]: i for i in itens}
    blocos = ""
    for a in assuntos:
        vistos, fontes = set(), ""
        for i in a.get("ids", []):
            it = por_id.get(i)
            if it and it["link"] not in vistos:
                vistos.add(it["link"])
                fontes += f'<a href="{html.escape(it["link"])}" rel="noopener" target="_blank">{html.escape(it["fonte"])}</a> '
        cor = "eco" if a["categoria"] == "Economia" else "pol"
        blocos += (f'<article><p class="k {cor}">{html.escape(a["categoria"])}</p>'
                   f'<h2>{html.escape(a["titulo"])}</h2><p>{html.escape(a["resumo"])}</p>'
                   f'<p class="s">Leia em: {fontes}</p></article>')
    prods = "".join(
        f'<a class="p" href="{html.escape(p["url"])}" rel="sponsored noopener" target="_blank">'
        f'<b>{html.escape(p["nome"])}</b><small>{html.escape(p["loja"])}</small></a>'
        for p in produtos)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Balanço: economia e política</title>
<style>
:root{{--bg:#F7F8FA;--sf:#fff;--ink:#101828;--mute:#566074;--line:#DDE1E8;--eco:#0B7A4B;--pol:#3F37C9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0D1117;--sf:#161B22;--ink:#E7EBF2;--mute:#9AA4B5;--line:#2A313C;--eco:#3DD598;--pol:#8F8AFF}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,sans-serif}}
.w{{max-width:980px;margin:0 auto;padding:0 16px}}
h1{{font-size:clamp(40px,11vw,64px);margin:20px 0 4px;letter-spacing:-.04em}}
.d{{color:var(--mute);border-bottom:3px solid var(--ink);padding-bottom:12px;margin:0}}
.g{{display:grid;gap:28px;padding:24px 0 48px}}@media(min-width:860px){{.g{{grid-template-columns:1fr 300px}}}}
article{{padding:16px 0;border-top:1px solid var(--line)}}h2{{margin:0 0 8px;font-size:21px;line-height:1.2}}
.k{{font-size:13px;font-weight:700;margin:0 0 6px}}.eco{{color:var(--eco)}}.pol{{color:var(--pol)}}
.s{{font-size:14px;color:var(--mute)}}.s a{{color:var(--ink);font-weight:600;margin-right:8px}}
.box{{background:var(--sf);border:1px solid var(--line);border-radius:12px;padding:16px}}
.p{{display:block;padding:10px 0;border-top:1px solid var(--line);text-decoration:none;color:var(--ink)}}
.p small{{display:block;color:var(--mute)}}footer{{color:var(--mute);font-size:14px;padding:0 0 40px}}
</style></head><body><div class="w">
<h1>Balanço</h1><p class="d">Economia e política do Brasil · Edição de {hoje}</p>
<div class="g"><main>{blocos}</main>
<aside><div class="box"><b>Para ler e se planejar</b>
<p class="s">Anúncios de lojas parceiras.</p>{prods}</div></aside></div>
<footer><p>Alguns links levam a lojas parceiras e podem render comissão ao Balanço, sem custo extra para você. Os resumos são escritos pela nossa equipe; a cobertura completa está nos links das fontes.</p></footer>
</div></body></html>"""


if __name__ == "__main__":
    itens = coletar()
    assuntos = curar(itens)
    os.makedirs("docs", exist_ok=True)
    open("docs/index.html", "w", encoding="utf-8").write(
        pagina(assuntos, escolher_produtos(assuntos), itens))
    print("Edição gerada com", len(assuntos), "assuntos")
