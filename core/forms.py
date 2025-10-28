import os
from django import forms
from .models import Models

EXTENSOES_PERMITIDAS = {".stl", ".obj", ".3mf", ".gcode"}

class ModelsForm(forms.ModelForm):
    class Meta:
        model = Models
        exclude = ['data_envio']  # não aparece no formulário

    def clean(self):
        cleaned_data = super().clean()
        arq = cleaned_data.get("arq_upload")
        link = cleaned_data.get("arq_link")

        if not arq and not link:
            raise forms.ValidationError("Envie um arquivo ou informe um link — pelo menos um é obrigatório.")

        return cleaned_data

    def clean_arq_upload(self):
        arquivo = self.cleaned_data.get('arq_upload')

        if arquivo:
            nome = arquivo.name
            extensao = os.path.splitext(nome)[1].lower()
            if extensao not in EXTENSOES_PERMITIDAS:
                raise forms.ValidationError(
                    "Formato inválido! Envie um arquivo 3D (.stl, .obj, .3mf ou .gcode)."
                )
        return arquivo
