import decimal


def quantize_decimal(value, precision='0.01'):
    return value.quantize(decimal.Decimal(precision))
