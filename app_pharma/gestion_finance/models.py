"""
Modèles Django pour la gestion des factures et finances
Application 6 : Gestion des factures & finances
Partie 1 : Factures, Paiements, Taxes
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from gestion_compte.models import Utilisateur, Pharmacie
from decimal import Decimal
import uuid
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
import hashlib
import secrets


# Create your models here.

# ============================================================================
# MODÈLES DEVISES ET TAXES
# ============================================================================

class Currency(models.Model):
    """Devise"""
    code = models.CharField(
        max_length=3,
        unique=True,
        help_text="Code ISO 4217 (XAF, EUR, USD)",
        verbose_name="Code"
    )
    name = models.CharField(max_length=100, verbose_name="Nom")
    symbol = models.CharField(max_length=10, verbose_name="Symbole")
    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('1.000000'),
        help_text="Taux de change par rapport à la devise de base (XAF)",
        verbose_name="Taux de change"
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Devise par défaut"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_currencies'
        ordering = ['code']
        verbose_name = "Devise"
        verbose_name_plural = "Devises"
    
    def __str__(self):
        return f"{self.code} - {self.name}"



class TaxRate(models.Model):
    """Taux de taxe"""
    TAX_TYPE_CHOICES = [
        ('vat', 'TVA'),
        ('local_tax', 'Taxe locale'),
        ('special_tax', 'Taxe spéciale'),
        ('exemption', 'Exonération'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='tax_rates',
        verbose_name="Pharmacie"
    )
    name = models.CharField(max_length=100, verbose_name="Nom")
    tax_type = models.CharField(
        max_length=20,
        choices=TAX_TYPE_CHOICES,
        verbose_name="Type de taxe"
    )
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Taux en %",
        verbose_name="Taux %"
    )
    
    # Applicabilité
    is_default = models.BooleanField(
        default=False,
        verbose_name="Taxe par défaut"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    # Période de validité
    valid_from = models.DateField(
        null=True,
        blank=True,
        verbose_name="Valide à partir du"
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="Valide jusqu'au"
    )
    
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_tax_rates'
        ordering = ['name']
        verbose_name = "Taux de taxe"
        verbose_name_plural = "Taux de taxes"
    
    def __str__(self):
        return f"{self.name} ({self.rate}%)"
    
    def is_valid_for_date(self, date=None):
        """Vérifie si la taxe est valide pour une date donnée"""
        if date is None:
            date = timezone.now().date()
        
        if self.valid_from and date < self.valid_from:
            return False
        if self.valid_until and date > self.valid_until:
            return False
        return True


# ============================================================================
# MODÈLES FACTURES
# ============================================================================

class Invoice(models.Model):
    """Facture"""
    INVOICE_TYPE_CHOICES = [
        ('counter_sale', 'Vente comptoir'),
        ('online_sale', 'Vente en ligne'),
        ('prescription', 'Ordonnance'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('issued', 'Émise'),
        ('paid', 'Payée'),
        ('partially_paid', 'Partiellement payée'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulée'),
        ('credited', 'Avoir émis'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name="Pharmacie"
    )
    
    # Numérotation
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de facture"
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        verbose_name="Type de facture"
    )
    
    # Client
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name="Client"
    )
    customer_name = models.CharField(
        max_length=255,
        help_text="Nom du client si non enregistré",
        blank=True,
        verbose_name="Nom du client"
    )
    customer_email = models.EmailField(
        blank=True,
        verbose_name="Email du client"
    )
    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone du client"
    )
    customer_address = models.TextField(
        blank=True,
        verbose_name="Adresse du client"
    )
    
    # Dates
    issue_date = models.DateField(
        default=timezone.now,
        verbose_name="Date d'émission"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date d'échéance"
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )
    
    # Montants
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name="Devise"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Sous-total"
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant taxes"
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant remise"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant total"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant payé"
    )
    balance_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Solde dû"
    )
    
    # Conversion en devise de base (XAF)
    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('1.000000'),
        verbose_name="Taux de change"
    )
    total_amount_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Montant total en devise de base (XAF)",
        verbose_name="Montant total (XAF)"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # QR Code pour vérification
    qr_code = models.ImageField(
        upload_to='invoices/qrcodes/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="QR Code"
    )
    verification_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="Hash SHA-256 pour vérification",
        verbose_name="Hash de vérification"
    )
    
    # Documents
    pdf_file = models.FileField(
        upload_to='invoices/pdfs/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Fichier PDF"
    )
    
    # Références
    sale = models.OneToOneField(
        'gestion_vente.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        verbose_name="Vente"
    )
    credit_note = models.ForeignKey(
        'CreditNote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='original_invoices',
        verbose_name="Avoir"
    )
    
    # Communication
    email_sent = models.BooleanField(
        default=False,
        verbose_name="Email envoyé"
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Email envoyé le"
    )
    sms_sent = models.BooleanField(
        default=False,
        verbose_name="SMS envoyé"
    )
    sms_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="SMS envoyé le"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    internal_notes = models.TextField(
        blank=True,
        verbose_name="Notes internes"
    )
    
    # Traçabilité
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_invoices'
        ordering = ['-issue_date', '-invoice_number']
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
        indexes = [
            models.Index(fields=['pharmacie', '-issue_date']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['customer', '-issue_date']),
            models.Index(fields=['status', '-issue_date']),
            models.Index(fields=['verification_hash']),
        ]
    
    def __str__(self):
        return f"Facture {self.invoice_number}"
    
    def save(self, *args, **kwargs):
        # Générer le hash de vérification
        if not self.verification_hash:
            self.verification_hash = self.generate_verification_hash()
        
        # Calculer le montant en devise de base
        self.total_amount_base = self.total_amount * self.exchange_rate
        
        super().save(*args, **kwargs)
        
        # Générer le QR Code
        if not self.qr_code:
            self.generate_qr_code()
    
    def generate_verification_hash(self):
        """Génère un hash SHA-256 pour la vérification de la facture"""
        data = f"{self.invoice_number}{self.pharmacie.id}{self.total_amount}{secrets.token_hex(16)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def generate_qr_code(self):
        """Génère un QR Code pour la facture"""
        qr_data = f"Invoice:{self.invoice_number}|Hash:{self.verification_hash}|Amount:{self.total_amount}{self.currency.code}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        file_name = f'invoice_{self.invoice_number}_qr.png'
        
        self.qr_code.save(file_name, File(buffer), save=True)
    
    def calculate_totals(self):
        """Calcule les totaux de la facture"""
        items = self.items.all()
        subtotal = sum(item.line_total for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        total = subtotal + tax_amount - self.discount_amount
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total_amount': total,
            'balance_due': total - self.paid_amount
        }
    
    def is_overdue(self):
        """Vérifie si la facture est en retard"""
        if self.due_date and self.status not in ['paid', 'cancelled', 'credited']:
            return timezone.now().date() > self.due_date
        return False


class InvoiceItem(models.Model):
    """Ligne de facture"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Facture"
    )
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='invoice_items',
        verbose_name="Produit"
    )
    
    # Description (si pas de produit)
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Description"
    )
    
    # Quantité et prix
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Prix unitaire"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Remise %"
    )
    
    # Taxes
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.PROTECT,
        related_name='invoice_items',
        verbose_name="Taux de taxe"
    )
    
    # Totaux calculés
    line_subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Sous-total ligne"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant taxe"
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total ligne"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'finance_invoice_items'
        ordering = ['created_at']
        verbose_name = "Ligne de facture"
        verbose_name_plural = "Lignes de facture"
    
    def __str__(self):
        desc = self.product.name if self.product else self.description
        return f"{desc} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        """Calcul automatique des totaux"""
        # Sous-total
        self.line_subtotal = self.unit_price * self.quantity
        
        # Appliquer la remise
        if self.discount_percentage > 0:
            discount = (self.line_subtotal * self.discount_percentage / 100)
            self.line_subtotal -= discount
        
        # Taxe
        self.tax_amount = self.line_subtotal * (self.tax_rate.rate / 100)
        
        # Total
        self.line_total = self.line_subtotal + self.tax_amount
        
        super().save(*args, **kwargs)
        

# ============================================================================
# MODÈLES AVOIRS (NOTES DE CRÉDIT)
# ============================================================================

class CreditNote(models.Model):
    """Avoir / Note de crédit"""
    REASON_CHOICES = [
        ('return', 'Retour de produits'),
        ('error', 'Erreur de facturation'),
        ('discount', 'Remise commerciale'),
        ('cancellation', 'Annulation'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='credit_notes',
        verbose_name="Pharmacie"
    )
    credit_note_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'avoir"
    )
    
    # Facture d'origine
    original_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='credit_notes',
        verbose_name="Facture d'origine"
    )
    
    # Dates
    issue_date = models.DateField(
        default=timezone.now,
        verbose_name="Date d'émission"
    )
    
    # Montants
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='credit_notes',
        verbose_name="Devise"
    )
    credit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant du crédit"
    )
    
    # Raison
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        verbose_name="Raison"
    )
    description = models.TextField(verbose_name="Description")
    
    # Documents
    pdf_file = models.FileField(
        upload_to='credit_notes/pdfs/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Fichier PDF"
    )
    
    # Traçabilité
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='credit_notes_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'finance_credit_notes'
        ordering = ['-issue_date']
        verbose_name = "Avoir"
        verbose_name_plural = "Avoirs"
        indexes = [
            models.Index(fields=['pharmacie', '-issue_date']),
            models.Index(fields=['credit_note_number']),
            models.Index(fields=['original_invoice']),
        ]
    
    def __str__(self):
        return f"Avoir {self.credit_note_number}"


# ============================================================================
# MODÈLES PAIEMENTS
# ============================================================================

class Payment(models.Model):
    """Paiement"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte bancaire'),
        ('bank_transfer', 'Virement bancaire'),
        ('check', 'Chèque'),
        ('credit', 'Crédit'),
        ('other', 'Autre'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('refunded', 'Remboursé'),
        ('cancelled', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Pharmacie"
    )
    sale_payment = models.OneToOneField(
        'gestion_vente.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_entry'
    )
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de paiement"
    )
    
    # Facture
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Facture"
    )
    
    # Montant
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )
    currency = models.ForeignKey(
        'Currency',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Devise"
    )
    
    # Méthode de paiement
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Méthode de paiement"
    )
    
    # Détails selon méthode
    mobile_money_operator = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex: Orange Money, MTN MoMo",
        verbose_name="Opérateur Mobile Money"
    )
    mobile_money_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro Mobile Money"
    )
    card_last4 = models.CharField(
        max_length=4,
        blank=True,
        verbose_name="4 derniers chiffres carte"
    )
    card_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Visa, Mastercard, etc.",
        verbose_name="Type de carte"
    )
    check_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numéro de chèque"
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom de la banque"
    )
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID de transaction"
    )
    
    # Dates
    payment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de paiement"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='completed',
        verbose_name="Statut"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Traçabilité
    processed_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='finance_payments_processed',
        verbose_name="Traité par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'finance_payments'
        ordering = ['-payment_date']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        indexes = [
            models.Index(fields=['pharmacie', '-payment_date']),
            models.Index(fields=['invoice', '-payment_date']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['payment_method', 'status']),
        ]
    
    def __str__(self):
        return f"Paiement {self.payment_number} - {self.amount} {self.currency.code}"


