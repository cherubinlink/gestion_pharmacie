from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm,PasswordChangeForm
from gestion_compte.models import Utilisateur, ProfilUtilisateur, Pharmacie,Role


class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription utilisateur"""
    
    class Meta:
        model = Utilisateur
        fields = ('email', 'first_name', 'last_name', 'telephone', 'password1', 'password2')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+237600000000'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Mot de passe'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirmer'})




class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion"""
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )


class UtilisateurForm(forms.ModelForm):
    """Formulaire pour les informations de base utilisateur"""
    class Meta:
        model = Utilisateur
        fields = ['first_name', 'last_name', 'telephone', 'whatsapp', 'photo', 
                  'adresse', 'ville', 'pays', 'date_naissance']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ville': forms.TextInput(attrs={'class': 'form-control'}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
            'date_naissance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class ProfilUtilisateurForm(forms.ModelForm):
    """Formulaire étendu pour le profil"""
    class Meta:
        model = ProfilUtilisateur
        fields = [
            'genre', 'situation_matrimoniale', 'nationalite', 'lieu_naissance',
            'numero_cni', 'profession', 'diplome', 'specialite', 'numero_ordre',
            'annees_experience', 'contact_urgence_nom', 'contact_urgence_telephone',
            'contact_urgence_relation', 'biographie'
        ]
        widgets = {
            'genre': forms.Select(attrs={'class': 'form-select'}),
            'situation_matrimoniale': forms.Select(attrs={'class': 'form-select'}),
            'nationalite': forms.TextInput(attrs={'class': 'form-control'}),
            'biographie': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class PharmacieForm(forms.ModelForm):
    """Formulaire de configuration pharmacie"""
    class Meta:
        model = Pharmacie
        fields = [
            'nom_commercial', 'slogan', 'logo', 'adresse', 'ville', 'region',
            'code_postal', 'telephone_principal', 'telephone_secondaire', 
            'email', 'whatsapp', 'site_web', 'numero_autorisation', 
            'nif', 'rccm', 'date_autorisation', 'date_expiration_autorisation'
        ]
        widgets = {
            'nom_commercial': forms.TextInput(attrs={'class': 'form-control'}),
            'slogan': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InvitationMembreForm(forms.Form):
    """Formulaire d'invitation de membre"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email du membre'})
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class PreferencesUtilisateurForm(forms.ModelForm):
    """Formulaire pour les préférences utilisateur"""
    class Meta:
        model = ProfilUtilisateur
        fields = [
            'theme', 'langue', 'notifications_email', 
            'notifications_sms', 'notifications_push'
        ]
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'langue': forms.Select(attrs={'class': 'form-select'}),
        }

