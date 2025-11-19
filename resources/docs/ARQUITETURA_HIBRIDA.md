# Arquitetura Híbrida de Dados - TCC Previsor Steam

## 📋 Visão Geral

Este projeto utiliza uma **arquitetura híbrida** para otimizar o armazenamento e processamento de grandes volumes de dados da Steam API.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                      FLUXO DE DADOS                             │
└─────────────────────────────────────────────────────────────────┘

  Steam API (280k+ jogos)
       │
       ├─────────────────────────────────────────────┐
       │                                             │
       ▼                                             ▼
  [DADOS BRUTOS]                              [PROCESSAMENTO]
  Docker/PostgreSQL Local                     Python ETL
  - steam_raw (JSONB)                         - Extração de campos
  - itad_raw (JSONB)                          - Conversão de tipos
  - Grande volume                             - Validação
  - Acesso rápido                             - Normalização
       │                                             │
       │                                             ▼
       │                                      [DADOS LIMPOS]
       │                                      Supabase Cloud
       │                                      - steam_bd (estruturado)
       │                                      - steam_generico
       │                                      - Otimizado para queries
       │                                      - Dashboard/Visualização
       │                                             │
       └─────────────────┬───────────────────────────┘
                         │
                         ▼
                  Análise e Previsão
                  (Modelos de ML)
```

## 🗄️ Estrutura de Bancos de Dados

### 1️⃣ Docker/PostgreSQL Local (`localhost:5432`)

**Propósito**: Armazenar dados BRUTOS em grande volume

**Tabelas**:
- `steam_raw`: Dados brutos da Steam API (JSONB)
  - `appid` (INTEGER): ID do jogo
  - `detalhes` (JSONB): JSON completo dos detalhes
  - `reviews` (JSONB): JSON completo das avaliações
  - `ultima_atualizacao` (TIMESTAMP)

- `itad_raw`: Dados brutos do IsThereAnyDeal (JSONB)
  - Similar estrutura com dados de preços

**Vantagens**:
- ✅ Armazenamento local rápido
- ✅ Sem custos de cloud para grande volume
- ✅ Histórico completo dos dados
- ✅ Backup e recuperação fácil

**Classe Python**: `PostgreSQL` (psycopg2)

### 2️⃣ Supabase Cloud (API REST)

**Propósito**: Dados ESTRUTURADOS para consulta e visualização

**Tabelas**:
- `steam_bd`: Dados processados e normalizados
  - `appid` (INTEGER): ID do jogo
  - `nome` (VARCHAR): Nome do jogo
  - `classificacao_etaria` (VARCHAR)
  - `linguagens` (ARRAY)
  - `desenvolvedores` (ARRAY)
  - `distribuidores` (ARRAY)
  - `preco` (VARCHAR)
  - `metacritic_score` (VARCHAR)
  - `categorias` (ARRAY)
  - `genero` (ARRAY)
  - `data_lancamento` (VARCHAR)
  - `review_score` (INTEGER)
  - `total_reviews` (INTEGER)
  - `total_negative` (INTEGER)
  - `total_positive` (INTEGER)
  - `review_score_desc` (VARCHAR)
  - `ultima_atualizacao` (TIMESTAMP)

- `steam_generico`: Dados gerais dos jogos

**Vantagens**:
- ✅ API REST para acesso remoto
- ✅ Dashboard web integrado
- ✅ Queries otimizadas
- ✅ Escalabilidade automática
- ✅ Backup automático

**Classe Python**: `SupabaseDB` (supabase-py)

## 💻 Uso das Classes

### Inserir Dados BRUTOS (Docker)

```python
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

# Dados como vêm da Steam API
dados_raw = {
    "steam_appid": 123456,
    "detalhes": {
        "name": "Nome do Jogo",
        "type": "game",
        "developers": ["Studio X"],
        # ... resto do JSON completo
    },
    "reviews": {
        "query_summary": {
            "total_reviews": 1000,
            # ... resto das reviews
        }
    }
}

# Inserir no Docker (steam_raw)
PostgreSQL.inserir_dadosSteamRaw_Bulk([dados_raw])
```

### Inserir Dados ESTRUTURADOS (Supabase)

```python
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

