#!/usr/bin/env python3
"""Bongarbit — Dashboard de Seleção · Escola de Luteria 2026"""

import csv, json, re, os, hashlib, random
from pathlib import Path
from collections import Counter

SHEET_ID = "1aV8c0MJ87UlccE056i3q1S0BXAbvwbaKeXxX9e0ZfF8"
TSV_FILE = "inscritos.tsv"          # arquivo local (baixado do Sheets ou copiado manualmente)
TSV_FALLBACK = "Inscritos Bongarbit - Escola de Luteria - Página1 (2).tsv"
OUTPUT   = "index.html"
IMAGES   = "imagens"
GEOCACHE = "geocache.json"

CITY_COORDS = {
    "recife":               (-8.0522, -34.9286),
    "olinda":               (-8.0089, -34.8553),
    "paulista":             (-7.9399, -34.8862),
    "jaboatão":             (-8.1787, -35.0035),
    "são lourenço":         (-8.0029, -35.0280),
    "abreu e lima":         (-7.9100, -34.9013),
    "camaragibe":           (-8.0223, -34.9814),
}

GROUPS = {
    "coco_umbigada": {
        "label": "Coco de Umbigada", "color": "#27AE60", "bg": "#0d2b18",
        "patterns": [r"umbigada", r"quinho.*caet", r"coco.*guadalup"],
        "fields": ["grupos_culturais", "coletivos", "terreiro", "comunidade", "como_soube"],
    },
    "darue_malungo": {
        "label": "Daruê Malungo", "color": "#E74C3C", "bg": "#2b0d0d",
        "patterns": [r"daruê?\s*malungo"],
        "fields": ["grupos_culturais", "coletivos", "terreiro", "comunidade", "por_que"],
    },
    "boi_mandingueiro": {
        "label": "Boi Mandingueiro", "color": "#F39C12", "bg": "#2b1a0d",
        "patterns": [r"boi\s*mandingueiro", r"mandingueiro"],
        "fields": ["grupos_culturais", "coletivos", "terreiro", "comunidade", "como_soube"],
    },
    "alafin_oyo": {
        "label": "Alafin Oyó", "color": "#9B59B6", "bg": "#1a0d2b",
        "patterns": [r"alafín?\s*oy"],
        "fields": ["grupos_culturais", "coletivos", "terreiro", "comunidade", "por_que"],
    },
    "cambinda_estrela": {
        "label": "Cambinda Estrela", "color": "#3498DB", "bg": "#0d1a2b",
        "patterns": [r"cambinda"],
        "fields": ["grupos_culturais", "coletivos", "terreiro", "por_que"],
    },
}

# ── Utilitários ────────────────────────────────────────────────────────────────

def normalize_city(s):
    if not s or not s.strip():
        return "Pernambuco (n/e)"
    s = s.strip()
    s = re.sub(r"[\s,/\-]+PE\.?\s*$", "", s, flags=re.I).strip()
    s = re.split(r"[,/]", s)[0].strip()
    s = re.sub(r"\s+pernambuco\s*$", "", s, flags=re.I).strip()
    s = re.sub(r"\s+pe\s*$", "", s, flags=re.I).strip()
    cl = s.lower()
    if "recife" in cl: return "Recife"
    if "olinda" in cl: return "Olinda"
    if "paulista" in cl: return "Paulista"
    if "jaboatão" in cl or "jaboatao" in cl: return "Jaboatão dos Guararapes"
    if "são lourenço" in cl or "sao lourenco" in cl: return "São Lourenço da Mata"
    if "sapucaia" in cl: return "Olinda"
    if not cl or cl in ("pe", "pe.", "pernambuco"): return "Pernambuco (n/e)"
    if "pernambuco" in cl: return "Pernambuco (n/e)"
    return s.title()


def get_coords(cep, city, cid):
    geo = {}
    if Path(GEOCACHE).exists():
        geo = json.loads(Path(GEOCACHE).read_text(encoding="utf-8"))
    cep_d = re.sub(r"\D", "", cep)
    if cep_d and cep_d in geo:
        lat, lon = geo[cep_d]["lat"], geo[cep_d]["lon"]
        random.seed(cid * 7)
        return lat + random.uniform(-0.003, 0.003), lon + random.uniform(-0.003, 0.003)
    cl = city.lower()
    for key, (lat, lon) in CITY_COORDS.items():
        if key in cl:
            random.seed(cid)
            return lat + random.uniform(-0.02, 0.02), lon + random.uniform(-0.02, 0.02)
    random.seed(cid)
    return -8.0522 + random.uniform(-0.02, 0.02), -34.9286 + random.uniform(-0.02, 0.02)


PALETTE = [
    "#C0392B","#E91E63","#9C27B0","#673AB7","#3F51B5",
    "#1565C0","#0277BD","#00838F","#2E7D32","#558B2F",
    "#F57F17","#E65100","#4E342E","#546E7A","#37474F",
]

def avatar_color(name):
    return PALETTE[int(hashlib.md5(name.encode()).hexdigest()[:6], 16) % len(PALETTE)]

def avatar_initials(name):
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "??"

def extract_instagram(text):
    if not text: return None
    m = re.search(r"instagram\.com/([^\s/?&|]+)", text, re.I)
    if m:
        u = m.group(1).strip("/")
        if u and u not in ("p", "explore", "accounts", "reel", "reels"):
            return u
    m = re.search(r"@([a-zA-Z0-9_.]{2,30})", text)
    return m.group(1) if m else None

def parse_age(s):
    if not s: return None
    m = re.search(r"\d+", s)
    if m:
        v = int(m.group())
        if 10 <= v <= 100: return v
    return None

def age_group(age):
    if age is None: return "Não informada"
    if age < 20: return "15-19"
    if age < 30: return "20-29"
    if age < 40: return "30-39"
    if age < 50: return "40-49"
    if age < 60: return "50-59"
    return "60+"

def detect_xamba(c):
    reasons = []
    t = c["terreiro"].lower()
    if "xambá" in t or "xamba" in t:
        reasons.append("Terreiro Xambá")
    com = c["comunidade"].lower()
    if "xambá" in com or "xamba" in com:
        reasons.append("Quilombo Xambá")
    blob = " ".join([c["terreiro"], c["comunidade"], c["grupos_culturais"],
                     c["coletivos"], c["endereco"], c["nome"]]).lower()
    if "portão do gelo" in blob or "portao do gelo" in blob:
        reasons.append("Portão do Gelo")
    gc = (c["grupos_culturais"] + " " + c["coletivos"]).lower()
    if "xambá" in gc or "xamba" in gc:
        reasons.append("Grupos/Coletivos Xambá")
    if re.sub(r"\D", "", c["cep"]).startswith("5327"):
        reasons.append("Mora na região do Xambá")
    if re.search(r"grupo\s+bongar|centro.*bongar", gc):
        reasons.append("Membro do Grupo Bongar")
    if not reasons and ("xambá" in blob or "xamba" in blob or "xambá" in gc or "xamba" in gc):
        reasons.append("Menção ao Xambá")
    return list(dict.fromkeys(reasons))

def detect_groups(c):
    found = {}
    for key, grp in GROUPS.items():
        for field in grp["fields"]:
            text = c.get(field, "").lower()
            if any(re.search(p, text, re.I) for p in grp["patterns"]):
                found[key] = grp["label"]
                break
    return found


# ── Google Sheets ─────────────────────────────────────────────────────────────

def fetch_sheet():
    """Baixa o TSV da planilha pública do Google Sheets.
    A planilha precisa estar com acesso 'Qualquer pessoa com o link pode ver'.
    Salva em TSV_FILE para ser lido por parse_tsv().
    """
    import urllib.request, urllib.error
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=tsv&gid=0"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read().decode("utf-8")
        with open(TSV_FILE, "w", encoding="utf-8") as f:
            f.write(data)
        rows = data.strip().count("\n")
        print(f"  ✓ Planilha baixada do Google Sheets ({rows} linhas)")
        return True
    except urllib.error.HTTPError as e:
        print(f"  ✗ Google Sheets: HTTP {e.code} — planilha não pública ou ID errado")
    except Exception as e:
        print(f"  ✗ Google Sheets: {e}")
    return False


# ── Parse TSV ──────────────────────────────────────────────────────────────────

