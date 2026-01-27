@dataclass
class ITADRaw:
    slug: str
    title: str
    type: str
    mature: bool
    assets: dict
    ultima_atualizacao: str
    id_itad: str
    historico_precos: list
    ...