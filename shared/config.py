import os
from pathlib import Path
def get_data_dir() -> Path:
    '''
    Resoves the directory where DevDesk stores persistent data (like SQLite databases)
    following the LINUX XDG Base Directory Specification.
    '''

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        data_dir= Path(xdg_data_home) / "devdesk"
    else:
        #default POSIX standard
        data_dir = Path.home() / ".local" / "share" / "devdesk"
    
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


def get_config_dir() -> Path:
    '''
    Resolves the directory for configuration files (following $XDG_CONFIG_HOME).
    Defaults to ~/.config/dev

    '''
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")

    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "devdesk"
    else:
        config_dir = Path.home() / ".config" / "devdesk"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_db_path(service_name: str = "snippets") -> Path:
    """
    Constructs the absolute path to a SQLite database file for a given service. 
    
    """

    return get_data_dir() / f"{service_name}.db"