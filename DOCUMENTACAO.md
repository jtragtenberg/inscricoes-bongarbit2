# Bongarbit — Dashboard de Seleção · Escola de Luteria 2026

Documentação técnica completa do sistema de visualização e seleção de inscritos.

---

## Visão Geral

Sistema de dashboard estático gerado por script Python a partir de uma planilha TSV exportada do Google Forms. O resultado é um único arquivo `index.html` autocontido que pode ser aberto diretamente no navegador, sem servidor, sem backend.

**Contexto:** Processo seletivo da Escola de Luteria do Grupo Bongarbit / Centro Cultural Bongarbit (Olinda/PE), com ~100 candidatos inscritos para a turma de julho/2026 a fevereiro/2027.

---

## Estrutura de Arquivos

```
inscricoes-bongarbit/
│
├── build_dashboard.py                          ← script principal (gera index.html)
├── download_photos.py                          ← baixa fotos via Instagram/Playwright
├── geocode_ceps.py                             ← geocodifica CEPs e salva geocache.json
├── verify_photos.py                            ← verifica rostos com OpenCV + Gravatar
│
├── Inscritos Bongarbit - Escola de Luteria     ← fonte de dados (exportação Google Forms)
│   - Página1 (1).tsv
│
├── geocache.json                               ← cache de lat/lon por CEP (90 CEPs)
├── index.html                                  ← dashboard gerado (não editar manualmente)
│
└── imagens/
    ├── {id}.jpg                                ← foto com rosto detectado
    ├── {id}_sem_rosto.jpg                      ← foto sem rosto detectado
    ├── haarcascade_frontalface_default.xml     ← modelo OpenCV (baixado automaticamente)
    ├── relatorio_rostos.json                   ← resultado da verificação de rostos
    └── resultados_fotos.json                   ← log do download de fotos
```

---

## Requisitos

### Python

- **Python 3.8+**
- Bibliotecas padrão: `csv`, `json`, `re`, `os`, `hashlib`, `time`, `urllib`

### Dependências externas (pip)

```bash
pip3 install playwright opencv-python
playwright install chromium
```

| Pacote | Uso | Scripts |
|---|---|---|
| `playwright` + Chromium | Scraping de fotos de perfil do Instagram | `download_photos.py`, `verify_photos.py` |
| `opencv-python` | Detecção de rostos via Haar Cascade | `verify_photos.py` |

> **Nota:** `build_dashboard.py` não requer dependências externas — usa apenas stdlib Python.

### APIs e serviços externos utilizados

| Serviço | Endpoint | Uso |
|---|---|---|
| BrasilAPI v2 | `https://brasilapi.com.br/api/cep/v2/{cep}` | Geocodificação de CEPs → lat/lon |
| Nominatim (OpenStreetMap) | `https://nominatim.openstreetmap.org/search` | Fallback de geocodificação |
| Gravatar | `https://www.gravatar.com/avatar/{md5(email)}?s=200&d=404` | Foto via hash do e-mail |
| Instagram (scraping) | `https://www.instagram.com/{usuario}/` | Foto de perfil via `og:image` |
| OpenCV GitHub | `haarcascade_frontalface_default.xml` | Modelo de detecção facial (baixado uma vez) |

### Frontend (CDN — sem instalação)

| Biblioteca | Versão | Uso |
|---|---|---|
| Bootstrap | 5.3.2 | Layout, dark theme, modal, grid |
| Font Awesome | 6.4.2 | Ícones |
| Leaflet.js | 1.9.4 | Mapa interativo |
| Chart.js | 4.4.0 | Gráficos de distribuição |
| CartoDB Dark tiles | — | Tiles do mapa (dark) |

---

## Fonte de Dados — TSV

Arquivo exportado do Google Forms com **24 colunas** (índice 0–23), **sem coluna de número sequencial**:

