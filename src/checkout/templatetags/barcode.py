import io
import barcode
from base64 import b64encode
from django import template

register = template.Library()


@register.filter
def generate_barcode(code):
    output = io.BytesIO()
    ITF = barcode.get_barcode_class('itf')
    itf = ITF(code)
    itf.write(output, options={'module_width': 0.16})
    svg = output.getvalue()

    return 'data:image/svg+xml;charset=utf-8;base64,' + b64encode(svg).decode('utf-8')
