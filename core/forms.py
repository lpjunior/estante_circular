from django import forms
from django.utils import timezone

from core.models import Livro, Reserva


class LivroForm(forms.ModelForm):
    GENEROS = tuple(Livro.GENERO_LABELS.items())
    ESTADOS_CONSERVACAO = tuple(Livro.ESTADO_CONSERVACAO_LABELS.items())

    genero = forms.ChoiceField(
        choices=GENEROS,
        label="Gênero ou categoria",
    )
    estado_conservacao = forms.ChoiceField(
        choices=ESTADOS_CONSERVACAO,
        label="Estado de conservação",
    )

    class Meta:
        model = Livro
        fields = ("titulo", "autor", "genero", "estado_conservacao", "descricao", "capa")
        labels = {  # noqa: RUF012
            "titulo": "Título do livro",
            "autor": "Autor",
            "descricao": "Descrição",
            "capa": "Capa do livro",
        }
        widgets = {  # noqa: RUF012
            "titulo": forms.TextInput(
                attrs={"placeholder": "Ex.: O Hobbit", "autocomplete": "off"}
            ),
            "autor": forms.TextInput(
                attrs={"placeholder": "Ex.: J. R. R. Tolkien", "autocomplete": "off"}
            ),
            "descricao": forms.Textarea(
                attrs={
                    "placeholder": (
                        "Descreva brevemente a obra e qualquer informação "
                        "relevante sobre este exemplar."
                    ),
                    "rows": 6,
                }
            ),
            "capa": forms.FileInput(
                attrs={
                    "accept": "image/*",
                }
            ),
        }

    def clean_titulo(self):
        titulo = (self.cleaned_data.get("titulo") or "").strip()
        if not titulo:
            raise forms.ValidationError("Informe o título do livro.")
        return titulo

    def clean_autor(self):
        autor = (self.cleaned_data.get("autor") or "").strip()
        if not autor:
            raise forms.ValidationError("Informe o autor.")
        if len(autor) < 2:
            raise forms.ValidationError(
                "O nome do autor deve ter pelo menos 2 caracteres."
            )
        return autor

    def clean_descricao(self):
        descricao = (self.cleaned_data.get("descricao") or "").strip()
        if not descricao:
            raise forms.ValidationError("Informe uma descrição.")
        if len(descricao) < 10:
            raise forms.ValidationError(
                "A descrição deve ter pelo menos 10 caracteres."
            )
        return descricao


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ("data_retirada_prevista",)
        labels = {
            "data_retirada_prevista": "Data desejada para retirada",
        }
        widgets = {
            "data_retirada_prevista": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_data_retirada_prevista(self):
        data = self.cleaned_data.get("data_retirada_prevista")
        if not data:
            raise forms.ValidationError("Informe uma data para retirada.")
        if data < timezone.localdate():
            raise forms.ValidationError(
                "A data de retirada não pode estar no passado."
            )
        return data


class AlterarDataReservaForm(forms.Form):
    data_retirada = forms.DateField(
        label="Nova data para retirada",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_data_retirada(self):
        data = self.cleaned_data.get("data_retirada")
        if data and data < timezone.localdate():
            raise forms.ValidationError(
                "A nova data de retirada não pode estar no passado."
            )
        return data
