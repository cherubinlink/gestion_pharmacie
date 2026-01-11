"""
Modèles Django pour la gestion des ventes
Application 4 : Gestion des ventes et caisse
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from gestion_compte.models import Utilisateur, Pharmacie
from decimal import Decimal
import uuid
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File

# Create your models here.


# ============================================================================
# MODÈLES PRODUITS ET CATALOGUE
# ============================================================================

class ProductCategory(models.Model):
    """Catégories de produits"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nom")
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, verbose_name="Description")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Catégorie parente"
    )
    image = models.ImageField(
        upload_to='categories/',
        null=True,
        blank=True,
        verbose_name="Image"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    display_order = models.IntegerField(default=0, verbose_name="Ordre d'affichage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_product_categories'
        ordering = ['display_order', 'name']
        verbose_name = "Catégorie de produit"
        verbose_name_plural = "Catégories de produits"
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'display_order']),
        ]
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Modèle de produit"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Pharmacie"
    )
    name = models.CharField(max_length=255, verbose_name="Nom")
    slug = models.SlugField(max_length=255)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Catégorie"
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Code SKU"
    )
    barcode = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Code-barres"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Informations médicales
    active_ingredient = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Principe actif"
    )
    dosage = models.CharField(max_length=100, blank=True, verbose_name="Dosage")
    pharmaceutical_form = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Forme pharmaceutique"
    )
    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Fabricant"
    )
    
    # Prix et marges
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Prix d'achat HT"
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Prix de vente TTC"
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('19.25'),
        help_text="Taux de TVA en %",
        verbose_name="Taux de TVA"
    )
    
    # Stock
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité en stock"
    )
    min_stock_level = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        verbose_name="Seuil de stock minimum"
    )
    
    # Vente en ligne
    is_available_online = models.BooleanField(
        default=False,
        verbose_name="Disponible en ligne"
    )
    requires_prescription = models.BooleanField(
        default=False,
        verbose_name="Nécessite une ordonnance"
    )
    
    # Informations complémentaires
    usage_instructions = models.TextField(
        blank=True,
        verbose_name="Instructions d'utilisation"
    )
    side_effects = models.TextField(
        blank=True,
        verbose_name="Effets secondaires"
    )
    contraindications = models.TextField(
        blank=True,
        verbose_name="Contre-indications"
    )
    storage_conditions = models.TextField(
        blank=True,
        verbose_name="Conditions de conservation"
    )
    
    # Images
    main_image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name="Image principale"
    )
    images = models.JSONField(
        default=list,
        help_text="URLs des images supplémentaires",
        verbose_name="Images supplémentaires"
    )
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_featured = models.BooleanField(default=False, verbose_name="Produit vedette")
    
    # Métadonnées
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_products'
        ordering = ['-created_at']
        unique_together = [['pharmacie', 'slug']]
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        indexes = [
            models.Index(fields=['pharmacie', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['is_available_online', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def calculate_margin(self):
        """Calcule la marge bénéficiaire"""
        if self.purchase_price > 0:
            margin = self.selling_price - self.purchase_price
            margin_percentage = (margin / self.purchase_price) * 100
            return {
                'margin_amount': margin,
                'margin_percentage': margin_percentage
            }
        return {'margin_amount': 0, 'margin_percentage': 0}
    
    def is_low_stock(self):
        """Vérifie si le stock est faible"""
        return self.stock_quantity <= self.min_stock_level
    
    def is_out_of_stock(self):
        """Vérifie si le produit est en rupture de stock"""
        return self.stock_quantity == 0


# ============================================================================
# MODÈLES PROMOTIONS ET REMISES
# ============================================================================

class Promotion(models.Model):
    """Promotions et offres spéciales"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Pourcentage'),
        ('fixed_amount', 'Montant fixe'),
        ('buy_x_get_y', 'Achetez X obtenez Y'),
        ('bundle', 'Lot/Bundle'),
    ]
    
    PROMOTION_SCOPE_CHOICES = [
        ('product', 'Produit spécifique'),
        ('category', 'Catégorie'),
        ('all_products', 'Tous les produits'),
        ('loyal_customers', 'Clients fidèles'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='promotions',
        verbose_name="Pharmacie"
    )
    name = models.CharField(max_length=255, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    promotion_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Code promo (optionnel)",
        verbose_name="Code promo"
    )
    
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="Type de remise"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Pourcentage ou montant",
        verbose_name="Valeur de la remise"
    )
    
    promotion_scope = models.CharField(
        max_length=20,
        choices=PROMOTION_SCOPE_CHOICES,
        verbose_name="Portée de la promotion"
    )
    
    # Applicabilité
    applicable_products = models.ManyToManyField(
        Product,
        blank=True,
        related_name='promotions',
        verbose_name="Produits concernés"
    )
    applicable_categories = models.ManyToManyField(
        ProductCategory,
        blank=True,
        related_name='promotions',
        verbose_name="Catégories concernées"
    )
    
    # Conditions
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Montant minimum d'achat",
        verbose_name="Montant minimum"
    )
    min_quantity = models.IntegerField(
        null=True,
        blank=True,
        help_text="Quantité minimum",
        verbose_name="Quantité minimum"
    )
    max_uses = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre maximum d'utilisations",
        verbose_name="Utilisations maximum"
    )
    max_uses_per_customer = models.IntegerField(
        null=True,
        blank=True,
        help_text="Utilisations max par client",
        verbose_name="Max par client"
    )
    current_uses = models.IntegerField(
        default=0,
        verbose_name="Utilisations actuelles"
    )
    
    # Périodes
    start_date = models.DateTimeField(verbose_name="Date de début")
    end_date = models.DateTimeField(verbose_name="Date de fin")
    
    # Happy hours (optionnel)
    happy_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Début des happy hours",
        verbose_name="Début happy hours"
    )
    happy_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="Fin des happy hours",
        verbose_name="Fin happy hours"
    )
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_stackable = models.BooleanField(
        default=False,
        help_text="Peut être cumulée avec d'autres promos",
        verbose_name="Cumulable"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_promotions'
        ordering = ['-start_date']
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        indexes = [
            models.Index(fields=['pharmacie', 'is_active']),
            models.Index(fields=['promotion_code']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    def is_valid(self):
        """Vérifie si la promotion est valide"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date or now > self.end_date:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def is_in_happy_hours(self):
        """Vérifie si on est dans les happy hours"""
        if not self.happy_hours_start or not self.happy_hours_end:
            return True
        now = timezone.now().time()
        return self.happy_hours_start <= now <= self.happy_hours_end


class Coupon(models.Model):
    """Coupons de réduction"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='coupons',
        verbose_name="Pharmacie"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Pourcentage'),
            ('fixed_amount', 'Montant fixe'),
        ],
        verbose_name="Type de remise"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Valeur"
    )
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant minimum"
    )
    max_uses = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Utilisations max"
    )
    current_uses = models.IntegerField(default=0, verbose_name="Utilisations")
    valid_from = models.DateTimeField(verbose_name="Valide du")
    valid_until = models.DateTimeField(verbose_name="Valide jusqu'au")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_coupons'
        ordering = ['-created_at']
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['pharmacie', 'is_active']),
        ]
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Vérifie si le coupon est valide"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True


# ============================================================================
# MODÈLES VENTES
# ============================================================================

class Sale(models.Model):
    """Vente/Commande"""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('processing', 'En traitement'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    ]
    
    SALE_TYPE_CHOICES = [
        ('counter', 'Vente comptoir'),
        ('online', 'Commande en ligne'),
        ('phone', 'Commande téléphonique'),
        ('prescription', 'Sur ordonnance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='sales',
        verbose_name="Pharmacie"
    )
    sale_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de vente"
    )
    sale_type = models.CharField(
        max_length=20,
        choices=SALE_TYPE_CHOICES,
        default='counter',
        verbose_name="Type de vente"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Client
    customer = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases',
        verbose_name="Client"
    )
    customer_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom du client si non enregistré",
        verbose_name="Nom du client"
    )
    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone du client"
    )
    customer_email = models.EmailField(
        blank=True,
        verbose_name="Email du client"
    )
    
    # Ordonnance
    prescription = models.ForeignKey(
        'ElectronicPrescription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name="Ordonnance"
    )
    
    # Montants
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Sous-total"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant remise"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant TVA"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant total"
    )
    profit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Bénéfice"
    )
    
    # Promotions appliquées
    applied_promotions = models.ManyToManyField(
        'Promotion',
        blank=True,
        related_name='sales',
        verbose_name="Promotions appliquées"
    )
    applied_coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name="Coupon appliqué"
    )
    
    # Vendeur
    cashier = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_made',
        verbose_name="Caissier"
    )
    
    # QR Code pour le ticket
    ticket_qr_code = models.ImageField(
        upload_to='tickets/qr/',
        null=True,
        blank=True,
        verbose_name="QR Code du ticket"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    internal_notes = models.TextField(
        blank=True,
        verbose_name="Notes internes"
    )
    
    # Mode hors ligne
    is_offline_sale = models.BooleanField(
        default=False,
        verbose_name="Vente hors ligne"
    )
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Synchronisée le"
    )
    
    # Dates
    sale_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de vente"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Terminée le"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_sales'
        ordering = ['-sale_date']
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        indexes = [
            models.Index(fields=['pharmacie', '-sale_date']),
            models.Index(fields=['sale_number']),
            models.Index(fields=['customer', '-sale_date']),
            models.Index(fields=['status', '-sale_date']),
            models.Index(fields=['sale_type', '-sale_date']),
        ]
    
    def __str__(self):
        return f"Vente {self.sale_number}"
    
    def calculate_totals(self):
        """Calcule les totaux de la vente"""
        items = self.items.all()
        
        subtotal = sum(item.line_total for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        profit_amount = sum(item.profit_amount for item in items)
        
        # Appliquer les remises
        discount_amount = Decimal('0.00')
        
        # Coupon
        if self.applied_coupon and self.applied_coupon.is_valid():
            if self.applied_coupon.discount_type == 'percentage':
                discount_amount += (subtotal * self.applied_coupon.discount_value / 100)
            else:
                discount_amount += self.applied_coupon.discount_value
        
        total_amount = subtotal + tax_amount - discount_amount
        
        return {
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'tax_amount': tax_amount,
            'total_amount': total_amount,
            'profit_amount': profit_amount
        }



class SaleItem(models.Model):
    """Ligne de vente"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Vente"
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name="Produit"
    )
    
    # Quantités et prix
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix unitaire"
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Coût unitaire"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Remise %"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant remise"
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
        verbose_name="TVA"
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total ligne"
    )
    profit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Bénéfice"
    )
    
    # Promotion appliquée
    applied_promotion = models.ForeignKey(
        'Promotion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Promotion appliquée"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_sale_items'
        ordering = ['created_at']
        verbose_name = "Ligne de vente"
        verbose_name_plural = "Lignes de vente"
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        """Calcul automatique des totaux"""
        # Sous-total avant remise
        self.line_subtotal = self.unit_price * self.quantity
        
        # Appliquer la remise
        if self.discount_percentage > 0:
            self.discount_amount = (self.line_subtotal * self.discount_percentage / 100)
        
        # Total après remise
        total_after_discount = self.line_subtotal - self.discount_amount
        
        # Calculer la TVA
        tax_rate = self.product.tax_rate / 100
        self.tax_amount = total_after_discount * tax_rate
        
        # Total ligne
        self.line_total = total_after_discount + self.tax_amount
        
        # Bénéfice = (Prix vente - Coût) * Quantité
        self.profit_amount = (self.unit_price - self.unit_cost) * self.quantity - self.discount_amount
        
        super().save(*args, **kwargs)


# ============================================================================
# MODÈLES PAIEMENTS
# ============================================================================

class Payment(models.Model):
    """Paiement"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('mobile_money', 'Mobile Money'),
        ('online', 'Paiement en ligne'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('deferred', 'Paiement différé'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Vente"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Méthode de paiement"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Informations spécifiques
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID de transaction (pour paiements en ligne)",
        verbose_name="ID de transaction"
    )
    reference_number = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Numéro de référence"
    )
    
    # Paiement fractionné
    is_installment = models.BooleanField(
        default=False,
        verbose_name="Paiement fractionné"
    )
    installment_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Numéro de versement",
        verbose_name="N° versement"
    )
    total_installments = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Total versements"
    )
    
    # Métadonnées
    payment_details = models.JSONField(
        default=dict,
        help_text="Détails supplémentaires du paiement",
        verbose_name="Détails"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    processed_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments_processed',
        verbose_name="Traité par"
    )
    
    payment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de paiement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_payments'
        ordering = ['-payment_date']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        indexes = [
            models.Index(fields=['sale', '-payment_date']),
            models.Index(fields=['payment_method', '-payment_date']),
            models.Index(fields=['status', '-payment_date']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"Paiement {self.amount} - {self.get_payment_method_display()}"


class PaymentInstallment(models.Model):
    """Plan de paiement fractionné"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='payment_plan',
        verbose_name="Vente"
    )
    installment_number = models.IntegerField(verbose_name="N° versement")
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant"
    )
    due_date = models.DateField(verbose_name="Date d'échéance")
    is_paid = models.BooleanField(default=False, verbose_name="Payé")
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installments',
        verbose_name="Paiement"
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_payment_installments'
        ordering = ['installment_number']
        unique_together = [['sale', 'installment_number']]
        verbose_name = "Versement"
        verbose_name_plural = "Versements"
    
    def __str__(self):
        return f"Versement {self.installment_number} - {self.amount}"



