# Especificação Completa do Projeto (Previsor Steam)

**Data da Especificação**: Agosto de 2026  
**Fase Atual**: Engenharia de Dados e Pipeline ML Concluídos (Fábrica de Modelos)

---

## 1. Visão Geral e Objetivo do Projeto
O **Previsor Steam** é um projeto de TCC com foco em Ciência de Dados e Engenharia de Machine Learning. Diferente de um sistema web tradicional, este repositório atua como uma **Fábrica de Dados (Data Factory)**. Seu papel é realizar a ingestão maciça de dados crus de múltiplas fontes, limpar, estruturar e, por fim, treinar modelos de Inteligência Artificial capazes de prever a direção e a data de variações de preços de jogos na plataforma Steam.

---

## 2. Processo de Coleta e Engenharia de Dados (Fase 1)

O módulo de coleta e persistência é a base do projeto, responsável por garantir a integridade e o volume de dados necessários para o aprendizado da máquina.

### 2.1 Fontes de Dados
- **Steam API & SteamSpy**: Coleta de metadados, gênero, preço original, reviews e detalhes técnicos. (Implementado mecanismo de fallback local).
- **ITAD (IsThereAnyDeal)**: Coleta do histórico cronológico completo das flutuações de preços dos jogos.

### 2.2 Arquitetura de Resiliência
Para suportar milhares de requisições e evitar interrupções:
- **Adaptive Batch Sizing**: O tamanho dos lotes de requisição (batch) aumenta ou diminui dinamicamente dependendo da taxa de sucesso da API, evitando banimentos por *Rate Limit (HTTP 429)*.
- **Progress Persistence (Checkpoints)**: O sistema salva o estado da fila no PostgreSQL de forma contínua. Em caso de queda de energia ou crash, o robô retoma o download do último ponto (Zero perda de processamento).
- **Connection Pooling**: Reutiliza conexões do banco de dados, reduzindo o overhead de infraestrutura e acelerando a gravação de dados em 30%.

### 2.3 ETL e Limpeza de Dados
- Normalização de nomenclaturas, remoção de caracteres inválidos.
- Transformação do JSONB cru extraído das APIs em tabelas relacionais organizadas (`steam_unificado`).
- Deduplicação de AppIDs na fila de processamento.

---

## 3. Pipeline de Machine Learning (Fase 2)

A fase "matemática" do projeto onde os dados normalizados são transformados em intuição e poder de predição.

### 3.1 Geração de Features (Feature Engineering)
Os dados brutos não são suficientes. O sistema constrói ativamente 18 *features* complexas para alimentar os algoritmos, tais como:
- Preço médio, máximo e mínimo dos últimos 180 dias.
- Dias desde o último desconto.
- Razão entre o preço atual e o mínimo histórico.

**Tratamento de Sazonalidade (A Grande Virada):**
Para remover o ponto cego do algoritmo sobre "épocas do ano", foi desenvolvido um motor matemático de datas (Unix Timestamp para Datetime):
- Extração do `mes_atual` e do `dia_do_ano`.
- **Cálculo de Distância Vetorial**: Cálculo automático de `dias_para_proxima_grande_promo` baseando-se no calendário das Big Four da Steam (Spring, Summer, Autumn e Winter Sale).

### 3.2 Modelagem de Classificação (O preço vai cair?)
- **Alvo**: "cai", "sobe" ou "mantém".
- **Horizontes**: Previsões divididas e isoladas em 30, 60 e 90 dias.
- **Tratativas**: Aplicação de balanceamento de classes (`class_weight="balanced"`) penalizando o algoritmo caso ele ignore os eventos de desconto (que são a minoria matemática dos dados diários da loja).
- **Modelos**: *XGBoost* e *Random Forest* assumiram a liderança, atingindo Acurácias de ~80% e F1-Scores superiores a 0.60.

### 3.3 Modelagem de Regressão (Faltam quantos dias?)
- **Alvo**: A distância exata, em dias numéricos inteiros, para o próximo desconto.
- **Tratativas**: Uso de *Clipping*. Limitou-se o espectro de predição a um teto máximo de 365 dias (1 ano), matando severamente os *outliers* ruidosos que forçavam regressões para milhares de dias irreais.
- **Modelos**: *XGBoost Regressor* consolidou a vitória derrubando o RMSE para menos de 39 dias.

---

## 4. Alinhamento ao Checklist Metodológico (Aurélien Géron)

A evolução do projeto seguiu categoricamente as etapas do `Checklist.md` da base do TCC:

1. **Abordar o Problema**: Definido o alvo do negócio de "predizer descontos para tomada de decisão no comércio de jogos".
2. **Obter os Dados**: Scripts robustos foram criados para varrer a Steam e ITAD. (Fase 1 Concluída).
3. **Explorar os Dados**: Uso de features estatísticas e agrupamentos (`mean`, `std`, `min`).
4. **Preparar os Dados**: A classe `NormalizarModelos` faz a conversão de timestamps, drop de colunas nulas, limpeza e injeção do vetor sazonal. (Fase 2 Concluída).
5. **Pré-selecionar Modelos**: Testes com LightGBM, XGBoost, Regressão Linear e Random Forest.
6. **Aperfeiçoar o Sistema**: Ajustes estruturais como *clipping de target* e *class weights*, com validação cruzada (CV temporal). (Fase 2 Concluída).
7. **Apresentar a Solução**: O modelo gera em disco matrizes de confusão (PNG), distribuições predito vs real (CSV) e logs métricos para análise.
8. **Implementar (Futuro)**: Como o sistema já produz os arquivos binários `.joblib`, a base técnica para a etapa produtiva está concretizada.

---

## 5. Próximos Passos e Futuro da Aplicação

Como a fábrica de dados e treinamento (backend pesado) cumpriu com todos os seus requisitos de forma resiliente, o futuro do projeto engloba a **Fase de Consumo / Produção (Inference)**:

1. **Microserviço de Inferência (O Bot)**
   - Um script isolado deste ecossistema pesado (provavelmente focado apenas no arquivo `bot.py` reestruturado).
   - Sua única responsabilidade será importar os artefatos `.joblib` mais recentes da pasta `resources/models`.
   - Ao receber o nome de um jogo, ele fará uma requisição *lightweight* para pegar os metadados atuais do jogo e fará o `model.predict()`, gerando a resposta instantaneamente para o usuário sem necessidade de treinamento.
2. **Plataforma de Acesso**
   - Criação de uma interface consumidora para os resultados do Bot (seja ela um Bot do Discord, Telegram ou Dashboard Web simples).
3. **Continuous Training (Opcional)**
   - Agendamento (via CronJob ou Github Actions) para rodar o orquestrador de treinamento mensalmente, garantindo que os modelos nunca fiquem obsoletos com as flutuações das regras econômicas mundiais.
