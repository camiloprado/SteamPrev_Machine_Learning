@dataclass
class SteamGenerico:
    appid: int
    nome: str
    ultima_atualizacao: str
    ...

@dataclass
class SteamRaw:
    appid: int
    detalhes: dict
    reviews: dict
    ultima_atualizacao: str
    ...

@dataclass  
class SteamUnificado:
    appid: int
    nome: str
    classificacao_etaria: str
    linguagens: list
    desenvolvedores: list
    distribuidores: list
    preco: str
    metacritic_score: str
    categorias: list
    genero: list
    data_lancamento: str
    type: str
    review_score: int
    total_reviews: int
    total_negative: int
    total_positive: int
    review_score_desc: str
    detalhes_completos: dict
    review_completos: dict
    ultima_atualizacao: str
    ...