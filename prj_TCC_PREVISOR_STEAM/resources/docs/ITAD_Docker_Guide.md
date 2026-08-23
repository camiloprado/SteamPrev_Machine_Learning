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

### 1. PostgreSQLITAD (postgre_itad.py)

#### Consulta
```python
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_itad import PostgreSQLITAD

# Busca AppIDs sem dados ITAD (steam_generico sem mapeamento)
var_listNovos = PostgreSQLITAD.buscar_appids_sem_itad(arg_intLimit=100)
# Retorna: [123, 456, 789, ...]

# Busca AppIDs com ITAD desatualizado (multi-PC)
var_listDesatualizados = PostgreSQLITAD.buscar_appids_itad_desatualizados(
    arg_intDiasAtualizacao=90,
    arg_intPcId=1,
    arg_intTotalPcs=1
)
# Retorna: [321, 654, 987, ...]
```

#### Inserção
```python
var_dictDados = {
    730: {
        "id": "app/730",
        "slug": "counter-strike-global-offensive",
        "title": "Counter-Strike: Global Offensive",
        "type": "game",
        "mature": False,
        "assets": {"banner": "https://..."}
    },
}

PostgreSQLITAD.inserir_dados_itad_raw_bulk(var_dictDados)
# Upsert em: itad_raw + steam_itad_mapping

PostgreSQLITAD.inserir_dados_itad_raw_batched(
    arg_dictDadosItad=var_dictGrande,
    arg_intBatchSize=1000
)
```

### 2. ITADClient (itad_api.py)

#### Busca ITAD API (`games/lookup/v1`)
```python
import asyncio
from prj_TCC_PREVISOR_STEAM.classes.api.itad_api import ITADClient

var_listAppIDs = [730, 570, 440, 10, 20]

var_dictResultados = asyncio.run(
    ITADClient.lookup_itad_ids_batched(arg_seqAppids=var_listAppIDs)
)
```

### 3. Previsor (previsor.py)

#### Workflow Completo
```python
# Execução automática via bot.py
# Opção 3: Alimentar banco de dados ITAD Docker

Previsor.alimentar_banco_dados_ITAD_docker()

# Fluxo interno:
# 1. Busca AppIDs sem ITAD (steam_generico - steam_itad_mapping)
# 2. Busca AppIDs ITAD desatualizados (>90 dias)
# 3. Processa em lotes de RANGE_PROCESSAMENTO_ITAD_RAW (default: 5000)
# 4. Para cada lote:
#    - Chama ITADClient.lookup_itad_ids_batched()
#    - Insere via PostgreSQLITAD.inserir_dados_itad_raw_bulk()
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
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_itad import PostgreSQLITAD
from prj_TCC_PREVISOR_STEAM.classes.api.itad_api import ITADClient
import asyncio

# 1. Conectar ao banco
PostgreSQLITAD.conectar()

# 2. Buscar AppIDs que precisam de dados ITAD
var_listAppIDs = PostgreSQLITAD.buscar_appids_sem_itad(arg_intLimit=100)
print(f"AppIDs sem ITAD: {len(var_listAppIDs)}")

# 3. Processar em lote pequeno (exemplo: 100)
var_listLote = var_listAppIDs[:100]

# 4. Buscar dados na API ITAD
var_dictDados = asyncio.run(ITADClient.lookup_itad_ids_batched(var_listLote))
print(f"Dados obtidos: {len(var_dictDados)}")

# 5. Inserir no banco
PostgreSQLITAD.inserir_dados_itad_raw_bulk(var_dictDados)

# 6. Desconectar
PostgreSQLITAD.desconectar()
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
