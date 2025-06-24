"""
Update manager module
"""
import os
import logging
import requests
import threading
import tkinter as tk
from tkinter import messagebox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='update.log'
)
logger = logging.getLogger(__name__)

# Update configuration
AUTO_UPDATE_CHECK_ON_START = True
AUTO_UPDATE_ENABLED = True

def check_for_update(current_version, force_check=False):
    """Check for app updates safely using the main thread for all Tkinter operations
    
    Args:
        current_version (str): The current version of the application
        force_check (bool): If True, force checking for updates regardless of settings
        
    Returns:
        bool: True if an update is available, False otherwise
    """
    try:
        logger.info(f"Checking for updates... Current version: {current_version}, force_check: {force_check}")
        
        # For demo purposes, we'll simulate a check with the remote server
        try:
            # In a real app, this would be a call to your server to check for updates
            # response = requests.get("https://api.example.com/check-version", params={"version": current_version})
            # latest_version = response.json().get("latest_version")
            
            # For now, we just simulate no update is available (return False)
            latest_version = current_version  # In real app, this would be fetched from server
            
            # Compare versions to determine if an update is needed
            if latest_version > current_version:
                logger.info(f"Update available: {latest_version}")
                return True
            else:
                logger.info("No update available. Running latest version.")
                return False
                
        except Exception as connection_error:
            logger.error(f"Connection error checking for updates: {connection_error}")
            if force_check:
                # Re-raise to handle in the caller
                raise connection_error
            return False
            
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        if force_check:
            # Re-raise to handle in the caller
            raise e
        return False
