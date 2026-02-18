"""
Configuration Manager for ASECNA Stock Management
Handles reading and writing admin configurations from the database.
"""

from typing import Any, Optional, Dict
from sqlalchemy.orm import Session
from data.database import SessionLocal
from data.models import AdminConfig
import logging
import json

logger = logging.getLogger(__name__)

class ConfigurationManager:
    """
    Manages application-wide configurations stored in the database.
    """
    
    _defaults = {
        "stability_duration_minutes": "60",
        "confidence_threshold": "0.60",
        "alert_delay_hours": "3",
        "asecna_countries": '["Sénégal", "Côte d\'Ivoire", "Mali", "Burkina Faso", "Gabon", "Cameroun", "Tchad", "Niger", "Mauritanie", "Guinée", "Guinée-Bissau", "Guinée Équatoriale", "Togo", "Bénin", "République Centrafricaine", "Congo", "Madagascar", "Comores", "France"]'
    }

    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._db_owned = False
        
    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
            self._db_owned = True
        return self._db
        
    def __del__(self):
        if self._db_owned and self._db:
            self._db.close()

    def get_config(self, key: str) -> str:
        """
        Get a configuration value by key.
        """
        config = self.db.query(AdminConfig).filter(AdminConfig.config_key == key).first()
        if config:
            return config.config_value
        return self._defaults.get(key, "")

    def set_config(self, key: str, value: Any, admin_id: Optional[int] = None) -> bool:
        """
        Set a configuration value.
        """
        try:
            # Convert value to string for storage
            if not isinstance(value, str):
                value = str(value)
                
            config = self.db.query(AdminConfig).filter(AdminConfig.config_key == key).first()
            if config:
                config.config_value = value
                config.updated_by = admin_id
            else:
                config = AdminConfig(
                    config_key=key,
                    config_value=value,
                    updated_by=admin_id
                )
                self.db.add(config)
            
            self.db.commit()
            logger.info(f"Configuration updated: {key} = {value}")
            
            # If it's a core detection setting, update the temporal engine
            if key in ["stability_duration_minutes", "confidence_threshold", "alert_delay_hours"]:
                self._update_temporal_engine()
                
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to set configuration {key}: {e}")
            return False

    def get_all_configs(self) -> Dict[str, str]:
        """
        Get all configurations as a dictionary.
        """
        configs = {**self._defaults}
        db_configs = self.db.query(AdminConfig).all()
        for c in db_configs:
            configs[c.config_key] = c.config_value
        return configs

    def _update_temporal_engine(self):
        """
        Update the singleton TemporalDetectionEngine with new settings.
        """
        try:
            from ai.temporal_detection import get_temporal_engine
            engine = get_temporal_engine()
            
            configs = self.get_all_configs()
            
            if "stability_duration_minutes" in configs:
                engine.stability_duration_minutes = int(configs["stability_duration_minutes"])
            if "confidence_threshold" in configs:
                engine.confidence_threshold = float(configs["confidence_threshold"])
            if "alert_delay_hours" in configs:
                engine.alert_delay_hours = int(configs["alert_delay_hours"])
                
            logger.info("TemporalDetectionEngine updated with new database configurations")
        except Exception as e:
            logger.error(f"Failed to update temporal engine from config: {e}")

# Singleton instance
_config_manager = None

def get_config_manager(db: Optional[Session] = None) -> ConfigurationManager:
    """Get or create the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(db)
    return _config_manager
