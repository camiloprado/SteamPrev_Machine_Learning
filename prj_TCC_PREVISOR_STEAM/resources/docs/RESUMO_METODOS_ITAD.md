# Métodos de Inserção ITAD - Resumo Executivo

## ✅ Métodos Criados

### 📁 postgre_itad.py (`PostgreSQLITAD`)

#### 1. `inserir_dados_itad_raw_bulk(arg_dictDadosItad: dict) -> None`
**Função:** Insere dados ITAD em bulk (uma transação)

**Parâmetros:**
- `arg_dictDadosItad` (dict): `{appid: {"id": str, "slug": str, "title": str, ...}}`

**Retorna:** None (persistência via upsert `ON CONFLICT`)

**O que faz:**
1. Insere/atualiza `itad_raw` (id_itad, slug, title, type, mature, assets, ultima_atualizacao)
2. Insere/atualiza `steam_itad_mapping` (appid, id_itad, slug, title)
3. Usa `ON CONFLICT` para upsert automático
4. Commit único ao final

**Exemplo:**
```python
var_dictDados = {
    730: {"id": "app/730", "slug": "csgo", "title": "CS:GO", "type": "game", "mature": False}
}
PostgreSQLITAD.inserir_dados_itad_raw_bulk(var_dictDados)
```

---

#### 2. `inserir_dados_itad_raw_batched(arg_dictDadosItad: dict, arg_intBatchSize: int = 1000) -> None`
**Função:** Divide inserção em lotes para evitar timeout

**Parâmetros:**
- `arg_dictDadosItad` (dict): Mesma estrutura acima
- `arg_intBatchSize` (int): Tamanho do lote (padrão: 1000)

**Retorna:** None

**O que faz:**
1. Divide `arg_dictDadosItad` em lotes de `arg_intBatchSize`
2. Chama `inserir_dados_itad_raw_bulk()` para cada lote
3. Pausa 1 segundo entre lotes
4. Não retorna contagem (side-effect no banco)

**Exemplo:**
```python
var_dictGrande = {1: {...}, 2: {...}, ..., 5000: {...}}  # 5000 registros
var_int = PostgreSQLITAD.inserir_dados_itad_raw_batched(var_dictGrande, arg_intBatchSize=1000)
# Processa: 1000 + 1000 + 1000 + 1000 + 1000 = 5000
```

---

#### 3. `buscar_appids_sem_itad(arg_intLimit: int = None) -> list[int]`
**Função:** Retorna AppIDs de `steam_generico` que não estão em `steam_itad_mapping`

**SQL:**
```sql
SELECT sg.appid
FROM steam_generico sg
LEFT JOIN steam_itad_mapping sim ON sg.appid = sim.appid
WHERE sim.appid IS NULL
ORDER BY sg.appid;
```

**Exemplo:**
```python
var_list = PostgreSQLITAD.buscar_appids_sem_itad(arg_intLimit=100)
# Retorna: [123, 456, 789, 1011, ...]
```

---

#### 4. `buscar_appids_itad_desatualizados(arg_intDiasAtualizacao: int = 90, ...) -> list[int]`
**Função:** Retorna AppIDs com ITAD desatualizado (>90 dias)

**SQL:**
```sql
SELECT sim.appid 
FROM steam_itad_mapping sim
JOIN itad_raw ir ON sim.id_itad = ir.id_itad
WHERE ir.ultima_atualizacao < NOW() - INTERVAL '90 days'
AND MOD(sim.appid, TOTAL_PCS) = PC_ID - 1;
```

**Exemplo:**
```python
var_list = PostgreSQLITAD.buscar_appids_itad_desatualizados(arg_intDiasAtualizacao=90)
# Retorna: [321, 654, 987, ...]
```

---

### 📁 previsor.py

#### 5. `alimentar_banco_dados_ITAD_docker()`
**Função:** Workflow completo de alimentação ITAD no PostgreSQL Docker