# ============================================================================
# MODÈLES CRÉDITS ET DETTES
# ============================================================================

class CustomerCredit(models.Model):
    """Crédit client / Dette"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('partially_paid', 'Partiellement payée'),
        ('paid', 'Payée'),
        ('overdue', 'En retard'),
        ('written_off', 'Radiée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='customer_credits',
        verbose_name="Pharmacie"
    )
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.PROTECT,
        related_name='credits',
        verbose_name="Client"
    )
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.PROTECT,
        related_name='credits',
        verbose_name="Facture"
    )
    
    # Montants
    credit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant du crédit"
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant payé"
    )
    balance_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Solde dû"
    )
    
    # Dates
    credit_date = models.DateField(
        default=timezone.now,
        verbose_name="Date du crédit"
    )
    due_date = models.DateField(verbose_name="Date d'échéance")
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_customer_credits'
        ordering = ['-credit_date']
        verbose_name = "Crédit client"
        verbose_name_plural = "Crédits clients"
        indexes = [
            models.Index(fields=['pharmacie', 'status']),
            models.Index(fields=['customer', '-credit_date']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"Crédit {self.customer} - {self.balance_due} XAF"
    
    def is_overdue(self):
        """Vérifie si le crédit est en retard"""
        if self.status not in ['paid', 'written_off']:
            return timezone.now().date() > self.due_date
        return False

class CreditPayment(models.Model):
    """Paiement de crédit"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credit = models.ForeignKey(
        CustomerCredit,
        on_delete=models.CASCADE,
        related_name='credit_payments',
        verbose_name="Crédit"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )
    payment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de paiement"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=Payment.PAYMENT_METHOD_CHOICES,
        verbose_name="Méthode de paiement"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='credit_payments_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'finance_credit_payments'
        ordering = ['-payment_date']
        verbose_name = "Paiement de crédit"
        verbose_name_plural = "Paiements de crédits"
    
    def __str__(self):
        return f"Paiement crédit {self.amount} XAF"


