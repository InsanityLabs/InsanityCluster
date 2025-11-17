"""
Configuration Manager for loading, saving, and managing system configurations.

This module provides:
- Configuration storage and retrieval from PostgreSQL
- Configuration versioning and history tracking
- Configuration import/export (JSON/YAML)
- Active configuration management
"""
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import yaml

from insanity_cluster.common.configuration import (
    ModeConfiguration,
    OperatingMode,
    get_default_config,
)
from insanity_cluster.table.models import Configuration, ConfigurationHistory, User


class ConfigurationManager:
    """
    Manager for configuration storage and retrieval.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize configuration manager.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def create_configuration(
        self,
        config: ModeConfiguration,
        user_id: Optional[uuid.UUID] = None,
        set_active: bool = False,
    ) -> uuid.UUID:
        """
        Create a new configuration.
        
        Args:
            config: ModeConfiguration to save
            user_id: Optional user ID (None for system-wide config)
            set_active: Whether to set this as the active configuration
            
        Returns:
            UUID of created configuration
        """
        # If setting as active, deactivate other configs for this user
        if set_active:
            self._deactivate_user_configs(user_id)
        
        # Create configuration record
        db_config = Configuration(
            id=uuid.uuid4(),
            user_id=user_id,
            name=config.name or f"{config.mode.value}_config",
            description=config.description,
            config_data=config.to_dict(),
            version=config.version,
            is_active=set_active,
            is_default=False,
        )
        
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        
        # Create initial history entry
        self._create_history_entry(
            config_id=db_config.id,
            config_data=config.to_dict(),
            version=config.version,
            changed_by=user_id,
            change_description="Initial configuration creation",
        )
        
        return db_config.id
    
    def get_configuration(self, config_id: uuid.UUID) -> Optional[ModeConfiguration]:
        """
        Get configuration by ID.
        
        Args:
            config_id: Configuration UUID
            
        Returns:
            ModeConfiguration or None if not found
        """
        db_config = self.db.query(Configuration).filter(
            Configuration.id == config_id
        ).first()
        
        if not db_config:
            return None
        
        return ModeConfiguration.from_dict(db_config.config_data)
    
    def get_active_configuration(
        self,
        user_id: Optional[uuid.UUID] = None
    ) -> Optional[ModeConfiguration]:
        """
        Get active configuration for a user or system.
        
        Args:
            user_id: Optional user ID (None for system-wide config)
            
        Returns:
            Active ModeConfiguration or None if not found
        """
        query = self.db.query(Configuration).filter(
            Configuration.is_active == True
        )
        
        if user_id:
            query = query.filter(Configuration.user_id == user_id)
        else:
            query = query.filter(Configuration.user_id.is_(None))
        
        db_config = query.first()
        
        if not db_config:
            return None
        
        return ModeConfiguration.from_dict(db_config.config_data)
    
    def list_configurations(
        self,
        user_id: Optional[uuid.UUID] = None,
        include_system: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        List all configurations for a user.
        
        Args:
            user_id: Optional user ID (None for system-wide configs only)
            include_system: Whether to include system-wide configs
            
        Returns:
            List of configuration metadata dictionaries
        """
        query = self.db.query(Configuration)
        
        if user_id:
            if include_system:
                query = query.filter(
                    (Configuration.user_id == user_id) |
                    (Configuration.user_id.is_(None))
                )
            else:
                query = query.filter(Configuration.user_id == user_id)
        else:
            query = query.filter(Configuration.user_id.is_(None))
        
        configs = query.order_by(desc(Configuration.updated_at)).all()
        
        return [
            {
                "id": str(config.id),
                "name": config.name,
                "description": config.description,
                "mode": config.config_data.get("mode"),
                "version": config.version,
                "is_active": config.is_active,
                "is_default": config.is_default,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat(),
            }
            for config in configs
        ]
    
    def update_configuration(
        self,
        config_id: uuid.UUID,
        config: ModeConfiguration,
        user_id: Optional[uuid.UUID] = None,
        change_description: Optional[str] = None,
    ) -> bool:
        """
        Update an existing configuration.
        
        Args:
            config_id: Configuration UUID to update
            config: New ModeConfiguration
            user_id: User making the change
            change_description: Description of changes
            
        Returns:
            True if updated successfully, False otherwise
        """
        db_config = self.db.query(Configuration).filter(
            Configuration.id == config_id
        ).first()
        
        if not db_config:
            return False
        
        # Increment version
        new_version = db_config.version + 1
        config.version = new_version
        config.updated_at = datetime.utcnow()
        
        # Update configuration
        db_config.config_data = config.to_dict()
        db_config.version = new_version
        db_config.name = config.name or db_config.name
        db_config.description = config.description or db_config.description
        db_config.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Create history entry
        self._create_history_entry(
            config_id=config_id,
            config_data=config.to_dict(),
            version=new_version,
            changed_by=user_id,
            change_description=change_description or "Configuration updated",
        )
        
        return True
    
    def delete_configuration(self, config_id: uuid.UUID) -> bool:
        """
        Delete a configuration.
        
        Args:
            config_id: Configuration UUID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        db_config = self.db.query(Configuration).filter(
            Configuration.id == config_id
        ).first()
        
        if not db_config:
            return False
        
        self.db.delete(db_config)
        self.db.commit()
        
        return True
    
    def set_active_configuration(
        self,
        config_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Set a configuration as active.
        
        Args:
            config_id: Configuration UUID to activate
            user_id: User ID (None for system-wide)
            
        Returns:
            True if set successfully, False otherwise
        """
        db_config = self.db.query(Configuration).filter(
            Configuration.id == config_id
        ).first()
        
        if not db_config:
            return False
        
        # Deactivate other configs
        self._deactivate_user_configs(user_id)
        
        # Activate this config
        db_config.is_active = True
        self.db.commit()
        
        return True
    
    def get_configuration_history(
        self,
        config_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get configuration history.
        
        Args:
            config_id: Configuration UUID
            limit: Maximum number of history entries to return
            
        Returns:
            List of history entries
        """
        history = self.db.query(ConfigurationHistory).filter(
            ConfigurationHistory.config_id == config_id
        ).order_by(desc(ConfigurationHistory.created_at)).limit(limit).all()
        
        return [
            {
                "id": str(entry.id),
                "version": entry.version,
                "changed_by": str(entry.changed_by) if entry.changed_by else None,
                "change_description": entry.change_description,
                "created_at": entry.created_at.isoformat(),
                "config_data": entry.config_data,
            }
            for entry in history
        ]
    
    def restore_configuration_version(
        self,
        config_id: uuid.UUID,
        version: int,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Restore a configuration to a previous version.
        
        Args:
            config_id: Configuration UUID
            version: Version number to restore
            user_id: User making the change
            
        Returns:
            True if restored successfully, False otherwise
        """
        # Get the historical version
        history_entry = self.db.query(ConfigurationHistory).filter(
            and_(
                ConfigurationHistory.config_id == config_id,
                ConfigurationHistory.version == version,
            )
        ).first()
        
        if not history_entry:
            return False
        
        # Load the configuration from history
        config = ModeConfiguration.from_dict(history_entry.config_data)
        
        # Update with new version number
        return self.update_configuration(
            config_id=config_id,
            config=config,
            user_id=user_id,
            change_description=f"Restored to version {version}",
        )
    
    def export_configuration(
        self,
        config_id: uuid.UUID,
        format: str = "json",
    ) -> Optional[str]:
        """
        Export configuration to JSON or YAML.
        
        Args:
            config_id: Configuration UUID
            format: Export format ("json" or "yaml")
            
        Returns:
            Serialized configuration string or None if not found
        """
        config = self.get_configuration(config_id)
        
        if not config:
            return None
        
        if format.lower() == "json":
            return config.to_json()
        elif format.lower() == "yaml":
            return yaml.dump(config.to_dict(), default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_configuration(
        self,
        data: str,
        format: str = "json",
        user_id: Optional[uuid.UUID] = None,
        set_active: bool = False,
    ) -> uuid.UUID:
        """
        Import configuration from JSON or YAML.
        
        Args:
            data: Serialized configuration string
            format: Import format ("json" or "yaml")
            user_id: User ID for the configuration
            set_active: Whether to set as active
            
        Returns:
            UUID of imported configuration
        """
        if format.lower() == "json":
            config_dict = json.loads(data)
        elif format.lower() == "yaml":
            config_dict = yaml.safe_load(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        config = ModeConfiguration.from_dict(config_dict)
        
        return self.create_configuration(
            config=config,
            user_id=user_id,
            set_active=set_active,
        )
    
    def create_default_configurations(self, user_id: Optional[uuid.UUID] = None):
        """
        Create default configurations for all operating modes.
        
        Args:
            user_id: Optional user ID (None for system-wide)
        """
        for mode in OperatingMode:
            default_config = get_default_config(mode)
            
            # Check if default already exists
            existing = self.db.query(Configuration).filter(
                and_(
                    Configuration.user_id == user_id,
                    Configuration.name == default_config.name,
                )
            ).first()
            
            if not existing:
                config_id = self.create_configuration(
                    config=default_config,
                    user_id=user_id,
                    set_active=(mode == OperatingMode.MIXED),  # Set MIXED as default active
                )
                
                # Mark as default
                db_config = self.db.query(Configuration).filter(
                    Configuration.id == config_id
                ).first()
                if db_config:
                    db_config.is_default = True
                    self.db.commit()
    
    def _deactivate_user_configs(self, user_id: Optional[uuid.UUID]):
        """Deactivate all configurations for a user."""
        query = self.db.query(Configuration).filter(
            Configuration.is_active == True
        )
        
        if user_id:
            query = query.filter(Configuration.user_id == user_id)
        else:
            query = query.filter(Configuration.user_id.is_(None))
        
        for config in query.all():
            config.is_active = False
        
        self.db.commit()
    
    def _create_history_entry(
        self,
        config_id: uuid.UUID,
        config_data: Dict[str, Any],
        version: int,
        changed_by: Optional[uuid.UUID],
        change_description: str,
    ):
        """Create a configuration history entry."""
        history_entry = ConfigurationHistory(
            id=uuid.uuid4(),
            config_id=config_id,
            config_data=config_data,
            version=version,
            changed_by=changed_by,
            change_description=change_description,
        )
        
        self.db.add(history_entry)
        self.db.commit()


class ConfigurationCache:
    """
    In-memory cache for active configurations to reduce database queries.
    """
    
    def __init__(self):
        """Initialize configuration cache."""
        self._cache: Dict[str, ModeConfiguration] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._ttl_seconds = 300  # 5 minutes
    
    def get(self, user_id: Optional[uuid.UUID] = None) -> Optional[ModeConfiguration]:
        """
        Get cached configuration.
        
        Args:
            user_id: User ID (None for system-wide)
            
        Returns:
            Cached ModeConfiguration or None if not cached or expired
        """
        cache_key = str(user_id) if user_id else "system"
        
        if cache_key not in self._cache:
            return None
        
        # Check if expired
        timestamp = self._cache_timestamps.get(cache_key)
        if timestamp and (datetime.utcnow() - timestamp).total_seconds() > self._ttl_seconds:
            self.invalidate(user_id)
            return None
        
        return self._cache.get(cache_key)
    
    def set(self, config: ModeConfiguration, user_id: Optional[uuid.UUID] = None):
        """
        Cache configuration.
        
        Args:
            config: ModeConfiguration to cache
            user_id: User ID (None for system-wide)
        """
        cache_key = str(user_id) if user_id else "system"
        self._cache[cache_key] = config
        self._cache_timestamps[cache_key] = datetime.utcnow()
    
    def invalidate(self, user_id: Optional[uuid.UUID] = None):
        """
        Invalidate cached configuration.
        
        Args:
            user_id: User ID (None for system-wide)
        """
        cache_key = str(user_id) if user_id else "system"
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
    
    def clear(self):
        """Clear all cached configurations."""
        self._cache.clear()
        self._cache_timestamps.clear()


# Global configuration cache instance
config_cache = ConfigurationCache()
