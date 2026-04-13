"""
Custom DRF renderer that stringifies ``Decimal`` values at the encoder
level.

DRF's built-in ``JSONEncoder`` converts raw ``Decimal`` instances to
``float``. That's fine when Decimals only reach the encoder via a
serializer ``DecimalField`` (which already emits strings), but the
dashboard and report services return plain dicts containing raw
Decimals. Floating-point money representations are both inconsistent
with the rest of the API and unsafe for currency math, so we force
``Decimal`` -> ``str`` globally here.
"""
from decimal import Decimal

from rest_framework import renderers
from rest_framework.utils import encoders


class FoxdJSONEncoder(encoders.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


class FoxdJSONRenderer(renderers.JSONRenderer):
    encoder_class = FoxdJSONEncoder
