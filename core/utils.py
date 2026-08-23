from django.utils.http import url_has_allowed_host_and_scheme


def destino_seguro(request, fallback):
    """Resolve para onde redirecionar depois de uma ação.

    Lê o campo/parâmetro `next` e só o aceita se apontar para dentro do próprio
    site — um `next` controlado por terceiros vira open redirect. Quando não há
    `next` válido, cai no `fallback`.
    """
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(
        url=destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destino
    return fallback
