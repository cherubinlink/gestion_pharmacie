"""
Modèles E-commerce Pharmacie
Application 9 - Boutique en ligne pour clients
Permet aux clients de commander en ligne les produits mis en vente par la pharmacie
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator, EmailValidator
from django.utils import timezone
from decimal import Decimal

# Create your models here.


# ============================================================================
# MODÈLES CONFIGURATION E-COMMERCE
# ============================================================================

class OnlineStore(models.Model):
    """Configuration de la boutique en ligne de la pharmacie"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.OneToOneField(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='online_store',
        verbose_name="Pharmacie"
    )
    
    # Configuration générale
    store_name = models.CharField(
        max_length=255,
        verbose_name="Nom de la boutique"
    )
    store_description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    store_logo = models.ImageField(
        upload_to='store/logos/',
        null=True,
        blank=True,
        verbose_name="Logo"
    )
    store_banner = models.ImageField(
        upload_to='store/banners/',
        null=True,
        blank=True,
        verbose_name="Bannière"
    )
    
    # Paramètres de livraison
    delivery_enabled = models.BooleanField(
        default=True,
        verbose_name="Livraison activée"
    )
    pickup_enabled = models.BooleanField(
        default=True,
        verbose_name="Retrait en pharmacie activé"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais de livraison"
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Montant minimum pour livraison gratuite",
        verbose_name="Seuil livraison gratuite"
    )
    
    # Zones de livraison
    delivery_zones = models.TextField(
        blank=True,
        help_text="Zones de livraison (une par ligne)",
        verbose_name="Zones de livraison"
    )
    estimated_delivery_time = models.CharField(
        max_length=100,
        default="24-48h",
        verbose_name="Délai de livraison estimé"
    )
    
    # Paiement
    payment_on_delivery = models.BooleanField(
        default=True,
        verbose_name="Paiement à la livraison"
    )
    mobile_money_enabled = models.BooleanField(
        default=False,
        verbose_name="Mobile Money activé"
    )
    card_payment_enabled = models.BooleanField(
        default=False,
        verbose_name="Paiement par carte activé"
    )
    
    # Commande minimale
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant minimum de commande"
    )
    
    # Contact
    contact_email = models.EmailField(
        blank=True,
        validators=[EmailValidator()],
        verbose_name="Email de contact"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone de contact"
    )
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro WhatsApp"
    )
    
    # Horaires
    opening_hours = models.TextField(
        blank=True,
        help_text="Horaires d'ouverture",
        verbose_name="Horaires"
    )
    
    # SEO
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Meta titre"
    )
    meta_description = models.TextField(
        blank=True,
        verbose_name="Meta description"
    )
    meta_keywords = models.TextField(
        blank=True,
        verbose_name="Mots-clés"
    )
    
    # Statut
    is_active = models.BooleanField(
        default=True,
        verbose_name="Boutique active"
    )
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Mode maintenance"
    )
    maintenance_message = models.TextField(
        blank=True,
        verbose_name="Message de maintenance"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ecommerce_online_stores'
        verbose_name = "Boutique en ligne"
        verbose_name_plural = "Boutiques en ligne"
    
    def __str__(self):
        return f"Boutique - {self.store_name}"



# ============================================================================
# MODÈLES PRODUITS EN LIGNE
# ============================================================================

class OnlineProduct(models.Model):
    """Produit mis en vente en ligne"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        OnlineStore,
        on_delete=models.CASCADE,
        related_name='online_products',
        verbose_name="Boutique"
    )
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.CASCADE,
        related_name='online_listings',
        verbose_name="Produit"
    )
    
    # Prix en ligne (peut être différent du prix en pharmacie)
    online_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix en ligne"
    )
    
    # Promotion
    is_on_sale = models.BooleanField(
        default=False,
        verbose_name="En promotion"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix promotionnel"
    )
    sale_start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Début promotion"
    )
    sale_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fin promotion"
    )
    
    # Stock en ligne
    online_stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Stock disponible pour la vente en ligne",
        verbose_name="Stock en ligne"
    )
    max_quantity_per_order = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name="Quantité max par commande"
    )
    
    # Visibilité
    is_visible = models.BooleanField(
        default=True,
        verbose_name="Visible sur le site"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Produit vedette affiché en premier",
        verbose_name="Produit vedette"
    )
    is_new_arrival = models.BooleanField(
        default=False,
        verbose_name="Nouvelle arrivée"
    )
    
    # Images produit (pour e-commerce)
    primary_image = models.ImageField(
        upload_to='products/online/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Image principale"
    )
    
    # Description enrichie pour e-commerce
    online_description = models.TextField(
        blank=True,
        help_text="Description détaillée pour le site web",
        verbose_name="Description en ligne"
    )
    short_description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Description courte"
    )
    
    # Informations supplémentaires
    usage_instructions = models.TextField(
        blank=True,
        verbose_name="Mode d'emploi"
    )
    warnings = models.TextField(
        blank=True,
        verbose_name="Avertissements"
    )
    storage_conditions = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Conditions de conservation"
    )
    
    # Prescription requise
    requires_prescription = models.BooleanField(
        default=False,
        verbose_name="Ordonnance requise"
    )
    
    # Statistiques
    views_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de vues"
    )
    sales_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de ventes"
    )
    
    # SEO
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Meta titre"
    )
    meta_description = models.TextField(
        blank=True,
        verbose_name="Meta description"
    )
    
    # Dates
    available_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Disponible à partir de"
    )
    available_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Disponible jusqu'à"
    )
    
    display_order = models.IntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ecommerce_online_products'
        unique_together = [['store', 'product']]
        ordering = ['-is_featured', 'display_order', '-created_at']
        verbose_name = "Produit en ligne"
        verbose_name_plural = "Produits en ligne"
        indexes = [
            models.Index(fields=['store', 'is_visible']),
            models.Index(fields=['is_featured', 'is_visible']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - En ligne"
    
    def get_current_price(self):
        """Retourne le prix actuel (promotionnel si applicable)"""
        if self.is_on_sale and self.sale_price:
            now = timezone.now()
            if self.sale_start_date and self.sale_end_date:
                if self.sale_start_date <= now <= self.sale_end_date:
                    return self.sale_price
        return self.online_price
    
    def get_discount_percentage(self):
        """Calcule le pourcentage de réduction"""
        if self.is_on_sale and self.sale_price:
            discount = ((self.online_price - self.sale_price) / self.online_price) * 100
            return round(discount, 2)
        return 0


class ProductImage(models.Model):
    """Images supplémentaires pour un produit en ligne"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    online_product = models.ForeignKey(
        OnlineProduct,
        on_delete=models.CASCADE,
        related_name='additional_images',
        verbose_name="Produit en ligne"
    )
    
    image = models.ImageField(
        upload_to='products/online/gallery/%Y/%m/',
        verbose_name="Image"
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Texte alternatif"
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ecommerce_product_images'
        ordering = ['display_order', 'created_at']
        verbose_name = "Image produit"
        verbose_name_plural = "Images produits"
    
    def __str__(self):
        return f"Image - {self.online_product.product.name}"


class ProductReview(models.Model):
    """Avis clients sur les produits"""
    RATING_CHOICES = [
        (1, '⭐'),
        (2, '⭐⭐'),
        (3, '⭐⭐⭐'),
        (4, '⭐⭐⭐⭐'),
        (5, '⭐⭐⭐⭐⭐'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    online_product = models.ForeignKey(
        OnlineProduct,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Produit"
    )
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='product_reviews',
        verbose_name="Client"
    )
    
    # Évaluation
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Note"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Titre"
    )
    comment = models.TextField(
        verbose_name="Commentaire"
    )
    
    # Achat vérifié
    verified_purchase = models.BooleanField(
        default=False,
        verbose_name="Achat vérifié"
    )
    
    # Modération
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Approuvé"
    )
    moderated_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews_moderated',
        verbose_name="Modéré par"
    )
    moderation_notes = models.TextField(
        blank=True,
        verbose_name="Notes de modération"
    )
    
    # Utilité
    helpful_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de 'utile'"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ecommerce_product_reviews'
        unique_together = [['online_product', 'customer']]
        ordering = ['-created_at']
        verbose_name = "Avis produit"
        verbose_name_plural = "Avis produits"
        indexes = [
            models.Index(fields=['online_product', 'is_approved']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"Avis de {self.customer.get_full_name()} - {self.rating}⭐"



# ============================================================================
# MODÈLES PANIER
# ============================================================================

class Cart(models.Model):
    """Panier d'achat client"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        OnlineStore,
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name="Boutique"
    )
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name="Client"
    )
    
    # Session (pour paniers anonymes avant connexion)
    session_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Clé de session"
    )
    
    # Statut
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    abandoned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Abandonné le"
    )
    
    class Meta:
        db_table = 'ecommerce_carts'
        ordering = ['-updated_at']
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"
        indexes = [
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"Panier - {self.customer.get_full_name()}"
    
    def get_total_items(self):
        """Nombre total d'articles"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def get_subtotal(self):
        """Sous-total du panier"""
        return sum(item.get_line_total() for item in self.items.all())
    
    def get_total(self):
        """Total avec frais de livraison"""
        subtotal = self.get_subtotal()
        delivery_fee = Decimal('0.00')
        
        if self.store.delivery_enabled:
            if subtotal < self.store.free_delivery_threshold:
                delivery_fee = self.store.delivery_fee
        
        return subtotal + delivery_fee


class CartItem(models.Model):
    """Article dans le panier"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Panier"
    )
    online_product = models.ForeignKey(
        OnlineProduct,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name="Produit"
    )
    
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Quantité"
    )
    
    # Prix au moment de l'ajout au panier
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix unitaire"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ecommerce_cart_items'
        unique_together = [['cart', 'online_product']]
        ordering = ['created_at']
        verbose_name = "Article panier"
        verbose_name_plural = "Articles panier"
    
    def __str__(self):
        return f"{self.online_product.product.name} x{self.quantity}"
    
    def get_line_total(self):
        """Total de la ligne"""
        return self.unit_price * self.quantity


# ============================================================================
# MODÈLES COMMANDES EN LIGNE
# ============================================================================

class OnlineOrder(models.Model):
    """Commande en ligne"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('processing', 'En préparation'),
        ('ready', 'Prête'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Paiement à la livraison'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte bancaire'),
        ('transfer', 'Virement bancaire'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('failed', 'Échoué'),
        ('refunded', 'Remboursé'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('delivery', 'Livraison à domicile'),
        ('pickup', 'Retrait en pharmacie'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        OnlineStore,
        on_delete=models.PROTECT,
        related_name='online_orders',
        verbose_name="Boutique"
    )
    
    # Numéro de commande
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de commande"
    )
    
    # Client
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.PROTECT,
        related_name='online_orders',
        verbose_name="Client"
    )
    
    # Informations de contact
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Méthode de livraison
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        verbose_name="Méthode de livraison"
    )
    
    # Adresse de livraison
    delivery_address = models.TextField(
        blank=True,
        verbose_name="Adresse de livraison"
    )
    delivery_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ville"
    )
    delivery_zone = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Zone/Quartier"
    )
    delivery_instructions = models.TextField(
        blank=True,
        verbose_name="Instructions de livraison"
    )
    
    # Paiement
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name="Méthode de paiement"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="Statut paiement"
    )
    payment_reference = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Référence paiement"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Payé le"
    )
    
    # Montants
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Sous-total"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais de livraison"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant de réduction"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total"
    )
    
    # Code promo appliqué
    promo_code = models.ForeignKey(
        'PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_used',
        verbose_name="Code promo"
    )
    
    # Ordonnance (si requise)
    prescription_required = models.BooleanField(
        default=False,
        verbose_name="Ordonnance requise"
    )
    prescription_file = models.FileField(
        upload_to='prescriptions/online/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Fichier ordonnance"
    )
    prescription_verified = models.BooleanField(
        default=False,
        verbose_name="Ordonnance vérifiée"
    )
    
    # Notes
    customer_notes = models.TextField(
        blank=True,
        verbose_name="Notes du client"
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="Notes internes"
    )
    
    # Traçabilité
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confirmée le"
    )
    confirmed_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_confirmed',
        verbose_name="Confirmée par"
    )
    
    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expédiée le"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Livrée le"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Annulée le"
    )
    cancellation_reason = models.TextField(
        blank=True,
        verbose_name="Raison d'annulation"
    )
    
    # Lien avec la vente physique (après paiement)
    sale = models.OneToOneField(
        'gestion_vente.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='online_order',
        verbose_name="Vente"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ecommerce_online_orders'
        ordering = ['-created_at']
        verbose_name = "Commande en ligne"
        verbose_name_plural = "Commandes en ligne"
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"Commande {self.order_number}"



class OnlineOrderItem(models.Model):
    """Article dans une commande en ligne"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        OnlineOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Commande"
    )
    online_product = models.ForeignKey(
        OnlineProduct,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name="Produit"
    )
    
    # Informations produit au moment de la commande
    product_name = models.CharField(
        max_length=255,
        verbose_name="Nom du produit"
    )
    product_sku = models.CharField(
        max_length=100,
        verbose_name="SKU"
    )
    
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantité"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix unitaire"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Sous-total"
    )
    
    # Si le produit était en promotion
    was_on_sale = models.BooleanField(
        default=False,
        verbose_name="Était en promotion"
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix original"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ecommerce_online_order_items'
        ordering = ['created_at']
        verbose_name = "Article commande"
        verbose_name_plural = "Articles commandes"
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class OrderStatusHistory(models.Model):
    """Historique des changements de statut de commande"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        OnlineOrder,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="Commande"
    )
    
    status = models.CharField(
        max_length=20,
        choices=OnlineOrder.STATUS_CHOICES,
        verbose_name="Statut"
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Commentaire"
    )
    
    changed_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_status_changes',
        verbose_name="Modifié par"
    )
    
    customer_notified = models.BooleanField(
        default=False,
        verbose_name="Client notifié"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ecommerce_order_status_history'
        ordering = ['created_at']
        verbose_name = "Historique statut"
        verbose_name_plural = "Historiques statuts"
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


# ============================================================================
# MODÈLES PROMOTIONS ET CODES PROMO
# ============================================================================

class PromoCode(models.Model):
    """Code promotionnel"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
        ('free_delivery', 'Livraison gratuite'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        OnlineStore,
        on_delete=models.CASCADE,
        related_name='promo_codes',
        verbose_name="Boutique"
    )
    
    # Code
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Type de réduction
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="Type de réduction"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Pourcentage ou montant fixe",
        verbose_name="Valeur réduction"
    )
    
    # Conditions d'utilisation
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant minimum d'achat"
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Réduction maximale (pour les pourcentages)",
        verbose_name="Réduction max"
    )
    
    # Limites d'utilisation
    usage_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre max d'utilisations (null = illimité)",
        verbose_name="Limite d'utilisation"
    )
    usage_limit_per_customer = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Limite par client"
    )
    times_used = models.IntegerField(
        default=0,
        verbose_name="Fois utilisé"
    )
    
    # Dates de validité
    valid_from = models.DateTimeField(
        verbose_name="Valide à partir de"
    )
    valid_until = models.DateTimeField(
        verbose_name="Valide jusqu'à"
    )
    
    # Restrictions
    applicable_categories = models.ManyToManyField(
        'gestion_vente.ProductCategory',
        blank=True,
        related_name='promo_codes',
        verbose_name="Catégories applicables"
    )
    applicable_products = models.ManyToManyField(
        OnlineProduct,
        blank=True,
        related_name='promo_codes',
        verbose_name="Produits applicables"
    )
    
    # Statut
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='promo_codes_created',
        verbose_name="Créé par"
    )
    
    class Meta:
        db_table = 'ecommerce_promo_codes'
        ordering = ['-created_at']
        verbose_name = "Code promo"
        verbose_name_plural = "Codes promo"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Vérifie si le code est valide"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from > now or self.valid_until < now:
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True
    
    def calculate_discount(self, subtotal):
        """Calcule le montant de la réduction"""
        if self.discount_type == 'percentage':
            discount = (subtotal * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        elif self.discount_type == 'fixed':
            return min(self.discount_value, subtotal)
        return Decimal('0.00')


class PromoCodeUsage(models.Model):
    """Suivi d'utilisation des codes promo"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name="Code promo"
    )
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='promo_code_usages',
        verbose_name="Client"
    )
    order = models.ForeignKey(
        OnlineOrder,
        on_delete=models.CASCADE,
        related_name='promo_usage',
        verbose_name="Commande"
    )
    
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant réduction"
    )
    
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ecommerce_promo_code_usages'
        ordering = ['-used_at']
        verbose_name = "Utilisation code promo"
        verbose_name_plural = "Utilisations codes promo"
    
    def __str__(self):
        return f"{self.promo_code.code} - {self.customer.get_full_name()}"


