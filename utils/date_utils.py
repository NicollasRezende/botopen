import re
import datetime
from typing import Optional, Tuple, Union

def validate_date(date_str: Optional[str]) -> bool:
    """
    Valida se a string está no formato DD/MM/YYYY e representa uma data válida.
    
    Args:
        date_str (Optional[str]): String de data a ser validada ou None/vazio
        
    Returns:
        bool: True se a data for válida ou None/vazio, False caso contrário
    """
    if not date_str:  # Se não for informada, é opcional
        return True
    
    # Verifica formato via regex
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        return False
    
    try:
        # Valida se é uma data existente
        day, month, year = map(int, date_str.split('/'))
        datetime.datetime(year, month, day)
        
        # Opcional: verificar se é uma data futura ou dentro de um intervalo aceitável
        # today = datetime.datetime.now().date()
        # date = datetime.date(year, month, day)
        # if date < today:
        #     return False
            
        return True
    except (ValueError, TypeError):
        return False

def convert_date_format(date_str: Optional[str]) -> str:
    """
    Converte data do formato DD/MM/YYYY para YYYY-MM-DD (formato da API).
    
    Args:
        date_str (Optional[str]): String de data no formato DD/MM/YYYY
        
    Returns:
        str: Data no formato YYYY-MM-DD ou string vazia se inválida
    """
    if not date_str:
        return ""
    try:
        # Valida o formato primeiro
        if not validate_date(date_str):
            return ""
            
        # Converte de DD/MM/YYYY para YYYY-MM-DD
        day, month, year = date_str.split('/')
        return f"{year}-{month}-{day}"
    except (ValueError, TypeError):
        return ""

def compare_dates(start_date: str, end_date: str) -> Tuple[bool, str]:
    """
    Compara duas datas no formato DD/MM/YYYY.
    
    Args:
        start_date (str): Data inicial no formato DD/MM/YYYY
        end_date (str): Data final no formato DD/MM/YYYY
        
    Returns:
        Tuple[bool, str]: (True, "") se end_date >= start_date, 
                          (False, mensagem de erro) caso contrário
    """
    if not start_date or not end_date:
        return True, ""
        
    try:
        start_day, start_month, start_year = map(int, start_date.split('/'))
        end_day, end_month, end_year = map(int, end_date.split('/'))
        
        start = datetime.datetime(start_year, start_month, start_day)
        end = datetime.datetime(end_year, end_month, end_day)
        
        if end < start:
            return False, "A data de término não pode ser anterior à data de início."
            
        return True, ""
    except (ValueError, TypeError):
        return False, "Formato de data inválido. Use DD/MM/AAAA."

def format_duration(hours: Union[float, str]) -> Optional[str]:
    """
    Formata um número de horas para o formato ISO8601 de duração.
    
    Args:
        hours (Union[float, str]): Horas em formato decimal (ex: 2.5) ou string
        
    Returns:
        Optional[str]: Duração no formato ISO8601 (ex: PT2H30M) ou None se inválido
    """
    try:
        if isinstance(hours, str):
            if not hours:
                return None
                
            # Verifica se é um número decimal válido
            if not hours.replace('.', '', 1).isdigit():
                return None
                
            hours = float(hours)
            
        horas_inteiras = int(hours)
        minutos = int((hours - horas_inteiras) * 60)
        
        # Formata no padrão ISO8601
        if minutos > 0:
            return f"PT{horas_inteiras}H{minutos}M"
        else:
            return f"PT{horas_inteiras}H"
    except (ValueError, TypeError):
        return None