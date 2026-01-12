"""
Modèles Django pour la gestion de stock et approvisionnements
Application 5 : Gestion du stock & approvisionnements
Partie 1 : Fournisseurs, Emplacements, Lots, Stock
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator, FileExtensionValidator
from gestion_compte.models import Utilisateur, Pharmacie
from decimal import Decimal
import uuid
from django.utils import timezone
from datetime import timedelta

# Create your models here.



# ============================================================================
# MODÈLES FOURNISSEURS
# ============================================================================

class Supplier(models.Model):
    """Fournisseur"""
    SUPPLIER_TYPE_CHOICES = [
        ('manufacturer', 'Fabricant'),
        ('wholesaler', 'Grossiste'),
        ('distributor', 'Distributeur'),
        ('importer', 'Importateur'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('inactive', 'Inactif'),
        ('blacklisted', 'Liste noire'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='suppliers',
        verbose_name="Pharmacie"
    )
    supplier_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code fournisseur"
    )
    name = models.CharField(max_length=255, verbose_name="Nom")
    supplier_type = models.CharField(
        max_length=20,
        choices=SUPPLIER_TYPE_CHOICES,
        verbose_name="Type"
    )
    
    # Informations de contact
    contact_person = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Personne de contact"
    )
    email = models.EmailField(
        validators=[EmailValidator()],
        verbose_name="Email"
    )
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    fax = models.CharField(max_length=20, blank=True, verbose_name="Fax")
    website = models.URLField(blank=True, verbose_name="Site web")
    
    # Adresse
    address = models.TextField(verbose_name="Adresse")
    city = models.CharField(max_length=100, verbose_name="Ville")
    country = models.CharField(max_length=100, verbose_name="Pays")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Code postal")
    
    # Informations légales
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="N° d'identification fiscale"
    )
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="N° d'enregistrement"
    )
    
    # Conditions commerciales
    payment_terms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Ex: 30 jours net, paiement à la livraison",
        verbose_name="Conditions de paiement"
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant minimum de commande"
    )
    delivery_time = models.IntegerField(
        null=True,
        blank=True,
        help_text="Délai de livraison en jours",
        verbose_name="Délai de livraison (jours)"
    )
    
    # Performance
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Note sur 5",
        verbose_name="Évaluation"
    )
    total_orders = models.IntegerField(
        default=0,
        verbose_name="Total commandes"
    )
    on_time_delivery_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Taux de livraison à temps en %",
        verbose_name="Taux livraison à temps %"
    )
    quality_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Taux de qualité des produits en %",
        verbose_name="Taux qualité %"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    is_preferred = models.BooleanField(
        default=False,
        verbose_name="Fournisseur préféré"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='suppliers_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_suppliers'
        ordering = ['name']
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        indexes = [
            models.Index(fields=['pharmacie', 'status']),
            models.Index(fields=['supplier_code']),
            models.Index(fields=['is_preferred', '-rating']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.supplier_code})"
    
    def calculate_performance_score(self):
        """Calcule le score de performance global"""
        weights = {
            'on_time_delivery': 0.4,
            'quality': 0.4,
            'rating': 0.2
        }
        score = (
            (self.on_time_delivery_rate / 100) * weights['on_time_delivery'] +
            (self.quality_rate / 100) * weights['quality'] +
            (float(self.rating) / 5) * weights['rating']
        ) * 100
        return round(score, 2)


# ============================================================================
# MODÈLES EMPLACEMENTS DE STOCK
# ============================================================================

class StorageLocation(models.Model):
    """Emplacement de stockage"""
    LOCATION_TYPE_CHOICES = [
        ('shelf', 'Rayon'),
        ('reserve', 'Réserve'),
        ('warehouse', 'Entrepôt'),
        ('refrigerator', 'Réfrigérateur'),
        ('freezer', 'Congélateur'),
        ('safe', 'Coffre'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='storage_locations',
        verbose_name="Pharmacie"
    )
    location_code = models.CharField(
        max_length=50,
        verbose_name="Code emplacement"
    )
    name = models.CharField(max_length=255, verbose_name="Nom")
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        verbose_name="Type"
    )
    
    # Hiérarchie
    parent_location = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_locations',
        verbose_name="Emplacement parent"
    )
    
    # Caractéristiques
    capacity = models.IntegerField(
        null=True,
        blank=True,
        help_text="Capacité en unités",
        verbose_name="Capacité"
    )
    temperature_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Température minimale en °C",
        verbose_name="Température min (°C)"
    )
    temperature_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Température maximale en °C",
        verbose_name="Température max (°C)"
    )
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_storage_locations'
        unique_together = [['pharmacie', 'location_code']]
        ordering = ['location_type', 'name']
        verbose_name = "Emplacement de stockage"
        verbose_name_plural = "Emplacements de stockage"
        indexes = [
            models.Index(fields=['pharmacie', 'location_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.location_code})"
    
    def get_current_occupancy(self):
        """Calcule le taux d'occupation actuel"""
        if not self.capacity:
            return None
        total_items = self.stock_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        return (total_items / self.capacity) * 100


