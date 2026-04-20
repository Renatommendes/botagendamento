from django import forms
from .models import Cliente
from .models import Contato

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if Cliente.objects.filter(telefone=telefone).exists():
            raise forms.ValidationError("Telefone já cadastrado.")
        return telefone


class ContatoForm(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ['nome', 'numero']

