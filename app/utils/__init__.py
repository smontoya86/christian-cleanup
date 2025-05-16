def format_ms_filter(ms):
    if ms is None:
        return "N/A"
    try:
        ms = int(ms)
    except (ValueError, TypeError):
        return "N/A" # Or some other placeholder for invalid input
    
    seconds = int((ms / 1000) % 60)
    minutes = int((ms / (1000 * 60)) % 60)
    # hours = int((ms / (1000 * 60 * 60)) % 24) # Uncomment if you need hours
    
    return f"{minutes:02d}:{seconds:02d}"
