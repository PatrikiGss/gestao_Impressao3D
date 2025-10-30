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

// Validação de arquivo (mantida)
document.getElementById('form-cadastro').addEventListener('submit', function(e){
    const fileInput = document.querySelector('input[type="file"][name="arq_upload"]');
    if (fileInput && fileInput.files.length > 0) {
        const allowed = ['.stl', '.obj', '.3mf', '.gcode'];
        const name = fileInput.files[0].name.toLowerCase();
        const ext = name.substring(name.lastIndexOf('.'));
        if (!allowed.includes(ext)) {
            e.preventDefault();
            alert('Formato inválido! Envie um arquivo 3D (.stl, .obj, .3mf ou .gcode).');
        }
    }
});
