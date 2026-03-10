from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_steam import PostgreSQLSteam

import unicodedata
import re
import logging

logger = logging.getLogger(__name__)

class LimparCategoria:
    """
    Classe responsável por limpar e padronizar o campo "categoria" dos jogos.
    """
    _var_setCategoriasNormalizadas = None
    _var_setIdCategorias = None
    
    @classmethod
    def _inserir_novas_categorias(cls, arg_dictNovasCategorias: dict[int, str]) -> list[str]:
        """
        Processa e normaliza categorias de steam_raw, inserindo novas na tabela steam_categorias.
        
        Parâmetros:
        - arg_dictNovasCategorias (dict[int, str]): Dicionário de categorias novas a serem inseridas.

        Retorna:
        - list[str]: Conjunto de categorias normalizadas
        """
        try:
            logger.info("Inserindo novas categorias no banco...")
            var_connConnection = PostgreSQL.conectar()
            arg_dictNovasCategorias = {idx: nome for idx, nome in enumerate(arg_dictNovasCategorias, start=1)}
            var_listValores = [(idx, nome) for idx, nome in arg_dictNovasCategorias.items()]

            # Insere usando execute_values para performance
            from psycopg2.extras import execute_values
            var_strSQLInsert = """
                INSERT INTO public.steam_categorias (id_categoria, nome_categoria)
                VALUES %s
                ON CONFLICT (id_categoria) DO NOTHING
            """
            
            with var_connConnection.cursor() as cursor:
                execute_values(cursor, var_strSQLInsert, var_listValores)
                var_connConnection.commit()
            
            logger.info(f"{len(arg_dictNovasCategorias)} categorias inseridas com sucesso")
            
            # Log das novas categorias
            logger.info("Novas categorias adicionadas:")
            for _, nome in var_listValores[:20]:  # Mostra apenas as primeiras 20
                logger.info(f"  • {nome}")
            if len(var_listValores) > 20:
                logger.info(f"  ... e mais {len(var_listValores) - 20} categorias")
            
            cls._var_setCategoriasNormalizadas.update(arg_dictNovasCategorias.values())

        except Exception as e:
            if var_connConnection:
                var_connConnection.rollback()
            logger.error(f"Erro ao inserir novas categorias: {e}")
            raise Exception(f"Erro ao inserir novas categorias: {e}")
        finally:
            if var_connConnection:
                PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def processar_categoria_completo(cls, arg_listCategorias: list[dict[int, str]]) -> list[str]:
        """
        Processa e normaliza categorias de steam_raw, inserindo novas na tabela steam_categorias.
        
        Parâmetros:
        - arg_listCategorias (list[dict[int, str]]): Lista de dicionários representando categorias do campo 'categories' do steam_raw.

        Retorna:
        - list[str]: Conjunto de categorias normalizadas
        """
        try:
            cls._var_setIdCategorias = set()
            
            var_listIdCategorias = []
            var_dictCategorias = {}
            for var_dictCategoria in arg_listCategorias:
                var_listIdCategorias.append(var_dictCategoria.get("id", None))
                var_dictCategorias[var_dictCategoria.get("id", None)] = var_dictCategoria.get("description", None)

            cls._var_setIdCategorias.update(var_listIdCategorias)
            
            # Identifica categorias que ainda não existem no BD
            var_dictCategoriasExistentes = PostgreSQLSteam.buscar_dados_categoria()
            
            var_dictNovasCategorias = {}
            for var_intId in cls._var_setIdCategorias:
                if var_intId not in var_dictCategoriasExistentes:
                    var_dictNovasCategorias[var_intId] = var_dictCategorias.get(var_intId, None)

            # Insere novas categorias no banco
            if var_dictNovasCategorias:
                # Dicionário de tradução e normalização
                var_dictTraducao = cls._obter_dicionario_traducao_categorias()
                
                for var_strCategoria in cls._var_setCategoriasNormalizadas:
                    var_strNomeNormalizado = cls._normalizar_categoria(var_strCategoria, var_dictTraducao)
                    if var_strNomeNormalizado:
                        cls._var_setCategoriasNormalizadas.add(var_strNomeNormalizado)
                cls._inserir_novas_categorias(var_dictNovasCategorias)
            
            return list(cls._var_setIdCategorias)
            
        except Exception as e:
            logger.error(f"Erro no processamento de categorias: {e}")
            raise
        
    @staticmethod
    def _normalizar_categoria(arg_strNome: str, arg_dictTraducao: dict[str, str]) -> str:
        """
        Normaliza nome de categoria usando dicionário de tradução.
        
        Parâmetros:
        - arg_strNome: Nome da categoria bruto
        - arg_dictTraducao: Dicionário de padrões -> nome normalizado
        
        Retorna:
        - str: Nome normalizado ou None se inválido
        """
        if not arg_strNome or len(arg_strNome) < 2:
            return None
        
        var_strNomeLower = arg_strNome.lower()
        
        # Verifica correspondência com padrões do dicionário
        for var_dictPadroes, var_strNomeNormalizado in arg_dictTraducao.items():
            for var_strPadrao in var_dictPadroes:
                if var_strPadrao.lower() in var_strNomeLower:
                    return var_strNomeNormalizado
        
        # Fallback: Capitaliza primeira letra de cada palavra
        return arg_strNome.title()
    
    @staticmethod
    def _obter_dicionario_traducao_categorias() -> dict[tuple, str]:
        """
        Retorna dicionário de tradução para normalização de categorias.
        
        Retorna:
        - dict[tuple, str]: {(padrão1, padrão2, ...): nome_normalizado}
        """
        return {
            # MODOS DE JOGO (Single/Multiplayer)
            ('um jogador', 'single-player', 'solo'): 'Um Jogador',
            ('multijogador', 'multijoueur', 'multi-player'): 'Multijogador',
            ('cooperativo', 'co-op'): 'Cooperativo',
            ('mmo',): 'MMO',
            ('multijogador multiplataforma', 'cross-platform multiplayer'): 'Multijogador Multiplataforma',
            ('jxj on-line', 'jcj en ligne', 'online pvp'): 'JxJ On-line',
            ('jxj tela dividida/compart.', 'jcj en écran partagé', 'shared/split screen pvp'): 'JxJ Tela Dividida/Compartilhada',
            ('cooperativo on-line', 'online co-op'): 'Cooperativo On-line',
            ('coop. tela dividida/compart.',): 'Coop. Tela Dividida/Compartilhada',
            ('jxj em rede local (lan)', 'lan pvp'): 'JxJ em Rede Local (LAN)',
            ('coop. em rede local (lan)',): 'Coop. em Rede Local (LAN)',
            ('jxj', 'pvp'): 'JxJ (PvP)',
            ('tela dividida/compartilhada', 'écran partagé', 'shared/split screen'): 'Tela Dividida/Compartilhada',

            # RECURSOS DA PLATAFORMA (Steam Features)
            ('conquistas steam', 'steam achievements'): 'Conquistas Steam',
            ('nuvem steam', 'steam cloud'): 'Steam Cloud',
            ('cartas colecionáveis steam', 'cartas colecion??veis steam', 'steam trading cards'): 'Cartas Colecionáveis Steam',
            ('oficina steam', 'steam workshop'): 'Oficina Steam',
            ('classificações steam', 'classifica????es steam', 'steam leaderboards'): 'Classificações Steam',
            ('notificações de turno no steam', 'notifica????es de turno no steam'): 'Notificações de Turno no Steam',
            ('linha do tempo do steam',): 'Linha do Tempo do Steam',
            ('compartilhamento em família', 'compartilhamento em fam??lia', 'family sharing', 'partage familial'): 'Compartilhamento em Família',

            # CONTROLES E ACESSIBILIDADE
            ('compat. total com controle', 'compat. contrôleurs complète', 'full controller support'): 'Compatibilidade Total com Controle',
            ('compat. parcial com controle', 'partial controller support'): 'Compatibilidade Parcial com Controle',
            ('compatível nativamente com controle steam', 'compat??vel nativamente com controle steam'): 'Compatível Nativamente com Controle Steam',
            ('compat. c/ contr. mov. rastr.',): 'Compatível c/ Controle de Movimento',
            ('opção apenas com teclado', 'op????o apenas com teclado', 'keyboard only option', 'option clavier uniquement'): 'Opção Apenas com Teclado',
            ('opção apenas com mouse', 'op????o apenas com mouse', 'mouse only option'): 'Opção Apenas com Mouse',
            ('opção apenas com toque', 'op????o apenas com toque'): 'Opção Apenas com Toque',

            # REALIDADE VIRTUAL (VR)
            ('compatível com rv', 'compat??vel com rv'): 'Compatível com RV',
            ('compatíveis com rv', 'compat??veis com rv'): 'Compatíveis com RV',
            ('exclusivos para rv',): 'Exclusivos para RV',
            ('colecionáveis do steamvr', 'colecion??veis do steamvr'): 'Colecionáveis do SteamVR',

            # REMOTE PLAY
            ('remote play no celular',): 'Remote Play no Celular',
            ('remote play no tablet',): 'Remote Play no Tablet',
            ('remote play na tv',): 'Remote Play na TV',
            ('remote play together',): 'Remote Play Together',

            # CONTEÚDO E EXTRAS
            ('conteúdo adicional', 'conte??do adicional', 'contenu téléchargeable', 'downloadable content'): 'Conteúdo Adicional (DLC)',
            ('compras em aplicativo',): 'Compras em Aplicativo',
            ('mods',): 'Mods',
            ('mods (requer hl2)',): 'Mods (Requer HL2)',
            ('inclui editor de níveis', 'inclui editor de n??veis', 'includes level editor'): 'Inclui Editor de Níveis',
            ('inclui o sdk da source',): 'Inclui o SDK da Source',
            ('demonstração de jogo', 'demonstra????o de jogo'): 'Demonstração de Jogo',

            # SISTEMA E ACESSIBILIDADE DE SOFTWARE
            ('usa valve antitrapaça', 'usa valve antitrapa??a'): 'Usa Valve Antitrapaça',
            ('estatísticas', 'estat??sticas', 'stats'): 'Estatísticas',
            ('legendas disponíveis', 'legendas dispon??veis', 'captions available'): 'Legendas Disponíveis',
            ('comentários disponíveis', 'coment??rios dispon??veis'): 'Comentários Disponíveis',
            ('hdr disponível', 'hdr dispon??vel', 'hdr available'): 'HDR Disponível',
            ('texto de tamanho ajustável', 'texto de tamanho ajust??vel'): 'Texto de Tamanho Ajustável',
            ('opções de legendas', 'op????es de legendas'): 'Opções de Legendas',
            ('alternativas de cores',): 'Alternativas de Cores',
            ('conforto de câmera', 'conforto de c??mera', 'caméra et confort de vue'): 'Conforto de Câmera',
            ('controles de volume independentes', 'contrôle du volume différencié', 'custom volume controls'): 'Controles de Volume Independentes',
            ('som estéreo', 'som est??reo'): 'Som Estéreo',
            ('som surround',): 'Som Surround',
            ('narração de menus', 'narra????o de menus'): 'Narração de Menus',
            ('transcrição da conversa por voz',): 'Transcrição da Conversa por Voz',
            ('narração da conversa por texto',): 'Narração da Conversa por Texto',
            ('jogável sem precisar de reação rápida', 'jog??vel sem precisar de rea????o r??pida'): 'Jogável sem Precisar de Reação Rápida',
            ('dificuldade ajustável', 'dificuldade ajust??vel', 'adjustable difficulty'): 'Dificuldade Ajustável',
            ('salvamento a qualquer momento', 'save anytime'): 'Salvamento a Qualquer Momento',
        }