# ============================================================================
# MODÈLES LOTS ET STOCK
# ============================================================================

class Batch(models.Model):
    """Lot de produits"""
    STATUS_CHOICES = [
        ('in_stock', 'En stock'),
        ('reserved', 'Réservé'),
        ('expired', 'Expiré'),
        ('recalled', 'Rappelé'),
        ('quarantine', 'En quarantaine'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='batches',
        verbose_name="Produit"
    )
    batch_number = models.CharField(
        max_length=100,
        verbose_name="Numéro de lot"
    )
    
    # Dates
    manufacturing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fabrication"
    )
    expiry_date = models.DateField(verbose_name="Date d'expiration")
    
    # Quantités
    initial_quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Quantité initiale"
    )
    current_quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Quantité actuelle"
    )
    reserved_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité réservée"
    )
    
    # Traçabilité
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches',
        verbose_name="Fournisseur"
    )
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches',
        verbose_name="Bon de commande"
    )
    
    # Coût
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Coût unitaire"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_stock',
        verbose_name="Statut"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_batches'
        ordering = ['expiry_date']
        verbose_name = "Lot"
        verbose_name_plural = "Lots"
        indexes = [
            models.Index(fields=['product', 'expiry_date']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['status', 'expiry_date']),
        ]
    
    def __str__(self):
        return f"Lot {self.batch_number} - {self.product.name}"
    
    def is_expired(self):
        """Vérifie si le lot est expiré"""
        return timezone.now().date() > self.expiry_date
    
    def days_until_expiry(self):
        """Calcule le nombre de jours avant expiration"""
        delta = self.expiry_date - timezone.now().date()
        return delta.days
    
    def available_quantity(self):
        """Quantité disponible (hors réservations)"""
        return self.current_quantity - self.reserved_quantity


