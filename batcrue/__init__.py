"""BatCrue – moteur de calcul de l'impact hydraulique d'un batardeau sur les crues.

Exemple ::

    from batcrue import EtudeBatardeau, defauts
    etude = EtudeBatardeau(defauts())
    s = etude.synthese()
    print(s["dZ_barrage"], s["verdict"])
"""
from .etude import EtudeBatardeau, ResultatDebit
from .ouvrage import FORMES, METHODES
from .parametres import DEFAUTS, completer, defauts, depuis_json, valider, vers_json

__version__ = "1.0.0"

__all__ = ["EtudeBatardeau", "ResultatDebit", "FORMES", "METHODES", "DEFAUTS", "completer",
           "defauts", "depuis_json", "valider", "vers_json", "__version__"]