# ============================================================================
# MODÈLES LISTE DE SOUHAITS
# ============================================================================

class Wishlist(models.Model):
    """Liste de souhaits client"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name="Client"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ecommerce_wishlists'
        verbose_name = "Liste de souhaits"
        verbose_name_plural = "Listes de souhaits"
    
    def __str__(self):
        return f"Liste de souhaits - {self.customer.get_full_name()}"
    
    def get_total_items(self):
        """Nombre d'articles"""
        return self.items.count()


class WishlistItem(models.Model):
    """Article dans la liste de souhaits"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Liste de souhaits"
    )
    online_product = models.ForeignKey(
        OnlineProduct,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name="Produit"
    )
    
    # Notification de baisse de prix
    notify_on_price_drop = models.BooleanField(
        default=False,
        verbose_name="Notifier si baisse de prix"
    )
    notify_on_availability = models.BooleanField(
        default=False,
        verbose_name="Notifier si disponible"
    )
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ecommerce_wishlist_items'
        unique_together = [['wishlist', 'online_product']]
        ordering = ['-added_at']
        verbose_name = "Article liste de souhaits"
        verbose_name_plural = "Articles listes de souhaits"
    
    def __str__(self):
        return f"{self.online_product.product.name}"


# ============================================================================
# MODÈLES NOTIFICATIONS E-COMMERCE
# ============================================================================

class CustomerNotification(models.Model):
    """Notifications pour les clients"""
    TYPE_CHOICES = [
        ('order_confirmed', 'Commande confirmée'),
        ('order_shipped', 'Commande expédiée'),
        ('order_delivered', 'Commande livrée'),
        ('order_cancelled', 'Commande annulée'),
        ('price_drop', 'Baisse de prix'),
        ('back_in_stock', 'Retour en stock'),
        ('promo_code', 'Code promo'),
        ('abandoned_cart', 'Panier abandonné'),
        ('newsletter', 'Newsletter'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='ecommerce_notifications',
        verbose_name="Client"
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name="Type"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Titre"
    )
    message = models.TextField(
        verbose_name="Message"
    )
    
    # Lien vers objet concerné
    order = models.ForeignKey(
        OnlineOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Commande"
    )
    online_product = models.ForeignKey(
        OnlineProduct,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Produit"
    )
    
    # Statut
    is_read = models.BooleanField(
        default=False,
        verbose_name="Lu"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Lu le"
    )
    
    # Envoi multi-canal
    sent_via_email = models.BooleanField(
        default=False,
        verbose_name="Envoyé par email"
    )
    sent_via_sms = models.BooleanField(
        default=False,
        verbose_name="Envoyé par SMS"
    )
    sent_via_push = models.BooleanField(
        default=False,
        verbose_name="Envoyé par push"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ecommerce_customer_notifications'
        ordering = ['-created_at']
        verbose_name = "Notification client"
        verbose_name_plural = "Notifications clients"
        indexes = [
            models.Index(fields=['customer', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.customer.get_full_name()}"

