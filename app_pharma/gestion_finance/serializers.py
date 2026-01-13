

"""
Serializers Django REST Framework pour la gestion financière
API complète avec champs calculés et statistiques
"""
from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from .models import (
    Currency, TaxRate, Invoice, InvoiceItem, CreditNote, Payment,
    CustomerCredit, CreditPayment, ExpenseCategory, Expense,
    FinancialForecast, TaxReport
)


# ============================================================================
# SERIALIZERS DEVISES ET TAXES
# ============================================================================

class CurrencySerializer(serializers.ModelSerializer):
    """Serializer pour les devises"""
    
    class Meta:
        model = Currency
        fields = '__all__'
        read_only_fields = ['updated_at']


class TaxRateSerializer(serializers.ModelSerializer):
    """Serializer pour les taux de taxe"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    is_currently_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = TaxRate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_currently_valid(self, obj):
        return obj.is_valid_for_date()


# ============================================================================
# SERIALIZERS FACTURES
# ============================================================================

class InvoiceItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes de facture"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    tax_rate_name = serializers.CharField(source='tax_rate.name', read_only=True)
    tax_rate_percentage = serializers.DecimalField(
        source='tax_rate.rate',
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = InvoiceItem
        fields = '__all__'
        read_only_fields = ['line_subtotal', 'tax_amount', 'line_total', 'created_at']


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de factures"""
    customer_display_name = serializers.SerializerMethodField()
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_type', 'customer_display_name',
            'issue_date', 'due_date', 'status', 'currency_code',
            'total_amount', 'paid_amount', 'balance_due',
            'is_overdue', 'items_count'
        ]
        read_only_fields = ['invoice_number']
    
    def get_customer_display_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name or 'Client anonyme'
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_items_count(self, obj):
        return obj.items.count()


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer complet pour les factures"""
    customer_name_display = serializers.SerializerMethodField()
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    items = InvoiceItemSerializer(many=True, read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = [
            'invoice_number', 'subtotal', 'tax_amount', 'total_amount',
            'balance_due', 'verification_hash', 'qr_code',
            'total_amount_base', 'created_at', 'updated_at'
        ]
    
    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name or 'Client anonyme'
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
        return None


# ============================================================================
# SERIALIZERS AVOIRS
# ============================================================================

class CreditNoteSerializer(serializers.ModelSerializer):
    """Serializer pour les avoirs"""
    original_invoice_number = serializers.CharField(source='original_invoice.invoice_number', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = CreditNote
        fields = '__all__'
        read_only_fields = ['credit_note_number', 'created_at']


# ============================================================================
# SERIALIZERS PAIEMENTS
# ============================================================================

class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de paiements"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_number', 'invoice_number', 'amount',
            'currency_code', 'payment_method', 'payment_date',
            'status', 'processed_by_name'
        ]
        read_only_fields = ['payment_number']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer complet pour les paiements"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    invoice_customer = serializers.SerializerMethodField()
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_number', 'created_at']
    
    def get_invoice_customer(self, obj):
        invoice = obj.invoice
        if invoice.customer:
            return invoice.customer.get_full_name()
        return invoice.customer_name or 'Client anonyme'


# ============================================================================
# SERIALIZERS CRÉDITS CLIENTS
# ============================================================================

class CreditPaymentSerializer(serializers.ModelSerializer):
    """Serializer pour les paiements de crédit"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = CreditPayment
        fields = '__all__'
        read_only_fields = ['created_at']


class CustomerCreditSerializer(serializers.ModelSerializer):
    """Serializer pour les crédits clients"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()
    credit_payments = CreditPaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomerCredit
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_days_overdue(self, obj):
        if obj.is_overdue():
            return (timezone.now().date() - obj.due_date).days
        return 0


# ============================================================================
# SERIALIZERS DÉPENSES
# ============================================================================

class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Serializer pour les catégories de dépenses"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    expenses_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpenseCategory
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_expenses_count(self, obj):
        return obj.expenses.filter(status__in=['approved', 'paid']).count()
    
    def get_total_amount(self, obj):
        from django.db.models import Sum
        return obj.expenses.filter(
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')


class ExpenseListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de dépenses"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_number', 'category_name', 'expense_type',
            'description', 'amount', 'currency_code', 'expense_date',
            'status', 'payee', 'created_by_name'
        ]
        read_only_fields = ['expense_number']


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer complet pour les dépenses"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = [
            'expense_number', 'approved_at', 'created_at', 'updated_at'
        ]


# ============================================================================
# SERIALIZERS PRÉVISIONS
# ============================================================================

class FinancialForecastSerializer(serializers.ModelSerializer):
    """Serializer pour les prévisions financières"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    accuracy_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialForecast
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_accuracy_percentage(self, obj):
        """Calcule le pourcentage de précision de la prévision"""
        if obj.actual_amount is not None and obj.predicted_amount > 0:
            variance_percentage = abs(
                (obj.actual_amount - obj.predicted_amount) / obj.predicted_amount * 100
            )
            accuracy = 100 - min(variance_percentage, 100)
            return round(float(accuracy), 2)
        return None


