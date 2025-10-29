function toggleCampos(mostrar) {
    document.getElementById('campos-tecnicos').style.display = mostrar ? 'block' : 'none';
}

document.getElementById('form-cadastro').addEventListener('submit', function(e){
    const fileInput = document.querySelector('input[type="file"][name="arq_upload"]');
    if (fileInput && fileInput.files.length > 0) {
        const allowed = ['.stl', '.obj', '.3mf', '.gcode'];
        const name = fileInput.files[0].name.toLowerCase();
        const ext = name.substring(name.lastIndexOf('.'));
        if (!allowed.includes(ext)) {
            e.preventDefault();
            alert('Formato inválido! Envie um arquivo 3D (.stl, .obj, .3mf ou .gcode).');
            return false;
        }
    }
});
