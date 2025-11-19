# 🖥️ Configuração Multi-PC para Coleta Paralela

## 📋 Visão Geral

Este sistema permite que **2 PCs coletem dados da Steam simultaneamente**, dobrando a velocidade de processamento:
- **PC 1**: Processa 50% dos AppIDs + Executa modelo de previsão
- **PC 2**: Processa 50% dos AppIDs (apenas coleta)

## 🚀 Nova Versão: OTIMIZADA para 280k Registros

### **⚡ Melhorias Implementadas:**
- ✅ **Consultas SQL eficientes** (LEFT JOIN no banco)
- ✅ **Sem timeout**: Não carrega 280k registros na memória
- ✅ **90% menos memória**: Transfere apenas IDs
- ✅ **12x mais rápido**: 2-5s em vez de 30-60s
- ✅ **Divisão automática**: Filtro de PC aplicado no SQL

📖 **Veja detalhes técnicos em:** `OTIMIZACAO_CONSULTAS_SQL.md`

## ⚙️ Como Funciona

### Divisão Automática de Trabalho
```
Total de AppIDs: 71.106 jogos
├── PC 1 (índices pares): 0, 2, 4, 6, 8... = ~35.553 jogos
└── PC 2 (índices ímpares): 1, 3, 5, 7, 9... = ~35.553 jogos
```

### Arquitetura de Dados
```
┌─────────────────────────────────────────────────────┐
│ PC 1                    │ PC 2                      │
├─────────────────────────┼───────────────────────────┤
│ Docker PostgreSQL       │ Docker PostgreSQL         │
│ (steam_raw local)       │ (steam_raw local)         │
│         │               │         │                 │
│         └───────────────┴─────────┘                 │
│                    │                                │
│                    ↓                                │
│        ┌──────────────────────┐                     │
│        │  SUPABASE CLOUD      │                     │
│        │  (Centralizado)      │                     │
│        │  • steam_bd          │                     │
│        │  • steam_generico    │                     │
│        └──────────────────────┘                     │
│                    │                                │
│                    ↓                                │
│        ┌──────────────────────┐                     │
│        │ MODELO PREVISÃO      │                     │
│        │ (apenas PC 1)        │                     │
│        └──────────────────────┘                     │
└─────────────────────────────────────────────────────┘
```

## 🚀 Configuração Passo a Passo

### **PC 1 (Principal)**

1. **Configure o .env**
   ```env
   PC_ID=1
   TOTAL_PCS=2
   ```

2. **Execute o bot normalmente**
   ```bash
   python prj_TCC_PREVISOR_STEAM/bot.py
   ```

3. **Logs esperados:**
   ```
   ============================================================
   MODO MULTI-PC ATIVADO: PC 1 de 2
   ============================================================
   DIVISÃO DE TRABALHO:
   Total de AppIDs disponíveis: 71,106
   AppIDs atribuídos ao PC 1: 35,553
   Percentual deste PC: 50.0%
   ============================================================
   ```

---

### **PC 2 (Auxiliar)**

1. **Copie o arquivo de exemplo**
   ```bash
   cp .env.pc2.example .env
   ```

2. **Verifique o .env**
   ```env
   PC_ID=2          # ← Este é o PC 2
   TOTAL_PCS=2      # ← Total de 2 PCs
   
   # ⚠️ IMPORTANTE: Mesmas credenciais Supabase do PC 1
   SUPABASE_URL=https://norphjcxnsgklyutnmin.supabase.co
   SUPABASE_KEY=eyJhbGci...
   ```

3. **Execute o bot**
   ```bash
   python prj_TCC_PREVISOR_STEAM/bot.py
   ```

4. **Logs esperados:**
   ```
   ============================================================
   MODO MULTI-PC ATIVADO: PC 2 de 2
   ============================================================
   DIVISÃO DE TRABALHO:
   Total de AppIDs disponíveis: 71,106
   AppIDs atribuídos ao PC 2: 35,553
   Percentual deste PC: 50.0%
   ============================================================
   ```

## 📊 Performance Esperada