**Fluxo:**
1. Busca AppIDs sem ITAD (`buscar_appids_sem_itad`)
2. Busca AppIDs desatualizados (`buscar_appids_itad_desatualizados`)
3. Combina listas (remove duplicatas)
4. Processa em lotes de `RANGE_PROCESSAMENTO_ITAD_RAW` (env)
5. Para cada lote:
   - Chama `ITADClient.lookup_itad_ids_batched()` (`games/lookup/v1`)
   - Chama `PostgreSQLITAD.inserir_dados_itad_raw_bulk()` (insere banco)
   - Pausa 2 segundos
6. Log de progresso

**Variáveis .env:**
- `RANGE_PROCESSAMENTO_ITAD_RAW=5000`: Lote por iteração
- `PC_ID=1`: ID deste PC
- `TOTAL_PCS=1`: Total de PCs
- `AMBIENTE=PRD`: PRD ou HML
- `BATCH_TESTE=20`: Limite em HML

**Uso:**
```python
# Via bot.py - Opção 3
Previsor.alimentar_banco_dados_ITAD_docker()
```

---

## 🔄 Fluxo de Dados Completo

```
1. Previsor.alimentar_banco_dados_ITAD_docker()
   ↓
2. PostgreSQLITAD.buscar_appids_sem_itad() → [123, 456, 789]
   ↓
3. PostgreSQLITAD.buscar_appids_itad_desatualizados() → [321, 654]
   ↓
4. Combina: [123, 456, 789, 321, 654]
   ↓
5. Loop por lotes (RANGE_PROCESSAMENTO_ITAD_RAW):
   ├─ ITADClient.lookup_itad_ids_batched([123, 456, ...])
   │  └─ API ITAD → {"123": {"id": "app/123", ...}, ...}
   │
   ├─ PostgreSQLITAD.inserir_dados_itad_raw_bulk({"123": {...}})
   │  ├─ INSERT INTO itad_raw ...
   │  └─ INSERT INTO steam_itad_mapping ...
   │
   └─ sleep(2)
   ↓
6. Fim
```

---

## 📊 Tabelas Afetadas

### itad_raw
```sql
CREATE TABLE itad_raw (
    id_itad VARCHAR PRIMARY KEY,              -- 'app/730'
    slug VARCHAR,                              -- 'counter-strike-global-offensive'
    title VARCHAR,                             -- 'Counter-Strike: Global Offensive'
    type VARCHAR,                              -- 'game', 'dlc', 'bundle'
    mature BOOLEAN,                            -- false
    assets JSONB,                              -- {"banner": "https://..."}
    ultima_atualizacao TIMESTAMP,              -- NOW()
    historico_preco JSONB                      -- (não usado ainda)
);
```

### steam_itad_mapping
```sql
CREATE TABLE steam_itad_mapping (
    appid INTEGER PRIMARY KEY,                 -- 730
    id_itad VARCHAR NOT NULL,                  -- 'app/730' (FK → itad_raw)
    slug VARCHAR,                              -- 'counter-strike-global-offensive'
    title VARCHAR,                             -- 'Counter-Strike: Global Offensive'
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (appid) REFERENCES steam_generico(appid),
    FOREIGN KEY (id_itad) REFERENCES itad_raw(id_itad)
);
```

---

## 🧪 Como Testar

### Teste 1: Inserção Manual
```python
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_itad import PostgreSQLITAD

PostgreSQLITAD.conectar()

var_dictTeste = {
    730: {
        "id": "app/730",
        "slug": "counter-strike-global-offensive",
        "title": "Counter-Strike: Global Offensive",
        "type": "game",
        "mature": False,
        "assets": {"banner": "https://example.com/csgo.jpg"}
    }
}

var_int = PostgreSQLITAD.inserir_dados_itad_raw_bulk(var_dictTeste)
print(f"Inseridos: {var_int}")  # Esperado: None

PostgreSQLITAD.desconectar()
```