class StockItem(models.Model):
    """Item de stock (produit + emplacement + lot)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name="Produit"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name="Lot"
    )
    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name='stock_items',
        verbose_name="Emplacement"
    )
    
    quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Quantité"
    )
    
    # Métadonnées
    last_counted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Dernière date d'inventaire",
        verbose_name="Dernier comptage"
    )
    last_counted_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_counts',
        verbose_name="Dernier comptage par"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_items'
        unique_together = [['product', 'batch', 'storage_location']]
        ordering = ['batch__expiry_date']
        verbose_name = "Item de stock"
        verbose_name_plural = "Items de stock"
        indexes = [
            models.Index(fields=['product', 'storage_location']),
            models.Index(fields=['batch', 'storage_location']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.storage_location.name} - Qté: {self.quantity}"


class StockMovement(models.Model):
    """Mouvement de stock"""
    MOVEMENT_TYPE_CHOICES = [
        ('purchase', 'Achat/Réception'),
        ('sale', 'Vente'),
        ('transfer', 'Transfert'),
        ('adjustment', 'Ajustement'),
        ('return_supplier', 'Retour fournisseur'),
        ('return_customer', 'Retour client'),
        ('loss', 'Perte'),
        ('damage', 'Avarie'),
        ('expiry', 'Péremption'),
        ('inventory', 'Inventaire'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name="Pharmacie"
    )
    movement_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de mouvement"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES,
        verbose_name="Type de mouvement"
    )
    
    # Produit et lot
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name="Produit"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name="Lot"
    )
    
    # Emplacements
    from_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_out',
        verbose_name="Emplacement de départ"
    )
    to_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_in',
        verbose_name="Emplacement d'arrivée"
    )
    
    # Quantité
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantité"
    )
    
    # Références
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name="Bon de commande"
    )
    sale = models.ForeignKey(
        'gestion_vente.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name="Vente"
    )
    
    # Informations
    reason = models.TextField(blank=True, verbose_name="Raison")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Traçabilité
    performed_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements_performed',
        verbose_name="Effectué par"
    )
    movement_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date du mouvement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-movement_date']
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"
        indexes = [
            models.Index(fields=['pharmacie', '-movement_date']),
            models.Index(fields=['product', '-movement_date']),
            models.Index(fields=['movement_type', '-movement_date']),
            models.Index(fields=['movement_number']),
        ]
    
    def __str__(self):
        return f"{self.movement_number} - {self.get_movement_type_display()}"


# ============================================================================
# MODÈLES COMMANDES FOURNISSEURS
# ============================================================================

class PurchaseOrder(models.Model):
    """Bon de commande fournisseur"""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('confirmed', 'Confirmée'),
        ('partially_received', 'Partiellement reçue'),
        ('received', 'Reçue'),
        ('cancelled', 'Annulée'),
        ('closed', 'Clôturée'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='purchase_orders',
        verbose_name="Pharmacie"
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de commande"
    )
    supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name="Fournisseur"
    )
    
    # Dates
    order_date = models.DateField(
        default=timezone.now,
        verbose_name="Date de commande"
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de livraison prévue"
    )
    actual_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de livraison réelle"
    )
    
    # Statut et priorité
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="Priorité"
    )
    
    # Montants
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
        verbose_name="Montant TVA"
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais de livraison"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
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
    
    # Livraison
    delivery_address = models.TextField(
        blank=True,
        verbose_name="Adresse de livraison"
    )
    shipping_method = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Méthode d'expédition"
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numéro de suivi"
    )
    
    # Documents
    pdf_file = models.FileField(
        upload_to='purchase_orders/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="Fichier PDF"
    )
    
    # Génération automatique
    is_auto_generated = models.BooleanField(
        default=False,
        help_text="Commande générée automatiquement",
        verbose_name="Générée automatiquement"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    internal_notes = models.TextField(
        blank=True,
        verbose_name="Notes internes"
    )
    
    # Envoi
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Envoyée le"
    )
    sent_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders_sent',
        verbose_name="Envoyée par"
    )
    sent_method = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('email', 'Email'),
            ('fax', 'Fax'),
            ('phone', 'Téléphone'),
            ('portal', 'Portail fournisseur'),
            ('other', 'Autre'),
        ],
        verbose_name="Méthode d'envoi"
    )
    
    # Traçabilité
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='purchase_orders_created',
        verbose_name="Créé par"
    )
    approved_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders_approved',
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
        db_table = 'stock_purchase_orders'
        ordering = ['-order_date']
        verbose_name = "Bon de commande"
        verbose_name_plural = "Bons de commande"
        indexes = [
            models.Index(fields=['pharmacie', '-order_date']),
            models.Index(fields=['supplier', '-order_date']),
            models.Index(fields=['status', '-order_date']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"Commande {self.order_number} - {self.supplier.name}"
    
    def calculate_totals(self):
        """Calcule les totaux de la commande"""
        items = self.items.all()
        subtotal = sum(item.line_total for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        total = subtotal + tax_amount + self.shipping_cost - self.discount_amount
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total_amount': total
        }
    
    def is_overdue(self):
        """Vérifie si la livraison est en retard"""
        if self.expected_delivery_date and self.status not in ['received', 'cancelled', 'closed']:
            return timezone.now().date() > self.expected_delivery_date
        return False


class PurchaseOrderItem(models.Model):
    """Ligne de commande fournisseur"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Commande"
    )
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.PROTECT,
        related_name='purchase_order_items',
        verbose_name="Produit"
    )
    
    # Quantités
    quantity_ordered = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantité commandée"
    )
    quantity_received = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité reçue"
    )
    
    # Prix
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
        verbose_name="Montant TVA"
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total ligne"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_purchase_order_items'
        ordering = ['created_at']
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity_ordered}"
    
    def save(self, *args, **kwargs):
        """Calcul automatique des totaux"""
        # Sous-total
        self.line_subtotal = self.unit_price * self.quantity_ordered
        
        # Appliquer la remise
        if self.discount_percentage > 0:
            discount = (self.line_subtotal * self.discount_percentage / 100)
            self.line_subtotal -= discount
        
        # TVA
        tax_rate = self.product.tax_rate / 100
        self.tax_amount = self.line_subtotal * tax_rate
        
        # Total
        self.line_total = self.line_subtotal + self.tax_amount
        
        super().save(*args, **kwargs)



