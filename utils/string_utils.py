import unicodedata
import re

def normalize_string(s):
    """
    Normaliza uma string: remove acentos, converte para minúsculas, padroniza espaços.
    
    Args:
        s (str): String a ser normalizada
        
    Returns:
        str: String normalizada
    """
    if not s:
        return ""
        
    # Remove acentos
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')
    
    # Converte para minúsculas e padroniza espaços
    return " ".join(s.lower().strip().split())
    
def truncate_string(s, max_length=100, suffix="..."):
    """
    Trunca uma string para o tamanho máximo especificado.
    
    Args:
        s (str): String a ser truncada
        max_length (int): Tamanho máximo da string
        suffix (str): Sufixo a ser adicionado à string truncada
        
    Returns:
        str: String truncada
    """
    if not s:
        return ""
        
    if len(s) <= max_length:
        return s
        
    return s[:max_length-len(suffix)] + suffix