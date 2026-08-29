
from typing import Dict, Any
import unicodedata
import re
import logging

logger = logging.getLogger(__name__)

class Limpar:
    """
    Classe genérica para limpeza de dados.
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
            var_strChar for var_strChar in var_strNormalizado
            if unicodedata.category(var_strChar) != 'Mn'
        )

        # Remove caracteres de controle
        var_strLimpo = ''.join(
            var_strChar for var_strChar in var_strSemAcento
            if var_strChar.isprintable() or var_strChar.isspace()
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
        for var_strChave in arg_strCaminho:
            if isinstance(var_dictResultado, dict):
                var_dictResultado = var_dictResultado.get(var_strChave)
            else:
                return arg_anyPadrao
            if var_dictResultado is None:
                return arg_anyPadrao
        return var_dictResultado if var_dictResultado is not None else arg_anyPadrao