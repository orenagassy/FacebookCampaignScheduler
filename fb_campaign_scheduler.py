import requests
import yaml
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.campaign import Campaign
from datetime import datetime, timedelta
import pytz
import logging
import time
from logging.handlers import RotatingFileHandler

def load_config():
    """
    Load configuration from YAML file
    Returns:
        dict: Configuration containing Facebook credentials, campaign IDs, and schedule
    """
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

def setup_logging(config):
    """
    Configure logging based on config settings
    Args:
        config (dict): Configuration dictionary
    """
    log_config = config['system']['logging']
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_config['file'],
        maxBytes=log_config['max_size'],
        backupCount=log_config['backup_count']
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Set format for both handlers
    formatter = logging.Formatter(log_config['format'])
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.root.setLevel(getattr(logging, log_config['level']))
    logging.root.addHandler(file_handler)
    logging.root.addHandler(console_handler)

def manage_campaign_status(campaign_id, should_be_active, config):
    """
    Update campaign status with retry logic
    Args:
        campaign_id (str): Facebook campaign ID
        should_be_active (bool): Whether campaign should be active
        config (dict): Configuration dictionary
    """
    status_config = config['campaigns']['status']
    error_config = config['errors']
    retry_config = error_config['retry']
    
    for attempt in range(retry_config['max_attempts']):
        try:
            # Add validation for campaign object
            campaign = Campaign(campaign_id)
            if not campaign:
                raise ValueError(f"Unable to initialize campaign with ID {campaign_id}")
            
            # Fetch both status and name
            campaign_data = campaign.api_get(
                fields=['status', 'name'],
                params={'fields': 'status,name'}
            )
            
            # Validate response
            if not campaign_data or 'status' not in campaign_data or 'name' not in campaign_data:
                raise ValueError(f"Invalid API response for campaign {campaign_id}")
            
            current_status = campaign_data['status']
            campaign_name = campaign_data['name']
            
            if should_be_active and current_status == status_config['paused']:
                campaign.api_update(
                    params={'status': status_config['active']}
                )
                logging.log(
                    getattr(logging, error_config['logging']['status_changes']),
                    f"Campaign '{campaign_name}' ({campaign_id}) activated"
                )
            elif not should_be_active and current_status == status_config['active']:
                campaign.api_update(
                    params={'status': status_config['paused']}
                )
                logging.log(
                    getattr(logging, error_config['logging']['status_changes']),
                    f"Campaign '{campaign_name}' ({campaign_id}) paused"
                )
            break
            
        except Exception as e:
            delay = retry_config['delay_seconds']
            if retry_config['exponential_backoff']:
                delay = delay * (attempt + 1)
            
            logging.log(
                getattr(logging, error_config['logging']['api_errors']),
                f"Error managing campaign {campaign_id} (attempt {attempt + 1}): {str(e)}"
            )
            
            if attempt < retry_config['max_attempts'] - 1:
                time.sleep(delay)
            elif not error_config['handling']['continue_on_error']:
                raise

def should_campaign_be_active(schedule, config):
    """
    Check if campaigns should be active based on current time and schedule
    Args:
        schedule (dict): Schedule configuration
        config (dict): Configuration dictionary
    Returns:
        bool: True if campaigns should be active
    """
    tz = pytz.timezone(config['timezone'])
    current_time = datetime.now(tz)
    current_day = current_time.strftime('%A').lower()
    current_hour_minute = current_time.strftime(config['campaigns']['time']['format'])

    # Use default schedule if day not specified
    day_schedule = schedule.get(current_day, schedule['defaults'])
    if not day_schedule.get('enabled', True):
        return False

    start_time = day_schedule.get('start_time', schedule['defaults']['start_time'])
    end_time = day_schedule.get('end_time', schedule['defaults']['end_time'])

    return start_time <= current_hour_minute <= end_time

