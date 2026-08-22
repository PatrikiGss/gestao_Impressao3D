// Mantém a aba ativa em sincronia com a URL.
//
// As abas do Bootstrap são só client-side: sem isto, paginar a aba
// "Concluídos" recarregava a página e o usuário voltava para "Pendentes".
document.addEventListener('DOMContentLoaded', function () {
    // 1. Ao carregar, abre a aba indicada pela âncora (ex.: /lista/?conc=2#concluidos)
    if (window.location.hash) {
        const botao = document.querySelector(`[data-bs-target="${window.location.hash}"]`);
        if (botao) {
            bootstrap.Tab.getOrCreateInstance(botao).show();
        }
    }

    // 2. Ao trocar de aba, grava a âncora na URL sem criar entrada no histórico,
    //    para que os links de paginação já saiam com a aba certa.
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (botao) {
        botao.addEventListener('shown.bs.tab', function (evento) {
            history.replaceState(null, '', evento.target.dataset.bsTarget);
        });
    });
});