# ============================================================================
# MODÈLES DÉPENSES
# ============================================================================

class ExpenseCategory(models.Model):
    """Catégorie de dépense"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='expense_categories',
        verbose_name="Pharmacie"
    )
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'finance_expense_categories'
        ordering = ['name']
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Catégories de dépenses"
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    """Dépense"""
    EXPENSE_TYPE_CHOICES = [
        ('supplier', 'Fournisseur'),
        ('utility', 'Charge (eau, électricité)'),
        ('rent', 'Loyer'),
        ('salary', 'Salaire'),
        ('maintenance', 'Entretien'),
        ('marketing', 'Marketing'),
        ('tax', 'Taxe'),
        ('insurance', 'Assurance'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('paid', 'Payée'),
        ('rejected', 'Rejetée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name="Pharmacie"
    )
    expense_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de dépense"
    )
    
    # Catégorie et type
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Catégorie"
    )
    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE_CHOICES,
        verbose_name="Type de dépense"
    )
    
    # Description
    description = models.CharField(max_length=255, verbose_name="Description")
    
    # Montant
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )
    currency = models.ForeignKey(
        'Currency',
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Devise"
    )
    
    # Dates
    expense_date = models.DateField(
        default=timezone.now,
        verbose_name="Date de la dépense"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date d'échéance"
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Bénéficiaire
    payee = models.CharField(
        max_length=255,
        help_text="Nom du bénéficiaire",
        verbose_name="Bénéficiaire"
    )
    
    # Méthode de paiement
    payment_method = models.CharField(
        max_length=20,
        choices=Payment.PAYMENT_METHOD_CHOICES,
        blank=True,
        verbose_name="Méthode de paiement"
    )
    
    # Document
    receipt = models.FileField(
        upload_to='expenses/receipts/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Reçu"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Traçabilité
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expenses_created',
        verbose_name="Créé par"
    )
    approved_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses_approved',
        verbose_name="Approuvé par"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Approuvé le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_expenses'
        ordering = ['-expense_date']
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        indexes = [
            models.Index(fields=['pharmacie', '-expense_date']),
            models.Index(fields=['expense_number']),
            models.Index(fields=['category', '-expense_date']),
            models.Index(fields=['status', '-expense_date']),
        ]
    
    def __str__(self):
        return f"Dépense {self.expense_number} - {self.description}"


# ============================================================================
# MODÈLES PRÉVISIONS FINANCIÈRES (IA)
# ============================================================================

class FinancialForecast(models.Model):
    """Prévision financière intelligente"""
    FORECAST_TYPE_CHOICES = [
        ('revenue', 'Recettes'),
        ('expense', 'Dépenses'),
        ('profit', 'Bénéfice'),
        ('cashflow', 'Trésorerie'),
    ]
    
    PERIOD_CHOICES = [
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('yearly', 'Annuel'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='financial_forecasts',
        verbose_name="Pharmacie"
    )
    
    # Type et période
    forecast_type = models.CharField(
        max_length=20,
        choices=FORECAST_TYPE_CHOICES,
        verbose_name="Type de prévision"
    )
    period = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        verbose_name="Période"
    )
    forecast_date = models.DateField(verbose_name="Date de prévision")
    
    # Montants
    predicted_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Montant prédit",
        verbose_name="Montant prédit"
    )
    actual_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Montant réel (à remplir ultérieurement)",
        verbose_name="Montant réel"
    )
    variance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Écart entre prévu et réel",
        verbose_name="Écart"
    )
    
    # Confiance et facteurs
    confidence_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Niveau de confiance en %",
        verbose_name="Niveau de confiance %"
    )
    seasonal_factor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Facteur saisonnier"
    )
    trend_factor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Facteur de tendance"
    )
    
    # Métadonnées IA
    algorithm_used = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Algorithme utilisé"
    )
    data_points_used = models.IntegerField(
        default=0,
        verbose_name="Points de données utilisés"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_forecasts'
        unique_together = [['pharmacie', 'forecast_type', 'forecast_date', 'period']]
        ordering = ['-forecast_date']
        verbose_name = "Prévision financière"
        verbose_name_plural = "Prévisions financières"
        indexes = [
            models.Index(fields=['pharmacie', 'forecast_type', '-forecast_date']),
        ]
    
    def __str__(self):
        return f"Prévision {self.get_forecast_type_display()} - {self.forecast_date}"
    
    def calculate_variance(self):
        """Calcule l'écart entre prévu et réel"""
        if self.actual_amount is not None:
            self.variance = self.actual_amount - self.predicted_amount
            return self.variance
        return None


