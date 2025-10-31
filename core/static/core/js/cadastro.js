function toggleCampos(mostrar) {
    const campos = document.getElementById('campos-tecnicos');
    const btnSim = document.getElementById('btnSim');
    const btnNao = document.getElementById('btnNao');

    if (mostrar) {
        campos.style.display = 'block';
        btnSim.classList.add('active');
        btnNao.classList.remove('active');
    } else {
        campos.style.display = 'none';
        btnNao.classList.add('active');
        btnSim.classList.remove('active');
    }
}


document.addEventListener('DOMContentLoaded', function() {
    
    // --- MÁSCARA DE TELEFONE ---
    const phoneInput = document.getElementById('id_telefone');
    if (phoneInput) {
        // Mantido o bloco IMask.js, sem a gambiarra do 'type="text"'
        // já que o backend foi corrigido!
        const maskOptions = {
            mask: [
                { mask: '(00) 0000-0000' },  // Fixo
                { mask: '(00) 00000-0000' } // Celular
            ]
        };
        const mask = IMask(phoneInput, maskOptions);
    }


    // --- BLOQUEAR NÚMEROS NEGATIVOS E LIMITAR PORCENTAGEM (NOVO) ---
    document.addEventListener('input', function(e) {
        if (e.target.type === 'number') {
            let valor = parseFloat(e.target.value);
            
            // 1. Bloquear números negativos (mantido)
            if (valor < 0) {
                e.target.value = 0;
            }
            
            // 2. Limitar porcentagem a 100
            if (e.target.id === 'id_porcentagem_preenchimento') {
                 if (valor > 100) {
                    e.target.value = 100;
                }
            }
        }
    });

    
    // --- VALIDAÇÃO GERAL ANTES DE ENVIAR (SEU CÓDIGO) ---
    const form = document.getElementById('form-cadastro');
    if (form) {
        form.addEventListener('submit', function(e){
            const alertBox = document.getElementById('alert-erro');
            alertBox.classList.add('d-none');
            let valido = true;

            const obrigatorios = ['nome', 'curso', 'quant_de_pecas', 'cor', 'telefone'];
            obrigatorios.forEach(nome => {
                const campo = document.getElementById(`id_${nome}`);
                if (campo && campo.value.trim() === '') {
                    campo.classList.add('is-invalid');
                    valido = false;
                } else if (campo) {
                    campo.classList.remove('is-invalid');
                }
            });

            // Regra: arquivo OU link deve ser preenchido
            const arquivo = document.getElementById('id_arq_upload');
            const link = document.getElementById('id_arq_link');
            const temArquivo = arquivo && arquivo.files.length > 0;
            const temLink = link && link.value.trim() !== '';

            if (!temArquivo && !temLink) {
                if (arquivo) arquivo.classList.add('is-invalid');
                if (link) link.classList.add('is-invalid');
                valido = false;
            } else {
                if (arquivo) arquivo.classList.remove('is-invalid');
                if (link) link.classList.remove('is-invalid');
            }

            if (!valido) {
                e.preventDefault();
                alertBox.textContent = '⚠️ Por favor, preencha todos os campos obrigatórios.';
                alertBox.classList.remove('d-none');
                window.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }

            // Verificação de formato do arquivo
            if (arquivo && arquivo.files.length > 0) {
                const allowed = ['.stl', '.obj', '.3mf', '.gcode'];
                const name = arquivo.files[0].name.toLowerCase();
                const ext = name.substring(name.lastIndexOf('.'));
                if (!allowed.includes(ext)) {
                    e.preventDefault();
                    alert('Formato inválido! Envie um arquivo 3D (.stl, .obj, .3mf ou .gcode).');
                }
            }
        });
    }

}); // Fim do DOMContentLoaded