| Índice | Campo interno | Pergunta no formulário |
|---|---|---|
| 0 | `timestamp` | Carimbo de data/hora |
| 1 | `nome` | Nome completo |
| 2 | `nome_social` | Nome social (se houver) |
| 3 | *(e-mail alternativo)* | E-mail (duplicado — o principal está no col. 23) |
| 4 | `telefone` | Telefone/WhatsApp |
| 5 | `cpf` | CPF |
| 6 | `endereco` | Endereço residencial |
| 7 | `cep` | CEP |
| 8 | `cidade_estado` | Cidade/Estado (campo livre — requer normalização) |
| 9 | `idade_raw` | Idade (campo livre — requer parse numérico) |
| 10 | `genero` | Gênero |
| 11 | `raca` | Raça/Cor (classificação IBGE) |
| 12 | `pcd` | Pessoa com Deficiência (Sim/Não) |
| 13 | `desc_deficiencia` | Descrição da deficiência |
| 14 | `renda` | Faixa de renda familiar mensal |
| 15 | `terreiro` | Terreiro / Povos Tradicionais |
| 16 | `comunidade` | Comunidade / Quilombo / Periferia |
| 17 | `grupos_culturais` | Grupos culturais (Afoxé, Maracatu, Coco etc.) |
| 18 | `coletivos` | Coletivos / ONGs / Associações |
| 19 | `por_que` | Por que deseja participar |
| 20 | `disponibilidade` | Disponibilidade para o projeto |
| 21 | `redes_sociais` | Links de redes sociais |
| 22 | `como_soube` | Como ficou sabendo |
| 23 | `email` | E-mail principal |

### Deduplicação

Linha duplicada = mesmo `nome.lower()` + `telefone`. A segunda ocorrência é descartada.

### Normalização de cidade (`normalize_city`)

O campo `cidade_estado` é livre (ex: "Recife/PE", "Olinda Pernambuco", "PE"). A função:

1. Remove sufixo de estado: `/PE`, `- PE`, `, PE`, `Pernambuco` ao final
2. Divide por vírgula ou barra e usa o primeiro fragmento
3. Mapeia variações para nomes canônicos:
   - `"recife"` → `"Recife"`
   - `"olinda"` → `"Olinda"`
   - `"paulista"` → `"Paulista"`
   - `"jaboatão"` / `"jaboatao"` → `"Jaboatão dos Guararapes"`
   - `"são lourenço"` / `"sao lourenco"` → `"São Lourenço da Mata"`
   - `"sapucaia"` → `"Olinda"` (bairro de Olinda)
   - Campo vazio ou só "PE" → `"Pernambuco (n/e)"`

---

## Scripts Python

### `build_dashboard.py` — Script Principal

Gera `index.html` a partir do TSV. Não requer dependências externas.

```bash
python3 build_dashboard.py
```

**Fluxo:**

1. Lê e parseia o TSV (`parse_tsv`)
2. Calcula estatísticas agregadas (`compute_stats`)
3. Gera o HTML completo com JS embutido (`generate_html`)
4. Salva `index.html`

**Funções principais:**

| Função | Descrição |
|---|---|
| `parse_tsv()` | Lê o TSV, desdup., normaliza campos, detecta Xambá e grupos culturais, carrega coords |
| `normalize_city(str)` | Normaliza nome de cidade (veja seção acima) |
| `get_coords(cep, cidade, id)` | Retorna lat/lon: geocache → fallback por cidade → Recife + jitter aleatório |
| `detect_xamba(c)` | Detecta vínculo com Xambá (terreiro, comunidade, CEP, grupos, como soube) |
| `detect_cultural_groups(c)` | Detecta pertencimento a grupos culturais específicos |
| `compute_stats(candidates)` | Calcula contagens, distribuições e médias para os gráficos |
| `generate_html(candidates, stats)` | Gera o HTML/JS completo como f-string Python |
| `avatar_color(nome)` | Cor determinística para avatar (MD5 do nome → índice na paleta) |
| `avatar_initials(nome)` | Iniciais para avatar (primeira + última palavra do nome) |
| `extract_instagram(texto)` | Extrai usuário do Instagram de texto livre |
| `parse_age(str)` | Extrai número de idade de campo livre |

**Armadilha f-string:** todo `{` literal em JavaScript dentro de uma f-string Python deve ser escrito como `{{` e `}}`. Desbalanceamentos causam `SyntaxError`.

---

### `geocode_ceps.py` — Geocodificação

Geocodifica os CEPs de todos os inscritos e salva em `geocache.json`.

```bash
python3 geocode_ceps.py
```

**Estratégia:**