# ============================================================================
# MODÈLES ORDONNANCES ÉLECTRONIQUES
# ============================================================================

class ElectronicPrescription(models.Model):
    """Ordonnance électronique"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('validated', 'Validée'),
        ('rejected', 'Rejetée'),
        ('dispensed', 'Délivrée'),
        ('partially_dispensed', 'Partiellement délivrée'),
        ('archived', 'Archivée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='electronic_prescriptions',
        verbose_name="Pharmacie"
    )
    prescription_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'ordonnance"
    )
    
    # Patient
    patient = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name="Patient"
    )
    
    # Prescripteur
    doctor_name = models.CharField(
        max_length=255,
        verbose_name="Nom du médecin"
    )
    doctor_license = models.CharField(
        max_length=100,
        verbose_name="N° de licence du médecin"
    )
    doctor_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone du médecin"
    )
    
    # Dates
    prescription_date = models.DateField(verbose_name="Date de prescription")
    expiry_date = models.DateField(verbose_name="Date d'expiration")
    
    # Document
    document = models.FileField(
        upload_to='prescriptions/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Document"
    )
    
    # Validation
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    validated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions_validated',
        verbose_name="Validé par"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Validé le"
    )
    validation_notes = models.TextField(
        blank=True,
        verbose_name="Notes de validation"
    )
    
    # Détection de fraude
    is_duplicate = models.BooleanField(
        default=False,
        verbose_name="Doublon détecté"
    )
    fraud_score = models.IntegerField(
        default=0,
        help_text="Score de suspicion de fraude (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score de fraude"
    )
    fraud_flags = models.JSONField(
        default=list,
        help_text="Indicateurs de fraude détectés",
        verbose_name="Alertes fraude"
    )
    
    # Archivage
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Archivé le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_electronic_prescriptions'
        ordering = ['-prescription_date']
        verbose_name = "Ordonnance électronique"
        verbose_name_plural = "Ordonnances électroniques"
        indexes = [
            models.Index(fields=['pharmacie', '-prescription_date']),
            models.Index(fields=['prescription_number']),
            models.Index(fields=['patient', '-prescription_date']),
            models.Index(fields=['status', '-prescription_date']),
            models.Index(fields=['is_duplicate']),
        ]
    
    def __str__(self):
        return f"Ordonnance {self.prescription_number}"
    
    def is_expired(self):
        """Vérifie si l'ordonnance est expirée"""
        return timezone.now().date() > self.expiry_date



