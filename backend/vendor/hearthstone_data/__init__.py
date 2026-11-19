"""Sustituto mínimo del paquete hearthstone_data.

Apunta a los datos de cartas de la build 23966 (parche 11.0, abril de 2018),
que es la versión que queremos reproducir.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.join(_HERE, "..", "..", "data", "CardDefs_23966.xml")


def get_carddefs_path():
    return os.environ.get("HS_CARDDEFS", os.path.normpath(_DEFAULT))
