from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam

from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

class LimparDataLancamento:
    """
    Classe responsável por limpar e padronizar o campo "data_lancamento" dos jogos.
    """

    @classmethod
    def processar_data_lancamento(cls, arg_dictDate: dict) -> str:
        """
        Converte data de lançamento para formato ISO (YYYY-MM-DD).
        
        Parametros:
        - arg_dictDate (dict): Dicionário contendo a data de lançamento em diversos formatos, com chaves como "date" e "coming_soon".
        
        Retorna:
        - str: Data no formato ISO (YYYY-MM-DD) ou string vazia se inválida
        
        Exemplos:
        - "1 Nov, 2000" -> "2000-11-01"
        - "Nov 1, 2000" -> "2000-11-01"
        - "1/Nov/2000" -> "2000-11-01"
        - "2000-11-01" -> "2000-11-01"
        - "2025" -> "2025-01-01"
        - "abril de 2026" -> "2026-04-01"
        """
        var_strDataFinal = "Desconhecido"  # Inicializa a variável
        var_strDataLimpa = ""
        
        try:
            if not isinstance(arg_dictDate, dict):
                raise Exception(f"Esperado dict para data de lançamento, recebido {type(arg_dictDate)}: {arg_dictDate}")
            
            var_dictMeses = cls._dicionario_traducao_data_lancamento()
            var_boolEmBreve = arg_dictDate.get("coming_soon")
            var_strData = arg_dictDate.get("date")
            var_strData = var_strData.strip() if var_strData else "Desconhecido"
            
            # Verificar se já está no formato ISO (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{2}-\d{2}$', var_strData):
                var_strDataFinal = var_strData
                var_strDataLimpa = var_strData
                return var_strDataFinal
            
            # Normalizar data: remover 'de' e converter para minúsculas
            var_strDataLimpa = var_strData.replace(' de ', ' ').lower().strip()
            
            # Verificar se não é status textual (buscar em todas as chaves do dicionário)
            for var_strKey, var_strValue in var_dictMeses.items():
                if isinstance(var_strKey, tuple):
                    if var_strDataLimpa in var_strKey:
                        var_strDataFinal = var_strValue
                        return var_strDataFinal

            # Verifica se é um texto de Trimestre ou similar (ex: "Q3 2020")
            var_reMatchTrimestre1 = re.search(r'q([1-4])\s+(\d{4})', var_strDataLimpa, re.IGNORECASE)

            if var_reMatchTrimestre1:
                var_strTrimestre = var_reMatchTrimestre1.group(1)
                var_strAno = var_reMatchTrimestre1.group(2)
                var_strChaveTrimestre = 'q' + var_strTrimestre
                
                # Buscar o template de trimestre no dicionário
                for var_strKey, var_strValue in var_dictMeses.items():
                    if isinstance(var_strKey, tuple) and var_strChaveTrimestre in var_strKey:
                        var_strDataFinal = var_strValue.replace('<ANO>', var_strAno)
                        return var_strDataFinal

            var_reMatchAno = re.search(r'\b(19\d{2}|20\d{2})\b', var_strDataLimpa, re.IGNORECASE)
            if not var_reMatchAno:
                var_strDataFinal = "Desconhecido"
                return var_strDataFinal
            
            var_strAno = var_reMatchAno.group(1)

            var_strMes = "01"
            var_strDataLimpa = var_strDataLimpa.replace('.', '').replace(',', '')

            # Buscar mês no texto
            for var_strKey, var_intValue in var_dictMeses.items():
                if isinstance(var_strKey, tuple):
                    var_reSearch = None
                    for var_strAlias in var_strKey:
                        var_reSearch = re.search(r'\b' + re.escape(var_strAlias) + r'\b', var_strDataLimpa, re.IGNORECASE)
                        if var_reSearch:
                            var_strMes = str(var_intValue)
                            break
                    
                    if var_reSearch:
                        break
            
            var_strDia = "01"
            var_reMatchDia = re.search(r'\b(\d{1,2})\b', var_strDataLimpa)
            if var_reMatchDia:
                var_strDia = var_reMatchDia.group(1).zfill(2)

            var_strDataFinal = f"{var_strAno}-{var_strMes}-{var_strDia}"

        except Exception as e:
            logger.warning(f"Erro ao processar data: {e}")
            var_strDataFinal = "Desconhecido"
        
        finally:
            return var_strDataFinal

    @classmethod
    def _dicionario_traducao_data_lancamento(cls) -> dict[str, str]:
        """
        Retorna dicionário de tradução para correção de textos corrompidos em data de lançamento.
        
        Retorna:
        - dict[str, str]: Dicionário de texto corrompido -> texto corrigido
        """
        return {
            # MESES
            ('jan', 'ene', 'janeiro', 'january', '01'): '01',
            ('fev', 'feb', 'fevereiro', 'february', '02'): '02',
            ('mar', 'marco', 'março', 'mar??o', 'march', '03'): '03',
            ('abr', 'apr', 'abril', 'april', '04'): '04',
            ('mai', 'may', 'maio', '05'): '05',
            ('jun', 'junho', 'june', '06'): '06',
            ('jul', 'julho', 'july', '07'): '07',
            ('ago', 'aug', 'agosto', 'august', '08'): '08',
            ('set', 'sep', 'setembro', 'september', '09'): '09',
            ('out', 'oct', 'outubro', 'october', '10'): '10',
            ('nov', 'novembro', 'november', '11'): '11',
            ('dez', 'dec', 'dic', 'dezembro', 'december', '12'): '12',

            # A SER ANUNCIADO
            ('coming soon', 'to be announced', 'tba', 'maybe'): 'EM BREVE',
            ('a ser anunciada', 'em breve'): 'EM BREVE',

            ('q1', 'quarter 1', 'trimestre 1'): '<ANO>-03-31',
            ('q2', 'quarter 2', 'trimestre 2'): '<ANO>-06-30',
            ('q3', 'quarter 3', 'trimestre 3'): '<ANO>-09-30',
            ('q4', 'quarter 4', 'trimestre 4'): '<ANO>-12-31',
        }