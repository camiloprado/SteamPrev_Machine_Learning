# 🎯 Inserção de Dados ITAD - Guia Rápido

## ✅ O QUE FOI CRIADO

### 4 Métodos PostgreSQL (`postgre.py`)

```python
# 1. Buscar AppIDs sem ITAD
PostgreSQL.buscar_appids_sem_itad(arg_intPcId=1, arg_intTotalPcs=1)
# → [123, 456, 789, ...]

# 2. Buscar AppIDs ITAD desatualizados
PostgreSQL.buscar_appids_itad_desatualizados(arg_intDiasAtualizacao=90, ...)
# → [321, 654, 987, ...]

# 3. Inserir ITAD em bulk (recomendado: até 1000 registros)
PostgreSQL.inserir_dados_itad_raw_bulk(arg_dictDadosItad)
# → 1000 (registros inseridos)

# 4. Inserir ITAD em lotes (grandes volumes)
PostgreSQL.inserir_dados_itad_raw_batched(arg_dictDadosItad, arg_intBatchSize=1000)
# → 5000 (total inserido)
```

### 1 Método Previsor (`previsor.py`)

```python
# Workflow completo automático
Previsor.alimentar_banco_dados_ITAD_docker()
# Busca → API ITAD → Insere PostgreSQL → Loop
```

---

## 📋 COMO USAR

### Opção 1: Via Bot (Automático)
```bash
python -m prj_TCC_PREVISOR_STEAM.bot
# Escolher opção: 3 - Alimentar banco ITAD Docker
```

### Opção 2: Manual (Python)
```python
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
import asyncio

# 1. Conectar
PostgreSQL.conectar()

# 2. Buscar AppIDs
appids = PostgreSQL.buscar_appids_sem_itad()[:100]  # 100 primeiros

# 3. Buscar dados ITAD
dados = asyncio.run(SteamClient.lookup_itad_ids_batched(appids))

# 4. Inserir no banco
inseridos = PostgreSQL.inserir_dados_itad_raw_bulk(dados)

# 5. Desconectar
PostgreSQL.desconectar()
```

### Opção 3: Teste Rápido
```bash
cd d:\Projeto_TCC_CC
python -m prj_TCC_PREVISOR_STEAM.classes.tests.test_itad_insert
# Testa com 10 AppIDs
```

---

## 🔧 CONFIGURAÇÃO (.env)

```bash
# Obrigatório
ITAD_API_KEY=sua_chave_aqui

# Opcional (valores padrão)
RANGE_PROCESSAMENTO_ITAD_RAW=5000  # Lote por iteração
PC_ID=1                             # ID deste PC
TOTAL_PCS=1                         # Total de PCs
AMBIENTE=PRD                        # PRD ou HML
```

---

## 📊 ESTRUTURA DE DADOS

### Entrada (API ITAD)
```python
{
    730: {
        "id": "app/730",
        "slug": "counter-strike-global-offensive",
        "title": "Counter-Strike: Global Offensive",
        "type": "game",
        "mature": False,
        "assets": {"banner": "https://..."}
    }
}
```

### Saída (PostgreSQL)
```
┌─────────────────┐
│   itad_raw      │  ← Dados completos ITAD
├─────────────────┤
│ id_itad (PK)    │  'app/730'
│ slug            │  'counter-strike-global-offensive'
│ title           │  'Counter-Strike: Global Offensive'
│ type            │  'game'
│ mature          │  false
│ assets (JSONB)  │  {"banner": "https://..."}
│ ultima_atual... │  2025-11-18 14:30:00
└─────────────────┘
         ▲
         │ (FK)
         │
┌─────────────────┐
│steam_itad_map..│  ← Mapeamento AppID ↔ ITAD
├─────────────────┤
│ appid (PK)      │  730
│ id_itad (FK)    │  'app/730'
│ slug            │  'counter-strike-global-offensive'
│ title           │  'Counter-Strike: Global Offensive'
└─────────────────┘
```

---

## ✅ CHECKLIST

