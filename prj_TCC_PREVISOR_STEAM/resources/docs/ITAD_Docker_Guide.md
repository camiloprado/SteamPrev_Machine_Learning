# Guia de Inserção de Dados ITAD no Docker PostgreSQL

## Arquitetura

```
┌─────────────────┐
│   steam_bd      │
│   (10,090)      │
└────────┬────────┘
         │ appid
         │
         ▼
┌─────────────────────┐      ┌──────────────────┐
│ steam_itad_mapping  │──────│   itad_raw       │
│  (bridge table)     │      │  (ITAD dados)    │
│                     │      │                  │
│ - appid (PK)        │      │ - id_itad (PK)   │
│ - id_itad (FK)──────┼─────►│ - slug           │
│ - slug              │      │ - title          │
│ - title             │      │ - type           │
│ - created_at        │      │ - mature         │
└─────────────────────┘      │ - assets (JSONB) │
                             │ - ultima_atuali  │
                             │ - historico_preco│
                             └──────────────────┘
```

## Métodos Disponíveis

### 1. PostgreSQL (postgre.py)

#### Consulta
```python
# Busca AppIDs sem dados ITAD
var_listNovos = PostgreSQL.buscar_appids_sem_itad(
    arg_intPcId=1,           # ID deste PC
    arg_intTotalPcs=1        # Total de PCs
)
# Retorna: [123, 456, 789, ...]

# Busca AppIDs com ITAD desatualizado (>90 dias)
var_listDesatualizados = PostgreSQL.buscar_appids_itad_desatualizados(
    arg_intDiasAtualizacao=90,  # Dias para considerar desatualizado
    arg_intPcId=1,
    arg_intTotalPcs=1
)
# Retorna: [321, 654, 987, ...]
```

#### Inserção
```python
# Inserção em bulk (até 1000 registros recomendado)
var_dictDados = {
    730: {
        "id": "app/730",
        "slug": "counter-strike-global-offensive",
        "title": "Counter-Strike: Global Offensive",
        "type": "game",
        "mature": False,
        "assets": {"banner": "https://..."}
    },
    570: {
        "id": "app/570",
        "slug": "dota-2",
        "title": "Dota 2",
        ...
    }
}

var_intInseridos = PostgreSQL.inserir_dados_itad_raw_bulk(var_dictDados)
# Insere em: itad_raw + steam_itad_mapping
# Retorna: 2

# Inserção em lotes (para grandes volumes)
var_intTotal = PostgreSQL.inserir_dados_itad_raw_batched(
    arg_dictDadosItad=var_dictGrande,
    arg_intBatchSize=1000  # Lotes de 1000
)
# Retorna: total de registros inseridos
```

### 2. SteamClient (steam_api.py)

#### Busca ITAD API
```python
import asyncio

# Busca dados ITAD para lista de AppIDs
var_listAppIDs = [730, 570, 440, 10, 20]

var_dictResultados = asyncio.run(
    SteamClient.lookup_itad_ids_batched(arg_seqAppids=var_listAppIDs)
)

# Estrutura retornada:
# {
#     730: {
#         "id": "app/730",
#         "slug": "counter-strike-global-offensive",
#         "title": "Counter-Strike: Global Offensive",
#         "type": "game",
#         "mature": False,
#         "assets": {"banner": "https://...", "boxart": "https://..."}
#     },
#     570: {...},
#     ...
# }
```

### 3. Previsor (previsor.py)

#### Workflow Completo
```python
# Execução automática via bot.py
# Opção 3: Alimentar banco de dados ITAD Docker

Previsor.alimentar_banco_dados_ITAD_docker()

# Fluxo interno:
# 1. Busca AppIDs sem ITAD (steam_bd - steam_itad_mapping)
# 2. Busca AppIDs ITAD desatualizados (>90 dias)
# 3. Processa em lotes de RANGE_PROCESSAMENTO_ITAD_RAW (default: 5000)
# 4. Para cada lote:
#    - Chama SteamClient.lookup_itad_ids_batched()
#    - Insere via PostgreSQL.inserir_dados_itad_raw_bulk()
# 5. Suporta multi-PC via PC_ID e TOTAL_PCS
```

## Variáveis de Ambiente (.env)

