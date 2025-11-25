# 📊 Exports CSV das Tabelas do Docker PostgreSQL

**Data da exportação:** 21 de novembro de 2025  
**Banco de dados:** Docker PostgreSQL (supabase-db)

---

## 📁 Arquivos Exportados

### 1️⃣ **steam_raw.csv** (JSONB - Dados Brutos)
- **Tamanho:** 2,63 GB (2.631,96 MB)
- **Registros:** 276.562
- **Descrição:** Dados brutos da Steam API em formato JSONB
- **Colunas principais:**
  - `appid` - ID do aplicativo
  - `detalhes` - JSONB com todos os detalhes do jogo
  - `reviews` - JSONB com informações de reviews
  - `ultima_atualizacao` - Timestamp da última atualização

**Uso:** Fonte primária de dados, contém informações completas e não estruturadas

---

### 2️⃣ **steam_bd.csv** (Dados Estruturados - Apenas Games Pagos)
- **Tamanho:** 19,59 MB
- **Registros:** 10.090
- **Descrição:** Dados estruturados apenas de **jogos pagos** (filtro: type='game' AND is_free=false)
- **Colunas principais:**
  - `appid`, `nome`, `classificacao_etaria`, `linguagens`, `desenvolvedores`
  - `distribuidores`, `preco`, `metacritic_score`, `categorias`, `genero`
  - `data_lancamento`, `type`, `review_score`, `total_reviews`
  - `total_negative`, `total_positive`, `review_score_desc`
  - `ultima_atualizacao`

**Uso:** Análise de jogos comerciais, modelos de previsão de preço

---

### 3️⃣ **steam_generico.csv** (Lista Mínima de AppIDs)
- **Tamanho:** 15,84 MB
- **Registros:** 276.513
- **Descrição:** Lista completa de AppIDs disponíveis na Steam
- **Colunas:**
  - `appid` - ID do aplicativo (PK)
  - `name` - Nome do jogo
  - `ultima_atualizacao` - Timestamp

**Uso:** Referência de todos os jogos disponíveis, base para ETL

---

### 4️⃣ **itad_raw.csv** (Dados ITAD - IsThereAnyDeal)
- **Tamanho:** 6,49 MB
- **Registros:** 9.961
- **Descrição:** Dados de preços históricos do ITAD
- **Colunas principais:**
  - `id_itad` - ID único ITAD (PK)
  - `slug` - Slug do jogo
  - `title` - Título do jogo
  - `type` - Tipo (game, bundle, etc)
  - `mature` - Conteúdo adulto (boolean)
  - `assets` - JSONB com imagens/assets
  - `historico_preco` - JSONB com histórico de preços
  - `ultima_atualizacao` - Timestamp

**Uso:** Análise de histórico de preços, comparação de ofertas

---

### 5️⃣ **steam_itad_mapping.csv** (Ponte Steam ↔ ITAD)
- **Tamanho:** 1,03 MB
- **Registros:** 9.867
- **Descrição:** Mapeamento entre AppIDs da Steam e IDs do ITAD
- **Colunas:**
  - `appid` - ID Steam (FK → steam_generico)
  - `id_itad` - ID ITAD (FK → itad_raw)
  - `slug` - Slug ITAD
  - `title` - Título do jogo
  - `created_at` - Data de criação do mapeamento

**Uso:** JOIN entre dados Steam e ITAD para análises consolidadas

---

### 6️⃣ **steam_unificado_export.csv** (Tabela Consolidada - Campos Estruturados)
- **Tamanho:** 26,34 MB
- **Registros:** 229.670
- **Descrição:** Dados estruturados + JSONB de **todos os tipos** (games, DLCs, demos, etc)
- **Colunas:** 13 campos principais (**JSONB omitido por limitação do formato CSV**)
  - Similar ao steam_bd, mas inclui DLCs, demos, music, etc
  - Campos JSONB (`detalhes_completos`, `reviews_completos`) **NÃO incluídos**

**Por que JSONB foi omitido do CSV?**
- ❌ CSV não suporta estruturas hierárquicas complexas
- ❌ JSONB contém objetos aninhados com milhares de caracteres
- ❌ Vírgulas dentro do JSON quebram o delimitador CSV
- ❌ Dificulta parsing e análise

**Solução: Use JSON para dados completos com JSONB**
- ✅ `steam_unificado_sample_1000.json` - 1.000 registros completos (11,2 MB)
- ✅ Para export completo: Execute `python export_steam_unificado_json.py`