Antes de executar:
- [ ] PostgreSQL rodando (Docker supabase-db)
- [ ] Tabela `steam_generico` populada
- [ ] Tabela `steam_bd` populada
- [ ] Tabelas `itad_raw` e `steam_itad_mapping` criadas
- [ ] `ITAD_API_KEY` configurada no `.env`

Para executar:
- [ ] Executar `Previsor.alimentar_banco_dados_ITAD_docker()` ou bot.py opção 3
- [ ] Acompanhar logs (sucesso%, falhas, não encontrados)
- [ ] Verificar no PostgreSQL: `SELECT COUNT(*) FROM steam_itad_mapping;`

---

## 🧪 VERIFICAÇÃO

```sql
-- Quantos AppIDs ainda sem ITAD?
SELECT COUNT(*) 
FROM steam_bd sb
LEFT JOIN steam_itad_mapping sim ON sb.appid = sim.appid
WHERE sim.appid IS NULL;

-- Últimas inserções
SELECT sim.appid, ir.title, ir.ultima_atualizacao
FROM steam_itad_mapping sim
JOIN itad_raw ir ON sim.id_itad = ir.id_itad
ORDER BY sim.created_at DESC
LIMIT 10;

-- Total de registros
SELECT 
    (SELECT COUNT(*) FROM itad_raw) AS itad_raw,
    (SELECT COUNT(*) FROM steam_itad_mapping) AS mapping;
```

---

## 📁 ARQUIVOS

### Código Python
- `classes/SQL/postgre.py` (linhas 859-977)
- `classes/scripts/previsor.py` (linhas 454-537)
- `classes/tests/test_itad_insert.py` (teste completo)

### SQL
- `resources/docs/create_steam_itad_mapping.sql` (criar tabelas)
- `resources/docs/test_itad_insert.sql` (testes manuais)

### Documentação
- `resources/docs/ITAD_Docker_Guide.md` (guia completo)
- `resources/docs/RESUMO_METODOS_ITAD.md` (resumo técnico)
- `resources/docs/QUICK_START_ITAD.md` (este arquivo)

---

## 🚀 COMEÇAR AGORA

```bash
# 1. Ativar ambiente
cd d:\Projeto_TCC_CC
.\.venv\Scripts\Activate.ps1

# 2. Executar bot
python -m prj_TCC_PREVISOR_STEAM.bot

# 3. Escolher opção 3

# Ou executar teste:
python -m prj_TCC_PREVISOR_STEAM.classes.tests.test_itad_insert
```

---

## 📈 LOGS ESPERADOS

```
INFO - Buscando AppIDs sem dados ITAD (PC 1/1)...
INFO - Encontrados 10,090 AppIDs sem dados ITAD
INFO - Total final de AppIDs a processar ITAD (PC 1): 10,090
INFO - Processando aplicativos ITAD de 1 a 5000 de 10090
INFO - Número de IDs ITAD a processar neste lote: 5000
INFO - Iniciando busca de 'ITAD LOOKUP' assíncrona para 5000 AppIDs...
INFO - 3245 sucesso(s) (64.90%), 1755 falha(s) (35.10%)
INFO - Obtidos 3,245 registros do ITAD
INFO - Inseridos/atualizados 3,245 registros no ITAD
INFO - Registros inseridos no banco: 3,245
```

**Taxa de sucesso típica:** 60-70% (nem todos os jogos estão no ITAD)

---

## ❓ FAQ

**P: Por que alguns jogos não são encontrados no ITAD?**  
R: ITAD é focado em jogos comerciais. Jogos gratuitos, demos, ferramentas não aparecem.

**P: Posso rodar em múltiplos PCs?**  
R: Sim! Configure `PC_ID` e `TOTAL_PCS` no `.env` de cada máquina.

**P: Quanto tempo leva para processar 10.000 AppIDs?**  
R: ~30-60 minutos (depende da API ITAD e taxa de sucesso).

**P: E se der timeout?**  
R: Use `inserir_dados_itad_raw_batched()` ou reduza `RANGE_PROCESSAMENTO_ITAD_RAW`.

**P: Como atualizar dados antigos?**  
R: `buscar_appids_itad_desatualizados()` já é chamado automaticamente (>90 dias).