1. BrasilAPI v2 (`/api/cep/v2/{cep}`) — retorna lat/lon + endereço completo
2. Fallback: Nominatim / OpenStreetMap — busca por `{cidade}, Pernambuco, Brazil`
3. Fallback final: coordenadas fixas da cidade + jitter aleatório

**Cache:** `geocache.json` — chave = CEP (só dígitos), valor = `{lat, lon, source, city, neighborhood, street}`.

O script respeita rate limiting: 300ms entre requisições BrasilAPI, 1s entre Nominatim.

---

### `download_photos.py` — Download de Fotos

Baixa fotos de perfil dos inscritos e salva em `imagens/{id}.jpg`.

```bash
python3 download_photos.py
```

**Estratégia por candidato:**

1. Extrai usuário do Instagram do campo `redes_sociais`
2. Abre `https://www.instagram.com/{usuario}/` com Playwright (Chromium headless)
3. Extrai a meta tag `og:image` como URL da foto de perfil
4. Faz download e salva

Salva log em `imagens/resultados_fotos.json` com status de cada candidato.

---

### `verify_photos.py` — Verificação de Rostos

Verifica se as fotos existentes contêm um rosto humano. Tenta melhorar fotos sem rosto.

```bash
python3 verify_photos.py
```

**Fluxo por candidato com foto:**

1. **OpenCV Haar Cascade** (`haarcascade_frontalface_default.xml`) — detecta rosto na foto existente
2. Se não detectar rosto → tenta **Gravatar**: `https://www.gravatar.com/avatar/{md5(email.lower())}?s=200&d=404`
   - Retorna HTTP 404 se não houver foto cadastrada
3. Se ainda sem rosto → tenta **Instagram** novamente via Playwright

**Nomenclatura:**
- Com rosto detectado: `imagens/{id}.jpg`
- Sem rosto: `imagens/{id}_sem_rosto.jpg`

**Resultado atual:** 40 fotos totais — 12 com rosto confirmado, 28 classificadas `_sem_rosto`.

O Haar Cascade (`haarcascade_frontalface_default.xml`) é baixado automaticamente do repositório OpenCV no GitHub na primeira execução.

---

## Dashboard — `index.html`

Arquivo HTML único (~200KB), autocontido, sem servidor. Abre diretamente no navegador.

### Abas

#### 1. Resumo

Visão estatística geral com gráficos Chart.js:

- **Gênero** — doughnut
- **Raça / Cor** — doughnut
- **Faixa Etária** — bar (grupos: 15-19, 20-29, 30-39, 40-49, 50-59, 60+)
- **Renda Familiar** — bar
- **Disponibilidade** — doughnut (total vs. parcial)
- **Como Soube** — doughnut
- **Distribuição por Cidade** — bar horizontal
- **Vínculos Culturais** — contagem de terreiro, comunidade, grupos, coletivos
- **Grupos Culturais Identificados** — contagem por grupo detectado

#### 2. Inscritos

Grade de cards com todos os inscritos. Cada card exibe:

- Foto de perfil ou avatar colorido com iniciais
- Nome completo e nome social (se houver)
- Badges: cidade, idade, gênero
- Badges de grupo cultural (coloridos por grupo)
- Header dourado e badge 🥁 para candidatos com conexão Xambá
- Indicador de disponibilidade (verde = total, laranja = parcial)
- Faixa de renda
- Tags de terreiro, comunidade, grupos
- Widget de estrelas (pontuação 1–5)
- Botão de seleção ☆/★
- Badge de nota no canto superior esquerdo (se pontuado)

**Filtros** (criados dinamicamente em JS):

| Filtro | Valores |
|---|---|
| Busca textual | Nome, nome social, cidade, grupos, terreiro, comunidade, coletivos, Instagram, por que |
| Cidade | Todas as cidades detectadas |
| Gênero | Todos os gêneros declarados |
| Raça/Cor | Todas as raças declaradas |
| Faixa de renda | 1 SM / 2 SM / 3 SM / +3 SM / Prefiro não informar |
| Disponibilidade | Total / Parcial |
| Terreiro | Com terreiro / Sem terreiro |
| Conexão Xambá | Com vínculo / Sem vínculo |
| Grupo cultural | Xambá + todos os grupos detectados |
| Nota | Com nota / 3+ / 4+ / 5 estrelas / Sem nota |
| Ordenação | Por nota (padrão) / Xambá primeiro / Nome A-Z / Idade |