**Uso:** 
- CSV: Análise rápida de campos estruturados (preço, reviews, tipo)
- JSON: Análise completa incluindo JSONB (detalhes API, reviews completos)

---

## 📈 Estatísticas Gerais

| Tabela | Registros | Tamanho | Cobertura |
|--------|-----------|---------|-----------|
| steam_raw | 276.562 | 2,63 GB | 100% dos dados brutos |
| steam_generico | 276.513 | 15,84 MB | 99,98% (49 a menos) |
| steam_unificado | 229.670 | 26,34 MB | 83% (estruturados) |
| steam_bd | 10.090 | 19,59 MB | 3,6% (só games pagos) |
| itad_raw | 9.961 | 6,49 MB | ~4% (ITAD coverage) |
| steam_itad_mapping | 9.867 | 1,03 MB | 99% do ITAD mapeado |

---

## 🔄 Export JSON (Com JSONB Completo)

### **Por que usar JSON?**
- ✅ Suporta estruturas aninhadas (objetos, arrays)
- ✅ Preserva campos JSONB nativamente
- ✅ Fácil parsing em Python (`json.load()`)
- ✅ Ideal para análise de dados completos da API

### **Arquivos JSON Disponíveis:**
1. **steam_unificado_sample_1000.json** - 11,2 MB (1.000 registros)
   - Amostra para testes
   - Inclui `detalhes_completos` e `reviews_completos`

### **Gerar Export JSON Completo:**
```bash
# Todos os registros (229.670) - ~2,5 GB estimado
python export_steam_unificado_json.py

# Apenas 5.000 registros (teste)
python export_steam_unificado_json.py output.json 1000 5000

# Argumentos: [arquivo_saida] [batch_size] [limit]
```

### **Usar JSON em Python:**
```python
import json

# Carregar JSON completo
with open('steam_unificado_complete.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

# Acessar campos JSONB
jogo = dados[0]
print(jogo['nome'])
print(jogo['detalhes_completos']['developers'])  # Array de desenvolvedores
print(jogo['reviews_completos']['total_positive'])  # Reviews positivas
```

**Tamanho estimado do JSON completo:** ~2,5 GB (todos os 229.670 registros)

---

## 🔗 Relacionamentos

```
steam_generico (276.513)
    ↓ (appid)
steam_itad_mapping (9.867)
    ↓ (id_itad)
itad_raw (9.961)

steam_raw (276.562) → steam_bd (10.090) [filtro: games pagos]
steam_raw (276.562) → steam_unificado (229.670) [sem filtros]
```

---

## 🔍 Queries Úteis

### Carregar CSV em Python (pandas):
```python
import pandas as pd

# Dados estruturados
df_bd = pd.read_csv('steam_bd.csv')
df_generico = pd.read_csv('steam_generico.csv')

# Dados ITAD
df_itad = pd.read_csv('itad_raw.csv')
df_mapping = pd.read_csv('steam_itad_mapping.csv')

# Consolidado
df_unificado = pd.read_csv('steam_unificado_export.csv')
```

### JOIN Steam + ITAD:
```python
# Via mapping
df_steam_itad = df_bd.merge(
    df_mapping[['appid', 'id_itad']], 
    on='appid', 
    how='left'
).merge(
    df_itad[['id_itad', 'historico_preco']], 
    on='id_itad', 
    how='left'
)
```

---

## ⚠️ Notas Importantes

1. **steam_raw.csv é muito grande (2,63 GB)** - Considere usar chunking para leitura
2. **Arrays SQL (TEXT[])** no CSV aparecem como strings: `{item1,item2,item3}`
3. **JSONB** foi exportado como texto - use `json.loads()` em Python
4. **Campos NULL** aparecem vazios no CSV
5. **Timestamps** no formato ISO: `YYYY-MM-DD HH:MM:SS.microseconds`

---

## 📦 Uso Recomendado

### Para Análise de Preços:
- Use `steam_bd.csv` + `itad_raw.csv` + `steam_itad_mapping.csv`

### Para Machine Learning (todos os jogos):
- Use `steam_unificado_export.csv` (já consolidado)

### Para Catálogo Completo:
- Use `steam_generico.csv` (lista completa)

### Para Dados Brutos Completos:
- Use `steam_raw.csv` (atenção ao tamanho!)

---

**Gerado automaticamente pelo GitHub Copilot Cloud Agent** 🤖