# ============================================================================
# MODÈLES ANALYTICS ET RAPPORTS
# ============================================================================

class SalesAnalytics(models.Model):
    """Analytics des ventes par période"""
    PERIOD_TYPE_CHOICES = [
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
        related_name='sales_analytics',
        verbose_name="Pharmacie"
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        verbose_name="Type de période"
    )
    period_start = models.DateField(verbose_name="Début période")
    period_end = models.DateField(verbose_name="Fin période")
    
    # Métriques de ventes
    total_sales_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de ventes"
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Chiffre d'affaires"
    )
    total_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Bénéfice total"
    )
    average_basket = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Panier moyen"
    )
    
    # Métriques produits
    total_items_sold = models.IntegerField(
        default=0,
        verbose_name="Articles vendus"
    )
    unique_products_sold = models.IntegerField(
        default=0,
        verbose_name="Produits uniques vendus"
    )
    
    # Métriques clients
    total_customers = models.IntegerField(
        default=0,
        verbose_name="Nombre de clients"
    )
    new_customers = models.IntegerField(
        default=0,
        verbose_name="Nouveaux clients"
    )
    returning_customers = models.IntegerField(
        default=0,
        verbose_name="Clients fidèles"
    )
    
    # Métriques de performance
    best_selling_product = models.JSONField(
        default=dict,
        help_text="Produit le plus vendu {id, name, quantity}",
        verbose_name="Produit best-seller"
    )
    best_revenue_product = models.JSONField(
        default=dict,
        help_text="Produit générant le plus de CA",
        verbose_name="Produit top CA"
    )
    
    # Tendances
    revenue_trend = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Évolution en % par rapport à la période précédente",
        verbose_name="Tendance CA %"
    )
    profit_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Marge bénéficiaire moyenne en %",
        verbose_name="Marge %"
    )
    
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_analytics'
        unique_together = [['pharmacie', 'period_type', 'period_start']]
        ordering = ['-period_start']
        verbose_name = "Analytics de vente"
        verbose_name_plural = "Analytics de ventes"
        indexes = [
            models.Index(fields=['pharmacie', 'period_type', '-period_start']),
        ]
    
    def __str__(self):
        return f"Analytics {self.pharmacie.nom} - {self.period_start}"