# ============================================================================
# MODÈLES RÉCEPTION ET CONTRÔLE
# ============================================================================

class Reception(models.Model):
    """Réception de commande"""
    STATUS_CHOICES = [
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('rejected', 'Rejetée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='receptions',
        verbose_name="Pharmacie"
    )
    reception_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de réception"
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='receptions',
        verbose_name="Bon de commande"
    )
    
    # Dates
    reception_date = models.DateField(
        default=timezone.now,
        verbose_name="Date de réception"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name="Statut"
    )
    
    # Informations de livraison
    delivery_note_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="N° bon de livraison"
    )
    carrier_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom du transporteur"
    )
    
    # Conformité
    is_complete = models.BooleanField(
        default=True,
        verbose_name="Livraison complète"
    )
    has_discrepancies = models.BooleanField(
        default=False,
        verbose_name="Écarts détectés"
    )
    has_damages = models.BooleanField(
        default=False,
        verbose_name="Avaries détectées"
    )
    
    # Documents
    delivery_note_file = models.FileField(
        upload_to='receptions/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Bon de livraison"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Traçabilité
    received_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='receptions_performed',
        verbose_name="Réceptionné par"
    )
    validated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receptions_validated',
        verbose_name="Validé par"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Validé le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_receptions'
        ordering = ['-reception_date']
        verbose_name = "Réception"
        verbose_name_plural = "Réceptions"
        indexes = [
            models.Index(fields=['pharmacie', '-reception_date']),
            models.Index(fields=['purchase_order', '-reception_date']),
            models.Index(fields=['reception_number']),
        ]
    
    def __str__(self):
        return f"Réception {self.reception_number}"



class ReceptionItem(models.Model):
    """Ligne de réception"""
    DISCREPANCY_TYPE_CHOICES = [
        ('none', 'Aucun'),
        ('missing', 'Manquant'),
        ('excess', 'Surplus'),
        ('damaged', 'Endommagé'),
        ('wrong_product', 'Produit incorrect'),
        ('expired', 'Expiré'),
        ('quality_issue', 'Problème de qualité'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reception = models.ForeignKey(
        Reception,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Réception"
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.CASCADE,
        related_name='reception_items',
        verbose_name="Ligne de commande"
    )
    
    # Quantités
    quantity_expected = models.IntegerField(
        verbose_name="Quantité attendue"
    )
    quantity_received = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Quantité reçue"
    )
    quantity_accepted = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Quantité acceptée"
    )
    quantity_rejected = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité rejetée"
    )
    
    # Lot
    batch_number = models.CharField(
        max_length=100,
        verbose_name="Numéro de lot"
    )
    expiry_date = models.DateField(verbose_name="Date d'expiration")
    
    # Contrôle
    is_conform = models.BooleanField(
        default=True,
        verbose_name="Conforme"
    )
    discrepancy_type = models.CharField(
        max_length=20,
        choices=DISCREPANCY_TYPE_CHOICES,
        default='none',
        verbose_name="Type d'écart"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_reception_items'
        ordering = ['created_at']
        verbose_name = "Ligne de réception"
        verbose_name_plural = "Lignes de réception"
    
    def __str__(self):
        product_name = self.purchase_order_item.product.name
        return f"{product_name} - Reçu: {self.quantity_received}"
    
    def has_discrepancy(self):
        """Vérifie s'il y a un écart"""
        return self.quantity_received != self.quantity_expected or not self.is_conform


# ============================================================================
# MODÈLES INVENTAIRES
# ============================================================================

class Inventory(models.Model):
    """Inventaire"""
    INVENTORY_TYPE_CHOICES = [
        ('full', 'Inventaire complet'),
        ('partial', 'Inventaire partiel'),
        ('cycle', 'Inventaire tournant'),
        ('spot_check', 'Contrôle ponctuel'),
    ]
    
    STATUS_CHOICES = [
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('validated', 'Validé'),
        ('cancelled', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name="Pharmacie"
    )
    inventory_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'inventaire"
    )
    inventory_type = models.CharField(
        max_length=20,
        choices=INVENTORY_TYPE_CHOICES,
        verbose_name="Type d'inventaire"
    )
    
    # Dates
    scheduled_date = models.DateField(
        verbose_name="Date prévue"
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de début"
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        verbose_name="Statut"
    )
    
    # Périmètre
    storage_locations = models.ManyToManyField(
        'StorageLocation',
        blank=True,
        related_name='inventories',
        verbose_name="Emplacements concernés"
    )
    product_categories = models.ManyToManyField(
        'gestion_vente.ProductCategory',
        blank=True,
        related_name='inventories',
        verbose_name="Catégories concernées"
    )
    
    # Statistiques
    total_items_counted = models.IntegerField(
        default=0,
        verbose_name="Nombre d'items comptés"
    )
    total_discrepancies = models.IntegerField(
        default=0,
        verbose_name="Nombre d'écarts"
    )
    value_discrepancy = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Valeur des écarts",
        verbose_name="Valeur des écarts"
    )
    
    # Participants
    assigned_to = models.ManyToManyField(
        Utilisateur,
        related_name='inventories_assigned',
        verbose_name="Assigné à"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Traçabilité
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventories_created',
        verbose_name="Créé par"
    )
    validated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories_validated',
        verbose_name="Validé par"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Validé le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_inventories'
        ordering = ['-scheduled_date']
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaires"
        indexes = [
            models.Index(fields=['pharmacie', '-scheduled_date']),
            models.Index(fields=['status', '-scheduled_date']),
            models.Index(fields=['inventory_number']),
        ]
    
    def __str__(self):
        return f"Inventaire {self.inventory_number}"


