from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB

from typing import List, Dict, Any
import re, logging
import unicodedata
from datetime import datetime

logger = logging.getLogger(__name__)

class ProcessadorETL:
    """
    Classe para processar dados brutos (steam_raw) em dados estruturados (steam_bd)
    """
    
    @staticmethod
    def normalizar_texto(arg_strTexto: str) -> str:
        """
        Remove acentuação e caracteres especiais, mantendo apenas ASCII.
        Converte caracteres corrompidos (Ingl??s) para formato limpo (Ingles).

        Parametros:
        - arg_strTexto (str): Texto para normalizar

        Retorna:
        - str: Texto normalizado sem acentuação
        
        Exemplo: "Português" -> "Portugues", "Ingl??s" -> "Ingles"
        """
        if not arg_strTexto:
            return arg_strTexto
        
        # Mapa de correções para palavras corrompidas conhecidas
        var_dictCorrecoes = {
            'Ingl??s': 'Ingles',
            'Portugu??s': 'Portugues',
            'Alem??o': 'Alemao',
            'Japon??s': 'Japones',
            'Franc??s': 'Frances',
            'Chin??s': 'Chines',
            'Italiano': 'Italiano',
            'Espa??ol': 'Espanhol',
            'Coreano': 'Coreano',
            'Russo': 'Russo',
            # Gêneros corrompidos
            'a????o': 'Acao',
            'A????o': 'Acao',
            'Aventura': 'Aventura',
            'Estrat??gia': 'Estrategia',
            'Simula????o': 'Simulacao',
            'simula????o': 'Simulacao'
        }
        
        # Aplica correções conhecidas
        var_strCorrigido = arg_strTexto
        for var_strCorreto, var_strSubstituto in var_dictCorrecoes.items():
            var_strCorrigido = var_strCorrigido.replace(var_strCorreto, var_strSubstituto)
        
        # Remove caracteres corrompidos restantes
        var_strLimpo = var_strCorrigido.replace('?', '').replace('�', '')
        
        # Normaliza NFD (decompõe caracteres acentuados)
        var_strNormalizado = unicodedata.normalize('NFD', var_strLimpo)
        
        # Remove marcas diacríticas (acentos)
        var_strSemAcento = ''.join(
            char for char in var_strNormalizado 
            if unicodedata.category(char) != 'Mn'
        )
        
        # Remove espaços duplicados e limpa
        var_strFinal = ' '.join(var_strSemAcento.split())
        
        return var_strFinal
    
    @staticmethod
    def extrair_campo_seguro(arg_dictDados: Dict, *arg_strCaminho: str, arg_anyPadrao: Any = None) -> Any:
        """
        Extrai campo de forma segura de um dicionário aninhado.

        Parametros:
        - arg_dictDados (dict): Dicionário de onde extrair o campo
        - arg_strCaminho (str): Sequência de chaves para acessar o campo
        - arg_anyPadrao (Any): Valor padrão se o campo não existir

        Retorna:
        - Any: Valor extraído ou valor padrão se não existir
        
        Exemplo: extrair_campo_seguro(dados, "price_overview", "final", arg_anyPadrao=0)
        """
        var_dictResultado = arg_dictDados
        for arg_strChave in arg_strCaminho:
            if isinstance(var_dictResultado, dict):
                var_dictResultado = var_dictResultado.get(arg_strChave)
            else:
                return arg_anyPadrao
            if var_dictResultado is None:
                return arg_anyPadrao
        return var_dictResultado if var_dictResultado is not None else arg_anyPadrao
    
    @staticmethod
    def processar_classificacao_etaria(arg_intRequiredAge: int) -> str:
        """
        Converte classificação etária numérica para formato brasileiro.
        
        Parametros:
        - arg_intRequiredAge (int): Idade mínima requerida (0, 12, 14, 16, 18)
        
        Retorna:
        - str: Classificação etária formatada ("L", "12", "14", "16", "18")
        """
        if not arg_intRequiredAge or arg_intRequiredAge == 0:
            return "L"  # Livre
        
        # Mapeia idades para classificações brasileiras
        var_dictClassificacoes = {
            10: "10",
            12: "12",
            14: "14",
            16: "16",
            18: "18"
        }
        
        # Retorna a classificação ou a idade como string se não estiver no mapa
        return var_dictClassificacoes.get(arg_intRequiredAge, str(arg_intRequiredAge))
    
    @staticmethod
    def processar_preco(arg_dictPriceOverview: Dict) -> str:
        """
        Converte informação de preço para formato legível

        Parametros:
        - arg_dictPriceOverview (dict): Dicionário com informações de preço

        Retorna:
        - str: Preço formatado como string
        """
        if not arg_dictPriceOverview:
            return "Gratuito"
        
        var_floatFinalPrice = arg_dictPriceOverview.get("final", 0)
        var_strCurrency = arg_dictPriceOverview.get("currency", "BRL")
        
        if var_floatFinalPrice == 0:
            return "Gratuito"
        
        # Converte centavos para reais
        var_floatValor = var_floatFinalPrice / 100
        
        var_dictSimbolos = {
            "BRL": "R$",
            "USD": "$",
            "EUR": "€"
        }
        
        var_strSimbolo = var_dictSimbolos.get(var_strCurrency, var_strCurrency)
        return f"{var_strSimbolo} {var_floatValor:.2f}"
    
    @staticmethod
    def processar_categorias(arg_listCategories: List[Dict]) -> List[str]:
        """
        Extrai descrições das categorias e remove acentuação

        Parametros:
        - arg_listCategories (list): Lista de dicionários com categorias

        Retorna:
        - List[str]: Lista de descrições das categorias (sem acentuação)
        """
        if not arg_listCategories:
            return []
        
        # Extrai descrições e normaliza texto
        var_listCategorias = [
            ProcessadorETL.normalizar_texto(cat.get("description", ""))
            for cat in arg_listCategories 
            if cat.get("description")
        ]
        
        return var_listCategorias
    
    @staticmethod
    def processar_generos(arg_listGenres: List[Dict]) -> List[str]:
        """
        Extrai descrições dos gêneros e remove acentuação

        Parametros:
        - arg_listGenres (list): Lista de dicionários com gêneros

        Retorna:
        - List[str]: Lista de descrições dos gêneros sem acentuação e sem duplicatas
        """
        if not arg_listGenres:
            return []
        
        var_listGeneros = [gen.get("description", "") for gen in arg_listGenres if gen.get("description")]
        
        # Normaliza cada gênero (remove acentuação)
        var_listNormalizados = [
            ProcessadorETL.normalizar_texto(var_strGenero) 
            for var_strGenero in var_listGeneros
        ]
        
        # Remove duplicatas mantendo a ordem
        var_listSemDuplicatas = []
        var_setVistos = set()
        for var_strGenero in var_listNormalizados:
            if var_strGenero not in var_setVistos:
                var_listSemDuplicatas.append(var_strGenero)
                var_setVistos.add(var_strGenero)
        
        return var_listSemDuplicatas
    
    @staticmethod
    def processar_linguas(arg_strSupportedLanguages: str) -> List[str]:
        """
        Processa string de linguagens suportadas e remove acentuação

        Parametros:
        - arg_strSupportedLanguages (str): String com linguagens suportadas

        Retorna:
        - List[str]: Lista de linguagens suportadas sem acentuação
        """
        if not arg_strSupportedLanguages:
            return []
        
        # Remove tags HTML e extras
        var_strLimpo = re.sub(r'<[^>]+>', '', arg_strSupportedLanguages)
        var_strLimpo = re.sub(r'\*[^*]+\*', '', var_strLimpo)
        
        # Separa por vírgula e limpa
        var_listLinguas = [l.strip() for l in var_strLimpo.split(',')]
        
        # Normaliza cada língua (remove acentuação e caracteres corrompidos)
        var_listNormalizadas = [
            ProcessadorETL.normalizar_texto(var_strLingua) 
            for var_strLingua in var_listLinguas 
            if var_strLingua
        ]
        
        return var_listNormalizadas[:10]  # Limita a 10
    
    @staticmethod
    def processar_data_lancamento(arg_strDate: str) -> str:
        """
        Converte data de lançamento para formato ISO (YYYY-MM-DD).
        
        Parametros:
        - arg_strDate (str): Data em diversos formatos (ex: "1/Nov/2000", "Nov 1, 2000", "2000-11-01")
        
        Retorna:
        - str: Data no formato ISO (YYYY-MM-DD) ou string vazia se inválida
        
        Exemplos:
        - "1 Nov, 2000" -> "2000-11-01"
        - "Nov 1, 2000" -> "2000-11-01"
        - "1/Nov/2000" -> "2000-11-01"
        - "2000-11-01" -> "2000-11-01"
        """
        if not arg_strDate or arg_strDate.strip() == "":
            return ""
        
        # Ignora textos descritivos
        var_listTextosDescritivos = [
            'em breve', 'a ser anunciada', 'coming soon', 'tba', 'to be announced',
            'trimestre', 'quarter', 'q1', 'q2', 'q3', 'q4'
        ]
        if any(texto in arg_strDate.lower() for texto in var_listTextosDescritivos):
            return "EM BREVE"
        
        # Mapa de meses em diferentes idiomas
        var_dictMeses = {
            # Português
            'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
            # Inglês
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            # Espanhol
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
            # Meses por extenso em inglês
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        try:
            # Remove espaços extras e normaliza
            var_strDataLimpa = arg_strDate.strip()
            
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
            logger.warning(f"Formato de data não reconhecido: {arg_strDate}")
            return ""
            
        except Exception as e:
            logger.warning(f"Erro ao processar data '{arg_strDate}': {e}")
            return ""
    
    @staticmethod
    def transformar_raw_para_bd(arg_dictDadosRaw: Dict) -> Dict:
        """
        Transforma dados brutos em dados estruturados
        
        Parametros:
        - arg_dictDadosRaw (dict): Dicionário com steam_appid, detalhes, reviews
        
        Retorna:
        - dict: Dicionário estruturado para steam_bd
        """
        var_dictDetalhes = arg_dictDadosRaw.get("detalhes", {})
        var_dictReviews = arg_dictDadosRaw.get("reviews", {})
        
        if var_dictDetalhes == "AUSENTE":
            raise ValueError(f"Detalhes ausentes para AppID {arg_dictDadosRaw.get('steam_appid')}")
        
        # Tenta pegar appid de diferentes campos possíveis
        var_intAppid = (
            arg_dictDadosRaw.get("steam_appid") or 
            arg_dictDadosRaw.get("appid") or 
            ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "steam_appid")
        )
        
        return {
            "appid": var_intAppid,
            "nome": ProcessadorETL.normalizar_texto(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "name", arg_anyPadrao="Desconhecido")
            ),
            "classificacao_etaria": ProcessadorETL.processar_classificacao_etaria(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "required_age", arg_anyPadrao=0)
            ),
            "linguagens": ProcessadorETL.processar_linguas(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "supported_languages", arg_anyPadrao="")
            ),
            "desenvolvedores": [
                ProcessadorETL.normalizar_texto(dev) 
                for dev in ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "developers", arg_anyPadrao=[])
            ],
            "distribuidores": [
                ProcessadorETL.normalizar_texto(pub) 
                for pub in ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "publishers", arg_anyPadrao=[])
            ],
            "preco": ProcessadorETL.processar_preco(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "price_overview")
            ),
            "metacritic_score": str(ProcessadorETL.extrair_campo_seguro(
                var_dictDetalhes, "metacritic", "score", arg_anyPadrao=""
            )),
            "categorias": ProcessadorETL.processar_categorias(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "categories", arg_anyPadrao=[])
            ),
            "genero": ProcessadorETL.processar_generos(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "genres", arg_anyPadrao=[])
            ),
            "data_lancamento": ProcessadorETL.processar_data_lancamento(
                ProcessadorETL.extrair_campo_seguro(
                    var_dictDetalhes, "release_date", "date", arg_anyPadrao=""
                )
            ),
            "review_score": ProcessadorETL.extrair_campo_seguro(var_dictReviews, "review_score", arg_anyPadrao=0),
            "total_reviews": ProcessadorETL.extrair_campo_seguro(var_dictReviews, "total_reviews", arg_anyPadrao=0),
            "total_negative": ProcessadorETL.extrair_campo_seguro(var_dictReviews, "total_negative", arg_anyPadrao=0),
            "total_positive": ProcessadorETL.extrair_campo_seguro(var_dictReviews, "total_positive", arg_anyPadrao=0),
            "review_score_desc": ProcessadorETL.normalizar_texto(
                ProcessadorETL.extrair_campo_seguro(var_dictReviews, "review_score_desc", arg_anyPadrao="")
            )
        }
    
    @staticmethod
    def processar_lote(arg_listAppids: List[int]) -> None:
        """
        Processa um lote de AppIDs do Docker para o Supabase
        
        Parametros:
        - arg_listAppids: Lista de AppIDs para processar
        """
        logger.info(f"Processando {len(arg_listAppids)} jogos...")
        
        # Garante conexão com o Docker
        PostgreSQL.conectar()
        
        # 1. Buscar dados brutos do Docker
        var_listDadosBrutos = []
        for var_intAppid in arg_listAppids:
            try:
                var_dictDados = PostgreSQL.buscar_dados(var_intAppid, "steam_raw")
                if var_dictDados:
                    # Adiciona o appid ao dicionário se não estiver presente
                    if "appid" not in var_dictDados:
                        var_dictDados["appid"] = var_intAppid
                    var_listDadosBrutos.append(var_dictDados)
            except Exception as e:
                logger.info(f"logger.infoErro ao buscar AppID {var_intAppid}: {e}")
        
        logger.info(f"{len(var_listDadosBrutos)} jogos encontrados no Docker")
        
        # 2. Transformar dados
        var_listDadosEstruturados = []
        for var_dictDadosRaw in var_listDadosBrutos:
            try:
                var_dictDadosBD = ProcessadorETL.transformar_raw_para_bd(var_dictDadosRaw)
                var_listDadosEstruturados.append(var_dictDadosBD)
            except Exception as e:
                logger.error(f"Erro ao processar AppID {var_dictDadosRaw.get('appid')}: {e}")
        
        logger.info(f"{len(var_listDadosEstruturados)} jogos transformados com sucesso")
        
        # 3. Inserir no Supabase
        if var_listDadosEstruturados:
            try:
                SupabaseDB.inserir_dadosSteamBD(var_listDadosEstruturados)
                logger.info(f"{len(var_listDadosEstruturados)} jogos inseridos no Supabase!")
            except Exception as e:
                logger.error(f"Erro ao inserir no Supabase: {e}")