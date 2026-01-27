from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.database import PostgreSQL

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
        Remove acentuação e caracteres especiais usando normalização NFKD.

        Parametros:
        - arg_strTexto (str): Texto para normalizar

        Retorna:
        - str: Texto normalizado sem acentuação
        
        Exemplo: "Português™" -> "PortuguesTM", "①Action" -> "1Action"
        """
        if not arg_strTexto:
            return arg_strTexto
        
        # Mapeamento direto para textos corrompidos conhecidos
        var_dictCorrecoes = {
            'Ingl??s': 'Ingles',
            'Portugu??s': 'Portugues',
            'Portugu??s (Brasil)': 'Portugues (Brasil)',
            'Franc??s': 'Frances',
            'Alem??o': 'Alemao',
            'Alem??oidiomas com suporte total de ??udio': 'Alemao',  # Corrige texto grudado
            'Espanhol': 'Espanhol',
            'Japon??s': 'Japones',
            'Chin??s simplificado': 'Chines simplificado',
            'Chin??s tradicional': 'Chines tradicional',
            'Russo': 'Russo',
            'Coreano': 'Coreano',
            'Tailand??s': 'Tailandes',
            'Italiano': 'Italiano',
            'Espanhol (Am??rica Latina)': 'Espanhol (America Latina)',
            'Espanhol (Espanha)': 'Espanhol (Espanha)',
            'A????o': 'Acao',
            'Demonstra????o de jogo': 'Demonstracao de jogo',
            'Op????o apenas com teclado': 'Opcao apenas com teclado',
            'Nenhuma an??lise de usu??rio': 'Nenhuma analise de usuario',
            'fam??lia': 'familia',
            'Compartilhamento em fam??lia': 'Compartilhamento em familia',
            'c??mera': 'camera',
            'Conforto de c??mera': 'Conforto de camera',
            'Som est??reo': 'Som estereo',
            'Dificuldade ajust??vel': 'Dificuldade ajustavel',
            'Texto de tamanho ajust??vel': 'Texto de tamanho ajustavel',
            'Cartas Colecion??veis Steam': 'Cartas Colecionaveis Steam',
            'idiomas com suporte total de ??udio': 'idiomas com suporte total de audio'
        }
        
        # Verifica correção direta primeiro
        if arg_strTexto in var_dictCorrecoes:
            return var_dictCorrecoes[arg_strTexto]
        
        # Se contém ??, remove toda parte corrompida
        if '??' in arg_strTexto:
            # Substitui sequências ?? por nada (remove caracteres corrompidos)
            var_strTexto = re.sub(r'\?+', '', arg_strTexto)
        else:
            var_strTexto = arg_strTexto
        
        # Normaliza NFKD (decompõe e normaliza compatibilidade)
        var_strNormalizado = unicodedata.normalize('NFKD', var_strTexto)
        
        # Remove marcas diacríticas (acentos)
        var_strSemAcento = ''.join(
            char for char in var_strNormalizado 
            if unicodedata.category(char) != 'Mn'
        )
        
        # Remove caracteres de controle
        var_strLimpo = ''.join(
            char for char in var_strSemAcento
            if char.isprintable() or char.isspace()
        )
        
        # Remove espaços duplicados
        var_strFinal = ' '.join(var_strLimpo.split())
        
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
        var_listNormalizadas = []
        for var_strLingua in var_listLinguas:
            if var_strLingua:
                var_strNormalizado = ProcessadorETL.normalizar_texto(var_strLingua)
                
                # Filtra entradas inválidas ou redundantes
                if var_strNormalizado and len(var_strNormalizado) > 2:
                    # Ignora se é apenas descrição de suporte de áudio
                    if var_strNormalizado.lower() not in ['idiomas com suporte total de audio', 'idiomas']:
                        var_listNormalizadas.append(var_strNormalizado)
        
        # Remove duplicatas mantendo ordem
        var_listUnicas = []
        for lang in var_listNormalizadas:
            if lang not in var_listUnicas:
                var_listUnicas.append(lang)
        
        return var_listUnicas[:10]  # Limita a 10
    
    @staticmethod
    def processar_data_lancamento(arg_strDate: str) -> str:
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
        if not arg_strDate or arg_strDate.strip() == "":
            return ""
        
        # Ignora textos descritivos
        var_listTextosDescritivos = [
            'em breve', 'a ser anunciada', 'coming soon', 'tba', 'to be announced',
            'trimestre', 'quarter', 'q1', 'q2', 'q3', 'q4', 'maybe'
        ]
        if any(texto in arg_strDate.lower() for texto in var_listTextosDescritivos):
            return "EM BREVE"
        
        # Trata apenas ano (ex: "2025", "2026", "2027")
        var_strDataLimpa = arg_strDate.strip()
        if var_strDataLimpa.isdigit() and len(var_strDataLimpa) == 4:
            var_intAno = int(var_strDataLimpa)
            # Valida ano razoável (1990-2030)
            if 1990 <= var_intAno <= datetime.now().year + 5:
                return f"{var_intAno}-01-01"
            else:
                logger.warning(f"Ano fora do intervalo esperado: {var_strDataLimpa}")
                return "EM BREVE"
        
        # Mapa de meses em diferentes idiomas
        var_dictMeses = {
            # Português
            'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
            'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6,
            'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
            # Inglês
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
            # Espanhol
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
        }
        
        # Trata formato "mês de ano" (ex: "abril de 2026", "agosto de 2027")
        var_matchMesAno = re.search(r'([a-zA-ZçÇ]+)\s+(?:de\s+)?(\d{4})', var_strDataLimpa.lower())
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
        # Validação inicial: verifica se há dados
        if not arg_dictDadosRaw:
            raise ValueError("Dicionário de dados está vazio")
        
        # Tenta pegar appid de diferentes campos possíveis
        var_intAppid = arg_dictDadosRaw.get("appid")
        
        # Validação: AppID deve existir
        if not var_intAppid:
            raise ValueError("AppID não encontrado nos dados brutos")
        
        # Extrai detalhes e reviews
        var_dictDetalhes = arg_dictDadosRaw.get("detalhes")
        var_dictReviews = arg_dictDadosRaw.get("reviews", {})
        
        # Validação crítica: detalhes não podem ser None ou "AUSENTE"
        if var_dictDetalhes is None or var_dictDetalhes == "AUSENTE" or not isinstance(var_dictDetalhes, dict):
            raise ValueError(f"Detalhes ausentes para AppID {var_intAppid}")
        
        # Se detalhes está vazio, tenta extrair do próprio arg_dictDadosRaw
        if not var_dictDetalhes:
            # Alguns registros podem ter detalhes diretamente no dicionário principal
            if "name" in arg_dictDadosRaw:
                var_dictDetalhes = arg_dictDadosRaw
            else:
                raise ValueError(f"Detalhes vazios para AppID {var_intAppid}")
        var_dictDadosTransformados = {}
        var_dictDadosTransformados['appid'] = var_intAppid
        
        # Nome: normaliza e trunca em 255 caracteres (limite do PostgREST)
        var_strNome = ProcessadorETL.normalizar_texto(
            ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "name", arg_anyPadrao="Desconhecido")
        )
        var_dictDadosTransformados["nome"] = var_strNome[:255] if len(var_strNome) > 255 else var_strNome
        
        var_dictDadosTransformados["classificacao_etaria"] = ProcessadorETL.processar_classificacao_etaria(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "required_age", arg_anyPadrao=0)
            )
        var_dictDadosTransformados['linguagens'] = ProcessadorETL.processar_linguas(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "supported_languages", arg_anyPadrao="")
            )
        var_dictDadosTransformados["desenvolvedores"] = [
                ProcessadorETL.normalizar_texto(dev) 
                for dev in ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "developers", arg_anyPadrao=[])
            ]
        var_dictDadosTransformados["distribuidores"] = [
                ProcessadorETL.normalizar_texto(pub) 
                for pub in ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "publishers", arg_anyPadrao=[])
            ]
        var_dictDadosTransformados["preco"] = ProcessadorETL.processar_preco(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "price_overview")
            )
        var_dictDadosTransformados["metacritic_score"] = str(ProcessadorETL.extrair_campo_seguro(
                var_dictDetalhes, "metacritic", "score", arg_anyPadrao=""
            ))
        var_dictDadosTransformados['categorias'] = ProcessadorETL.processar_categorias(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "categories", arg_anyPadrao=[])
            )
        var_dictDadosTransformados["genero"] = ProcessadorETL.processar_generos(
                ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "genres", arg_anyPadrao=[])
            )
        var_dictDadosTransformados["data_lancamento"] = ProcessadorETL.processar_data_lancamento(
                ProcessadorETL.normalizar_texto(
                    ProcessadorETL.extrair_campo_seguro(
                        var_dictDetalhes, "release_date", "date", arg_anyPadrao=""
                    )
                )
            )
        var_dictDadosTransformados['review_score'] =  ProcessadorETL.extrair_campo_seguro(var_dictReviews, "review_score", arg_anyPadrao=0)
        var_dictDadosTransformados["total_reviews"] = ProcessadorETL.extrair_campo_seguro(var_dictReviews, "total_reviews", arg_anyPadrao=0)
        var_dictDadosTransformados["total_negative"] = ProcessadorETL.extrair_campo_seguro(var_dictReviews, "total_negative", arg_anyPadrao=0)
        var_dictDadosTransformados["total_positive"] = ProcessadorETL.extrair_campo_seguro(var_dictReviews, "total_positive", arg_anyPadrao=0)
        var_dictDadosTransformados["review_score_desc"] = ProcessadorETL.normalizar_texto(
            ProcessadorETL.extrair_campo_seguro(var_dictReviews, "review_score_desc", arg_anyPadrao="")
            )
        
        # Extrai o tipo do jogo (game, dlc, bundle, etc)
        var_strType = ProcessadorETL.extrair_campo_seguro(var_dictDetalhes, "type", arg_anyPadrao="game")
        var_dictDadosTransformados["type"] = var_strType if var_strType else "game"
        
        return var_dictDadosTransformados
    
    @staticmethod
    def transformar_raw_para_unificado(arg_dictDadosRaw: Dict) -> Dict:
        """
        Transforma dados brutos em formato para steam_unificado.
        Combina dados estruturados + mantém JSONB completo.
        
        Parâmetros:
        - arg_dictDadosRaw (dict): Dicionário com appid, detalhes, reviews
        
        Retorna:
        - dict: Dicionário estruturado para steam_unificado
        """
        # Primeiro transforma usando o método existente
        var_dictDadosEstruturados = ProcessadorETL.transformar_raw_para_bd(arg_dictDadosRaw)
        
        # Adiciona os campos JSONB completos
        var_dictDadosEstruturados['detalhes_completos'] = arg_dictDadosRaw.get('detalhes')
        var_dictDadosEstruturados['reviews_completos'] = arg_dictDadosRaw.get('reviews')
        
        return var_dictDadosEstruturados
    
    @staticmethod
    def processar_lote_unificado() -> None:
        """
        Processa um lote de AppIDs do Docker para steam_unificado.
        Versão consolidada que mantém dados estruturados + JSONB.
        
        Parâmetros:
        """
        # Garante conexão com o Docker
        PostgreSQL.conectar()
        
        # Buscar dados brutos do Docker
        var_listDados = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="steam_raw")
        logger.info(f"{len(var_listDados)} jogos encontrados no Docker.")
        
        # Transformar dados
        var_listDadosUnificados = []
        var_intErrosTransformacao = 0
        var_dictContagemErros = {
            'detalhes_ausentes': 0,
            'appid_invalido': 0,
            'dados_vazios': 0,
            'outros': 0
        }
        
        for var_dictDadosRaw in var_listDados:
            try:
                var_dictDadosUnificado = ProcessadorETL.transformar_raw_para_unificado(var_dictDadosRaw)
                var_listDadosUnificados.append(var_dictDadosUnificado)
            except ValueError as e:
                var_intErrosTransformacao += 1
                var_strErro = str(e).lower()
                
                # Categoriza o erro
                if 'detalhes ausentes' in var_strErro or 'detalhes vazios' in var_strErro:
                    var_dictContagemErros['detalhes_ausentes'] += 1
                elif 'appid' in var_strErro:
                    var_dictContagemErros['appid_invalido'] += 1
                elif 'vazio' in var_strErro:
                    var_dictContagemErros['dados_vazios'] += 1
                else:
                    var_dictContagemErros['outros'] += 1
                    logger.error(f"Erro ao processar AppID {var_dictDadosRaw.get('appid', 'DESCONHECIDO')}: {e}")
            except Exception as e:
                var_intErrosTransformacao += 1
                var_dictContagemErros['outros'] += 1
                logger.error(f"Erro inesperado ao processar AppID {var_dictDadosRaw.get('appid', 'DESCONHECIDO')}: {e}")
        
        logger.info(f"{len(var_listDadosUnificados)} jogos transformados com sucesso")
        
        if var_intErrosTransformacao > 0:
            logger.warning(f"{var_intErrosTransformacao} erros de transformação:")
            logger.warning(f"  - Detalhes ausentes: {var_dictContagemErros['detalhes_ausentes']}")
            logger.warning(f"  - AppID inválido: {var_dictContagemErros['appid_invalido']}")
            logger.warning(f"  - Dados vazios: {var_dictContagemErros['dados_vazios']}")
            logger.warning(f"  - Outros erros: {var_dictContagemErros['outros']}")
        
        # Inserir em steam_unificado
        if var_listDadosUnificados:
            try:
                var_intInseridos = 0
                var_intTotal = len(var_listDadosUnificados)
                for var_dictDado in var_listDadosUnificados:
                    var_floatPercentual = (var_intInseridos / var_intTotal) * 100
                    if var_floatPercentual in [0, 25, 50, 75, 100]:
                        logger.info(f"Inseridos {var_floatPercentual}% do total de {var_intTotal}")
                    try:
                        PostgreSQL.inserir_steam_unificado(var_dictDado)
                        var_intInseridos += 1
                    except Exception as e:
                        logger.error(f"Erro ao inserir AppID {var_dictDado.get('appid')}: {e}")
                
                logger.info(f"{var_intInseridos}/{len(var_listDadosUnificados)} jogos inseridos em steam_unificado!")
            except Exception as e:
                logger.error(f"Erro ao inserir em steam_unificado: {e}")
        else:
            logger.warning("Nenhum jogo válido para inserir em steam_unificado")