class InventoryCount(models.Model):
    """Comptage d'inventaire"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='counts',
        verbose_name="Inventaire"
    )
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='inventory_counts',
        verbose_name="Produit"
    )
    batch = models.ForeignKey(
        'Batch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='inventory_counts',
        verbose_name="Lot"
    )
    storage_location = models.ForeignKey(
        'StorageLocation',
        on_delete=models.CASCADE,
        related_name='inventory_counts',
        verbose_name="Emplacement"
    )
    
    # Quantités
    expected_quantity = models.IntegerField(
        default=0,
        help_text="Quantité système",
        verbose_name="Quantité attendue"
    )
    counted_quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Quantité physique comptée",
        verbose_name="Quantité comptée"
    )
    discrepancy = models.IntegerField(
        default=0,
        help_text="Écart = Compté - Attendu",
        verbose_name="Écart"
    )
    
    # Valeurs
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Coût unitaire"
    )
    discrepancy_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Valeur de l'écart"
    )
    
    # Vérification
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Vérifié"
    )
    recount_required = models.BooleanField(
        default=False,
        verbose_name="Recomptage requis"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Traçabilité
    counted_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_counts_performed',
        verbose_name="Compté par"
    )
    counted_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Compté le"
    )
    verified_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_counts_verified',
        verbose_name="Vérifié par"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Vérifié le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_inventory_counts'
        unique_together = [['inventory', 'product', 'batch', 'storage_location']]
        ordering = ['storage_location', 'product']
        verbose_name = "Comptage d'inventaire"
        verbose_name_plural = "Comptages d'inventaire"
        indexes = [
            models.Index(fields=['inventory', 'storage_location']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - Écart: {self.discrepancy}"
    
    def save(self, *args, **kwargs):
        """Calcul automatique de l'écart"""
        self.discrepancy = self.counted_quantity - self.expected_quantity
        self.discrepancy_value = self.discrepancy * self.unit_cost
        super().save(*args, **kwargs)


# ============================================================================
# MODÈLES PRÉVISIONS ET IA
# ============================================================================