| Configuração | AppIDs/min | Tempo Total (71.106 jogos) |
|--------------|------------|----------------------------|
| 1 PC         | ~45        | ~26 horas                  |
| **2 PCs**    | **~90**    | **~13 horas** ⚡           |

## ✅ Checklist de Configuração

### PC 1 (Principal)
- [ ] Docker instalado e rodando
- [ ] PostgreSQL container ativo (`docker-compose up -d`)
- [ ] `.env` configurado com `PC_ID=1` e `TOTAL_PCS=2`
- [ ] Credenciais Supabase corretas
- [ ] Python 3.10+ instalado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)

### PC 2 (Auxiliar)
- [ ] Docker instalado e rodando
- [ ] PostgreSQL container ativo (`docker-compose up -d`)
- [ ] `.env` configurado com `PC_ID=2` e `TOTAL_PCS=2`
- [ ] **MESMAS** credenciais Supabase do PC 1
- [ ] Python 3.10+ instalado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)

## 🔍 Validação

### Teste se a divisão está funcionando

Execute em ambos os PCs e compare os logs:

**PC 1 deve mostrar:**
```
AppIDs atribuídos ao PC 1: 35,553
```

**PC 2 deve mostrar:**
```
AppIDs atribuídos ao PC 2: 35,553
```

### Verifique o Supabase

Acesse o Supabase Dashboard e confirme que:
- Dados estão sendo inseridos de ambos os PCs
- Não há duplicação de AppIDs (cada jogo aparece apenas 1x)

## ⚠️ Importante

### ✅ O que você DEVE fazer:
- Usar as **mesmas credenciais Supabase** em ambos os PCs
- Executar ambos os bots **simultaneamente** para máxima eficiência
- Monitorar logs para garantir que não há erros

### ❌ O que você NÃO deve fazer:
- Alterar `PC_ID` depois de iniciar o processamento
- Usar credenciais Supabase diferentes entre PCs
- Processar com `TOTAL_PCS=1` em um PC e `TOTAL_PCS=2` em outro

## 🛠️ Troubleshooting

### "Nenhum AppID sendo processado"
- Verifique se `PC_ID` e `TOTAL_PCS` estão corretos
- Confirme que há AppIDs não processados no `steam_generico`

### "Dados duplicados no Supabase"
- Certifique-se de que ambos os PCs têm `TOTAL_PCS=2`
- Verifique se os `PC_ID` são diferentes (1 e 2)

### "PC 2 não está fazendo nada"
- Confirme que o `.env` do PC 2 tem `PC_ID=2`
- Verifique se o PostgreSQL está rodando (`docker ps`)

## 📈 Monitoramento

### Acompanhe o progresso em tempo real

**PC 1:**
```bash
tail -f logs/bot_*.log | grep "Progresso:"
```

**PC 2:**
```bash
tail -f logs/bot_*.log | grep "Progresso:"
```

## 🎯 Próximos Passos (Modelo de Previsão)

Após a coleta completa:

1. **PC 1** terá todos os dados no Supabase
2. Desenvolver modelo de previsão que lê do Supabase
3. Executar modelo apenas no **PC 1**
4. **PC 2** pode ser desligado (coleta finalizada)

## 💡 Dicas

### Acelerar ainda mais a coleta
Ajuste no `.env` (ambos PCs):
```env
# Aumentar concorrência de reviews
STEAM_ASYNC_CONCURRENCY_REVIEWS=15

# Reduzir delay entre batches (cuidado: pode causar rate limiting)
STEAM_DELAY_BETWEEN_BATCHES_REVIEWS=20
```

### Modo de teste
Para testar com poucos jogos primeiro:
```env
AMBIENTE=HML
BATCH_TESTE=10
```

---

## 📞 Suporte

Se encontrar problemas, verifique:
1. Logs em `logs/bot_*.log`
2. Container PostgreSQL: `docker-compose logs db`
3. Conexão Supabase: `python -c "from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB; print('OK' if SupabaseDB._var_clientSupabase else 'ERRO')"`