# ============================================================================
# SERIALIZERS RAPPORTS FISCAUX
# ============================================================================

class TaxReportSerializer(serializers.ModelSerializer):
    """Serializer pour les rapports fiscaux"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    period_duration_days = serializers.SerializerMethodField()
    
    class Meta:
        model = TaxReport
        fields = '__all__'
        read_only_fields = ['report_number', 'created_at', 'updated_at']
    
    def get_period_duration_days(self, obj):
        return (obj.period_end - obj.period_start).days + 1


# ============================================================================
# SERIALIZERS STATISTIQUES
# ============================================================================

class FinancialSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé financier"""
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Factures
    total_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    unpaid_invoices = serializers.IntegerField()
    overdue_invoices = serializers.IntegerField()
    
    # Montants factures
    total_invoiced = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_unpaid = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Crédits clients
    total_credits = serializers.IntegerField()
    active_credits = serializers.IntegerField()
    overdue_credits = serializers.IntegerField()
    total_credit_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class RevenueByPeriodSerializer(serializers.Serializer):
    """Serializer pour les revenus par période"""
    period = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    invoice_count = serializers.IntegerField()


class ExpensesByCategorySerializer(serializers.Serializer):
    """Serializer pour les dépenses par catégorie"""
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense_count = serializers.IntegerField()
    percentage_of_total = serializers.DecimalField(max_digits=5, decimal_places=2)


class PaymentMethodStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques par méthode de paiement"""
    payment_method = serializers.CharField()
    transaction_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    percentage_of_total = serializers.DecimalField(max_digits=5, decimal_places=2)


class CustomerCreditSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé des crédits clients"""
    customer_id = serializers.UUIDField()
    customer_name = serializers.CharField()
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance_due = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_credits_count = serializers.IntegerField()
    overdue_credits_count = serializers.IntegerField()


class CashFlowSerializer(serializers.Serializer):
    """Serializer pour le flux de trésorerie"""
    period = serializers.CharField()
    cash_in = serializers.DecimalField(max_digits=15, decimal_places=2)
    cash_out = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_cash_flow = serializers.DecimalField(max_digits=15, decimal_places=2)
    cumulative_cash_flow = serializers.DecimalField(max_digits=15, decimal_places=2)


class TaxSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé fiscal"""
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_tax_collected = serializers.DecimalField(max_digits=15, decimal_places=2)
    tax_rate_average = serializers.DecimalField(max_digits=5, decimal_places=2)
    number_of_invoices = serializers.IntegerField()


# ============================================================================
# SERIALIZERS POUR ACTIONS BULK
# ============================================================================

class BulkInvoiceItemSerializer(serializers.Serializer):
    """Serializer pour création en masse de lignes de facture"""
    product_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'))
    discount_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        min_value=Decimal('0.00'),
        max_value=Decimal('100.00'),
        required=False,
        default=Decimal('0.00')
    )
    tax_rate_id = serializers.UUIDField()


class BulkPaymentSerializer(serializers.Serializer):
    """Serializer pour enregistrement de paiements multiples"""
    invoice_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHOD_CHOICES)
    payment_date = serializers.DateTimeField(required=False, default=timezone.now)
    notes = serializers.CharField(required=False, allow_blank=True)


class BulkExpenseSerializer(serializers.Serializer):
    """Serializer pour création en masse de dépenses"""
    category_id = serializers.UUIDField()
    expense_type = serializers.ChoiceField(choices=Expense.EXPENSE_TYPE_CHOICES)
    description = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    expense_date = serializers.DateField(required=False, default=timezone.now().date)
    payee = serializers.CharField(max_length=255)
    payment_method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        required=False,
        allow_blank=True
    )


# ============================================================================
# SERIALIZERS POUR RAPPORTS
# ============================================================================

class InvoiceReportSerializer(serializers.Serializer):
    """Serializer pour le rapport de factures"""
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_invoices = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    unpaid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    by_status = serializers.DictField()
    by_type = serializers.DictField()


class ExpenseReportSerializer(serializers.Serializer):
    """Serializer pour le rapport de dépenses"""
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_expenses = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    by_category = serializers.ListField()
    by_type = serializers.DictField()
    by_status = serializers.DictField()


class ProfitLossSerializer(serializers.Serializer):
    """Serializer pour le compte de résultat"""
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    
    # Revenus
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    revenue_breakdown = serializers.DictField()
    
    # Dépenses
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense_breakdown = serializers.DictField()
    
    # Résultat
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)