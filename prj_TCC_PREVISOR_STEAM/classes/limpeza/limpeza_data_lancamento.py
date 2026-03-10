from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_steam import PostgreSQLSteam

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
        - arg_strDate (str): Data em diversos formatos (ex: "1/Nov/2000", "Nov 1, 2000", "2000-11-01", "2025", "abril de 2026")
        
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
        if not isinstance(arg_dictDate, dict):
            raise Exception(f"Esperado dict para data de lançamento, recebido {type(arg_dictDate)}")
        
        var_dictMeses = cls._dicionario_traducao_data_lancamento()
        var_boolEmBreve = arg_dictDate.get("coming_soon")
        var_strData = arg_dictDate.get("date")
        var_strData = var_strData.replace(' de ', '').lower().strip() if var_strData else "Desconhecido"
        
        # Se for "coming soon" ou equivalente, e a data atual já passou da data indicada, considera como "EM BREVE"
        # if var_boolEmBreve:
        #     return "EM BREVE"

        # Verificar se não é status textutal
        if var_strData in var_dictMeses:
            return var_dictMeses[var_strData]

        # Verifica se é um texto de Trimestre ou similar
        var_reMatchTrimestre = re.search(r'(q[1-4]|quarter\s*[1-4]|trimestre\s*[1-4])', var_strData, re.IGNORECASE)
        var_reMatchTrimestre1 = re.search(r'q([1-4])\s+(\d{4})', var_strData, re.IGNORECASE)

        if var_reMatchTrimestre1:
            var_strTrimestre = var_reMatchTrimestre.group(1)
            var_strAno = var_reMatchTrimestre.group(2)
            var_strDataTrimestre = var_dictMeses.get(var_strTrimestre.lower())
            var_strData = var_strDataTrimestre.replace('<ANO>', var_strAno)

        var_reMatchAno = re.search(r'\b(19\d{2}|20\d{2})\b', var_strData, re.IGNORECASE)
        if not var_reMatchAno:
            return "EM BREVE"
        
        var_strAno = var_reMatchAno.group(1)

        var_strMes = "01"
        var_strDataLimpa = var_strData.replace('.', '')

        for var_strKey, var_intValue in var_dictMeses.items():
            var_reSearch = re.search(r'\b' + re.escape(var_strKey) + r'\b', var_strDataLimpa, re.IGNORECASE)
            # Usa \b para garantir que apanha a palavra exata
            if var_reSearch:
                var_strMes = str(var_intValue)
                break
            
        # Trata formato "mês de ano" (ex: "abril de 2026", "agosto de 2027")
        var_matchMesAno = re.search(r'([a-zA-ZçÇ]+)\s+(?:de\s+)?(\d{4})', var_strData.lower())
        if var_matchMesAno:
            var_strMes = var_matchMesAno.group(1).lower()
            var_strAno = var_matchMesAno.group(2)
            
            # Busca o mês no dicionário (usando primeiras 3 letras ou nome completo)
            var_intMes = None
            if var_strMes in var_dictMeses:
                var_intMes = var_dictMeses[var_strMes]
            elif var_strMes[:3] in var_dictMeses:
                var_intMes = var_dictMeses[var_strMes[:3]]
            
            if var_intMes:
                return f"{var_strAno}-{var_intMes:02d}-01"
        
        try:
            # Remove espaços extras e normaliza
            var_strDataLimpa = var_strData.strip()
            
            # Trata formato especial D/MMM./AAAA (ex: 22/fev./2018)
            # Remove pontos que aparecem após abreviações de mês
            var_strDataLimpa = re.sub(r'([a-z]{3})\.', r'\1', var_strDataLimpa, flags=re.IGNORECASE)
            
            # Remove pontos restantes e normaliza espaços
            var_strDataLimpa = var_strDataLimpa.replace('.', '')
            var_strDataLimpa = ' '.join(var_strDataLimpa.split())
            
            # Tenta parsing manual para formato D/MMM/AAAA (ex: 22/fev/2018)
            if '/' in var_strDataLimpa:
                var_listPartesBarra = var_strDataLimpa.split('/')
                if len(var_listPartesBarra) == 3:
                    var_strPrimeiro = var_listPartesBarra[0]
                    var_strSegundo = var_listPartesBarra[1].lower()
                    var_strTerceiro = var_listPartesBarra[2]
                    
                    # Verifica se é D/MMM/AAAA
                    if var_strPrimeiro.isdigit() and var_strSegundo[:3] in var_dictMeses and var_strTerceiro.isdigit():
                        var_intDia = int(var_strPrimeiro)
                        var_intMes = var_dictMeses[var_strSegundo[:3]]
                        var_intAno = int(var_strTerceiro)
                        return f"{var_intAno:04d}-{var_intMes:02d}-{var_intDia:02d}"
            
            # Tenta vários formatos comuns
            var_listFormatos = [
                '%Y-%m-%d',           # 2000-11-01
                '%d %b, %Y',          # 1 Nov, 2000
                '%b %d, %Y',          # Nov 1, 2000
                '%d/%b/%Y',           # 1/Nov/2000, 1/fev/2018
                '%d %B, %Y',          # 1 November, 2000
                '%B %d, %Y',          # November 1, 2000
                '%d/%m/%Y',           # 01/11/2000
                '%m/%d/%Y',           # 11/01/2000
                '%Y/%m/%d',           # 2000/11/01
                '%d-%m-%Y',           # 01-11-2000
                '%m-%d-%Y',           # 11-01-2000
            ]
            
            # Tenta parsear com formatos conhecidos
            for var_strFormato in var_listFormatos:
                try:
                    # Para formatos com mês abreviado, precisa estar em minúsculas
                    var_strDataParaTeste = var_strDataLimpa
                    if '%b' in var_strFormato or '%B' in var_strFormato:
                        var_strDataParaTeste = var_strDataLimpa.lower()
                    
                    var_dateData = datetime.strptime(var_strDataParaTeste, var_strFormato)
                    return var_dateData.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Se não deu certo, tenta parsear manualmente para formatos como "1 Nov, 2000"
            # Remove vírgulas e divide
            var_strDataSemVirgula = var_strDataLimpa.replace(',', '')
            var_listPartes = var_strDataSemVirgula.split()
            
            if len(var_listPartes) == 3:
                # Formato: dia mês ano ou mês dia ano
                var_strPrimeiro = var_listPartes[0].lower()
                var_strSegundo = var_listPartes[1].lower()
                var_strTerceiro = var_listPartes[2]
                
                # Tenta dia mês ano
                if var_strPrimeiro.isdigit() and var_strSegundo[:3] in var_dictMeses:
                    var_intDia = int(var_strPrimeiro)
                    var_intMes = var_dictMeses[var_strSegundo[:3]]
                    var_intAno = int(var_strTerceiro)
                    return f"{var_intAno:04d}-{var_intMes:02d}-{var_intDia:02d}"
                
                # Tenta mês dia ano
                elif var_strPrimeiro[:3] in var_dictMeses and var_strSegundo.isdigit():
                    var_intMes = var_dictMeses[var_strPrimeiro[:3]]
                    var_intDia = int(var_strSegundo)
                    var_intAno = int(var_strTerceiro)
                    return f"{var_intAno:04d}-{var_intMes:02d}-{var_intDia:02d}"
            
            # Se chegou aqui, não conseguiu parsear
            logger.warning(f"Formato de data não reconhecido: {var_strDataSemVirgula}")
            return ""
            
        except Exception as e:
            logger.warning(f"Erro ao processar data: {e}")
            return ""

    @classmethod
    def _dicionario_traducao_data_lancamento(cls) -> dict[str, str]:
        """
        Retorna dicionário de tradução para correção de textos corrompidos em data de lançamento.
        
        Retorna:
        - dict[str, str]: Dicionário de texto corrompido -> texto corrigido
        """
        return {
            # MESES
            ('jan', 'ene', 'janeiro', 'january'): 1,
            ('fev', 'feb', 'fevereiro', 'february'): 2,
            ('mar', 'marco', 'março', 'mar??o', 'march'): 3,
            ('abr', 'apr', 'abril', 'april'): 4,
            ('mai', 'may', 'maio'): 5,
            ('jun', 'junho', 'june'): 6,
            ('jul', 'julho', 'july'): 7,
            ('ago', 'aug', 'agosto', 'august'): 8,
            ('set', 'sep', 'setembro', 'september'): 9,
            ('out', 'oct', 'outubro', 'october'): 10,
            ('nov', 'novembro', 'november'): 11,
            ('dez', 'dec', 'dic', 'dezembro', 'december'): 12,

            # A SER ANUNCIADO
            ('coming soon', 'to be announced', 'tba', 'maybe'): 'EM BREVE',
            ('a ser anunciada', 'em breve'): 'EM BREVE',

            ('q1', 'quarter 1', 'trimestre 1'): '<ANO>-03-31',
            ('q2', 'quarter 2', 'trimestre 2'): '<ANO>-06-30',
            ('q3', 'quarter 3', 'trimestre 3'): '<ANO>-09-30',
            ('q4', 'quarter 4', 'trimestre 4'): '<ANO>-12-31',
        }