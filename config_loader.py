import json
import os

def load_config(config_file='managex_signer.config'):
    """Load configuration from the config file or generate a new one with defaults."""
    
    # Default config values
    default_config = {
        "FLASK_HOST": "0.0.0.0",
        "FLASK_PORT": 5020
    }
    
    # Check if the config file exists
    if not os.path.exists(config_file):
        try:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            raise
        return default_config  # Return default config after creating the file

    # If config file exists, attempt to load it
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise
