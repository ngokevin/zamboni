from tower import ugettext_lazy as _lazy


PENDING = 'PENDING'
COMPLETED = 'OK'
FAILED = 'FAILED'

PROVIDER_PAYPAL = 0
PROVIDER_BANGO = 1

PROVIDERS = {
    PROVIDER_PAYPAL: _lazy('PayPal'),
    PROVIDER_BANGO: _lazy('Bango'),
}
