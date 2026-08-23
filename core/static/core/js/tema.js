// Alternância entre tema claro e escuro.
//
// A escolha inicial já foi aplicada por um script inline no <head>, para não
// piscar branco antes do CSS carregar. Aqui fica só o clique e a preferência
// gravada no navegador.
document.addEventListener('DOMContentLoaded', function () {
    const botao = document.getElementById('alternar-tema');
    if (!botao) return;

    botao.addEventListener('click', function () {
        const raiz = document.documentElement;
        const estaEscuro = raiz.getAttribute('data-bs-theme') === 'dark';

        raiz.setAttribute('data-bs-theme', estaEscuro ? 'light' : 'dark');
        localStorage.setItem('tema', estaEscuro ? 'claro' : 'escuro');
    });
});