```bash
# Processamento ITAD
RANGE_PROCESSAMENTO_ITAD_RAW=5000   # Lote de AppIDs por iteração
PC_ID=1                              # ID deste PC (1, 2, 3, ...)
TOTAL_PCS=1                          # Total de PCs processando
AMBIENTE=PRD                         # PRD ou HML (teste)
BATCH_TESTE=20                       # Limite em HML

# API ITAD
ITAD_API_KEY=your_key_here          # Chave da API IsThereAnyDeal
```

## Exemplo de Uso Manual

```python
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
import asyncio

# 1. Conectar ao banco
PostgreSQL.conectar()

# 2. Buscar AppIDs que precisam de dados ITAD
var_listAppIDs = PostgreSQL.buscar_appids_sem_itad(arg_intPcId=1, arg_intTotalPcs=1)
print(f"AppIDs sem ITAD: {len(var_listAppIDs)}")

# 3. Processar em lote pequeno (exemplo: 100)
var_listLote = var_listAppIDs[:100]

# 4. Buscar dados na API ITAD
var_dictDados = asyncio.run(SteamClient.lookup_itad_ids_batched(var_listLote))
print(f"Dados obtidos: {len(var_dictDados)}")

# 5. Inserir no banco
var_intInseridos = PostgreSQL.inserir_dados_itad_raw_bulk(var_dictDados)
print(f"Inseridos: {var_intInseridos}")

# 6. Desconectar
PostgreSQL.desconectar()
```

## Verificação no PostgreSQL

```sql
-- Contar registros
SELECT COUNT(*) FROM itad_raw;
SELECT COUNT(*) FROM steam_itad_mapping;

-- Verificar últimas inserções
SELECT id_itad, title, ultima_atualizacao 
FROM itad_raw 
ORDER BY ultima_atualizacao DESC 
LIMIT 10;

-- Verificar mapeamento
SELECT sim.appid, sim.id_itad, ir.title, ir.ultima_atualizacao
FROM steam_itad_mapping sim
JOIN itad_raw ir ON sim.id_itad = ir.id_itad
ORDER BY sim.created_at DESC
LIMIT 10;

-- Jogos sem ITAD
SELECT COUNT(*) 
FROM steam_bd sb
LEFT JOIN steam_itad_mapping sim ON sb.appid = sim.appid
WHERE sim.appid IS NULL;
```

## Troubleshooting

### Erro: "column ir.appid does not exist"
✅ **Corrigido!** Agora usa `steam_itad_mapping` como ponte.

### Erro: Foreign key violation
- Certifique-se que o `appid` existe em `steam_generico`
- Verifique se `id_itad` está correto (formato: "app/123456")

### API ITAD retorna vazio
- Verifique `ITAD_API_KEY` no `.env`
- Alguns jogos não existem no ITAD (normal)
- Limite de rate: 60 req/min (implementado: 3 concurrent)

### Performance lenta
- Reduza `RANGE_PROCESSAMENTO_ITAD_RAW` para 1000-2000
- Use multi-PC: `PC_ID=1 TOTAL_PCS=2` (processa MOD 2)
- Verifique índices: `idx_steam_itad_mapping_appid` e `idx_steam_itad_mapping_id_itad`

## Estrutura de Dados ITAD

```json
{
  "id": "app/730",                    // Chave primária itad_raw
  "slug": "counter-strike-global-offensive",
  "title": "Counter-Strike: Global Offensive",
  "type": "game",                     // ou "dlc", "bundle"
  "mature": false,                    // conteúdo adulto
  "assets": {                         // JSONB
    "banner": "https://...",
    "boxart": "https://...",
    "screenshots": ["https://..."]
  }
}
```

## Logs Esperados

```
INFO - Buscando AppIDs sem dados ITAD (PC 1/1)...
INFO - Encontrados 5,000 AppIDs sem dados ITAD
INFO - Processando aplicativos ITAD de 1 a 5000 de 5000
INFO - Progresso: 0.0%
INFO - Número de IDs ITAD a processar neste lote: 5000
INFO - Iniciando busca de 'ITAD LOOKUP' assíncrona para 5000 AppIDs com concorrência 3...
INFO - Busca assíncrona concluída.
INFO - 3245 sucesso(s) (64.90%), 1755 falha(s) (35.10%)
INFO - Obtidos 3,245 registros do ITAD
INFO - Inseridos/atualizados 3,245 registros no ITAD (itad_raw + steam_itad_mapping)
INFO - Registros inseridos no banco: 3,245
INFO - Processamento ITAD concluído com sucesso!
```
