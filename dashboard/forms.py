import re
from django import forms
from django.contrib.auth import get_user_model
from users.models import User as UserProfile

User = get_user_model()

class LoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            'placeholder': 'seu.email@exemplo.com',
            'class': 'form-input'
        })
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'form-input'
        })
    )


class CadastroForm(forms.Form):
    nome = forms.CharField(
        label="Nome completo",
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Seu Nome',
            'class': 'form-input'
        })
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            'placeholder': 'seu.email@exemplo.com',
            'class': 'form-input'
        })
    )
    phone_number = forms.CharField(
        label="Telefone do WhatsApp",
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': '5511999998888',
            'class': 'form-input',
            'help_text': 'Digite apenas os números, incluindo o DDD'
        })
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'form-input'
        })
    )
    password_confirm = forms.CharField(
        label="Confirmação de Senha",
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'form-input'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este endereço de e-mail já está em uso.")
        return email

    def clean_phone_number(self):
        raw_phone = self.cleaned_data.get('phone_number')
        # Normalização: Manter apenas dígitos
        clean_phone = "".join(filter(str.isdigit, raw_phone))
        
        if not clean_phone:
            raise forms.ValidationError("Telefone inválido. Digite apenas números.")
        
        # Verificar se o telefone existe no banco de dados (tabela users_user)
        try:
            profile = UserProfile.objects.get(phone_number=clean_phone)
            # Se o perfil já possui um usuário associado
            if profile.auth_user is not None:
                raise forms.ValidationError("Este número de telefone já está associado a uma conta cadastrada.")
        except UserProfile.DoesNotExist:
            raise forms.ValidationError(
                "Não é possível finalizar o cadastro, pois o número de telefone não está vinculado "
                "a nenhuma conversa com o assistente no WhatsApp."
            )
            
        return clean_phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "As senhas informadas não coincidem.")
            
        return cleaned_data
