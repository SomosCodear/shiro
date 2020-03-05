from django.contrib import admin
from . import models


class ItemOptionInline(admin.TabularInline):
    model = models.ItemOption
    extra = 0


class ItemAdmin(admin.ModelAdmin):
    inlines = [
        ItemOptionInline,
    ]


class DiscountCodeRestrictionInline(admin.TabularInline):
    model = models.DiscountCodeRestriction
    extra = 0


class DiscountCodeAdmin(admin.ModelAdmin):
    inlines = [
        DiscountCodeRestrictionInline,
    ]


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0


class InvoiceInline(admin.StackedInline):
    model = models.Invoice
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ('order_total',)
    inlines = [
        OrderItemInline,
        InvoiceInline,
    ]

    def order_total(self, order):
        return order.calculate_total()

    order_total.short_description = 'Total de la Orden'


class CancellationItemInline(admin.TabularInline):
    model = models.CancellationItem
    extra = 0


class CreditNoteInline(admin.StackedInline):
    model = models.CreditNote
    extra = 0


class CancellationAdmin(admin.ModelAdmin):
    inlines = [
        CancellationItemInline,
        CreditNoteInline,
    ]


admin.site.register(models.Item, ItemAdmin)
admin.site.register(models.DiscountCode, DiscountCodeAdmin)
admin.site.register(models.Customer)
admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.Cancellation, CancellationAdmin)
