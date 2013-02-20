from tower import ugettext as _, ugettext_lazy as _lazy


PENDING = 'PENDING'
COMPLETED = 'OK'
FAILED = 'FAILED'
REFUND_STATUSES = {
    PENDING: _('Pending'),
    COMPLETED: _('Completed'),
    FAILED: _('Failed'),
}

PROVIDER_PAYPAL = 0
PROVIDER_BANGO = 1

PROVIDERS = {
    PROVIDER_PAYPAL: _lazy('PayPal'),
    PROVIDER_BANGO: _lazy('Bango'),
}
