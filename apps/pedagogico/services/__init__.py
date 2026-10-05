from apps.pedagogico.services.agrupamentos import (
    _AGRUPAMENTO_ID_INICIAL,
)
from apps.pedagogico.services.agrupamentos import (
    agrupar_atribuicoes_territorio_saber as _agrupar,
)
from apps.pedagogico.services.agrupamentos import (
    chave_grupo_atribuicao as _chave_grupo,
)
from apps.pedagogico.services.agrupamentos import (
    montar_indices_agrupamentos_existentes as _montar_indices_agr_existentes,
)
from apps.pedagogico.services.agrupamentos import (
    resolver_cod_agrupamento as _cod_agrupamento,
)
from apps.pedagogico.services.etl_pedagogico_service import (
    EtlPedagogicoService,
)

__all__ = [
    "EtlPedagogicoService",
    "_AGRUPAMENTO_ID_INICIAL",
    "_agrupar",
    "_chave_grupo",
    "_cod_agrupamento",
    "_montar_indices_agr_existentes",
]
