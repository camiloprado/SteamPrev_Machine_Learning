from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.base import BaseEstimator, TransformerMixin
import pandas as pd
import numpy as np
import logging
import joblib
import os
import time
import gc
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

@contextmanager
def timer_context(arg_strNomeOperacao: str):
    """
    Context manager para medir tempo de execução de operações.
    
    Parâmetros:
    - arg_strNomeOperacao (str): Nome da operação para log
    """
    var_floatInicio = time.time()
    logger.info(f"Iniciando: {arg_strNomeOperacao}")
    try:
        yield
    finally:
        var_floatDuracao = time.time() - var_floatInicio
        logger.info(f"Concluído: {arg_strNomeOperacao} em {var_floatDuracao:.2f} segundos")

class MultiLabelBinarizerTransformer(BaseEstimator, TransformerMixin):
    """
    Transformador customizado para colunas com múltiplos valores separados por vírgula.
    Cria uma coluna binária para cada valor único encontrado.
    """
    
    def __init__(self, arg_intMaxFeatures=50, arg_intMinFreq=10):
        """
        Parâmetros:
        - arg_intMaxFeatures (int): Número máximo de features a serem criadas
        - arg_intMinFreq (int): Frequência mínima para incluir uma categoria
        """
        self.arg_intMaxFeatures = arg_intMaxFeatures
        self.arg_intMinFreq = arg_intMinFreq
        self.var_listCategories_ = None
    
    def fit(self, arg_pdX, y=None):
        """
        Identifica as categorias mais comuns na coluna.
        
        Parâmetros:
        - arg_pdX (pd.DataFrame ou pd.Series): Coluna a ser analisada
        - y: Ignorado, presente para compatibilidade

        Retorna:
        - self
        """
        # Normalizar entrada para array 2D
        if isinstance(arg_pdX, pd.Series):
            var_arrayValues = arg_pdX.values.reshape(-1, 1)
        elif isinstance(arg_pdX, pd.DataFrame):
            var_arrayValues = arg_pdX.values
        else:
            var_arrayValues = arg_pdX
        
        # Conta frequência de cada categoria
        var_dictCategoryCounts = {}
        for row in var_arrayValues:
            if pd.notna(row[0]) and row[0] != "" and str(row[0]).strip() != "":
                # Limpar e separar itens, removendo espaços e vazios
                var_listItems = [var_strItem.strip() for var_strItem in str(row[0]).split(",") if var_strItem.strip()]
                for var_strItem in var_listItems:
                    if var_strItem:  # Garantir que não está vazio
                        var_dictCategoryCounts[var_strItem] = var_dictCategoryCounts.get(var_strItem, 0) + 1
        
        # Seleciona categorias mais frequentes
        var_listSortedCategories = sorted(var_dictCategoryCounts.items(), key=lambda x: x[1], reverse=True)
        self.var_listCategories_ = [
            cat for cat, var_intCount in var_listSortedCategories 
            if var_intCount >= self.arg_intMinFreq
        ][:self.arg_intMaxFeatures]
        
        logger.info(f"MultiLabelBinarizer: {len(self.var_listCategories_)} categorias selecionadas")
        if len(self.var_listCategories_) > 0:
            logger.debug(f"  Top 5 categorias: {self.var_listCategories_[:5]}")
        else:
            logger.warning(f"  Nenhuma categoria encontrada (min_freq={self.arg_intMinFreq}, total_unique={len(var_dictCategoryCounts)})")
            if len(var_dictCategoryCounts) > 0:
                # Mostrar o que foi encontrado
                var_listTop = sorted(var_dictCategoryCounts.items(), key=lambda x: x[1], reverse=True)[:3]
                logger.debug(f"  Categorias mais comuns encontradas: {var_listTop}")
        return self
    
    def transform(self, arg_pdX):
        """
        Transforma a coluna em múltiplas colunas binárias (otimizado).
        
        Parâmetros:
        - arg_pdX (pd.DataFrame ou pd.Series): Coluna a ser transformada

        Retorna:
        - var_listResult (np.ndarray): Matriz binária indicando presença de categorias
        """
        if isinstance(arg_pdX, pd.Series):
            arg_pdX = arg_pdX.values.reshape(-1, 1)
        
        var_listResult = np.zeros((arg_pdX.shape[0], len(self.var_listCategories_)), dtype=np.int8)
        
        # Criar dicionário de índices para busca rápida
        var_dictCategoryIndex = {cat: idx for idx, cat in enumerate(self.var_listCategories_)}
        
        # Processar em batch
        for i, row in enumerate(arg_pdX):
            if pd.notna(row[0]) and row[0] != "":
                var_listItems = [var_strItem.strip() for var_strItem in str(row[0]).split(",")]
                for var_strItem in var_listItems:
                    if var_strItem in var_dictCategoryIndex:
                        var_listResult[i, var_dictCategoryIndex[var_strItem]] = 1
        
        return var_listResult