> **Implementação:** todos os `<select>` e `<input>` são criados via `document.createElement()` no evento `DOMContentLoaded`. Nenhum elemento de formulário existe no HTML estático — isso impede que o Chrome restaure valores salvos de sessões anteriores, que causava exibição de subset filtrado no carregamento.

#### 3. Mapa

Mapa Leaflet interativo com tiles CartoDB Dark. Cada inscrito é um marcador circular:

- **Cor do preenchimento:** dourado (#e8a045) para Xambá, cor do avatar para os demais
- **Borda:** azul se selecionado, dourado se Xambá, verde se disponibilidade total, laranja se parcial
- **Tamanho:** raio 10 para Xambá, 8 para os demais
- **Popup:** nome, grupo, cidade, idade, gênero, renda, disponibilidade, link Instagram, botões "Ver detalhes" e "Selecionar"
- **Labels de cidade:** contagem de inscritos por cidade
- **Legenda:** canto inferior esquerdo

**Coordenadas:** carregadas do `geocache.json` (lat/lon por CEP via BrasilAPI). Pequeno jitter aleatório (seed = ID do candidato) evita sobreposição de marcadores do mesmo endereço.

#### 4. Selecionados

Painel dos candidatos marcados com ★. Mostra:

- Estatísticas do grupo selecionado: total, disponibilidade, conexão Xambá, cidades
- Gráficos de distribuição: gênero, raça, pontuação (1–5), cidade, renda
- Cards dos selecionados ordenados por nota
- Botão "Limpar seleção"

### Sistema de Pontuação (1–5 estrelas)

Permite avaliar cada candidato de 1 a 5. Persistido em `localStorage`.

| Nota | Label | Cor |
|---|---|---|
| 1 | Não recomendado | Vermelho (#e74c3c) |
| 2 | Abaixo da média | Laranja (#e67e22) |
| 3 | Interessante | Amarelo (#f1c40f) |
| 4 | Muito bom | Verde claro (#2ecc71) |
| 5 | Excelente! | Verde (#27ae60) |

Clicar na mesma estrela novamente remove a nota. Visível no card (badge de estrelas no canto superior esquerdo) e no modal de detalhes. A ordenação padrão é por nota decrescente.

### Sistema de Seleção

Botão ☆/★ em cada card marca o candidato como selecionado. Persistido em `localStorage`.

- Cards selecionados ganham borda azul e checkmark ✓
- Barra flutuante no canto inferior direito mostra contagem e abre aba Selecionados
- O modal exibe botão "☆ Selecionar" / "★ Selecionado"

### Modal de Detalhes

Clique em qualquer card abre modal com todos os dados do candidato:

- Foto / avatar
- Badges de cidade, idade, gênero, raça, PCD, Xambá, grupos culturais
- Botão de seleção
- Widget de estrelas (tamanho maior)
- Todos os campos preenchidos (disponibilidade, renda, endereço, por que quer participar, terreiro, comunidade, grupos, coletivos, PCD, como soube, timestamp, telefone, e-mail, redes sociais)
- Link direto para Instagram

### Persistência (localStorage)

| Chave | Tipo | Conteúdo |
|---|---|---|
| `bongarbit_sel` | JSON array | IDs dos candidatos selecionados |
| `bongarbit_ratings` | JSON object | `{id: 1-5}` com notas de cada candidato |

Os dados persistem entre sessões do navegador no mesmo computador.

---

## Detecção de Vínculos Culturais

### Conexão Xambá (`detect_xamba`)

Candidato é marcado como Xambá se qualquer critério for atendido:

| Critério | Exemplo |
|---|---|
| Campo `terreiro` contém "xambá" | "Terreiro Xambá" |
| Campo `comunidade` contém "xambá" | "Quilombo Xambá" |
| Qualquer campo contém "Portão do Gelo" | endereço, comunidade |
| `grupos_culturais` ou `coletivos` contém "xambá" | "Maracatu Estrela de Ouro do Xambá" |
| CEP começa com `5327` | Região do Portão do Gelo, Olinda |
| `grupos_culturais`/`coletivos` contém "Grupo Bongar" | membro do grupo mantenedor |

Os motivos detectados aparecem no badge do card e no popup do mapa.

### Grupos Culturais (`detect_cultural_groups`)

Detectados por padrão regex nos campos relevantes (exceto `por_que`, que é descartado por todos mencionarem "bongarbit"):

| Grupo | Cor | Padrões buscados | Campos |
|---|---|---|---|
| Coco de Umbigada | Verde #27AE60 | `umbigada`, `quinho.*caet`, `coco.*guadalup` | grupos_culturais, coletivos, terreiro, comunidade, como_soube |
| Daruê Malungo | Vermelho #E74C3C | `daruê malungo`, `darue malungo` | grupos_culturais, coletivos, terreiro, comunidade, por_que |
| Boi Mandingueiro | Laranja #F39C12 | `boi mandingueiro`, `mandingueiro` | grupos_culturais, coletivos, terreiro, comunidade, como_soube |
| Alafin Oyó | Roxo #9B59B6 | `alafin oy`, `alafín oy` | grupos_culturais, coletivos, terreiro, comunidade, por_que |
| Cambinda Estrela | Azul #3498DB | `cambinda estrela`, `cambinda` | grupos_culturais, coletivos, terreiro, por_que |

---

## Como Usar

### Fluxo completo do zero

```bash
# 1. Geocodificar CEPs (só precisa rodar uma vez ou quando entrar nova inscrição)
python3 geocode_ceps.py

# 2. Baixar fotos (requer playwright instalado)
python3 download_photos.py

# 3. Verificar rostos e melhorar fotos (requer opencv-python)
python3 verify_photos.py

# 4. Gerar o dashboard
python3 build_dashboard.py

# 5. Abrir no navegador
open index.html
```

### Fluxo rápido (só atualizar o dashboard)

```bash
python3 build_dashboard.py && open index.html
```

### Atualizar inscrições

1. Exportar novo TSV do Google Sheets (Arquivo → Download → TSV)
2. Substituir o arquivo `.tsv` no diretório
3. Rodar `python3 geocode_ceps.py` para geocodificar novos CEPs
4. Rodar `python3 build_dashboard.py` para regenerar

---

## Estatísticas Atuais (build de junho/2026)

| Métrica | Valor |
|---|---|
| Total de inscritos | 100 |
| Disponibilidade total | 78 |
| Com terreiro / povos tradicionais | 52 |
| Conexão Xambá | 17 |
| Coco de Umbigada | 4 |
| Daruê Malungo | 1 |
| Boi Mandingueiro | 1 |
| Alafin Oyó | 2 |
| Cambinda Estrela | 1 |
| CEPs geocodificados | 90 |
| Fotos baixadas | 40 |
| Fotos com rosto confirmado | 12 |
| Cidades representadas | 6 |

**Cidades:** Recife, Olinda, Paulista, Jaboatão dos Guararapes, São Lourenço da Mata, Pernambuco (n/e)

---

## Decisões Técnicas

### Por que arquivo único HTML?

Facilita distribuição e uso: basta compartilhar o `index.html` e abrir no navegador. Não requer servidor web, Node.js, nem instalação de nada no computador de quem vai usar o dashboard.

### Por que os selects são criados em JavaScript?

O Chrome salva o estado dos elementos `<select>` entre sessões (session restore) e restaura os valores após o carregamento da página. Isso causava o dashboard abrir já filtrado para uma cidade específica, mostrando apenas 3 dos 100 inscritos. A solução definitiva: não incluir nenhum `<select>` no HTML estático — todos os elementos de filtro são criados por `document.createElement()` no evento `DOMContentLoaded`. O Chrome não consegue restaurar estado em elementos que não existiam no HTML ao fazer o parse.

### Por que geocache.json?

Geocodificar 100 CEPs a cada `build_dashboard.py` seria lento (~2 minutos) e geraria requisições desnecessárias às APIs externas. O cache persiste os resultados para builds subsequentes.

### Por que jitter nas coordenadas do mapa?

Vários inscritos podem ter o mesmo CEP (mesmo endereço ou CEP aproximado). Sem jitter, os marcadores se sobrepõem completamente e são impossíveis de distinguir. O jitter é determinístico por ID (seed fixo), então não muda a cada build.
