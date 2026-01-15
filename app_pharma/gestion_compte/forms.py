"""
Formulaire d'inscription amélioré pour l'application de gestion pharmacie
Avec validation avancée et sécurité renforcée
"""
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
import re
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm,PasswordChangeForm
from django.contrib.auth import authenticate
from gestion_compte.models import Utilisateur, ProfilUtilisateur, Pharmacie,Role


User = get_user_model()




class InscriptionForm(forms.ModelForm):
    """Formulaire d'inscription avec gestion correcte des champs optionnels"""
    
    # Champs mot de passe
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe (min. 8 caractères)',
            'autocomplete': 'new-password',
        }),
        help_text=(
            "Le mot de passe doit contenir au moins 8 caractères, "
            "incluant majuscule, minuscule et chiffre."
        )
    )
    
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe',
            'autocomplete': 'new-password',
        })
    )
    
    # Acceptation conditions
    accepter_conditions = forms.BooleanField(
        label="J'accepte les conditions d'utilisation et la politique de confidentialité",
        required=True,
        error_messages={
            'required': 'Vous devez accepter les conditions pour continuer.'
        }
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'telephone', 'whatsapp', 'photo',
            'date_naissance', 'adresse', 'ville', 'pays'
        ]
        
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse email',
            'telephone': 'Téléphone',
            'whatsapp': 'WhatsApp (optionnel)',
            'photo': 'Photo de profil (optionnel)',
            'date_naissance': 'Date de naissance (optionnel)',
            'adresse': 'Adresse (optionnel)',
            'ville': 'Ville',
            'pays': 'Pays',
        }
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom',
                'required': True,
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemple@email.com',
                'required': True,
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+237 6XX XX XX XX',
            }),
            'whatsapp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+237 6XX XX XX XX',
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'date_naissance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse complète',
                'rows': 3,
            }),
            'ville': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville',
            }),
            'pays': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'Cameroun',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Marquer les champs obligatoires
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['telephone'].required = True
        
        # Champs optionnels
        self.fields['whatsapp'].required = False
        self.fields['photo'].required = False
        self.fields['date_naissance'].required = False
        self.fields['adresse'].required = False
        self.fields['ville'].required = False
        self.fields['pays'].required = False
    
    def clean_email(self):
        """Validation de l'email"""
        email = self.cleaned_data.get('email')
        
        # Gestion None
        if not email:
            raise ValidationError("L'adresse email est obligatoire.")
        
        email = email.lower().strip()
        
        # Vérifier format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise ValidationError("Format d'email invalide.")
        
        # Vérifier unicité
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "Cette adresse email est déjà utilisée. "
                "Veuillez en choisir une autre ou vous connecter."
            )
        
        # Bloquer emails temporaires (optionnel)
        domaines_bloques = [
            'tempmail.com', 'throwaway.email', 'guerrillamail.com',
            'mailinator.com', '10minutemail.com', 'trashmail.com'
        ]
        domaine = email.split('@')[1] if '@' in email else ''
        if domaine in domaines_bloques:
            raise ValidationError(
                "Les adresses email temporaires ne sont pas autorisées."
            )
        
        return email
    
    def clean_first_name(self):
        """Validation du prénom"""
        first_name = self.cleaned_data.get('first_name')
        
        # Gestion None
        if not first_name:
            raise ValidationError("Le prénom est obligatoire.")
        
        first_name = first_name.strip()
        
        if len(first_name) < 2:
            raise ValidationError("Le prénom doit contenir au moins 2 caractères.")
        
        if len(first_name) > 50:
            raise ValidationError("Le prénom ne peut pas dépasser 50 caractères.")
        
        # Vérifier caractères autorisés
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\'-]+$', first_name):
            raise ValidationError(
                "Le prénom ne peut contenir que des lettres, espaces, tirets et apostrophes."
            )
        
        return first_name.title()
    
    def clean_last_name(self):
        """Validation du nom"""
        last_name = self.cleaned_data.get('last_name')
        
        # Gestion None
        if not last_name:
            raise ValidationError("Le nom est obligatoire.")
        
        last_name = last_name.strip()
        
        if len(last_name) < 2:
            raise ValidationError("Le nom doit contenir au moins 2 caractères.")
        
        if len(last_name) > 50:
            raise ValidationError("Le nom ne peut pas dépasser 50 caractères.")
        
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\'-]+$', last_name):
            raise ValidationError(
                "Le nom ne peut contenir que des lettres, espaces, tirets et apostrophes."
            )
        
        return last_name.upper()
    
    def clean_telephone(self):
        """Validation du téléphone"""
        telephone = self.cleaned_data.get('telephone')
        
        # Gestion None - CORRECTION ICI
        if not telephone:
            raise ValidationError("Le téléphone est obligatoire.")
        
        telephone = str(telephone).strip()
        
        # Nettoyer (enlever espaces, tirets, etc.)
        telephone_clean = re.sub(r'[\s\-\(\)]', '', telephone)
        
        # Vérifier format international
        if not re.match(r'^\+?[1-9]\d{8,14}$', telephone_clean):
            raise ValidationError(
                "Format de téléphone invalide. Utilisez le format international: +237 6XX XX XX XX"
            )
        
        # Vérifier si le numéro existe déjà (optionnel)
        if User.objects.filter(telephone=telephone_clean).exists():
            raise ValidationError("Ce numéro de téléphone est déjà utilisé.")
        
        return telephone_clean
    
    def clean_whatsapp(self):
        """Validation du numéro WhatsApp - CORRIGÉ"""
        whatsapp = self.cleaned_data.get('whatsapp')
        
        # CORRECTION: Gérer None ou chaîne vide
        if not whatsapp or whatsapp == '':
            return ''  # Retourner chaîne vide si optionnel
        
        # Convertir en string et nettoyer
        whatsapp = str(whatsapp).strip()
        
        # Si vide après strip, retourner chaîne vide
        if not whatsapp:
            return ''
        
        # Nettoyer
        whatsapp_clean = re.sub(r'[\s\-\(\)]', '', whatsapp)
        
        # Vérifier format
        if not re.match(r'^\+?[1-9]\d{8,14}$', whatsapp_clean):
            raise ValidationError("Format de numéro WhatsApp invalide.")
        
        return whatsapp_clean
    
    def clean_photo(self):
        """Validation de la photo de profil - CORRIGÉ"""
        photo = self.cleaned_data.get('photo')
        
        # CORRECTION: Gérer None
        if not photo:
            return None  # Retourner None si pas de photo
        
        # Vérifier taille (max 5MB)
        if photo.size > 5 * 1024 * 1024:
            raise ValidationError("La taille de l'image ne doit pas dépasser 5MB.")
        
        # Vérifier extension
        extensions_valides = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        ext = photo.name.split('.')[-1].lower()
        if ext not in extensions_valides:
            raise ValidationError(
                f"Format d'image non supporté. Utilisez: {', '.join(extensions_valides)}"
            )
        
        return photo
    
    def clean_ville(self):
        """Validation ville - CORRIGÉ"""
        ville = self.cleaned_data.get('ville')
        
        # CORRECTION: Gérer None
        if not ville:
            return ''
        
        return str(ville).strip()
    
    def clean_pays(self):
        """Validation pays - CORRIGÉ"""
        pays = self.cleaned_data.get('pays')
        
        # CORRECTION: Gérer None
        if not pays:
            return 'Cameroun'  # Valeur par défaut
        
        return str(pays).strip()
    
    def clean_adresse(self):
        """Validation adresse - CORRIGÉ"""
        adresse = self.cleaned_data.get('adresse')
        
        # CORRECTION: Gérer None
        if not adresse:
            return ''
        
        return str(adresse).strip()
    
    def clean_date_naissance(self):
        """Validation date naissance - CORRIGÉ"""
        date_naissance = self.cleaned_data.get('date_naissance')
        
        # CORRECTION: Gérer None
        if not date_naissance:
            return None
        
        return date_naissance
    
    def clean_password1(self):
        """Validation du mot de passe"""
        password = self.cleaned_data.get('password1')
        
        if not password:
            raise ValidationError("Le mot de passe est obligatoire.")
        
        # Longueur minimum
        if len(password) < 8:
            raise ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        
        # Au moins une majuscule
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Le mot de passe doit contenir au moins une majuscule.")
        
        # Au moins une minuscule
        if not re.search(r'[a-z]', password):
            raise ValidationError("Le mot de passe doit contenir au moins une minuscule.")
        
        # Au moins un chiffre
        if not re.search(r'[0-9]', password):
            raise ValidationError("Le mot de passe doit contenir au moins un chiffre.")
        
        # Vérifier avec les validateurs Django
        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        # Vérifier que le mot de passe n'est pas trop commun
        mots_de_passe_communs = [
            'password', 'motdepasse', '12345678', 'azerty', 'qwerty',
            'admin', 'user', 'test', 'password123'
        ]
        if password.lower() in mots_de_passe_communs:
            raise ValidationError("Ce mot de passe est trop commun. Choisissez-en un plus sécurisé.")
        
        return password
    
    def clean(self):
        """Validation croisée"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        # Vérifier correspondance mots de passe
        if password1 and password2:
            if password1 != password2:
                raise ValidationError({
                    'password2': "Les mots de passe ne correspondent pas."
                })
        
        # Vérifier que le mot de passe ne contient pas le nom/prénom
        first_name = cleaned_data.get('first_name', '')
        last_name = cleaned_data.get('last_name', '')
        
        if password1 and first_name and last_name:
            password_lower = password1.lower()
            if (first_name.lower() in password_lower) or (last_name.lower() in password_lower):
                raise ValidationError({
                    'password1': "Le mot de passe ne doit pas contenir votre nom ou prénom."
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarde de l'utilisateur"""
        user = super().save(commit=False)
        
        # Définir le mot de passe
        user.set_password(self.cleaned_data['password1'])
        
        # Normaliser l'email
        user.email = user.email.lower().strip()
        
        # Définir le username si vide
        if not user.username:
            user.username = user.email.split('@')[0]
        
        if commit:
            user.save()
        
        return user