class ProductPerformance(models.Model):
    """Performance des produits"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='performance_metrics',
        verbose_name="Produit"
    )
    period_start = models.DateField(verbose_name="Début période")
    period_end = models.DateField(verbose_name="Fin période")
    
    # Ventes
    units_sold = models.IntegerField(default=0, verbose_name="Unités vendues")
    revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="CA généré"
    )
    profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Bénéfice"
    )
    
    # Tendances
    sales_trend = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Évolution des ventes en %",
        verbose_name="Tendance ventes %"
    )
    
    # Alertes
    is_declining = models.BooleanField(
        default=False,
        verbose_name="En baisse"
    )
    restock_recommended = models.BooleanField(
        default=False,
        verbose_name="Réassort recommandé"
    )
    recommended_quantity = models.IntegerField(
        default=0,
        verbose_name="Quantité recommandée"
    )
    
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_product_performance'
        unique_together = [['product', 'period_start']]
        ordering = ['-period_start', '-revenue']
        verbose_name = "Performance produit"
        verbose_name_plural = "Performances produits"
        indexes = [
            models.Index(fields=['product', '-period_start']),
            models.Index(fields=['-revenue']),
            models.Index(fields=['is_declining']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.period_start}"


# ============================================================================
# MODÈLES RECOMMANDATIONS
# ============================================================================

class CustomerPurchasePattern(models.Model):
    """Analyse des comportements d'achat des clients"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='purchase_patterns',
        verbose_name="Client"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='customer_patterns',
        verbose_name="Pharmacie"
    )
    
    # Fréquence d'achat
    total_purchases = models.IntegerField(
        default=0,
        verbose_name="Nombre d'achats"
    )
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total dépensé"
    )
    average_basket_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Panier moyen"
    )
    
    # Préférences
    favorite_categories = models.JSONField(
        default=list,
        help_text="Catégories préférées",
        verbose_name="Catégories favorites"
    )
    favorite_products = models.JSONField(
        default=list,
        help_text="Produits achetés régulièrement",
        verbose_name="Produits favoris"
    )
    
    # Comportement
    average_purchase_frequency = models.IntegerField(
        default=0,
        help_text="Fréquence moyenne en jours",
        verbose_name="Fréquence moyenne (jours)"
    )
    last_purchase_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dernier achat"
    )
    next_predicted_purchase = models.DateField(
        null=True,
        blank=True,
        help_text="Date prédite du prochain achat",
        verbose_name="Prochain achat prédit"
    )
    
    # Alertes
    is_at_risk = models.BooleanField(
        default=False,
        help_text="Client à risque de désabonnement",
        verbose_name="À risque"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_customer_patterns'
        unique_together = [['customer', 'pharmacie']]
        verbose_name = "Comportement d'achat"
        verbose_name_plural = "Comportements d'achat"
        indexes = [
            models.Index(fields=['customer', 'pharmacie']),
            models.Index(fields=['is_at_risk']),
        ]
    
    def __str__(self):
        return f"Pattern {self.customer.get_full_name()}"


class ProductRecommendation(models.Model):
    """Recommandations de produits"""
    RECOMMENDATION_TYPE_CHOICES = [
        ('frequently_bought_together', 'Souvent achetés ensemble'),
        ('similar_products', 'Produits similaires'),
        ('complementary', 'Produits complémentaires'),
        ('based_on_history', 'Basé sur l\'historique'),
        ('trending', 'Tendance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='recommendations_from',
        verbose_name="Produit source"
    )
    recommended_product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='recommendations_to',
        verbose_name="Produit recommandé"
    )
    recommendation_type = models.CharField(
        max_length=30,
        choices=RECOMMENDATION_TYPE_CHOICES,
        verbose_name="Type de recommandation"
    )
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score de confiance (0-100)",
        verbose_name="Score de confiance"
    )
    times_bought_together = models.IntegerField(
        default=0,
        verbose_name="Fois achetés ensemble"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales_product_recommendations'
        unique_together = [['source_product', 'recommended_product']]
        ordering = ['-confidence_score']
        verbose_name = "Recommandation produit"
        verbose_name_plural = "Recommandations produits"
        indexes = [
            models.Index(fields=['source_product', '-confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.source_product.name} → {self.recommended_product.name}"


# ============================================================================
# MODÈLES DÉTECTION DE FRAUDE
# ============================================================================

class FraudAlert(models.Model):
    """Alertes de fraude détectées"""
    ALERT_TYPE_CHOICES = [
        ('duplicate_prescription', 'Ordonnance en double'),
        ('unusual_purchase_pattern', 'Pattern d\'achat inhabituel'),
        ('excessive_quantity', 'Quantité excessive'),
        ('rapid_repeat_purchase', 'Rachat rapide'),
        ('suspicious_prescription', 'Ordonnance suspecte'),
        ('resale_indicator', 'Indicateur de revente'),
        ('multiple_pharmacies', 'Achats dans plusieurs pharmacies'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Élevée'),
        ('critical', 'Critique'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Nouvelle'),
        ('investigating', 'En investigation'),
        ('confirmed', 'Confirmée'),
        ('false_positive', 'Fausse alerte'),
        ('resolved', 'Résolue'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='fraud_alerts',
        verbose_name="Pharmacie"
    )
    alert_type = models.CharField(
        max_length=30,
        choices=ALERT_TYPE_CHOICES,
        verbose_name="Type d'alerte"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        verbose_name="Sévérité"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Statut"
    )
    
    # Entités concernées
    customer = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fraud_alerts',
        verbose_name="Client"
    )
    sale = models.ForeignKey(
        'Sale',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fraud_alerts',
        verbose_name="Vente"
    )
    prescription = models.ForeignKey(
        'ElectronicPrescription',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fraud_alerts',
        verbose_name="Ordonnance"
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fraud_alerts',
        verbose_name="Produit"
    )
    
    # Détails
    description = models.TextField(verbose_name="Description")
    indicators = models.JSONField(
        default=list,
        help_text="Indicateurs détectés",
        verbose_name="Indicateurs"
    )
    risk_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score de risque (0-100)",
        verbose_name="Score de risque"
    )
    
    # Investigation
    investigated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fraud_investigations',
        verbose_name="Investigué par"
    )
    investigation_notes = models.TextField(
        blank=True,
        verbose_name="Notes d'investigation"
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name="Notes de résolution"
    )
    
    # Actions prises
    actions_taken = models.JSONField(
        default=list,
        help_text="Actions entreprises",
        verbose_name="Actions prises"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Résolue le"
    )
    
    class Meta:
        db_table = 'sales_fraud_alerts'
        ordering = ['-created_at']
        verbose_name = "Alerte de fraude"
        verbose_name_plural = "Alertes de fraude"
        indexes = [
            models.Index(fields=['pharmacie', 'status', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['severity', 'status']),
        ]
    
    def __str__(self):
        return f"Alerte {self.get_alert_type_display()} - {self.severity}"


class PurchaseAnomalyLog(models.Model):
    """Journal des anomalies d'achat détectées"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='purchase_anomalies',
        verbose_name="Client"
    )
    sale = models.ForeignKey(
        'Sale',
        on_delete=models.CASCADE,
        related_name='anomaly_logs',
        verbose_name="Vente"
    )
    anomaly_type = models.CharField(max_length=100, verbose_name="Type d'anomalie")
    description = models.TextField(verbose_name="Description")
    anomaly_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score d'anomalie"
    )
    details = models.JSONField(
        default=dict,
        verbose_name="Détails"
    )
    auto_flagged = models.BooleanField(
        default=True,
        help_text="Détecté automatiquement",
        verbose_name="Auto-détecté"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_purchase_anomaly_logs'
        ordering = ['-created_at']
        verbose_name = "Anomalie d'achat"
        verbose_name_plural = "Anomalies d'achat"
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['sale']),
        ]
    
    def __str__(self):
        return f"Anomalie {self.anomaly_type} - {self.customer.get_full_name()}"
