from django import forms
from .models import Models

class ModelsForm(forms.ModelForm):
    class Meta:
        model = Models
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        arq = cleaned_data.get("arq_upload")
        link = cleaned_data.get("arq_link")

        if not arq and not link:
            raise forms.ValidationError("Envie um arquivo ou informe um link — pelo menos um é obrigatório.")

        return cleaned_data