# ============================================================================
# FORMULAIRE INSCRIPTION SIMPLIFIÉE (Pour modal/popup)
# ============================================================================

class InscriptionRapideForm(forms.ModelForm):
    """
    Version simplifiée du formulaire d'inscription
    Pour les modals ou popups (moins de champs)
    """
    
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe',
        })
    )
    
    password2 = forms.CharField(
        label="Confirmer",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer',
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email',
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email déjà utilisé.")
        return email
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise ValidationError("Minimum 8 caractères.")
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.email = user.email.lower().strip()
        
        if commit:
            user.save()
        
        return user
    

class ConnexionForm(AuthenticationForm):
    """
    Formulaire de connexion avec validation personnalisée
    """
    
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'exemple@email.com',
            'autocomplete': 'email',
            'autofocus': True,
        }),
        error_messages={
            'required': 'L\'adresse email est obligatoire.',
            'invalid': 'Format d\'email invalide.',
        }
    )
    
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe',
            'autocomplete': 'current-password',
        }),
        error_messages={
            'required': 'Le mot de passe est obligatoire.',
        }
    )
    
    remember_me = forms.BooleanField(
        label="Se souvenir de moi",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnaliser les messages d'erreur
        self.error_messages['invalid_login'] = (
            "Email ou mot de passe incorrect. "
            "Veuillez réessayer."
        )
        self.error_messages['inactive'] = (
            "Ce compte est inactif. "
            "Contactez l'administrateur."
        )
    
    def clean_username(self):
        """Validation de l'email"""
        username = self.cleaned_data.get('username', '').lower().strip()
        
        if not username:
            raise ValidationError("L'adresse email est obligatoire.")
        
        # Vérifier format email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, username):
            raise ValidationError("Format d'email invalide.")
        
        return username
    
    def clean(self):
        """Validation croisée"""
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Authentifier l'utilisateur
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            
            if self.user_cache is None:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            else:
                # Vérifier si le compte est actif
                if not self.user_cache.is_active:
                    raise ValidationError(
                        self.error_messages['inactive'],
                        code='inactive',
                    )
        
        return self.cleaned_data



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