### Teste 2: Workflow Completo (HML)
```bash
# .env
AMBIENTE=HML
BATCH_TESTE=5
RANGE_PROCESSAMENTO_ITAD_RAW=10
PC_ID=1
TOTAL_PCS=1
```

```python
# bot.py - Opção 3
Previsor.alimentar_banco_dados_ITAD_docker()
# Processa apenas 5 AppIDs (BATCH_TESTE)
```

### Teste 3: Multi-PC
```bash
# PC 1
PC_ID=1
TOTAL_PCS=2

# PC 2
PC_ID=2
TOTAL_PCS=2
```

Cada PC processa `MOD(appid, 2) = PC_ID - 1`:
- PC 1: AppIDs pares (0, 2, 4, 6, ...)
- PC 2: AppIDs ímpares (1, 3, 5, 7, ...)

---

## 📝 Verificação SQL

```sql
-- Contar registros
SELECT 
    (SELECT COUNT(*) FROM itad_raw) AS itad_raw_count,
    (SELECT COUNT(*) FROM steam_itad_mapping) AS mapping_count;

-- Últimas inserções
SELECT id_itad, title, ultima_atualizacao 
FROM itad_raw 
ORDER BY ultima_atualizacao DESC 
LIMIT 5;

-- Verificar mapeamento
SELECT sim.appid, sim.id_itad, ir.title
FROM steam_itad_mapping sim
JOIN itad_raw ir ON sim.id_itad = ir.id_itad
LIMIT 5;

-- Jogos sem ITAD ainda
SELECT COUNT(*) 
FROM steam_bd sb
LEFT JOIN steam_itad_mapping sim ON sb.appid = sim.appid
WHERE sim.appid IS NULL;
```

---

## ⚠️ Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| Foreign key violation (steam_generico) | AppID não existe em steam_generico | Rodar `alimentar_banco_dados_steam_generico()` primeiro |
| Foreign key violation (itad_raw) | Tentou inserir mapping antes de itad_raw | Ordem correta: 1º itad_raw, 2º mapping (método já faz isso) |
| column ir.appid does not exist | Query antiga sem steam_itad_mapping | ✅ Corrigido nas queries |
| ITAD_API_KEY não definido | Falta chave no .env | Adicionar `ITAD_API_KEY=xxx` |
| Timeout no bulk insert | Muitos registros | Usar `inserir_dados_itad_raw_batched()` |

---

## 🎯 Checklist de Uso

- [ ] Tabela `steam_generico` populada (AppIDs base)
- [ ] Tabela `steam_generico` populada (dados steam)
- [ ] Tabela `itad_raw` criada (`create_steam_itad_mapping.sql`)
- [ ] Tabela `steam_itad_mapping` criada
- [ ] `.env` configurado (`ITAD_API_KEY`, `RANGE_PROCESSAMENTO_ITAD_RAW`)
- [ ] Executar `Previsor.alimentar_banco_dados_ITAD_docker()`
- [ ] Verificar logs (sucesso%, erros HTTP, não encontrados)
- [ ] Validar no PostgreSQL (contagem, últimas inserções)

---

## 📦 Arquivos Criados

1. **postgre_itad.py** (`PostgreSQLITAD`):
   - `inserir_dados_itad_raw_bulk()`
   - `inserir_dados_itad_raw_batched()`
   - `buscar_appids_sem_itad()`
   - `buscar_appids_itad_desatualizados()`

2. **itad_api.py** (`ITADClient`):
   - `lookup_itad_ids_batched()` — `games/lookup/v1`
   - histórico — `games/history/v2`

3. **previsor.py**:
   - `alimentar_banco_dados_ITAD_docker()`

4. **SQL**:
   - `resources/SQL/test_itad_insert.sql`

5. **Documentação**:
   - `ITAD_Docker_Guide.md` (guia completo)
   - `RESUMO_METODOS_ITAD.md` (este arquivo)