# Dados processados e estruturados
dados_estruturados = {
    "appid": 123456,
    "nome": "Nome do Jogo",
    "classificacao_etaria": "12",
    "linguagens": ["English", "Portuguese"],
    "desenvolvedores": ["Studio X"],
    "preco": "R$ 49.99",
    "metacritic_score": "85",
    "categorias": ["Single-player"],
    "genero": ["Action", "Adventure"],
    "data_lancamento": "2025-01-15",
    "review_score": 90,
    "total_reviews": 1000,
    "total_positive": 900,
    "total_negative": 100,
    "review_score_desc": "Very Positive"
}

# Inserir no Supabase (steam_bd)
SupabaseDB.inserir_dadosSteamBD([dados_estruturados])
```

## 🚀 Configuração

### 1. Iniciar Docker

```bash
cd docker
docker compose up -d
```

### 2. Verificar Variáveis de Ambiente

Arquivo `.env`:

```env
# Docker/PostgreSQL Local (Dados RAW)
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=projetotccADMIN
DB_HOST=localhost
DB_PORT=5432

# Supabase Cloud (Dados Estruturados)
SUPABASE_URL=https://norphjcxnsgklyutnmin.supabase.co
SUPABASE_KEY=eyJhbGci...
```

### 3. Executar Teste

```bash
python prj_TCC_PREVISOR_STEAM/test_arquitetura_hibrida.py
```

## 🔍 Verificação de Dados

### Docker/PostgreSQL

```bash
# Verificar dados brutos
docker exec -it supabase-db psql -U postgres -d postgres \
  -c "SELECT appid, detalhes->>'name' FROM steam_raw LIMIT 5;"

# Contar registros
docker exec -it supabase-db psql -U postgres -d postgres \
  -c "SELECT COUNT(*) FROM steam_raw;"
```

### Supabase Cloud

1. Acesse: https://supabase.com/dashboard
2. Selecione projeto: `norphjcxnsgklyutnmin`
3. Vá em **Table Editor** → `steam_bd`
4. Visualize e filtre os dados

## 📊 Quando Usar Cada Banco

| Operação | Banco | Classe | Método |
|----------|-------|--------|--------|
| Coletar dados da Steam API | Docker | `PostgreSQL` | `inserir_dadosSteamRaw()` |
| Coletar dados do ITAD | Docker | `PostgreSQL` | `inserir_dadosItadRaw()` |
| Processar e normalizar dados | Supabase | `SupabaseDB` | `inserir_dadosSteamBD()` |
| Consultas para dashboard | Supabase | `SupabaseDB` | `buscar_*()` |
| Análise de ML (features) | Docker | `PostgreSQL` | Query direta |
| Exportar relatórios | Supabase | `SupabaseDB` | API REST |

## ⚠️ Notas Importantes

1. **Dados RAW sempre no Docker**: Mantenha os dados brutos localmente para evitar custos e ter histórico completo
2. **Dados Estruturados no Supabase**: Apenas dados processados e otimizados para consulta
3. **ETL**: Crie processos para transformar dados de `steam_raw` → `steam_bd`
4. **Backup Docker**: Configure backup periódico dos volumes Docker
5. **Limites Supabase**: Fique atento aos limites do plano free (500MB database)

## 🧪 Testes

- `test_insercao.py`: Teste simples de inserção no Docker
- `test_arquitetura_hibrida.py`: Teste completo da arquitetura híbrida

## 📝 Logs

Os logs mostram claramente onde os dados estão sendo inseridos:

```
INFO - Conexão com o banco de dados estabelecida com sucesso: postgres@localhost:5432/postgres
INFO - Dados steam_raw inseridos/atualizados para o AppID 888888 (linhas afetadas: 1)
INFO - Conectado ao Supabase com sucesso
INFO - Dados processados salvos para 1 registros.
```

## 🎯 Benefícios da Arquitetura Híbrida

✅ **Performance**: Dados locais para processamento intensivo
✅ **Custo**: Evita custos de armazenamento cloud para grande volume  
✅ **Escalabilidade**: Supabase para consultas distribuídas
✅ **Flexibilidade**: Dados brutos preservados para reprocessamento
✅ **Facilidade**: Dashboard web para visualização sem código
✅ **Segurança**: Backup local + backup cloud