class StockForecast(models.Model):
    """Prévisions de stock avec IA"""
    FORECAST_TYPE_CHOICES = [
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='forecasts',
        verbose_name="Produit"
    )
    forecast_date = models.DateField(verbose_name="Date de prévision")
    forecast_type = models.CharField(
        max_length=20,
        choices=FORECAST_TYPE_CHOICES,
        verbose_name="Type de prévision"
    )
    
    # Prévisions
    predicted_demand = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Demande prévue",
        verbose_name="Demande prédite"
    )
    confidence_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Niveau de confiance en %",
        verbose_name="Niveau de confiance %"
    )
    
    # Stock recommandé
    recommended_stock_level = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Niveau de stock recommandé"
    )
    recommended_order_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité de commande recommandée"
    )
    
    # Facteurs d'influence
    seasonal_factor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Facteur saisonnier",
        verbose_name="Facteur saisonnier"
    )
    trend_factor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Facteur de tendance",
        verbose_name="Facteur de tendance"
    )
    
    # Alertes
    stockout_risk = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Faible'),
            ('medium', 'Moyen'),
            ('high', 'Élevé'),
            ('critical', 'Critique'),
        ],
        default='low',
        verbose_name="Risque de rupture"
    )
    
    # Métadonnées IA
    algorithm_used = models.CharField(
        max_length=100,
        blank=True,
        help_text="Algorithme utilisé pour la prévision",
        verbose_name="Algorithme utilisé"
    )
    training_data_points = models.IntegerField(
        default=0,
        help_text="Nombre de points de données utilisés",
        verbose_name="Points de données"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_forecasts'
        unique_together = [['product', 'forecast_date', 'forecast_type']]
        ordering = ['-forecast_date']
        verbose_name = "Prévision de stock"
        verbose_name_plural = "Prévisions de stock"
        indexes = [
            models.Index(fields=['product', '-forecast_date']),
            models.Index(fields=['stockout_risk', '-forecast_date']),
        ]
    
    def __str__(self):
        return f"Prévision {self.product.name} - {self.forecast_date}"


class ReorderRule(models.Model):
    """Règle de réapprovisionnement automatique"""
    REORDER_METHOD_CHOICES = [
        ('min_max', 'Min-Max'),
        ('fixed_quantity', 'Quantité fixe'),
        ('economic_order', 'Quantité économique (EOQ)'),
        ('forecast_based', 'Basé sur prévisions'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='reorder_rule',
        verbose_name="Produit"
    )
    
    # Règle
    reorder_method = models.CharField(
        max_length=20,
        choices=REORDER_METHOD_CHOICES,
        default='min_max',
        verbose_name="Méthode de réapprovisionnement"
    )
    reorder_point = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Point de commande (seuil minimum)",
        verbose_name="Point de commande"
    )
    reorder_quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantité à commander",
        verbose_name="Quantité de commande"
    )
    max_stock_level = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Niveau de stock maximum"
    )
    
    # Paramètres avancés
    lead_time_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(0)],
        help_text="Délai d'approvisionnement en jours",
        verbose_name="Délai d'approvisionnement (jours)"
    )
    safety_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Stock de sécurité",
        verbose_name="Stock de sécurité"
    )
    
    # Fournisseur préféré
    preferred_supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reorder_rules',
        verbose_name="Fournisseur préféré"
    )
    
    # Automatisation
    is_active = models.BooleanField(
        default=True,
        verbose_name="Règle active"
    )
    auto_create_order = models.BooleanField(
        default=False,
        help_text="Créer automatiquement les commandes",
        verbose_name="Création automatique"
    )
    
    # Dernière commande auto
    last_auto_order_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dernière commande auto"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_reorder_rules'
        verbose_name = "Règle de réapprovisionnement"
        verbose_name_plural = "Règles de réapprovisionnement"
        indexes = [
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Règle {self.product.name} - Point: {self.reorder_point}"
    
    def should_reorder(self, current_stock):
        """Vérifie si une commande doit être déclenchée"""
        return current_stock <= self.reorder_point



class StockAlert(models.Model):
    """Alertes de stock"""
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Stock faible'),
        ('out_of_stock', 'Rupture de stock'),
        ('expiring_soon', 'Expiration proche'),
        ('expired', 'Expiré'),
        ('overstock', 'Surstock'),
        ('slow_moving', 'Rotation lente'),
        ('reorder_needed', 'Réapprovisionnement nécessaire'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Élevée'),
        ('critical', 'Critique'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Prise en compte'),
        ('resolved', 'Résolue'),
        ('dismissed', 'Ignorée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='stock_alerts',
        verbose_name="Pharmacie"
    )
    alert_type = models.CharField(
        max_length=20,
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
        default='active',
        verbose_name="Statut"
    )
    
    # Entité concernée
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='stock_alerts',
        verbose_name="Produit"
    )
    batch = models.ForeignKey(
        'Batch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name="Lot"
    )
    
    # Message
    message = models.TextField(verbose_name="Message")
    
    # Données contextuelles
    current_stock = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Stock actuel"
    )
    threshold_value = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Valeur de seuil"
    )
    
    # Traçabilité
    acknowledged_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_alerts_acknowledged',
        verbose_name="Pris en compte par"
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Pris en compte le"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Résolue le"
    )
    
    class Meta:
        db_table = 'stock_alerts'
        ordering = ['-created_at']
        verbose_name = "Alerte de stock"
        verbose_name_plural = "Alertes de stock"
        indexes = [
            models.Index(fields=['pharmacie', 'status', '-created_at']),
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['severity', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.product.name}"

