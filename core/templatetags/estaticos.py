"""Tag de estáticos com marca de versão.

Sem isso o navegador continua servindo o CSS e o JS antigos depois de uma
edição local ou de um deploy, até alguém forçar a recarga. O sintoma é
traiçoeiro: o HTML vem sempre fresco do Django, então a página mistura
template novo com estilo velho e parece um bug de CSS.

`{% static_v 'core/css/base.css' %}` acrescenta ?v=<mtime> à URL. Quando o
arquivo muda, a URL muda, e o navegador é obrigado a buscar de novo.
"""

from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

register = template.Library()

# Em produção os arquivos não mudam enquanto o processo vive; em
# desenvolvimento a versão é recalculada a cada uso.
_versoes = {}


def _caminho_no_disco(caminho):
    """Localiza o arquivo pelos finders (dev) ou no STATIC_ROOT (produção)."""
    encontrado = finders.find(caminho)
    if encontrado:
        return Path(encontrado)
    try:
        return Path(staticfiles_storage.path(caminho))
    except (NotImplementedError, ValueError):
        return None


def _storage_ja_versiona():
    """O storage já põe hash no nome do arquivo?

    É o caso do CompressedManifestStaticFilesStorage do WhiteNoise, usado em
    produção. Aí a URL já muda sozinha e o ?v= seria redundante — pior, mudaria
    a cada deploy e anularia o cache longo que o hash permite.
    """
    return hasattr(staticfiles_storage, 'manifest_name')


@register.simple_tag
def static_v(caminho):
    if not settings.DEBUG and caminho in _versoes:
        return _versoes[caminho]

    url = static(caminho)

    if not _storage_ja_versiona():
        arquivo = _caminho_no_disco(caminho)
        if arquivo and arquivo.exists():
            url = f'{url}?v={int(arquivo.stat().st_mtime)}'

    _versoes[caminho] = url
    return url