class ProcessadorLimpeza:
    """
    Classe responsável por processar a limpeza de dados.
    """
    
    # Constantes de configuração
    COLUNAS_ID = ["appid", "id_itad"]
    COLUNAS_MULTILABEL = ["categorias", "genero", "linguagens", "desenvolvedores", "distribuidores"]
    COLUNAS_CATEGORICAS_SIMPLES = ["classificacao_etaria", "review_score_desc"]
    COLUNAS_REMOVER_ITAD = ["title", "type", "mature", "assets", "ultima_atualizacao"]
    COLUNAS_REMOVER_MAPPING = ["slug", "title", "created_at"]
    
    REVIEW_SCORES_VALIDOS = [
        'Extremamente positivas', 
        'Muito positivas', 
        'Bem positivas',
        'Positivas', 
        'Mistas', 
        'Negativas', 
        'Bem negativas', 
        'Muito negativas', 
        'Extremamente negativas', 
        'Nenhuma analise de usuario', 
        'Outros'
    ]
    
    # Mapeamento de valores problemáticos para valores válidos
    REVIEW_SCORES_MAPPING = {
        # Padrões com problemas de encoding ou formato
        'analise': 'Outros',
        'anlise': 'Outros',
        'usuario': 'Outros',
        'usurio': 'Outros',
    }
    
    # Parâmetros padrão para transformadores
    DEFAULT_MAX_FEATURES = 30
    DEFAULT_MIN_FREQ = 2  # Reduzido de 5 para 2 para capturar mais categorias
    
    # Cache para otimização
    _var_boolCacheHabilitado = True
    _var_strHashUltimoDataset = None
    
    # Diretório para salvar pipelines
    PIPELINE_DIR = "prj_TCC_PREVISOR_STEAM/resources/models"
    
    # Controle de cache
    _var_dictCacheDataframes = {}
    _var_dictMetricasProcessamento = {}
    
    @classmethod
    def obter_estatisticas_dataframe(cls, arg_dfDataframe: pd.DataFrame) -> Dict[str, Any]:
        """
        Gera estatísticas descritivas completas do DataFrame.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame para análise
        
        Retorna:
        - var_dictStats (dict): shape, tipos, nulos, duplicatas, memória, etc.
        """
        var_dictStats = {
            'timestamp': datetime.now().isoformat(),
            'total_registros': len(arg_dfDataframe),
            'total_colunas': len(arg_dfDataframe.columns),
            'memoria_mb': arg_dfDataframe.memory_usage(deep=True).sum() / 1024**2,
            'colunas_numericas': len(arg_dfDataframe.select_dtypes(include=[np.number]).columns),
            'colunas_categoricas': len(arg_dfDataframe.select_dtypes(include=['object']).columns),
            'valores_nulos_total': int(arg_dfDataframe.isnull().sum().sum()),
            'percentual_nulos': float((arg_dfDataframe.isnull().sum().sum() / (arg_dfDataframe.shape[0] * arg_dfDataframe.shape[1])) * 100),
            'duplicatas_completas': int(arg_dfDataframe.duplicated().sum()),
            'colunas_com_nulos': arg_dfDataframe.columns[arg_dfDataframe.isnull().any()].tolist(),
        }
        
        # Estatísticas por coluna (converter nome da coluna para string para garantir hashability)
        var_dictStats['colunas_info'] = {}
        for col in arg_dfDataframe.columns:
            var_strColName = str(col)  # Garantir que é string, não lista
            var_dictStats['colunas_info'][var_strColName] = {
                'tipo': str(arg_dfDataframe[col].dtype),
                'nulos': int(arg_dfDataframe[col].isnull().sum()),
                'unicos': int(arg_dfDataframe[col].nunique()),
                'perc_nulos': float((arg_dfDataframe[col].isnull().sum() / len(arg_dfDataframe)) * 100)
            }
        
        return var_dictStats
    
    @classmethod
    def limpar_valores_nao_hashable(cls, arg_dfDataframe: pd.DataFrame, arg_boolInplace: bool = False) -> pd.DataFrame:
        """
        Remove ou converte valores não hashable (listas, dicts, sets) em um DataFrame.
        Otimizado para processar grandes volumes de dados rapidamente.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame a ser limpo
        - arg_boolInplace (bool): Se True, modifica o DataFrame original (mais rápido)
        
        Retorna:
        - var_dfWork (pd.DataFrame): DataFrame com valores hashable
        """
        if len(arg_dfDataframe) == 0:
            return arg_dfDataframe if arg_boolInplace else arg_dfDataframe.copy()
        
        var_dfWork = arg_dfDataframe if arg_boolInplace else arg_dfDataframe.copy()
        var_intColunasConvertidas = 0
        var_floatInicio = time.time()
        
        # Processar apenas colunas tipo object (onde podem haver listas/dicts)
        var_listColunasObject = var_dfWork.select_dtypes(include=['object']).columns.tolist()
        
        if not var_listColunasObject:
            return var_dfWork
        
        logger.debug(f"Verificando {len(var_listColunasObject)} colunas object...")
        
        # Identificar colunas com arrays PostgreSQL (listas, dicts, sets, tuples)
        var_listColunasProblematicas = []
        for var_strCol in var_listColunasObject:
            var_serNaoNulos = var_dfWork[var_strCol].dropna()
            if len(var_serNaoNulos) > 0:
                var_firstValue = var_serNaoNulos.iloc[0]
                if isinstance(var_firstValue, (list, dict, set, tuple)):
                    var_listColunasProblematicas.append(var_strCol)
        
        if not var_listColunasProblematicas:
            logger.debug("Nenhuma coluna com valores não hashable detectada")
            return var_dfWork
        
        logger.info(f"Convertendo {len(var_listColunasProblematicas)} colunas com arrays PostgreSQL...")
        
        # Converter arrays para strings separadas por vírgula
        for var_strCol in var_listColunasProblematicas:
            try:
                # Log ANTES da conversão
                var_serAmostraAntes = var_dfWork[var_strCol].dropna().head(3)
                logger.info(f"  [{var_strCol}] ANTES (tipo={type(var_serAmostraAntes.iloc[0]).__name__}): {list(var_serAmostraAntes)}")
                
                # Converter listas para strings separadas por vírgula (formato esperado pelo MultiLabelBinarizer)
                def converter_lista(x):
                    if not isinstance(x, list):
                        return str(x) if pd.notna(x) else ''
                    if not x:  # Lista vazia
                        return ''
                    # Tentar join direto (se lista de strings)
                    try:
                        return ', '.join(x)
                    except TypeError:
                        # Lista contém não-strings (dicts, etc) → converter para string
                        return str(x)
                
                var_dfWork[var_strCol] = var_dfWork[var_strCol].apply(converter_lista)
                var_intColunasConvertidas += 1
                
                # Log DEPOIS da conversão
                var_serAmostraDepois = var_dfWork[var_strCol].dropna().head(3)
                logger.info(f"  [{var_strCol}] DEPOIS (tipo={type(var_serAmostraDepois.iloc[0]).__name__}): {list(var_serAmostraDepois)}")
                logger.info(f"  Valores únicos: {var_dfWork[var_strCol].nunique()}")
            except Exception as e:
                logger.warning(f"  {var_strCol}: Fallback para str() - {e}")
                # Fallback: conversão direta para string
                var_dfWork[var_strCol] = var_dfWork[var_strCol].astype(str)
                var_intColunasConvertidas += 1
        
        var_floatDuracao = time.time() - var_floatInicio
        if var_intColunasConvertidas > 0:
            logger.info(f"Convertidas {var_intColunasConvertidas} colunas em {var_floatDuracao:.2f}s")
        
        return var_dfWork
    
    @classmethod
    def validar_qualidade_dados(cls, arg_dfDataframe: pd.DataFrame, 
                               arg_floatLimiteNulos: float = 0.5,
                               arg_floatLimiteDuplicatas: float = 0.1) -> Tuple[bool, List[str]]:
        """
        Valida qualidade dos dados com base em thresholds.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame a validar
        - arg_floatLimiteNulos (float): % máximo aceitável de nulos (0.5 = 50%)
        - arg_floatLimiteDuplicatas (float): % máximo de duplicatas (0.1 = 10%)
        
        Retorna:
        - Tuple[var_boolValido (bool), var_listAvisos (List[str])]: (passou_validacao, lista_de_avisos)
        """
        var_listAvisos = []
        var_boolValido = True
        
        # Verificar nulos excessivos
        var_floatPercNulos = arg_dfDataframe.isnull().sum().sum() / (arg_dfDataframe.shape[0] * arg_dfDataframe.shape[1])
        if var_floatPercNulos > arg_floatLimiteNulos:
            var_listAvisos.append(f"Taxa de nulos muito alta: {var_floatPercNulos*100:.1f}% (limite: {arg_floatLimiteNulos*100}%)")
            var_boolValido = False
        
        # Verificar duplicatas excessivas (otimizado com amostragem)
        try:
            # Para datasets grandes (>50k), usar amostragem para eficiência
            var_boolUsarAmostra = len(arg_dfDataframe) > 50000
            var_dfParaVerificar = arg_dfDataframe.sample(n=min(50000, len(arg_dfDataframe)), random_state=42) if var_boolUsarAmostra else arg_dfDataframe
            
            # Verificar duplicatas apenas em colunas numéricas (sempre hashable e mais rápido)
            var_listColunasNumericas = var_dfParaVerificar.select_dtypes(include=[np.number]).columns.tolist()
            
            if var_listColunasNumericas:
                var_floatPercDuplicatas = var_dfParaVerificar[var_listColunasNumericas].duplicated().sum() / len(var_dfParaVerificar)
                if var_floatPercDuplicatas > arg_floatLimiteDuplicatas:
                    var_strMsgAmostra = " (verificado em amostra)" if var_boolUsarAmostra else ""
                    var_listAvisos.append(f"Taxa de duplicatas muito alta: {var_floatPercDuplicatas*100:.1f}% (limite: {arg_floatLimiteDuplicatas*100}%){var_strMsgAmostra}")
                    var_boolValido = False
            else:
                logger.debug("Nenhuma coluna numérica para verificação rápida de duplicatas")
        except Exception as e:
            logger.debug(f"Verificação de duplicatas pulada: {e}")
        
        # Verificar colunas com apenas um valor
        for var_strCol in arg_dfDataframe.columns:
            if arg_dfDataframe[var_strCol].nunique() == 1:
                var_listAvisos.append(f"Coluna '{var_strCol}' possui apenas um valor único")
        
        # Verificar colunas completamente nulas
        for var_strCol in arg_dfDataframe.columns:
            if arg_dfDataframe[var_strCol].isnull().all():
                var_listAvisos.append(f"Coluna '{var_strCol}' está completamente vazia")
                var_boolValido = False
        
        return var_boolValido, var_listAvisos
    
    @classmethod
    def validar_dataframe(cls, arg_dfDataframe: pd.DataFrame, arg_strNomeDataframe: str, 
                         arg_listColunasEsperadas: Optional[List[str]] = None) -> bool:
        """
        Valida se o DataFrame atende aos requisitos básicos.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame a ser validado
        - arg_strNomeDataframe (str): Nome do DataFrame para logging
        - arg_listColunasEsperadas (Optional[List[str]]): Lista de colunas que devem existir
        
        Retorna:
        - bool: True se válido, False caso contrário
        """
        try:
            # Verifica se está vazio
            if arg_dfDataframe is None or arg_dfDataframe.empty:
                raise ValueError(f"{arg_strNomeDataframe} está vazio ou None")
            
            logger.info(f"Validando {arg_strNomeDataframe}: {len(arg_dfDataframe)} registros, {len(arg_dfDataframe.columns)} colunas")
            
            # Verifica colunas esperadas
            if arg_listColunasEsperadas:
                var_setColunasAusentes = set(arg_listColunasEsperadas) - set(arg_dfDataframe.columns)
                if var_setColunasAusentes:
                    raise ValueError(f"{arg_strNomeDataframe} está faltando colunas: {var_setColunasAusentes}")
            
            # Verifica tipos de dados problemáticos
            var_intColunasTipoObject = len(arg_dfDataframe.select_dtypes(include=['object']).columns)
            logger.debug(f"{arg_strNomeDataframe} possui {var_intColunasTipoObject} colunas tipo object")
            
            # Verifica valores nulos excessivos
            var_floatPercNulos = (arg_dfDataframe.isnull().sum().sum() / (arg_dfDataframe.shape[0] * arg_dfDataframe.shape[1])) * 100
            if var_floatPercNulos > 50:
                logger.warning(f"{arg_strNomeDataframe} possui {var_floatPercNulos:.2f}% de valores nulos")
            
            # Verifica duplicatas em colunas ID
            for var_strColunaId in cls.COLUNAS_ID:
                if var_strColunaId in arg_dfDataframe.columns:
                    var_intDuplicatas = arg_dfDataframe[var_strColunaId].duplicated().sum()
                    if var_intDuplicatas > 0:
                        logger.warning(f"{arg_strNomeDataframe} possui {var_intDuplicatas} valores duplicados em {var_strColunaId}")
            
            return True
            
        except ValueError as e:
            logger.error(f"Erro na validação de {arg_strNomeDataframe}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado na validação de {arg_strNomeDataframe}: {str(e)}")
            raise

    @classmethod
    def salvar_dataframe(cls, arg_dfDataframe: pd.DataFrame, 
                        arg_strNomeArquivo: str,
                        arg_strFormato: str = 'parquet',
                        arg_boolComprimir: bool = True) -> str:
        """
        Salva DataFrame processado em disco.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame a salvar
        - arg_strNomeArquivo (str): Nome do arquivo (sem extensão)
        - arg_strFormato (str): 'parquet', 'csv', 'pickle' (padrão: parquet)
        - arg_boolComprimir (bool): Aplicar compressão (padrão: True)
        
        Retorna:
        - var_strCaminhoCompleto (str): Caminho do arquivo salvo
        """
        try:
            var_pathDiretorio = Path("prj_TCC_PREVISOR_STEAM/resources/dados/exports")
            var_pathDiretorio.mkdir(parents=True, exist_ok=True)
            
            if arg_strFormato == 'parquet':
                var_strCaminhoCompleto = os.path.join(var_pathDiretorio, f"{arg_strNomeArquivo}.parquet")
                arg_dfDataframe.to_parquet(var_strCaminhoCompleto, 
                                          compression='gzip' if arg_boolComprimir else None,
                                          index=False)
            elif arg_strFormato == 'csv':
                var_strCaminhoCompleto = os.path.join(var_pathDiretorio, f"{arg_strNomeArquivo}.csv")
                arg_dfDataframe.to_csv(var_strCaminhoCompleto, index=False)
            elif arg_strFormato == 'pickle':
                var_strCaminhoCompleto = os.path.join(var_pathDiretorio, f"{arg_strNomeArquivo}.pkl")
                arg_dfDataframe.to_pickle(var_strCaminhoCompleto, 
                                         compression='gzip' if arg_boolComprimir else None)
            else:
                raise ValueError(f"Formato não suportado: {arg_strFormato}")
            
            logger.info(f"DataFrame salvo: {var_strCaminhoCompleto} ({arg_dfDataframe.shape[0]} linhas)")
            return str(var_strCaminhoCompleto)
            
        except Exception as e:
            logger.error(f"Erro ao salvar DataFrame: {str(e)}")
            raise
    
    @classmethod
    def carregar_dataframe(cls, arg_strCaminhoArquivo: str) -> pd.DataFrame:
        """
        Carrega DataFrame salvo do disco.
        
        Parâmetros:
        - arg_strCaminhoArquivo (str): Caminho completo ou nome do arquivo
        
        Retorna:
        - var_dfDataframe (pd.DataFrame): DataFrame carregado
        """
        try:
            var_pathArquivo = Path(arg_strCaminhoArquivo)
            
            if not var_pathArquivo.exists():
                # Tentar no diretório padrão
                var_pathArquivo = os.path.join("prj_TCC_PREVISOR_STEAM/resources/dados/exports", arg_strCaminhoArquivo)
            
            if not var_pathArquivo.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {arg_strCaminhoArquivo}")
            
            if var_pathArquivo.suffix == '.parquet':
                var_dfDataframe = pd.read_parquet(var_pathArquivo)
            elif var_pathArquivo.suffix == '.csv':
                var_dfDataframe = pd.read_csv(var_pathArquivo)
            elif var_pathArquivo.suffix == '.pkl':
                var_dfDataframe = pd.read_pickle(var_pathArquivo)
            else:
                raise ValueError(f"Formato não suportado: {var_pathArquivo.suffix}")
            
            logger.info(f"DataFrame carregado: {var_pathArquivo} ({var_dfDataframe.shape[0]} linhas)")
            return var_dfDataframe
            
        except Exception as e:
            logger.error(f"Erro ao carregar DataFrame: {str(e)}")
            raise
    
    @classmethod
    def gerar_relatorio_processamento(cls, arg_dfOriginal: pd.DataFrame, 
                                      arg_dfProcessado: pd.DataFrame) -> Dict[str, Any]:
        """
        Gera relatório comparativo entre DataFrame original e processado.
        
        Parâmetros:
        - arg_dfOriginal (pd.DataFrame): DataFrame antes do processamento
        - arg_dfProcessado (pd.DataFrame): DataFrame após processamento
        
        Retorna:
        - var_dictRelatorio (Dict[str, Any]): Dict com métricas comparativas
        """
        var_dictRelatorio = {
            'timestamp': datetime.now().isoformat(),
            'registros_original': len(arg_dfOriginal),
            'registros_processado': len(arg_dfProcessado),
            'registros_removidos': len(arg_dfOriginal) - len(arg_dfProcessado),
            'colunas_original': len(arg_dfOriginal.columns),
            'colunas_processado': len(arg_dfProcessado.columns),
            'colunas_adicionadas': len(arg_dfProcessado.columns) - len(arg_dfOriginal.columns),
            'colunas_removidas': list(set(arg_dfOriginal.columns) - set(arg_dfProcessado.columns)),
            'colunas_novas': list(set(arg_dfProcessado.columns) - set(arg_dfOriginal.columns)),
            'memoria_original_mb': arg_dfOriginal.memory_usage(deep=True).sum() / 1024**2,
            'memoria_processado_mb': arg_dfProcessado.memory_usage(deep=True).sum() / 1024**2,
            'metricas': cls._metricas_processamento.copy()
        }
        
        var_dictRelatorio['reducao_memoria_perc'] = (
            (var_dictRelatorio['memoria_original_mb'] - var_dictRelatorio['memoria_processado_mb']) / 
            var_dictRelatorio['memoria_original_mb'] * 100
        )
        
        return var_dictRelatorio
    
    @classmethod
    def limpar_memoria(cls, *args):
        """
        Libera memória de objetos e força garbage collection.
        
        Parâmetros:
        - *args: Objetos para deletar explicitamente
        """
        for obj in args:
            del obj
        gc.collect()
        logger.debug("Memória liberada via garbage collection")
    
    @classmethod
    def processar_ITAD(cls) -> pd.DataFrame:
        """
        Processa a limpeza dos dados da tabela itad_raw.
        
        Retorna:
        - var_dfDataITADAux (pd.DataFrame): DataFrame contendo os dados limpos.
        """
        try:
            with timer_context("Processamento ITAD"):
                logger.info(f"{'-'*10}Iniciando o processamento dos dados ITAD...{'-'*10}")
                
                var_dfDataITAD = LimpezaDados.carregar_dataframe(arg_strNomeTabela="itad_raw")
                cls.validar_dataframe(var_dfDataITAD, "itad_raw", ["id_itad"])
                
                var_intRegistrosOriginais = len(var_dfDataITAD)
                logger.info(f"Número de registros carregados: {var_intRegistrosOriginais}")
                
                var_dfDataITADAux = var_dfDataITAD.copy()
                var_dfDataITADAux = var_dfDataITADAux.drop_duplicates(subset=["id_itad"])
                
                # Remove apenas colunas que existem
                var_listColunasRemover = [var_strCol for var_strCol in cls.COLUNAS_REMOVER_ITAD if var_strCol in var_dfDataITADAux.columns]
                if var_listColunasRemover:
                    var_dfDataITADAux = var_dfDataITADAux.drop(columns=var_listColunasRemover)
                
                var_dfDataITADAux = var_dfDataITADAux.reset_index(drop=True)
                
                # Registrar métricas
                cls._var_dictMetricasProcessamento['itad'] = {
                    'registros_inicial': var_intRegistrosOriginais,
                    'registros_final': len(var_dfDataITADAux),
                    'duplicatas_removidas': var_intRegistrosOriginais - len(var_dfDataITADAux),
                    'colunas_removidas': len(var_listColunasRemover)
                }
                
                logger.info(f"Número de registros após filtragem: {len(var_dfDataITADAux)}")
                logger.info(f"{'-'*10}Processamento dos dados ITAD concluído.{'-'*10}")
                
                # Liberar memória do DataFrame original
                cls.limpar_memoria(var_dfDataITAD)
                
                return var_dfDataITADAux
            
        except Exception as e:
            logger.error(f"Erro ao processar dados ITAD: {str(e)}")
            raise

    @classmethod
    def processar_itad_map(cls) -> pd.DataFrame:
        """
        Processa a limpeza dos dados da tabela itad_map.
        
        Retorna:
        - var_dfDataITADMapAux (pd.DataFrame): DataFrame contendo os dados limpos.
        """
        try:
            logger.info(f"{'-'*10}Iniciando o processamento dos dados ITAD Mapping...{'-'*10}")
            
            var_dfDataITADMap = LimpezaDados.carregar_dataframe(arg_strNomeTabela="steam_itad_mapping")
            cls.validar_dataframe(var_dfDataITADMap, "steam_itad_mapping", ["appid", "id_itad"])
            
            logger.info(f"Número de registros carregados: {len(var_dfDataITADMap)}")
            var_dfDataITADMapAux = var_dfDataITADMap.copy()
            var_dfDataITADMapAux = var_dfDataITADMapAux.drop_duplicates(subset=["appid"])
            var_dfDataITADMapAux = var_dfDataITADMapAux.drop_duplicates(subset=["id_itad"])
            
            # Remove apenas colunas que existem
            var_listColunasRemover = [var_strCol for var_strCol in cls.COLUNAS_REMOVER_MAPPING if var_strCol in var_dfDataITADMapAux.columns]
            if var_listColunasRemover:
                var_dfDataITADMapAux = var_dfDataITADMapAux.drop(columns=var_listColunasRemover)
            
            logger.info(f"Número de registros após filtragem: {len(var_dfDataITADMapAux)}")
            var_dfDataITADMapAux = var_dfDataITADMapAux.reset_index(drop=True)
            logger.info(f"{'-'*10}Processamento dos dados ITAD Mapping concluído.{'-'*10}")

            return var_dfDataITADMapAux
            
        except Exception as e:
            logger.error(f"Erro ao processar dados ITAD Mapping: {str(e)}")
            raise
    
    @classmethod
    def processar_unificado(cls) -> pd.DataFrame:
        """
        Processa a limpeza dos dados da tabela steam_unificado.
        
        Retorna:
        - var_dfDataUnificadoAux (pd.DataFrame): DataFrame contendo os dados limpos.
        """
        try:
            logger.info(f"{'-'*10}Iniciando o processamento dos dados steam_unificado...{'-'*10}")

            var_dfDataUnificado = LimpezaDados.carregar_dataframe(arg_strNomeTabela="steam_unificado")
            cls.validar_dataframe(var_dfDataUnificado, "steam_unificado", ["appid", "type"])
            
            logger.info(f"Número de registros carregados: {len(var_dfDataUnificado)}")
            var_dfDataUnificadoAux = var_dfDataUnificado.copy()
            
            # Validação de valores antes de filtrar
            if "type" not in var_dfDataUnificadoAux.columns:
                raise ValueError("Coluna 'type' não encontrada no DataFrame steam_unificado")
            
            var_dfDataUnificadoAux = var_dfDataUnificadoAux[var_dfDataUnificadoAux["type"] == "game"]
            
            if "preco" in var_dfDataUnificadoAux.columns:
                var_dfDataUnificadoAux = var_dfDataUnificadoAux[var_dfDataUnificadoAux["preco"] != "Gratuito"]
            
            var_dfDataUnificadoAux = var_dfDataUnificadoAux.fillna({"metacritic_score": 0})
            logger.info(f"Número de registros após filtragem: {len(var_dfDataUnificadoAux)}")

            # Validar e limpar a coluna de reviews
            if "review_score_desc" in var_dfDataUnificadoAux.columns:
                # Identificar valores inconsistentes
                var_boolMaskInvalidos = ~var_dfDataUnificadoAux["review_score_desc"].isin(cls.REVIEW_SCORES_VALIDOS)
                var_intInvalidos = var_boolMaskInvalidos.sum()
                
                if var_intInvalidos > 0:
                    logger.warning(f"Encontrados {var_intInvalidos} valores inconsistentes em review_score_desc")
                    var_listValoresUnicosInvalidos = var_dfDataUnificadoAux.loc[var_boolMaskInvalidos, "review_score_desc"].unique()
                    logger.info(f"Valores inconsistentes encontrados: {var_listValoresUnicosInvalidos[:10]}")  # Limitar a 10 para log
                    
                    # Substituir valores inconsistentes por 'Outros'
                    # Verificar se contém palavras-chave problemáticas
                    for var_strPalavraChave in cls.REVIEW_SCORES_MAPPING.keys():
                        var_boolMask = var_dfDataUnificadoAux["review_score_desc"].astype(str).str.contains(var_strPalavraChave, case=False, na=False)
                        if var_boolMask.any():
                            var_dfDataUnificadoAux.loc[var_boolMask, "review_score_desc"] = cls.REVIEW_SCORES_MAPPING[var_strPalavraChave]
                    
                    # Substituir quaisquer valores restantes inválidos por 'Outros'
                    var_boolMaskAindaInvalidos = ~var_dfDataUnificadoAux["review_score_desc"].isin(cls.REVIEW_SCORES_VALIDOS)
                    if var_boolMaskAindaInvalidos.any():
                        var_dfDataUnificadoAux.loc[var_boolMaskAindaInvalidos, "review_score_desc"] = "Outros"
                    
                    logger.info(f"Valores inconsistentes substituídos por 'Outros'")
                else:
                    logger.info("Todos os valores de review_score_desc são válidos")
            else:
                logger.warning("Coluna 'review_score_desc' não encontrada no DataFrame")
            
            # Remove apenas se a coluna existir
            if "ultima_atualizacao" in var_dfDataUnificadoAux.columns:
                var_dfDataUnificadoAux = var_dfDataUnificadoAux.drop(columns=["ultima_atualizacao"])
            
            var_dfDataUnificadoAux = var_dfDataUnificadoAux.reset_index(drop=True)
            logger.info(f"{'-'*10}Processamento dos dados steam_unificado concluído.{'-'*10}")

            return var_dfDataUnificadoAux
            
        except Exception as e:
            logger.error(f"Erro ao processar dados steam_unificado: {str(e)}")
            raise
    
    @classmethod
    def processar_todos(cls):
        """
        Processa a limpeza dos dados de todas as tabelas.
        
        Parâmetros:
        
        Retorna:
        - var_dfGeral (pd.DataFrame): DataFrame contendo os dados limpos combinados.
        """
        try:
            var_dfITAD = cls.processar_ITAD()
            var_dfUnificado = cls.processar_unificado()
            var_dfMapping = cls.processar_itad_map()

            logger.info(f"{'-'*10}Iniciando o merge dos dados limpos...{'-'*10}")
            logger.info(f"Número de registros em unificado: {len(var_dfUnificado)}")
            logger.info(f"Número de registros em mapping: {len(var_dfMapping)}")
            logger.info(f"Número de registros em ITAD: {len(var_dfITAD)}")

            var_dfPrimeiroMerge = pd.merge(var_dfUnificado, var_dfMapping, how="left", on="appid")
            var_dfGeral = pd.merge(var_dfPrimeiroMerge, var_dfITAD, how="left", on="id_itad")
            
            var_dfGeral = var_dfGeral.reset_index(drop=True)
            logger.info(f"Número de registros após merge: {len(var_dfGeral)}")

            var_dfGeralCopy = var_dfGeral.copy()
            var_dfGeralCopy = var_dfGeralCopy.drop_duplicates(subset=["appid"])
            var_dfGeralCopy = var_dfGeralCopy.drop_duplicates(subset=["id_itad"])
            logger.info(f"Número de registros após remoção de duplicatas: {len(var_dfGeralCopy)}")

            var_dfGeralCopy = var_dfGeralCopy.fillna({"metacritic_score": 0,
                                                    "preco": "Desconhecido",
                                                    "review_score_desc": "Nenhuma analise de usuario"})
            
            var_dfGeralCopy = var_dfGeralCopy.reset_index(drop=True)
            
            return var_dfGeralCopy
        except Exception as e:
            logger.error(f"Erro ao processar todos os dados: {e}")
            raise Exception(f"Erro ao processar todos os dados: {e}")
    
    @classmethod
    def processar_categoricos(cls, arg_dfDataframe: pd.DataFrame,
                             arg_intMaxFeatures: Optional[int] = None,
                             arg_intMinFreq: Optional[int] = None,
                             arg_strEstrategiaEncoding: str = 'label',
                             arg_boolManterOriginais: bool = False) -> pd.DataFrame:
        """
        Processa colunas categóricas e de texto, criando encodings apropriados.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame a ser processado
        - arg_intMaxFeatures (Optional[int]): Máximo de features multilabel (padrão: 30)
        - arg_intMinFreq (Optional[int]): Frequência mínima para categoria (padrão: 5)
        - arg_strEstrategiaEncoding (str): 'label' ou 'onehot' (padrão: 'label')
        - arg_boolManterOriginais (bool): Manter colunas originais após encoding (padrão: False)
        
        Retorna:
        - var_dfCopy (pd.DataFrame) : DataFrame com colunas categóricas processadas
        """
        try:
            with timer_context("Processamento Categórico"):
                logger.info(f"{'-'*10}Iniciando processamento de atributos categóricos...{'-'*10}")
                var_dfCopy = arg_dfDataframe.copy()
                
                # Usar valores padrão se não fornecidos
                var_intMaxFeatures = arg_intMaxFeatures or cls.DEFAULT_MAX_FEATURES
                var_intMinFreq = arg_intMinFreq or cls.DEFAULT_MIN_FREQ
                
                var_intColunasInicial = len(var_dfCopy.columns)
            
            # Processar colunas multi-label
            for var_strColuna in cls.COLUNAS_MULTILABEL:
                if var_strColuna in var_dfCopy.columns:
                    try:
                        logger.info(f"Processando coluna multi-label: {var_strColuna}")
                        
                        # Verificar se há dados não vazios
                        var_intNaoVazios = var_dfCopy[var_strColuna].notna().sum()
                        var_intComConteudo = var_dfCopy[var_strColuna].astype(str).str.strip().ne("").sum()
                        logger.info(f"  {var_strColuna}: {var_intNaoVazios} não-nulos, {var_intComConteudo} com conteúdo")
                        
                        # Diagnóstico: verificar primeiros valores
                        if var_intComConteudo > 0:
                            var_serAmostra = var_dfCopy[var_strColuna].dropna().head(3)
                            logger.info(f"  Amostra de valores (tipo={type(var_serAmostra.iloc[0]).__name__}): {list(var_serAmostra)}")
                        
                        if var_intComConteudo < 10:
                            logger.warning(f"  Coluna {var_strColuna} tem poucos dados ({var_intComConteudo}), pulando processamento")
                            continue
                        
                        # Criar transformador para esta coluna
                        var_objTransformer = MultiLabelBinarizerTransformer(
                            arg_intMaxFeatures=var_intMaxFeatures,
                            arg_intMinFreq=var_intMinFreq
                        )
                        
                        # Ajustar e transformar
                        var_objTransformer.fit(var_dfCopy[[var_strColuna]])
                        var_objTransformed = var_objTransformer.transform(var_dfCopy[[var_strColuna]])
                        
                        # Criar nomes de colunas
                        var_listColumnNames = [f"{var_strColuna}_{cat}" for cat in var_objTransformer.var_listCategories_]
                        
                        if len(var_listColumnNames) == 0:
                            logger.warning(f"Nenhuma categoria encontrada para {var_strColuna}")
                            continue
                        
                        # Adicionar ao DataFrame
                        var_dfTransformed = pd.DataFrame(var_objTransformed, columns=var_listColumnNames, index=var_dfCopy.index)
                        var_dfCopy = pd.concat([var_dfCopy, var_dfTransformed], axis=1)
                        
                        # Remover coluna original se não for para manter
                        if not arg_boolManterOriginais:
                            var_dfCopy = var_dfCopy.drop(columns=[var_strColuna])
                            logger.info(f"  Criadas {len(var_listColumnNames)} colunas binárias para {var_strColuna}")
                        else:
                            logger.info(f"  Criadas {len(var_listColumnNames)} colunas binárias para {var_strColuna} (original mantida)")
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar coluna multilabel '{var_strColuna}': {str(e)}")
                        continue

            # Processar colunas categóricas simples
            for var_strColuna in cls.COLUNAS_CATEGORICAS_SIMPLES:
                if var_strColuna in var_dfCopy.columns:
                    try:
                        logger.info(f"Processando coluna categórica: {var_strColuna} (estratégia: {arg_strEstrategiaEncoding})")
                        
                        # Preencher valores faltantes
                        var_dfCopy[var_strColuna] = var_dfCopy[var_strColuna].fillna("Desconhecido")
                        
                        if arg_strEstrategiaEncoding == 'label':
                            # Label Encoding
                            var_leLabel = LabelEncoder()
                            var_dfCopy[f"{var_strColuna}_encoded"] = var_leLabel.fit_transform(var_dfCopy[var_strColuna].astype(str))
                            logger.info(f"  Coluna {var_strColuna} codificada com Label Encoding. Classes: {len(var_leLabel.classes_)}")
                            
                            if not arg_boolManterOriginais:
                                var_dfCopy = var_dfCopy.drop(columns=[var_strColuna])
                                
                        elif arg_strEstrategiaEncoding == 'onehot':
                            # One-Hot Encoding
                            var_ohEncoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                            var_arrEncoded = var_ohEncoder.fit_transform(var_dfCopy[[var_strColuna]])
                            var_listColNames = [f"{var_strColuna}_{cat}" for cat in var_ohEncoder.categories_[0]]
                            
                            var_dfEncoded = pd.DataFrame(var_arrEncoded, columns=var_listColNames, index=var_dfCopy.index)
                            var_dfCopy = pd.concat([var_dfCopy, var_dfEncoded], axis=1)
                            logger.info(f"  Coluna {var_strColuna} codificada com One-Hot Encoding. Classes: {len(var_listColNames)}")
                            
                            if not arg_boolManterOriginais:
                                var_dfCopy = var_dfCopy.drop(columns=[var_strColuna])
                        else:
                            logger.warning(f"Estratégia '{arg_strEstrategiaEncoding}' não reconhecida, usando 'label'")
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar coluna categórica '{var_strColuna}': {str(e)}")
                        continue
            
                var_intColunasFinal = len(var_dfCopy.columns)
                var_intColunasAdicionadas = var_intColunasFinal - var_intColunasInicial
                
                # Garantir que o DataFrame não tenha colunas com listas como nomes
                var_listColunasProblematicas = [var_strCol for var_strCol in var_dfCopy.columns if isinstance(var_strCol, (list, tuple))]
                if var_listColunasProblematicas:
                    logger.warning(f"Detectadas {len(var_listColunasProblematicas)} colunas com nomes não-string, corrigindo...")
                    var_dfCopy.columns = [str(var_strCol) for var_strCol in var_dfCopy.columns]
                
                # Registrar métricas (garantir que não há listas como chaves)
                cls._var_dictMetricasProcessamento['categorico'] = {
                    'colunas_inicial': int(var_intColunasInicial),
                    'colunas_final': int(var_intColunasFinal),
                    'colunas_adicionadas': int(var_intColunasAdicionadas),
                    'estrategia_encoding': str(arg_strEstrategiaEncoding),
                    'manteve_originais': bool(arg_boolManterOriginais)
                }
                
                logger.info(f"Número de colunas após processamento categórico: {var_intColunasFinal} (+{var_intColunasAdicionadas})")
                logger.info(f"{'-'*10}Processamento de atributos categóricos concluído.{'-'*10}")
                
                # Limpar valores não hashable antes de retornar (inplace para economia de memória)
                logger.debug("Limpando valores não hashable após processamento categórico...")
                cls.limpar_valores_nao_hashable(var_dfCopy, arg_boolInplace=True)
                
                return var_dfCopy
            
        except Exception as e:
            logger.error(f"Erro no processamento categórico: {str(e)}")
            raise
        
    @classmethod
    def criar_pipeline_escalonamento(cls, arg_dfDataframe, arg_listColunasNumericas=None):
        """
        Cria e aplica pipeline de escalonamento para características numéricas.
        
        Parâmetros:
        - arg_dfDataframe (pd.DataFrame): DataFrame a ser processado
        - arg_listColunasNumericas (list): Lista de colunas numéricas a escalonar.
                                   Se None, detecta automaticamente.
        
        Retorna:
        - df_scaled (pd.DataFrame): DataFrame com colunas numéricas escalonadas
        - pipeline (ColumnTransformer): Pipeline usado para transformação
        """
        try:
            logger.info(f"{'-'*10}Iniciando escalonamento de características...{'-'*10}")
            var_dfCopy = arg_dfDataframe.copy()
            
            # Detectar colunas numéricas automaticamente se não fornecidas
            if arg_listColunasNumericas is None:
                arg_listColunasNumericas = var_dfCopy.select_dtypes(include=[np.number]).columns.tolist()
                
                # Remover colunas que são IDs ou não devem ser escalonadas
                arg_listColunasNumericas = [var_strCol for var_strCol in arg_listColunasNumericas 
                                           if var_strCol not in cls.COLUNAS_ID]
            
            logger.info(f"Colunas numéricas identificadas para escalonamento: {len(arg_listColunasNumericas)}")
            
            if len(arg_listColunasNumericas) > 0:
                # Validar que as colunas existem no DataFrame
                arg_listColunasNumericas = [var_strCol for var_strCol in arg_listColunasNumericas if var_strCol in var_dfCopy.columns]
                
                if len(arg_listColunasNumericas) == 0:
                    logger.warning("Nenhuma coluna numérica válida encontrada após validação")
                    return var_dfCopy, None
                
                # Criar transformadores
                # StandardScaler para a maioria das features (média 0, desvio padrão 1)
                # MinMaxScaler para features que devem estar entre 0 e 1
                
                # Identificar colunas que devem usar MinMaxScaler (scores, percentuais, etc.)
                var_listColunasMinMax = [var_strCol for var_strCol in arg_listColunasNumericas 
                                if any(var_strKeyword in var_strCol.lower() 
                                    for var_strKeyword in ["score", "percent", "rating"])]
                
                var_listColunasStandard = [var_strCol for var_strCol in arg_listColunasNumericas if var_strCol not in var_listColunasMinMax]
                
                var_listTransformers = []
                
                if var_listColunasStandard:
                    logger.info(f"Aplicando StandardScaler em {len(var_listColunasStandard)} colunas")
                    # Converter lista para tupla para garantir hashability
                    var_listTransformers.append(('standard', StandardScaler(), tuple(var_listColunasStandard)))
                
                if var_listColunasMinMax:
                    logger.info(f"Aplicando MinMaxScaler em {len(var_listColunasMinMax)} colunas")
                    # Converter lista para tupla para garantir hashability
                    var_listTransformers.append(('minmax', MinMaxScaler(), tuple(var_listColunasMinMax)))
                
                # Criar pipeline de transformação
                var_objPipeline = ColumnTransformer(
                    transformers=var_listTransformers,
                    remainder='passthrough'  # Manter outras colunas inalteradas
                )
                
                # Aplicar transformação
                var_dfScaledArray = var_objPipeline.fit_transform(var_dfCopy)
                
                # Reconstruir DataFrame
                # Obter nomes das colunas transformadas (converter tuplas de volta para listas se necessário)
                var_listColunasStandard = list(var_listColunasStandard) if isinstance(var_listColunasStandard, tuple) else var_listColunasStandard
                var_listColunasMinMax = list(var_listColunasMinMax) if isinstance(var_listColunasMinMax, tuple) else var_listColunasMinMax
                var_listColunasTransformadas = var_listColunasStandard + var_listColunasMinMax
                var_listColunasRestantes = [var_strCol for var_strCol in var_dfCopy.columns if var_strCol not in var_listColunasTransformadas]
                
                # Criar novo DataFrame
                var_dfScaled = pd.DataFrame(
                    var_dfScaledArray[:, :len(var_listColunasTransformadas)],
                    columns=[f"{var_strCol}_scaled" for var_strCol in var_listColunasTransformadas],
                    index=var_dfCopy.index
                )
                
                # Adicionar colunas restantes
                var_dfFinal = pd.concat([var_dfCopy[var_listColunasRestantes], var_dfScaled], axis=1)
                
                # Garantir que não há valores não hashable (inplace para eficiência)
                logger.debug("Verificando tipos de dados após escalonamento...")
                cls.limpar_valores_nao_hashable(var_dfFinal, arg_boolInplace=True)
                
                logger.info(f"Escalonamento concluído. Total de colunas: {len(var_dfFinal.columns)}")
                logger.info(f"{'-'*10}Escalonamento de características concluído.{'-'*10}")
                
                return var_dfFinal, var_objPipeline
            else:
                logger.warning("Nenhuma coluna numérica encontrada para escalonamento")
                return var_dfCopy, None
        except Exception as e:
            logger.error(f"Erro ao criar pipeline de escalonamento: {e}")
            raise Exception(f"Erro ao criar pipeline de escalonamento: {e}")
        
    @classmethod
    def salvar_pipeline(cls, arg_objPipeline: ColumnTransformer, 
                       arg_strNomeArquivo: str = "pipeline_escalonamento.joblib") -> str:
        """
        Salva o pipeline de transformação para reutilização.
        
        Parâmetros:
        - arg_objPipeline: Pipeline a ser salvo
        - arg_strNomeArquivo: Nome do arquivo (padrão: pipeline_escalonamento.joblib)
        
        Retorna:
        - str: Caminho completo do arquivo salvo
        """
        try:
            # Criar diretório se não existir
            var_pathDiretorio = Path(cls.PIPELINE_DIR)
            var_pathDiretorio.mkdir(parents=True, exist_ok=True)
            
            var_strCaminhoCompleto = os.path.join(var_pathDiretorio, arg_strNomeArquivo)
            
            joblib.dump(arg_objPipeline, var_strCaminhoCompleto)
            logger.info(f"Pipeline salvo em: {var_strCaminhoCompleto}")
            
            return str(var_strCaminhoCompleto)
            
        except Exception as e:
            logger.error(f"Erro ao salvar pipeline: {str(e)}")
            raise
    
    @classmethod
    def carregar_pipeline(cls, arg_strNomeArquivo: str = "pipeline_escalonamento.joblib") -> ColumnTransformer:
        """
        Carrega um pipeline de transformação salvo.
        
        Parâmetros:
        - arg_strNomeArquivo: Nome do arquivo a carregar
        
        Retorna:
        - ColumnTransformer: Pipeline carregado
        """
        try:
            var_strCaminhoCompleto = os.path.join(cls.PIPELINE_DIR, arg_strNomeArquivo)
            
            if not os.path.exists(var_strCaminhoCompleto):
                raise FileNotFoundError(f"Pipeline não encontrado: {var_strCaminhoCompleto}")
            
            var_objPipeline = joblib.load(var_strCaminhoCompleto)
            logger.info(f"Pipeline carregado de: {var_strCaminhoCompleto}")
            
            return var_objPipeline
            
        except Exception as e:
            logger.error(f"Erro ao carregar pipeline: {str(e)}")
            raise
    
    @classmethod
    def processar_completo(cls, arg_boolSalvarPipeline: bool = True) -> Tuple[pd.DataFrame, Optional[ColumnTransformer]]:
        """
        Processa todos os dados aplicando limpeza, processamento categórico e escalonamento.
        
        Parâmetros:
        - arg_boolSalvarPipeline: Se True, salva o pipeline automaticamente
        
        Retorna:
        - Tuple[pd.DataFrame, ColumnTransformer]: DataFrame processado e pipeline
        """
        try:
            with timer_context("Processamento Completo"):
                logger.info(f"{'='*50}")
                logger.info(f"Iniciando processamento completo dos dados")
                logger.info(f"{'='*50}")
                
                var_floatInicioTotal = time.time()
                cls._var_dictMetricasProcessamento = {}  # Resetar métricas
                
                # Etapa 1: Limpeza básica e merge
                logger.info("[ETAPA 1/3] Limpeza e merge de dados")
                var_dfOriginal = None  # Para relatório posterior
                var_dfLimpo = cls.processar_todos()
                logger.info(f"Etapa 1 concluída - Shape: {var_dfLimpo.shape}")
                
                # Converter arrays PostgreSQL ANTES do processamento categórico
                logger.info("Convertendo arrays PostgreSQL para strings...")
                var_dfLimpo = cls.limpar_valores_nao_hashable(var_dfLimpo, arg_boolInplace=False)  # Retornar cópia modificada
                
                # Etapa 2: Processamento de atributos categóricos
                logger.info("[ETAPA 2/3] Processamento de atributos categóricos")
                var_dfCategorico = cls.processar_categoricos(var_dfLimpo)
                logger.info(f"Etapa 2 concluída - Shape: {var_dfCategorico.shape}")
                
                # Liberar memória
                cls.limpar_memoria(var_dfLimpo)
                
                # Etapa 3: Escalonamento de características
                logger.info("[ETAPA 3/3] Escalonamento de características")                
                # Verificar integridade antes do escalonamento
                var_listColunasProblematicas = [col for col in var_dfCategorico.columns if isinstance(col, (list, tuple))]
                if var_listColunasProblematicas:
                    logger.error(f"Detectadas colunas com nomes problemáticos antes do escalonamento: {var_listColunasProblematicas[:5]}")
                    raise ValueError(f"DataFrame possui colunas com nomes não-string: {len(var_listColunasProblematicas)} colunas")
                
                var_dfFinal, var_objPipeline = cls.criar_pipeline_escalonamento(var_dfCategorico)
                logger.info(f"Etapa 3 concluída - Shape: {var_dfFinal.shape}")
                
                # Liberar memória
                cls.limpar_memoria(var_dfCategorico)
            
                # Salvar pipeline se solicitado
                if arg_boolSalvarPipeline and var_objPipeline is not None:
                    try:
                        cls.salvar_pipeline(var_objPipeline)
                    except Exception as e:
                        logger.warning(f"Não foi possível salvar pipeline: {str(e)}")
                
                # Calcular tempo total
                var_floatDuracaoTotal = time.time() - var_floatInicioTotal
                cls._var_dictMetricasProcessamento['tempo_total_segundos'] = var_floatDuracaoTotal
                cls._var_dictMetricasProcessamento['shape_final'] = var_dfFinal.shape
                
                # Verificação final já não é necessária pois convertemos no início
                logger.debug("Verificação final de integridade concluída")
                
                # Validar qualidade final
                var_boolQualidadeOk, var_listAvisos = cls.validar_qualidade_dados(var_dfFinal)
                if not var_boolQualidadeOk:
                    logger.warning(f"Avisos de qualidade: {var_listAvisos}")
                
                # Exibir resumo
                logger.info(f"{'='*50}")
                logger.info(f"PROCESSAMENTO COMPLETO FINALIZADO!")
                logger.info(f"{'='*50}")
                logger.info(f"DataFrame final: {var_dfFinal.shape[0]} linhas x {var_dfFinal.shape[1]} colunas")
                logger.info(f"Tempo total: {var_floatDuracaoTotal:.2f} segundos ({var_floatDuracaoTotal/60:.1f} minutos)")
                logger.info(f"Memória utilizada: {var_dfFinal.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
                
                if cls._var_dictMetricasProcessamento:
                    logger.info(f"Métricas do processamento:")
                    for var_strChave, var_valor in cls._var_dictMetricasProcessamento.items():
                        if isinstance(var_valor, dict):
                            logger.info(f"  {var_strChave}:")
                            for var_strSubChave, var_subValor in var_valor.items():
                                logger.info(f"    {var_strSubChave}: {var_subValor}")
                        else:
                            logger.info(f"  {var_strChave}: {var_valor}")
                
                logger.info(f"{'='*50}")
                
                return var_dfFinal, var_objPipeline
            
        except Exception as e:
            logger.error(f"Erro no processamento completo: {str(e)}", exc_info=True)
            # Fornecer informações detalhadas sobre o erro
            import traceback
            logger.error(f"Traceback completo:\n{traceback.format_exc()}")
            raise