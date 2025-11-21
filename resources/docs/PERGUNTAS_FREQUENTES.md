# 📖 Guia Rápido: Perguntas e Respostas

## ❓ Perguntas Frequentes sobre o Previsor Steam

### 1. **O que o sistema faz?**
O Previsor Steam coleta automaticamente dados de jogos da plataforma Steam (detalhes, preços, avaliações) e armazena em um banco de dados PostgreSQL para análises e estudos.

### 2. **Por que foi criado?**
Foi desenvolvido como Trabalho de Conclusão de Curso (TCC) em Ciência da Computação para demonstrar coleta de dados em larga escala, integração com APIs externas e processamento assíncrono.

### 3. **Quais dados são coletados?**
- Nome do jogo, desenvolvedores, distribuidores
- Categorias, gêneros, idiomas suportados
- Preços atuais e histórico de promoções
- Avaliações (reviews positivas/negativas)
- Classificação etária, data de lançamento
- Score do Metacritic

### 4. **De onde vêm os dados?**
- **Steam Web API**: Informações oficiais dos jogos
- **IsThereAnyDeal (ITAD)**: Histórico de preços e promoções

### 5. **Quantos jogos o sistema pode processar?**
O sistema é otimizado para processar dezenas de milhares de jogos. Com a arquitetura multi-PC, pode escalar ainda mais.

### 6. **Quanto tempo leva para coletar dados?**
Depende do volume e da configuração:
- **1.000 jogos**: ~2-4 horas
- **10.000 jogos**: ~1-2 dias
- **50.000+ jogos**: ~1 semana (single PC) ou ~1-2 dias (multi-PC)

*Tempos variam com rate limits de API e delays configurados.*

### 7. **O sistema precisa rodar continuamente?**
Não. Você pode:
- Executar uma vez para coleta inicial
- Agendar execuções periódicas (semanal/mensal)
- Rodar sob demanda quando precisar de dados atualizados

### 8. **Pode coletar dados de jogos específicos?**
Sim! Você pode:
- Filtrar por lista de AppIDs
- Buscar apenas jogos sem dados
- Atualizar apenas jogos desatualizados (> 90 dias)

### 9. **Como os dados são organizados?**
Em duas camadas:
- **Raw (bruto)**: Dados originais das APIs (JSON)
- **Processed (processado)**: Dados limpos e normalizados

### 10. **Posso usar para fins comerciais?**
Não. É um projeto acadêmico e sem fins lucrativos. Os dados coletados devem respeitar os Termos de Uso da Steam e ITAD.

## 🔍 Casos de Uso Comuns

### **Caso 1: Primeira Execução**
**Objetivo**: Coletar dados iniciais de todos os jogos  
**Como fazer**: Execute `python prj_TCC_PREVISOR_STEAM/bot.py`  
**Resultado**: Banco de dados populado com dados de jogos

### **Caso 2: Atualizar Preços ITAD**
**Objetivo**: Atualizar histórico de preços desatualizado  
**Como fazer**: Use o método `alimentar_banco_dados_ITAD_docker()`  
**Resultado**: Dados ITAD atualizados para jogos > 90 dias

### **Caso 3: Coleta Distribuída**
**Objetivo**: Acelerar coleta com múltiplos PCs  
**Como fazer**: Configure `PC_ID` e `TOTAL_PCS` em cada máquina  
**Resultado**: Cada PC processa uma parte dos jogos

### **Caso 4: Análise de Dados**
**Objetivo**: Estudar tendências de mercado  
**Como fazer**: Consulte o PostgreSQL com queries SQL  
**Resultado**: Insights sobre preços, gêneros, desenvolvedores

## 🛠️ Comandos Básicos

### Iniciar o Sistema
```bash
# Ativar ambiente virtual
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Executar bot principal
python prj_TCC_PREVISOR_STEAM/bot.py
```

### Verificar Logs
```bash
# Ver logs de execução
cat prj_TCC_PREVISOR_STEAM/resources/logs/execucao_YYYY-MM-DD.log

# Ver erros
cat prj_TCC_PREVISOR_STEAM/resources/logs/erros_YYYY-MM-DD.log
```

### Consultar Dados
```sql
-- Contar jogos coletados
SELECT COUNT(*) FROM steam_games_raw;

-- Jogos mais bem avaliados
SELECT nome, review_score 
FROM steam_games_processed 
ORDER BY review_score DESC 
LIMIT 10;

-- Histórico de preços
SELECT appid, preco, data_preco 
FROM itad_historico_raw 
WHERE appid = 123456 
ORDER BY data_preco DESC;
```

## 📚 Documentação Completa

Para informações detalhadas, consulte:

- **[O Que o Sistema Faz](O_QUE_O_SISTEMA_FAZ.md)**: Explicação completa do sistema
- **[Arquitetura do Sistema](ARQUITETURA_SISTEMA.md)**: Diagramas e componentes técnicos
- **[Quick Start ITAD](QUICK_START_ITAD.md)**: Guia rápido de inserção de dados ITAD
- **[Guia de Instalação](GUIA_INSTALACAO_OUTRO_PC.md)**: Como instalar em outro PC
- **[Configuração Multi-PC](CONFIGURACAO_MULTI_PC.md)**: Setup para coleta distribuída

## 💡 Dicas e Boas Práticas

### ✅ Faça
- Configure delays adequados para respeitar rate limits
- Monitore logs regularmente para identificar problemas
- Faça backups regulares do banco de dados
- Use ambiente virtual Python
- Configure variáveis de ambiente (.env)

### ❌ Evite
- Executar múltiplas instâncias no mesmo PC sem coordenação
- Ignorar erros de API sem investigar
- Coletar mesmos dados repetidamente (desperdício)
- Expor credenciais de banco de dados
- Desrespeitar limites de APIs

## 🆘 Solução de Problemas

### Erro: "API Rate Limit Exceeded"
**Solução**: Aumente o delay entre requisições em `AllSettings.py`

### Erro: "Connection to PostgreSQL failed"
**Solução**: Verifique se o PostgreSQL está rodando e credenciais estão corretas

### Erro: "No data returned from Steam API"
**Solução**: Verifique sua conexão com internet e chave de API

### Sistema muito lento
**Solução**: 
- Reduza tamanho dos batches
- Aumente delays (paradoxalmente, pode melhorar throughput)
- Use multi-PC para paralelizar

### Dados duplicados no banco
**Solução**: Use queries com `ON CONFLICT DO NOTHING` ou `UPSERT`

## 📞 Contato e Suporte

Este é um projeto acadêmico. Para dúvidas:
- Revise a documentação completa
- Verifique os logs de erro
- Consulte o código-fonte (bem documentado)

---

> **Guia Rápido - Previsor Steam**  
> Última atualização: 2025
