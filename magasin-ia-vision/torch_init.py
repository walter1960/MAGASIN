"""
Script d'initialisation pour configurer PyTorch avant le chargement des modèles.
"""
import torch

# Sauvegarder la fonction originale
_original_load = torch.load

# Créer une version patchée qui force weights_only=False
def patched_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_load(*args, **kwargs)

# Remplacer torch.load par la version patchée
torch.load = patched_load