# ============================================================================
# MODÈLES RAPPORTS FISCAUX
# ============================================================================

class TaxReport(models.Model):
    """Rapport fiscal automatisé"""
    REPORT_TYPE_CHOICES = [
        ('vat', 'Rapport TVA'),
        ('income', 'Rapport de revenus'),
        ('expense', 'Rapport de dépenses'),
        ('comprehensive', 'Rapport complet'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('generated', 'Généré'),
        ('submitted', 'Soumis'),
        ('accepted', 'Accepté'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='tax_reports',
        verbose_name="Pharmacie"
    )
    report_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de rapport"
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name="Type de rapport"
    )
    
    # Période
    period_start = models.DateField(verbose_name="Début de période")
    period_end = models.DateField(verbose_name="Fin de période")
    
    # Données
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Revenu total"
    )
    total_tax_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total taxes collectées"
    )
    total_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Dépenses totales"
    )
    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Bénéfice net"
    )
    
    # Document
    pdf_file = models.FileField(
        upload_to='tax_reports/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Fichier PDF"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Soumis le"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tax_reports_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'finance_tax_reports'
        ordering = ['-period_end']
        verbose_name = "Rapport fiscal"
        verbose_name_plural = "Rapports fiscaux"
        indexes = [
            models.Index(fields=['pharmacie', '-period_end']),
            models.Index(fields=['report_number']),
        ]
    
    def __str__(self):
        return f"Rapport fiscal {self.report_number}"