def get_next_schedule_change(schedule, config):
    """
    Calculate time until next schedule change
    Args:
        schedule (dict): Schedule configuration
        config (dict): Configuration dictionary
    Returns:
        tuple: (seconds until next change, description of next change)
    """
    tz = pytz.timezone(config['timezone'])
    current_time = datetime.now(tz)
    current_day = current_time.strftime('%A').lower()
    current_time_str = current_time.strftime(config['campaigns']['time']['format'])
    
    days_order = config['campaigns']['time']['days_order']
    current_day_index = days_order.index(current_day)
    
    # Check current day's schedule
    day_schedule = schedule.get(current_day)
    if day_schedule and day_schedule.get('enabled', True):
        start_time = day_schedule['start_time']
        end_time = day_schedule['end_time']
        
        # Before start time
        if current_time_str < start_time:
            next_time = datetime.strptime(start_time, '%H:%M').time()
            next_datetime = datetime.combine(current_time.date(), next_time)
            next_datetime = tz.localize(next_datetime)
            seconds_until = (next_datetime - current_time).total_seconds()
            return seconds_until, f"Activation at {start_time}"
            
        # Before end time
        if current_time_str < end_time:
            next_time = datetime.strptime(end_time, '%H:%M').time()
            next_datetime = datetime.combine(current_time.date(), next_time)
            next_datetime = tz.localize(next_datetime)
            seconds_until = (next_datetime - current_time).total_seconds()
            return seconds_until, f"Deactivation at {end_time}"
    
    # Find next active day
    for i in range(1, 8):
        next_day_index = (current_day_index + i) % 7
        next_day = days_order[next_day_index]
        next_schedule = schedule.get(next_day)
        
        if next_schedule and next_schedule.get('enabled', True):
            next_start = datetime.strptime(next_schedule['start_time'], '%H:%M').time()
            next_date = current_time.date() + timedelta(days=i)
            next_datetime = datetime.combine(next_date, next_start)
            next_datetime = tz.localize(next_datetime)
            seconds_until = (next_datetime - current_time).total_seconds()
            return seconds_until, f"Next activation on {next_day} at {next_schedule['start_time']}"
    
    # If no next change found, return 24 hours as default
    return 86400, "No schedule changes in the next 24 hours"

def main():
    """
    Main function to continuously manage Facebook campaigns according to schedule
    """
    config = load_config()
    setup_logging(config)
    
    # Initialize Facebook API
    FacebookAdsApi.init(
        config['facebook']['app_id'],
        config['facebook']['app_secret'],
        config['facebook']['access_token']
    )

    logging.info(f"Using timezone: {config['timezone']}")

    consecutive_failures = 0
    
    # Continuous monitoring loop
    while True:
        try:
            should_be_active = should_campaign_be_active(config['campaigns']['schedule'], config)
            seconds_until_change, next_change_msg = get_next_schedule_change(
                config['campaigns']['schedule'], 
                config
            )
            
            # Log current status
            current_time = datetime.now(pytz.timezone(config['timezone'])).strftime(
                config['campaigns']['time']['display_format']
            )
            logging.info(f"\nCurrent time ({config['timezone']}): {current_time}")
            logging.info(f"Status: {'ACTIVE' if should_be_active else 'PAUSED'}")
            logging.info(f"Next Change: {next_change_msg}")
            logging.info(f"Time until change: {int(seconds_until_change/3600)}h {int((seconds_until_change%3600)/60)}m")
            
            # Update campaign statuses
            for campaign_id in config['campaigns']['managed_campaigns']:
                manage_campaign_status(campaign_id, should_be_active, config)
            
            consecutive_failures = 0
            
        except Exception as e:
            consecutive_failures += 1
            logging.error(f"Error in main loop: {str(e)}")
            
            if consecutive_failures >= config['errors']['handling']['alert_on_consecutive_failures']:
                logging.critical(f"Critical: {consecutive_failures} consecutive failures!")
        
        # Wait before next check
        time.sleep(config['system']['check_interval'])

if __name__ == "__main__":
    main()