def parse_tsv():
    candidates = []
    seen = set()
    with open(TSV_FILE, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        for row in reader:
            while len(row) < 24:
                row.append("")
            if not row[0].strip() and not row[1].strip():
                continue
            name = row[1].strip()
            phone = row[4].strip()
            dup_key = f"{name.lower()}|{phone}"
            if dup_key in seen and dup_key != "|":
                continue
            seen.add(dup_key)

            c = {
                "id": len(candidates) + 1,
                "timestamp": row[0].strip(),
                "nome": name,
                "nome_social": row[2].strip(),
                "telefone": phone,
                "cpf": row[5].strip(),
                "endereco": row[6].strip(),
                "cep": row[7].strip(),
                "cidade_estado": row[8].strip(),
                "idade_raw": row[9].strip(),
                "genero": row[10].strip(),
                "raca": row[11].strip(),
                "pcd": row[12].strip(),
                "desc_deficiencia": row[13].strip(),
                "renda": row[14].strip(),
                "terreiro": row[15].strip(),
                "comunidade": row[16].strip(),
                "grupos_culturais": row[17].strip(),
                "coletivos": row[18].strip(),
                "por_que": row[19].strip(),
                "disponibilidade": row[20].strip(),
                "redes_sociais": row[21].strip(),
                "como_soube": row[22].strip(),
                "email": row[23].strip(),
            }

            c["cidade"] = normalize_city(c["cidade_estado"])
            c["idade"] = parse_age(c["idade_raw"])
            c["faixa_etaria"] = age_group(c["idade"])
            c["instagram"] = extract_instagram(c["redes_sociais"])
            c["avatar_color"] = avatar_color(name)
            c["avatar_initials"] = avatar_initials(name)
            c["disponivel_total"] = "total disponibilidade" in c["disponibilidade"].lower()
            c["is_pcd"] = c["pcd"].strip().upper().startswith("S")

            soube = c["como_soube"]
            c["is_indicado"] = bool(re.search(r"indica[çcr]", soube, re.I))
            # Texto além da palavra genérica "Indicação" → tem nome ou contexto específico
            generic = re.fullmatch(r"indica[çc][aã]o\.?", soube.strip(), re.I)
            c["indicador"] = "" if generic else soube if c["is_indicado"] else ""

            lat, lon = get_coords(c["cep"], c["cidade"], c["id"])
            c["lat"] = round(lat, 6)
            c["lon"] = round(lon, 6)

            xamba = detect_xamba(c)
            c["is_xamba"] = bool(xamba)
            c["xamba_reasons"] = xamba
            c["cultural_groups"] = detect_groups(c)

            photo = None
            for suffix in ("", "_sem_rosto"):
                path = f"{IMAGES}/{c['id']}{suffix}.jpg"
                if os.path.exists(path):
                    photo = path
                    break
            c["photo"] = photo

            candidates.append(c)
    return candidates


# ── Stats ──────────────────────────────────────────────────────────────────────

def compute_stats(candidates):
    neg = {"não", "nao", "no", "não.", "nao.", "n/a", ""}

    def has(c, field):
        return c.get(field, "").strip().lower() not in neg

    ages = [c["idade"] for c in candidates if c["idade"]]
    stats = {
        "total": len(candidates),
        "disponivel_total": sum(1 for c in candidates if c["disponivel_total"]),
        "is_xamba": sum(1 for c in candidates if c["is_xamba"]),
        "tem_terreiro": sum(1 for c in candidates if has(c, "terreiro")),
        "tem_comunidade": sum(1 for c in candidates if has(c, "comunidade")),
        "tem_grupos": sum(1 for c in candidates if has(c, "grupos_culturais")),
        "tem_coletivos": sum(1 for c in candidates if has(c, "coletivos")),
        "media_idade": round(sum(ages) / len(ages), 1) if ages else 0,
        "genero": dict(Counter(c["genero"] for c in candidates if c["genero"])),
        "raca": dict(Counter(c["raca"] for c in candidates if c["raca"])),
        "cidade": dict(Counter(c["cidade"] for c in candidates)),
        "renda": dict(Counter(c["renda"] for c in candidates if c["renda"])),
        "como_soube": dict(Counter(c["como_soube"] for c in candidates if c["como_soube"])),
        "faixa_etaria": dict(Counter(c["faixa_etaria"] for c in candidates)),
        "disponibilidade": {
            "Total": sum(1 for c in candidates if c["disponivel_total"]),
            "Parcial": sum(1 for c in candidates if not c["disponivel_total"]),
        },
    }
    for key in GROUPS:
        stats[f"group_{key}"] = sum(1 for c in candidates if key in c["cultural_groups"])
    stats["groups_def"] = {
        k: {"label": v["label"], "color": v["color"], "bg": v["bg"]}
        for k, v in GROUPS.items()
    }
    return stats


# ── HTML ───────────────────────────────────────────────────────────────────────

def generate_html(candidates, stats):
    data_json  = json.dumps(candidates, ensure_ascii=False)
    stats_json = json.dumps(stats, ensure_ascii=False)

    extra_pills = ""
    for key, grp in GROUPS.items():
        count = stats.get(f"group_{key}", 0)
        if count:
            extra_pills += (
                f'<div class="col-6 col-md-2"><div class="stat-pill" '
                f'style="border-color:{grp["color"]}40;background:linear-gradient(135deg,#1a1a2e,{grp["bg"]})">'
                f'<span class="pill-num" style="color:{grp["color"]}">{count}</span>'
                f'<span class="pill-lbl" style="color:{grp["color"]}">{grp["label"]}</span>'
                f'</div></div>\n'
            )

    css = """
:root{--bg:#0f0f1a;--surf:#1a1a2e;--surf2:#16213e;--acc:#e8a045;--text:#e8e8e8;--muted:#9a9aaa;--bdr:#2a2a3e;--sel:#1565C0}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;margin:0}
a{color:inherit}
.hdr{background:linear-gradient(135deg,#0f0f1a,#1a0a2e,#0f1a2e);border-bottom:1px solid var(--bdr);padding:1.2rem 1.5rem 1rem}
.hdr h1{color:var(--acc);font-size:1.7rem;font-weight:700;margin:0 0 .15rem}
.hdr .sub{color:var(--muted);font-size:.85rem}
.stat-pill{background:var(--surf);border:1px solid var(--bdr);border-radius:12px;padding:.5rem 1rem;text-align:center;transition:transform .2s}
.stat-pill:hover{transform:translateY(-2px)}
.pill-num{display:block;font-size:1.5rem;font-weight:700;color:var(--acc)}
.pill-lbl{display:block;font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.tabs{background:var(--surf2);border-bottom:1px solid var(--bdr);display:flex;padding:0 1rem}
.tab-btn{background:none;border:none;border-bottom:3px solid transparent;color:var(--muted);cursor:pointer;font-size:.88rem;font-weight:500;padding:.85rem 1.1rem;transition:color .2s,border-color .2s}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--acc);border-bottom-color:var(--acc)}
.sel-badge{background:var(--sel);border-radius:50%;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:.68rem;font-weight:700;height:18px;margin-left:5px;width:18px}
.pane{display:none;height:calc(100vh - 150px);overflow-y:auto}
.pane.active{display:block}
#pane-mapa{overflow:hidden;height:calc(100vh - 150px)}
.cards-wrap{padding:1.2rem}
.card{background:var(--surf);border:1px solid var(--bdr);border-radius:12px;cursor:pointer;height:100%;overflow:hidden;position:relative;transition:transform .2s,box-shadow .2s,border-color .2s}
.card:hover{border-color:var(--acc);box-shadow:0 8px 28px rgba(0,0,0,.4);transform:translateY(-4px)}
.card.xamba{border-color:#e8a045;box-shadow:0 0 0 1px rgba(232,160,69,.2)}
.card.selected{border-color:var(--sel);box-shadow:0 0 0 2px rgba(21,101,192,.35)}
.card.selected::after{content:'✓';position:absolute;top:7px;right:7px;background:var(--sel);border-radius:50%;color:#fff;font-size:.75rem;font-weight:700;width:22px;height:22px;display:flex;align-items:center;justify-content:center;z-index:10}
.card-img{width:100%;height:155px;object-fit:cover;object-position:top}
.card-avatar{width:100%;height:155px;display:flex;align-items:center;justify-content:center;font-size:2.4rem;font-weight:700;color:#fff}
.card-body{padding:.85rem}
.card-name{font-size:.9rem;font-weight:600;line-height:1.3;margin-bottom:.1rem;color:#fff}
.card-alias{color:var(--acc);font-size:.75rem;font-style:italic;margin-bottom:.35rem}
.card-meta{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.35rem}
.rated-badge{position:absolute;top:7px;left:7px;background:rgba(0,0,0,.7);border:1px solid rgba(241,196,15,.4);border-radius:9px;color:#f1c40f;font-size:.68rem;font-weight:700;padding:1px 5px;z-index:10}
.xamba-hdr{background:linear-gradient(90deg,rgba(232,160,69,.12),transparent);border-left:3px solid #e8a045;color:#e8a045;font-size:.65rem;font-weight:600;padding:.2rem .6rem}
.avail-dot{border-radius:50%;display:inline-block;height:8px;margin-right:3px;width:8px}
.dot-total{background:#2ecc71}.dot-parcial{background:#f39c12}
.tags{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.35rem}
.tag{background:rgba(232,160,69,.1);border:1px solid rgba(232,160,69,.22);border-radius:4px;color:var(--acc);font-size:.62rem;padding:.1rem .38rem}
.bdg{border-radius:6px;font-size:.65rem;font-weight:500;padding:.16rem .4rem}
.b-city{background:#1e3a5f;color:#7eb8f7}
.b-age{background:#2d1b4e;color:#b48af7}
.b-gf{background:#4a1530;color:#f090b0}
.b-gm{background:#0f2d4a;color:#80c0f0}
.b-gnb{background:#1a3a20;color:#80d0a0}
.b-go{background:#3a2a10;color:#d0a060}
.b-xamba{background:linear-gradient(135deg,#2a1505,#3a2008);border:1px solid #e8a045;border-radius:8px;color:#e8a045;font-size:.65rem;font-weight:600;padding:.1rem .38rem;white-space:nowrap}
.b-cult{border-radius:8px;font-size:.62rem;font-weight:600;padding:.1rem .35rem;white-space:nowrap}
.sel-btn{align-items:center;background:rgba(15,15,26,.7);border:2px solid var(--bdr);border-radius:50%;bottom:8px;color:var(--muted);cursor:pointer;display:flex;font-size:.85rem;height:27px;justify-content:center;position:absolute;right:8px;transition:all .2s;width:27px;z-index:10}
.sel-btn:hover,.sel-btn.on{background:var(--sel);border-color:var(--sel);color:#fff}
.stars{background:rgba(0,0,0,.15);border-top:1px solid var(--bdr);display:flex;gap:2px;padding:.3rem .5rem .4rem;align-items:center}
.star{color:#3a3a55;cursor:pointer;font-size:.95rem;line-height:1;transition:color .12s,transform .1s;user-select:none}
.star:hover,.star.h{color:#f1c40f;transform:scale(1.22)}
.star.on{color:#f1c40f}
.star.on.s1{color:#e74c3c}.star.on.s2{color:#e67e22}.star.on.s3{color:#f1c40f}.star.on.s4{color:#2ecc71}.star.on.s5{color:#27ae60}
.star-lbl{color:var(--muted);font-size:.6rem;margin-left:3px}
.modal-stars .star{font-size:1.35rem}
.chart-card{background:var(--surf);border:1px solid var(--bdr);border-radius:12px;padding:1.1rem}
.chart-ttl{color:var(--muted);font-size:.78rem;font-weight:600;letter-spacing:.5px;margin-bottom:.9rem;text-transform:uppercase}
.filter-bar{background:var(--surf2);border-bottom:1px solid var(--bdr);display:flex;flex-wrap:wrap;gap:.5rem;padding:.55rem 1rem;align-items:center}
.filter-bar input,.filter-bar select{background:var(--surf);border:1px solid var(--bdr);border-radius:8px;color:var(--text);font-size:.8rem;padding:.28rem .6rem}
.filter-bar input:focus,.filter-bar select:focus{border-color:var(--acc);outline:none}
.filter-count{color:var(--muted);font-size:.8rem;margin-left:auto}
.clr-btn{background:var(--bdr);border:none;border-radius:6px;color:var(--text);cursor:pointer;font-size:.78rem;padding:.28rem .6rem}
#map{height:100%}
.leaflet-popup-content-wrapper{background:var(--surf);border:1px solid var(--bdr);color:var(--text)}
.leaflet-popup-tip{background:var(--surf)}
.pop-name{color:var(--acc);font-size:.88rem;font-weight:600}
.pop-info{color:var(--muted);font-size:.76rem}
.float-bar{position:fixed;bottom:18px;right:18px;background:var(--sel);border-radius:28px;color:#fff;cursor:pointer;display:flex;align-items:center;gap:.45rem;font-size:.88rem;font-weight:600;padding:.55rem 1.1rem;box-shadow:0 4px 18px rgba(0,0,0,.4);transition:transform .2s;z-index:1000}
.float-bar:hover{transform:translateY(-2px)}
.float-bar.hidden{display:none}
.modal-overlay{align-items:flex-start;background:rgba(0,0,0,.72);display:none;inset:0;justify-content:center;overflow-y:auto;padding:2rem 1rem;position:fixed;z-index:2000}
.modal-overlay.open{display:flex}
.modal-box{background:var(--surf);border:1px solid var(--bdr);border-radius:14px;max-width:680px;width:100%}
.modal-head{border-bottom:1px solid var(--bdr);display:flex;align-items:flex-start;gap:1rem;justify-content:space-between;padding:1rem 1.2rem}
.modal-photo{border-radius:50%;height:90px;object-fit:cover;object-position:top;width:90px}
.modal-ava{align-items:center;border-radius:50%;color:#fff;display:flex;font-size:1.8rem;font-weight:700;height:90px;justify-content:center;width:90px}
.modal-title{color:var(--acc);font-size:1rem;font-weight:700;margin:0 0 .1rem}
.modal-body{padding:1rem 1.2rem}
.detail{background:var(--surf2);border-radius:8px;margin-bottom:.55rem;padding:.65rem .85rem}
.detail-lbl{color:var(--muted);font-size:.68rem;letter-spacing:.5px;margin-bottom:.15rem;text-transform:uppercase}
.detail-val{font-size:.86rem;line-height:1.5}
.highlight{background:rgba(232,160,69,.07);border-left:3px solid var(--acc);border-radius:0 6px 6px 0;font-size:.83rem;line-height:1.6;padding:.45rem .7rem}
.ig-link{align-items:center;color:#c13584;display:inline-flex;gap:4px;font-size:.82rem;text-decoration:none}
.close-btn{background:none;border:none;color:var(--muted);cursor:pointer;font-size:1.2rem;line-height:1;padding:.2rem}
.close-btn:hover{color:var(--text)}
.empty-state{color:var(--muted);padding:4rem 2rem;text-align:center}
.empty-state i{display:block;font-size:2.8rem;margin-bottom:.8rem}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:3px}
@media(max-width:576px){.filter-bar{flex-direction:column}.filter-bar input,.filter-bar select{width:100%}}
"""

    js = r"""
let ratings = JSON.parse(localStorage.getItem('bongarbit_ratings') || '{}');
const RLABELS = ['','Não recomendado','Abaixo da média','Interessante','Muito bom','Excelente!'];

function getRating(id) { return ratings[String(id)] || 0; }
function setRating(id, val, e) {
  e && e.stopPropagation();
  const k = String(id);
  ratings[k] === val ? delete ratings[k] : (ratings[k] = val);
  localStorage.setItem('bongarbit_ratings', JSON.stringify(ratings));
  syncRatingUI(id); applyFilters();
}
function syncRatingUI(id) {
  const r = getRating(id);
  document.querySelectorAll(`[data-rid="${id}"]`).forEach(w => {
    w.querySelectorAll('.star').forEach((s, i) => {
      s.classList.toggle('on', i < r);
      s.className = s.className.replace(/\bs\d\b/g, '').trim();
      if (i < r) s.classList.add('s' + r);
    });
    const lbl = w.querySelector('.star-lbl');
    if (lbl) lbl.textContent = r ? RLABELS[r] : '';
  });
  document.querySelectorAll(`.card[data-id="${id}"] .rated-badge`).forEach(b => {
    b.textContent = r ? '★'.repeat(r) : ''; b.style.display = r ? '' : 'none';
  });
}
function hoverStars(el, val) {
  el.closest('[data-rid]').querySelectorAll('.star').forEach((s, i) => s.classList.toggle('h', i < val));
}
function unhoverStars(el) {
  el.closest('[data-rid]').querySelectorAll('.star').forEach(s => s.classList.remove('h'));
}
function starsWidget(id, extra) {
  const r = getRating(id), ex = extra || '';
  const stars = [1,2,3,4,5].map(i =>
    `<span class="star${i<=r?' on s'+r:''}" data-val="${i}"
      onclick="setRating(${id},${i},event)"
      onmouseenter="hoverStars(this,${i})"
      onmouseleave="unhoverStars(this)">★</span>`
  ).join('');
  return `<div class="stars ${ex}" data-rid="${id}">${stars}<span class="star-lbl">${r ? RLABELS[r] : ''}</span></div>`;
}

let selected = new Set(JSON.parse(localStorage.getItem('bongarbit_sel') || '[]'));
let modalId = null;

function toggleSel(id, e) {
  e && e.stopPropagation();
  selected.has(id) ? selected.delete(id) : selected.add(id);
  localStorage.setItem('bongarbit_sel', JSON.stringify([...selected]));
  syncSelUI();
}
function syncSelUI() {
  const n = selected.size;
  document.getElementById('sel-count').textContent = n;
  document.getElementById('float-count').textContent = n;
  document.getElementById('float-bar').classList.toggle('hidden', n === 0);
  document.querySelectorAll('.card').forEach(el => {
    const id = +el.dataset.id, on = selected.has(id);
    el.classList.toggle('selected', on);
    const btn = el.querySelector('.sel-btn');
    if (btn) { btn.classList.toggle('on', on); btn.textContent = on ? '★' : '☆'; }
  });
  if (modalId) {
    const btn = document.getElementById('modal-sel-btn');
    if (btn) { const on = selected.has(modalId); btn.textContent = on ? '★ Selecionado' : '☆ Selecionar'; btn.style.background = on ? '#c0392b' : 'var(--sel)'; }
  }
  if (currentTab === 'selecionados') renderSelecionados();
}

let currentTab = 'resumo', mapReady = false;
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentTab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
    document.getElementById('pane-' + currentTab).classList.add('active');
    if (currentTab === 'mapa' && !mapReady) { initMap(); mapReady = true; }
    if (currentTab === 'selecionados') renderSelecionados();
  });
});
document.getElementById('float-bar').addEventListener('click', () => {
  document.querySelector('[data-tab="selecionados"]').click();
});

Chart.defaults.color = '#9a9aaa';
Chart.defaults.borderColor = '#2a2a3e';
const CP = ['#e8a045','#c0392b','#9b59b6','#3498db','#2ecc71','#e74c3c','#1abc9c','#f39c12','#6c3483','#1a5276','#1e8449','#784212'];
function mkChart(id, type, labels, data, opts) {
  const ctx = document.getElementById(id); if (!ctx) return;
  opts = opts || {};
  return new Chart(ctx, { type, data: { labels, datasets: [{ data, backgroundColor: CP, borderWidth: 0, ...(opts.ds||{}) }] },
    options: { responsive: true, plugins: { legend: { position: 'right', labels: { boxWidth: 11, font: { size: 10 } } }, ...(opts.pl||{}) }, ...(opts.ch||{}) }
  });
}
function sorted(obj) { return Object.entries(obj).sort((a,b) => b[1]-a[1]); }
const barOpts = color => ({
  ds: { backgroundColor: color, borderRadius: 5 },
  pl: { legend: { display: false } },
  ch: { scales: { y: { beginAtZero: true, grid: { color: '#2a2a3e' } }, x: { grid: { display: false } } } }
});

(function buildCharts() {
  const g = sorted(STATS.genero); mkChart('ch-genero','doughnut',g.map(x=>x[0]),g.map(x=>x[1]));
  const r = sorted(STATS.raca);   mkChart('ch-raca',  'doughnut',r.map(x=>x[0]),r.map(x=>x[1]));
  const ageOrd = ['15-19','20-29','30-39','40-49','50-59','60+','Não informada'];
  const ageL = ageOrd.filter(k => STATS.faixa_etaria[k]);
  mkChart('ch-idade','bar',ageL,ageL.map(k=>STATS.faixa_etaria[k]||0),barOpts('#e8a045'));
  const rOrd = ['Até 1 salário mínimo','Até 2 salários mínimos','Até 3 salários mínimos','Mais de 3 salários mínimos','Prefiro não informar'];
  const rL = rOrd.filter(k => STATS.renda[k]);
  const rS = rL.map(l => l.replace('salários mínimos','SM').replace('salário mínimo','SM').replace('Mais de','>').replace('Até','≤'));
  mkChart('ch-renda','bar',rS,rL.map(k=>STATS.renda[k]||0),barOpts('#9b59b6'));
  mkChart('ch-disponib','doughnut',['Total','Parcial'],[STATS.disponibilidade['Total']||0,STATS.disponibilidade['Parcial']||0],{ds:{backgroundColor:['#2ecc71','#f39c12']}});
  const cs = sorted(STATS.como_soube); mkChart('ch-soube','doughnut',cs.map(x=>x[0]),cs.map(x=>x[1]));
  const ci = sorted(STATS.cidade);    mkChart('ch-cidade','bar',ci.map(x=>x[0]),ci.map(x=>x[1]),barOpts('#3498db'));
  const gc = document.getElementById('cult-groups-list');
  if (gc) {
    let h = `<div style="font-size:1.8rem;font-weight:700;color:#e8a045">${STATS.is_xamba}</div><div style="font-size:.72rem;color:var(--muted)">🥁 Xambá</div>`;
    Object.entries(GROUPS_DEF).forEach(([k,g]) => {
      const n = STATS['group_'+k]||0;
      if (n) h += `<div style="margin-top:.6rem"><span style="font-size:1.8rem;font-weight:700;color:${g.color}">${n}</span> <span style="font-size:.72rem;color:var(--muted)">${g.label}</span></div>`;
    });
    gc.innerHTML = h;
  }
})();

function gBadge(g) {
  if (!g) return '';
  const l = g.toLowerCase();
  const c = l.includes('mulher') ? 'b-gf' : l.includes('homem cis') ? 'b-gm' : (l.includes('não binár')||l.includes('nao binar')) ? 'b-gnb' : 'b-go';
  return `<span class="bdg ${c}">${g}</span>`;
}
function cultBadges(c) {
  return Object.entries(c.cultural_groups||{}).map(([k,lbl]) => {
    const g = GROUPS_DEF[k];
    return g ? `<span class="b-cult" style="background:${g.bg};color:${g.color};border:1px solid ${g.color}30">${lbl}</span>` : '';
  }).join('');
}
function cardTags(c) {
  const skip = ['não','nao','no'], tags = [];
  if (c.terreiro   && !skip.includes(c.terreiro.trim().toLowerCase()))   tags.push('Terreiro');
  if (c.comunidade && !skip.includes(c.comunidade.trim().toLowerCase())) tags.push('Comunidade');
  (c.grupos_culturais||'').split(/[;,]/).map(s=>s.trim()).filter(s=>s.length>2&&s.length<40).slice(0,2).forEach(g=>tags.push(g));
  return tags.slice(0,4).map(t=>`<span class="tag">${t}</span>`).join('');
}
function makeCard(c) {
  const sel = selected.has(c.id), rat = getRating(c.id);
  const img = c.photo ? `<img src="${c.photo}" class="card-img" alt="" onerror="this.style.display='none';this.nextSibling.style.display='flex'">` : '';
  const ava = `style="display:${c.photo?'none':'flex'};background:${c.avatar_color}"`;
  const alias = c.nome_social && c.nome_social !== c.nome ? `<div class="card-alias">"${c.nome_social}"</div>` : '';
  const indicHtml = c.is_indicado
    ? `<div style="display:flex;align-items:center;gap:4px;font-size:.68rem;color:#7eb8f7;margin-bottom:3px">🤝 <span>${c.indicador || 'Indicação'}</span></div>`
    : '';
  const xhdr = c.is_xamba && c.xamba_reasons.length ? `<div class="xamba-hdr">${c.xamba_reasons.slice(0,2).join(' · ')}</div>` : '';
  const avail = c.disponivel_total ? '<span class="avail-dot dot-total"></span>Total' : '<span class="avail-dot dot-parcial"></span>Parcial';
  const igL = c.instagram ? `<a href="https://instagram.com/${c.instagram}" target="_blank" onclick="event.stopPropagation()" style="color:#c13584;font-size:.8rem"><i class="fab fa-instagram"></i></a>` : '';
  const cb = cultBadges(c);
  const rshort = (c.renda||'').replace('salários mínimos','SM').replace('salário mínimo','SM').replace('Mais de','>').replace('Até','≤');
  return `<div class="col-12 col-sm-6 col-lg-4 col-xl-3">
    <div class="card${c.is_xamba?' xamba':''}${sel?' selected':''}" data-id="${c.id}" onclick="showModal(${c.id})">
      ${xhdr}${img}
      <div class="card-avatar" ${ava}>${c.avatar_initials}</div>
      <div class="rated-badge" style="display:${rat?'':'none'}">${rat?'★'.repeat(rat):''}</div>
      <div class="card-body">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:4px;margin-bottom:4px">
          <div class="card-name">${c.nome}</div>
          <div style="display:flex;gap:4px;flex-shrink:0">${c.is_xamba?'<span class="b-xamba">🥁</span>':''}${igL}</div>
        </div>
        ${alias}
        <div class="card-meta">
          ${c.cidade?`<span class="bdg b-city">${c.cidade}</span>`:''}
          ${c.idade?`<span class="bdg b-age">${c.idade}a</span>`:''}
          ${gBadge(c.genero)}
        </div>
        ${cb?`<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:4px">${cb}</div>`:''}
        <div style="display:flex;align-items:center;justify-content:space-between;font-size:.72rem;color:var(--muted)">
          <div>${avail}</div>${rshort?`<div>${rshort}</div>`:''}
        </div>
        ${indicHtml}
        <div class="tags">${cardTags(c)}</div>
      </div>
      ${starsWidget(c.id,'')}
      <button class="sel-btn${sel?' on':''}" onclick="toggleSel(${c.id},event)">${sel?'★':'☆'}</button>
    </div>
  </div>`;
}

function initFilters() {
  const bar = document.getElementById('filter-bar');
  const cnt = document.getElementById('filter-count');
  const cidades = [...new Set(CANDIDATES.map(c=>c.cidade))].sort();
  const generos = [...new Set(CANDIDATES.map(c=>c.genero).filter(Boolean))].sort();
  const racas   = [...new Set(CANDIDATES.map(c=>c.raca).filter(Boolean))].sort();
  function mkSel(id, ph, pairs) {
    const s = document.createElement('select'); s.id = id;
    if (ph) { const o=document.createElement('option'); o.value=''; o.textContent=ph; s.appendChild(o); }
    pairs.forEach(([v,l]) => { const o=document.createElement('option'); o.value=v; o.textContent=l!=null?l:v; s.appendChild(o); });
    s.addEventListener('change', applyFilters); return s;
  }
  const search = document.createElement('input');
  search.type='text'; search.id='search'; search.placeholder='🔍 Nome, cidade, grupos...';
  search.addEventListener('input', applyFilters);
  const cultP = [['xamba','🥁 Xambá'],...Object.entries(GROUPS_DEF).map(([k,g])=>[k,g.label])];
  [
    search,
    mkSel('f-cidade','Todas as cidades',cidades.map(c=>[c,c])),
    mkSel('f-genero','Todos os gêneros',generos.map(g=>[g,g])),
    mkSel('f-raca','Todas as raças',racas.map(r=>[r,r])),
    mkSel('f-renda','Toda faixa de renda',[['Até 1 salário mínimo','≤ 1 SM'],['Até 2 salários mínimos','≤ 2 SM'],['Até 3 salários mínimos','≤ 3 SM'],['Mais de 3 salários mínimos','> 3 SM'],['Prefiro não informar','Prefiro n/i']]),
    mkSel('f-disponib','Toda disponibilidade',[['total','Disponib. total'],['parcial','Parcial']]),
    mkSel('f-terreiro','Com ou sem terreiro',[['sim','Com terreiro'],['nao','Sem terreiro']]),
    mkSel('f-xamba','Conn. Xambá',[['sim','🥁 Com vínculo'],['nao','Sem vínculo']]),
    mkSel('f-indicado','Indicação',[['sim','🤝 Por indicação'],['nao','Sem indicação']]),
    mkSel('f-grupo','Grupo cultural',cultP),
    mkSel('f-nota','Qualquer nota',[['rated','Com nota'],['5','⭐⭐⭐⭐⭐'],['4','⭐⭐⭐⭐+'],['3','⭐⭐⭐+'],['unrated','Sem nota']]),
    mkSel('f-sort',null,[['rating','Nota ↓'],['xamba','Xambá primeiro'],['name','Nome A-Z'],['age','Idade']]),
  ].forEach(el => bar.insertBefore(el, cnt));
  const clr = document.createElement('button'); clr.className='clr-btn'; clr.textContent='✕ Limpar';
  clr.addEventListener('click', clearFilters); bar.insertBefore(clr, cnt);
  renderCards(CANDIDATES); syncSelUI();
}

function getFiltered() {
  const v = id => document.getElementById(id)?.value || '';
  const search = v('search').toLowerCase();
  let list = CANDIDATES.filter(c => {
    if (search) { const b=[c.nome,c.nome_social,c.cidade,c.grupos_culturais,c.terreiro,c.comunidade,c.coletivos,c.instagram||'',c.por_que].join(' ').toLowerCase(); if(!b.includes(search)) return false; }
    if (v('f-cidade') && c.cidade !== v('f-cidade')) return false;
    if (v('f-genero') && c.genero !== v('f-genero')) return false;
    if (v('f-raca')   && c.raca   !== v('f-raca'))   return false;
    if (v('f-renda')  && c.renda  !== v('f-renda'))  return false;
    if (v('f-disponib')==='total'  && !c.disponivel_total) return false;
    if (v('f-disponib')==='parcial' && c.disponivel_total) return false;
    if (v('f-terreiro')==='sim') { const skip=['não','nao','no']; if(!c.terreiro||skip.includes(c.terreiro.trim().toLowerCase())) return false; }
    if (v('f-xamba')==='sim' && !c.is_xamba) return false;
    if (v('f-xamba')==='nao' &&  c.is_xamba) return false;
    if (v('f-indicado')==='sim' && !c.is_indicado) return false;
    if (v('f-indicado')==='nao' &&  c.is_indicado) return false;
    if (v('f-grupo')==='xamba' && !c.is_xamba) return false;
    if (v('f-grupo') && v('f-grupo')!=='xamba' && !(c.cultural_groups&&c.cultural_groups[v('f-grupo')])) return false;
    const nota=v('f-nota');
    if (nota==='rated'   && !getRating(c.id)) return false;
    if (nota==='unrated' &&  getRating(c.id)) return false;
    if (['3','4','5'].includes(nota) && getRating(c.id)<+nota) return false;
    return true;
  });
  const ord = v('f-sort')||'rating';
  list.sort((a,b) => {
    if (ord==='name') return a.nome.localeCompare(b.nome);
    if (ord==='age')  return (a.idade||0)-(b.idade||0);
    if (ord==='xamba' && a.is_xamba!==b.is_xamba) return a.is_xamba?-1:1;
    const ra=getRating(a.id),rb=getRating(b.id);
    if (ra!==rb) return rb-ra;
    if (a.is_xamba!==b.is_xamba) return a.is_xamba?-1:1;
    return a.nome.localeCompare(b.nome);
  });
  return list;
}
function renderCards(list) {
  document.getElementById('cards-grid').innerHTML = list.map(makeCard).join('');
  const xn=list.filter(c=>c.is_xamba).length, rn=list.filter(c=>getRating(c.id)).length;
  let info = `${list.length} de ${CANDIDATES.length}`;
  if (xn) info+=` · 🥁 ${xn}`; if (rn) info+=` · ⭐ ${rn} avaliados`;
  document.getElementById('filter-count').textContent = info;
}
function applyFilters() { renderCards(getFiltered()); }
function clearFilters() {
  ['search','f-cidade','f-genero','f-raca','f-renda','f-disponib','f-terreiro','f-xamba','f-indicado','f-grupo','f-nota'].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});
  const s=document.getElementById('f-sort'); if(s) s.value='rating';
  applyFilters();
}
// Chamada direta — não usa DOMContentLoaded porque após decriptação
// do Staticrypt (document.write) o evento já disparou e não dispara de novo.
if (document.getElementById('filter-bar')) initFilters();
else document.addEventListener('DOMContentLoaded', initFilters);

let selCharts = {};
function renderSelecionados() {
  const box = document.getElementById('sel-content');
  const list = CANDIDATES.filter(c => selected.has(c.id));
  if (!list.length) { box.innerHTML='<div class="empty-state"><i class="fas fa-star"></i><h4>Nenhum selecionado</h4><p>Use ☆ nos cards para marcar candidatos.</p></div>'; return; }
  Object.values(selCharts).forEach(c=>c&&c.destroy()); selCharts={};
  const genD={},racaD={},cidD={};
  const dispT=list.filter(c=>c.disponivel_total).length, xaT=list.filter(c=>c.is_xamba).length;
  list.forEach(c=>{ genD[c.genero||'N/I']=(genD[c.genero||'N/I']||0)+1; racaD[c.raca||'N/I']=(racaD[c.raca||'N/I']||0)+1; cidD[c.cidade||'N/I']=(cidD[c.cidade||'N/I']||0)+1; });
  const rCounts=[0,0,0,0,0]; let rSum=0,rN=0;
  list.forEach(c=>{const r=getRating(c.id);if(r){rCounts[r-1]++;rSum+=r;rN++;}});
  const avg=rN?(rSum/rN).toFixed(1):null;
  const sorted2=[...list].sort((a,b)=>{const ra=getRating(a.id),rb=getRating(b.id);return rb-ra||a.nome.localeCompare(b.nome);});
  const groupCounts={};
  list.forEach(c=>{if(c.is_xamba)groupCounts['xamba']=(groupCounts['xamba']||0)+1;Object.keys(c.cultural_groups||{}).forEach(k=>{groupCounts[k]=(groupCounts[k]||0)+1;});});
  let gcHtml='';
  if(groupCounts['xamba'])gcHtml+=`<div style="margin-top:.6rem"><span style="font-size:1.8rem;font-weight:700;color:#e8a045">${groupCounts['xamba']}</span> <span style="font-size:.72rem;color:var(--muted)">🥁 Xambá</span></div>`;
  Object.entries(groupCounts).filter(([k])=>k!=='xamba').forEach(([k,n])=>{const g=GROUPS_DEF[k];if(g)gcHtml+=`<div style="margin-top:.6rem"><span style="font-size:1.8rem;font-weight:700;color:${g.color}">${n}</span> <span style="font-size:.72rem;color:var(--muted)">${g.label}</span></div>`;});
  box.innerHTML=`<div style="padding:1.2rem 1.5rem">
    <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:1.2rem">
      <h4 style="color:var(--acc);margin:0"><i class="fas fa-star me-2"></i>Selecionados</h4>
      <span style="background:var(--sel);border-radius:20px;color:#fff;font-size:.85rem;padding:2px 10px">${list.length} pessoas</span>
      <button onclick="exportCSV()" style="margin-left:auto;background:#27ae60;border:none;border-radius:6px;color:#fff;cursor:pointer;font-size:.8rem;padding:.3rem .7rem">⬇ Exportar CSV</button>
      <button onclick="clearAllSel()" style="background:#c0392b;border:none;border-radius:6px;color:#fff;cursor:pointer;font-size:.8rem;padding:.3rem .7rem">✕ Limpar</button>
    </div>
    <div class="row g-2 mb-3">
      <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num">${list.length}</span><span class="pill-lbl">Selecionados</span></div></div>
      <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num" style="color:#2ecc71">${dispT}</span><span class="pill-lbl">Disponib. Total</span></div></div>
      <div class="col-6 col-md-2"><div class="stat-pill" style="border-color:#e8a04540"><span class="pill-num" style="color:#e8a045">${xaT}</span><span class="pill-lbl">Conn. Xambá</span></div></div>
      <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num">${Object.keys(cidD).length}</span><span class="pill-lbl">Cidades</span></div></div>
      <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num" style="color:#f1c40f">${rN}</span><span class="pill-lbl">Avaliados</span></div></div>
      ${avg?`<div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num" style="color:#f1c40f">${avg}⭐</span><span class="pill-lbl">Média</span></div></div>`:''}
    </div>
    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl">Gênero</div><canvas id="sel-g" height="200"></canvas></div></div>
      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl">Raça / Cor</div><canvas id="sel-r" height="200"></canvas></div></div>
      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl">Pontuação</div><canvas id="sel-n" height="200"></canvas></div></div>
    </div>
    ${gcHtml?`<div class="chart-card mb-3"><div class="chart-ttl">Vínculos Culturais</div>${gcHtml}</div>`:''}
    <h6 style="color:var(--muted);margin-bottom:.8rem">Cards dos selecionados · por nota</h6>
    <div class="row g-3">${sorted2.map(makeCard).join('')}</div>
  </div>`;
  const sg=sorted(genD);  selCharts.g=mkChart('sel-g','doughnut',sg.map(x=>x[0]),sg.map(x=>x[1]));
  const sr2=sorted(racaD); selCharts.r=mkChart('sel-r','doughnut',sr2.map(x=>x[0]),sr2.map(x=>x[1]));
  selCharts.n=new Chart(document.getElementById('sel-n'),{type:'bar',data:{labels:['⭐','⭐⭐','⭐⭐⭐','⭐⭐⭐⭐','⭐⭐⭐⭐⭐'],datasets:[{data:rCounts,backgroundColor:['#e74c3c','#e67e22','#f1c40f','#2ecc71','#27ae60'],borderWidth:0,borderRadius:5}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:'#2a2a3e'}},x:{grid:{display:false}}}}});
}
function clearAllSel() { selected.clear(); localStorage.setItem('bongarbit_sel','[]'); syncSelUI(); renderSelecionados(); }

function exportCSV() {
  const list = CANDIDATES.filter(c => selected.has(c.id));
  if (!list.length) return;
  const esc = v => {
    const s = v == null ? '' : String(v);
    return (s.includes(',') || s.includes('"') || s.includes('\\n')) ? '"' + s.replace(/"/g,'""') + '"' : s;
  };
  const cols = [
    ['ID',            c => c.id],
    ['Timestamp',     c => c.timestamp],
    ['Nome',          c => c.nome],
    ['Nome Social',   c => c.nome_social],
    ['Telefone',      c => c.telefone],
    ['CPF',           c => c.cpf],
    ['E-mail',        c => c.email],
    ['Endereço',      c => c.endereco],
    ['CEP',           c => c.cep],
    ['Cidade/Estado', c => c.cidade_estado],
    ['Cidade',        c => c.cidade],
    ['Idade',         c => c.idade || c.idade_raw],
    ['Faixa Etária',  c => c.faixa_etaria],
    ['Gênero',        c => c.genero],
    ['Raça/Cor',      c => c.raca],
    ['PcD',           c => c.pcd],
    ['Desc. Defic.',  c => c.desc_deficiencia],
    ['Renda',         c => c.renda],
    ['Terreiro',      c => c.terreiro],
    ['Comunidade',    c => c.comunidade],
    ['Grupos Culturais', c => c.grupos_culturais],
    ['Coletivos',     c => c.coletivos],
    ['Por que quer participar', c => c.por_que],
    ['Disponibilidade', c => c.disponibilidade],
    ['Disp. Total',   c => c.disponivel_total ? 'Sim' : 'Não'],
    ['Redes Sociais', c => c.redes_sociais],
    ['Instagram',     c => c.instagram],
    ['Como soube',    c => c.como_soube],
    ['Indicação',     c => c.is_indicado ? 'Sim' : 'Não'],
    ['Indicador',     c => c.indicador],
    ['Vinc. Xambá',   c => c.is_xamba ? 'Sim' : 'Não'],
    ['Nota (estrelas)', c => getRating(c.id) || ''],
  ];
  const header = cols.map(([h]) => esc(h)).join(',');
  const rows   = list.map(c => cols.map(([,fn]) => esc(fn(c))).join(','));
  const csv = '\\uFEFF' + [header, ...rows].join('\\r\\n'); // BOM para Excel
  const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'selecionados_bongarbit.csv'; a.click();
  URL.revokeObjectURL(url);
}

function showModal(id) {
  const c = CANDIDATES.find(x=>x.id===id); if(!c) return;
  modalId = id;
  document.getElementById('modal-name').textContent = c.nome;
  document.getElementById('modal-alias').textContent = c.nome_social&&c.nome_social!==c.nome?`"${c.nome_social}"`:'';
  const pc = document.getElementById('modal-photo');
  pc.innerHTML = c.photo
    ? `<img src="${c.photo}" class="modal-photo" onerror="this.outerHTML='<div class=\\"modal-ava\\" style=\\"background:${c.avatar_color}\\">${c.avatar_initials}</div>'">`
    : `<div class="modal-ava" style="background:${c.avatar_color}">${c.avatar_initials}</div>`;
  const cb=Object.entries(c.cultural_groups||{}).map(([k,lbl])=>{const g=GROUPS_DEF[k];return g?`<span class="b-cult" style="background:${g.bg};color:${g.color};border:1px solid ${g.color}30">${lbl}</span>`:''}).join('');
  document.getElementById('modal-badges').innerHTML=`
    ${c.cidade?`<span class="bdg b-city">${c.cidade}</span>`:''}
    ${c.idade?`<span class="bdg b-age">${c.idade} anos</span>`:''}
    ${gBadge(c.genero)}
    ${c.raca?`<span class="bdg" style="background:#2a1a10;color:#c8a070">${c.raca}</span>`:''}
    ${c.is_pcd?'<span class="bdg" style="background:#1a3a1a;color:#70c070">PCD</span>':''}
    ${c.is_xamba?`<span class="b-xamba">🥁 Xambá: ${(c.xamba_reasons||[]).join(' · ')}</span>`:''}
    ${cb}`;
  const isSel=selected.has(id);
  const selBtn=document.getElementById('modal-sel-btn');
  selBtn.textContent=isSel?'★ Selecionado':'☆ Selecionar'; selBtn.style.background=isSel?'#c0392b':'var(--sel)';
  const skip=['não','nao','no','n/a','não.'];
  const rows=[
    ['Disponibilidade',c.disponibilidade],['Renda Familiar',c.renda],
    ['Endereço',[c.endereco,c.cidade_estado,c.cep].filter(Boolean).join(' — ')],
    ['Por que deseja participar',c.por_que,true],
    ['Terreiro / Povos Tradicionais',c.terreiro],['Comunidade / Quilombo',c.comunidade],
    ['Grupos Culturais',c.grupos_culturais],['Coletivos / ONGs',c.coletivos],
    ['PCD',c.desc_deficiencia],['Como ficou sabendo',c.como_soube],
    ['Telefone',c.telefone],['E-mail',c.email],['Redes Sociais',c.redes_sociais],['Inscrito em',c.timestamp],
  ];
  let body=`<div class="detail"><div class="detail-lbl">Pontuação</div>${starsWidget(id,'modal-stars')}</div>`;
  rows.forEach(([lbl,val,hi])=>{if(!val||skip.includes(val.trim().toLowerCase()))return;body+=`<div class="detail"><div class="detail-lbl">${lbl}</div><div class="detail-val">${hi?`<div class="highlight">${val}</div>`:val}</div></div>`;});
  if(c.instagram)body+=`<div class="detail"><div class="detail-lbl">Instagram</div><div class="detail-val"><a href="https://instagram.com/${c.instagram}" target="_blank" class="ig-link"><i class="fab fa-instagram"></i> @${c.instagram}</a></div></div>`;
  document.getElementById('modal-body').innerHTML=body;
  document.getElementById('modal-overlay').classList.add('open');
  document.getElementById('modal-overlay').scrollTop=0;
}
document.getElementById('modal-overlay').addEventListener('click',e=>{if(e.target===e.currentTarget)closeModal();});
document.getElementById('modal-close').addEventListener('click',closeModal);
document.getElementById('modal-sel-btn').addEventListener('click',()=>{if(modalId)toggleSel(modalId);});
function closeModal(){document.getElementById('modal-overlay').classList.remove('open');modalId=null;}

function initMap() {
  const map=L.map('map').setView([-8.05,-34.93],12);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{attribution:'&copy; OpenStreetMap &copy; CARTO',subdomains:'abcd',maxZoom:19}).addTo(map);
  CANDIDATES.forEach(c=>{
    const fill=c.is_xamba?'#e8a045':c.avatar_color;
    const bdr=selected.has(c.id)?'#1565C0':c.is_xamba?'#e8a045':c.disponivel_total?'#2ecc71':'#f39c12';
    const mk=L.circleMarker([c.lat,c.lon],{radius:c.is_xamba?10:8,fillColor:fill,color:bdr,weight:c.is_xamba?3:2,opacity:1,fillOpacity:.85}).addTo(map);
    const ig=c.instagram?`<a href="https://instagram.com/${c.instagram}" target="_blank" style="color:#c13584">@${c.instagram}</a>`:'';
    const xr=c.is_xamba?`<div style="color:#e8a045;font-size:.74rem;font-weight:600">🥁 ${(c.xamba_reasons||[]).slice(0,2).join(' · ')}</div>`:'';
    const cb2=Object.values(c.cultural_groups||{}).map(lbl=>{const g=Object.values(GROUPS_DEF).find(x=>x.label===lbl);return g?`<span style="color:${g.color};font-size:.7rem">● ${lbl}</span>`:''}).join('<br>');
    mk.bindPopup(`<div class="pop-name">${c.nome}</div>
      ${c.nome_social&&c.nome_social!==c.nome?`<div style="color:#aaa;font-size:.74rem;font-style:italic">"${c.nome_social}"</div>`:''}
      ${xr}${cb2}
      <div class="pop-info">${c.cidade}${c.idade?' · '+c.idade+'a':''} · ${c.genero}</div>
      <div class="pop-info">${c.renda}</div>
      <div class="pop-info">${c.disponivel_total?'🟢 Total':'🟡 Parcial'}</div>${ig}
      <div style="margin-top:6px;display:flex;gap:4px">
        <button onclick="document.querySelector('.leaflet-popup-close-button').click();showModal(${c.id})" style="background:#e8a045;color:#000;border:none;border-radius:4px;cursor:pointer;font-size:.74rem;padding:3px 9px">Ver detalhes</button>
        <button onclick="toggleSel(${c.id});this.textContent=selected.has(${c.id})?'★ Sel':'☆ Sel'" style="background:var(--sel);color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:.74rem;padding:3px 9px">${selected.has(c.id)?'★ Sel':'☆ Sel'}</button>
      </div>`);
  });
  const byCity={};
  CANDIDATES.forEach(c=>{if(!byCity[c.cidade])byCity[c.cidade]={lats:[],lons:[]};byCity[c.cidade].lats.push(c.lat);byCity[c.cidade].lons.push(c.lon);});
  Object.entries(byCity).forEach(([city,d])=>{
    const lat=d.lats.reduce((s,x)=>s+x,0)/d.lats.length, lon=d.lons.reduce((s,x)=>s+x,0)/d.lons.length;
    L.marker([lat+0.014,lon],{icon:L.divIcon({className:'',iconAnchor:[50,10],html:`<div style="background:rgba(15,15,30,.9);border:1px solid #e8a045;border-radius:18px;color:#e8a045;font-size:.7rem;font-weight:700;padding:2px 9px;white-space:nowrap">${city}: ${d.lats.length}</div>`})}).addTo(map);
  });
  const leg=L.control({position:'bottomleft'});
  leg.onAdd=()=>{const d=L.DomUtil.create('div');d.style.cssText='background:rgba(15,15,26,.92);border:1px solid #2a2a3e;border-radius:8px;color:#e8e8e8;font-size:.74rem;padding:9px 12px';d.innerHTML=`<div style="color:#e8a045;font-weight:700;margin-bottom:5px">Legenda</div><div><span style="background:#e8a045;border-radius:50%;display:inline-block;height:10px;margin-right:5px;width:10px"></span>Xambá</div><div><span style="background:#333;border:2px solid #2ecc71;border-radius:50%;display:inline-block;height:10px;margin-right:5px;width:10px"></span>Disponib. total</div><div><span style="background:#333;border:2px solid #f39c12;border-radius:50%;display:inline-block;height:10px;margin-right:5px;width:10px"></span>Parcial</div><div><span style="background:#333;border:2px solid #1565C0;border-radius:50%;display:inline-block;height:10px;margin-right:5px;width:10px"></span>Selecionado</div>`;return d;};
  leg.addTo(map);
}
"""

    html = (
        f'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n'
        f'  <meta charset="UTF-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'  <title>Inscritos — Bongarbit Escola de Luteria</title>\n'
        f'  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">\n'
        f'  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">\n'
        f'  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">\n'
        f'  <style>{css}</style>\n'
        f'</head>\n<body>\n\n'

        f'<div class="hdr">\n'
        f'  <h1><i class="fas fa-drum me-2"></i>Bongarbit — Escola de Luteria</h1>\n'
        f'  <div class="sub">Processo Seletivo 2026 · Dashboard de Inscrições</div>\n'
        f'  <div class="row g-2 mt-2">\n'
        f'    <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num">{stats["total"]}</span><span class="pill-lbl">Inscritos</span></div></div>\n'
        f'    <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num" style="color:#2ecc71">{stats["disponivel_total"]}</span><span class="pill-lbl">Disponib. Total</span></div></div>\n'
        f'    <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num" style="color:#9b59b6">{len(stats["cidade"])}</span><span class="pill-lbl">Cidades</span></div></div>\n'
        f'    <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num" style="color:#e74c3c">{stats["tem_terreiro"]}</span><span class="pill-lbl">Com Terreiro</span></div></div>\n'
        f'    <div class="col-6 col-md-2"><div class="stat-pill" style="border-color:#e8a04540;background:linear-gradient(135deg,#1a1a2e,#2a1505)"><span class="pill-num" style="color:#e8a045">{stats["is_xamba"]}</span><span class="pill-lbl" style="color:#e8a045">🥁 Xambá</span></div></div>\n'
        f'    <div class="col-6 col-md-2"><div class="stat-pill"><span class="pill-num">{stats["media_idade"]}</span><span class="pill-lbl">Média de Idade</span></div></div>\n'
        f'    {extra_pills}'
        f'  </div>\n</div>\n\n'

        '<div class="tabs">\n'
        '  <button class="tab-btn active" data-tab="resumo"><i class="fas fa-chart-pie me-1"></i>Resumo</button>\n'
        '  <button class="tab-btn" data-tab="inscritos"><i class="fas fa-users me-1"></i>Inscritos</button>\n'
        '  <button class="tab-btn" data-tab="mapa"><i class="fas fa-map-marker-alt me-1"></i>Mapa</button>\n'
        '  <button class="tab-btn" data-tab="selecionados"><i class="fas fa-star me-1"></i>Selecionados<span class="sel-badge" id="sel-count">0</span></button>\n'
        '</div>\n\n'

        '<div id="pane-resumo" class="pane active">\n'
        '  <div class="container-fluid py-4 px-4">\n'
        '    <div class="row g-3">\n'
        '      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-venus-mars me-1"></i>Gênero</div><canvas id="ch-genero" height="200"></canvas></div></div>\n'
        '      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-users me-1"></i>Raça / Cor</div><canvas id="ch-raca" height="200"></canvas></div></div>\n'
        '      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-birthday-cake me-1"></i>Faixa Etária</div><canvas id="ch-idade" height="200"></canvas></div></div>\n'
        '      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-money-bill-wave me-1"></i>Renda Familiar</div><canvas id="ch-renda" height="200"></canvas></div></div>\n'
        '      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-calendar-check me-1"></i>Disponibilidade</div><canvas id="ch-disponib" height="200"></canvas></div></div>\n'
        '      <div class="col-md-4"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-bullhorn me-1"></i>Como Soube</div><canvas id="ch-soube" height="200"></canvas></div></div>\n'
        '      <div class="col-12"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-map-marked-alt me-1"></i>Distribuição por Cidade</div><canvas id="ch-cidade" height="80"></canvas></div></div>\n'
        f'      <div class="col-md-6"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-praying-hands me-1"></i>Vínculos Culturais</div><div class="row text-center g-3 py-1"><div class="col-6"><div style="font-size:2rem;font-weight:700;color:var(--acc)">{stats["tem_terreiro"]}</div><div style="font-size:.74rem;color:var(--muted)">Terreiro / Povos Trad.</div></div><div class="col-6"><div style="font-size:2rem;font-weight:700;color:#9b59b6">{stats["tem_comunidade"]}</div><div style="font-size:.74rem;color:var(--muted)">Comunidade / Quilombo</div></div><div class="col-6"><div style="font-size:2rem;font-weight:700;color:#3498db">{stats["tem_grupos"]}</div><div style="font-size:.74rem;color:var(--muted)">Grupos Culturais</div></div><div class="col-6"><div style="font-size:2rem;font-weight:700;color:#2ecc71">{stats["tem_coletivos"]}</div><div style="font-size:.74rem;color:var(--muted)">Coletivos / ONGs</div></div></div></div></div>\n'
        '      <div class="col-md-6"><div class="chart-card"><div class="chart-ttl"><i class="fas fa-drum me-1"></i>Grupos Culturais Identificados</div><div id="cult-groups-list" class="py-2"></div></div></div>\n'
        '    </div>\n  </div>\n</div>\n\n'

        '<div id="pane-inscritos" class="pane">\n'
        '  <div class="filter-bar" id="filter-bar"><span class="filter-count" id="filter-count"></span></div>\n'
        '  <div class="cards-wrap"><div class="row g-3" id="cards-grid"></div></div>\n'
        '</div>\n\n'

        '<div id="pane-mapa" class="pane"><div id="map"></div></div>\n\n'
        '<div id="pane-selecionados" class="pane"><div id="sel-content"></div></div>\n\n'

        '<div class="float-bar hidden" id="float-bar">'
        '<i class="fas fa-star"></i><span id="float-count">0</span> selecionado(s)'
        '<span style="font-size:.73rem;opacity:.75;margin-left:3px">· Ver painel</span></div>\n\n'

        '<div class="modal-overlay" id="modal-overlay">\n'
        '  <div class="modal-box">\n'
        '    <div class="modal-head">\n'
        '      <div style="display:flex;align-items:center;gap:.9rem">\n'
        '        <div id="modal-photo"></div>\n'
        '        <div>\n'
        '          <div class="modal-title" id="modal-name"></div>\n'
        '          <div id="modal-alias" style="color:var(--muted);font-size:.83rem;font-style:italic"></div>\n'
        '          <div id="modal-badges" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px"></div>\n'
        '        </div>\n'
        '      </div>\n'
        '      <div style="display:flex;align-items:center;gap:.5rem;flex-shrink:0">\n'
        '        <button id="modal-sel-btn" style="background:var(--sel);border:none;border-radius:18px;color:#fff;cursor:pointer;font-size:.82rem;padding:.25rem .7rem">☆ Selecionar</button>\n'
        '        <button class="close-btn" id="modal-close">✕</button>\n'
        '      </div>\n'
        '    </div>\n'
        '    <div class="modal-body" id="modal-body"></div>\n'
        '  </div>\n'
        '</div>\n\n'

        '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>\n'
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>\n'
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n'
        '<script>\n'
        f'const CANDIDATES = {data_json};\n'
        f'const STATS = {stats_json};\n'
        'const GROUPS_DEF = STATS.groups_def || {};\n'
        + js +
        '</script>\n</body>\n</html>'
    )
    return html


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Buscando planilha...")
    ok = fetch_sheet()
    if not ok:
        if not Path(TSV_FILE).exists() and Path(TSV_FALLBACK).exists():
            import shutil
            shutil.copy(TSV_FALLBACK, TSV_FILE)
            print(f"  Usando arquivo local: {TSV_FALLBACK}")
        elif not Path(TSV_FILE).exists():
            raise FileNotFoundError(f"Sem dados: nem Sheets funcionou nem '{TSV_FILE}' existe.")

    print("Lendo inscrições...")
    candidates = parse_tsv()
    print(f"  {len(candidates)} inscritos")

    stats = compute_stats(candidates)
    print(f"  Xambá: {stats['is_xamba']}  ·  Terreiro: {stats['tem_terreiro']}  ·  Disponib. total: {stats['disponivel_total']}")
    print(f"  Cidades: {sorted(stats['cidade'])}")

    print(f"Gerando {OUTPUT}...")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(generate_html(candidates, stats))
    size = Path(OUTPUT).stat().st_size // 1024
    print(f"  ✓ {OUTPUT} ({size} KB)")


if __name__ == "__main__":
    main()
