# Facebook Campaign Scheduler

A Python-based automation tool that manages Facebook ad campaigns based on a customizable schedule. The script automatically activates and pauses campaigns according to predefined time slots, helping you optimize ad spend and campaign management.

## Features

- 🕒 Schedule campaigns by day and time in UTC timezone
- 🔄 Automatic activation and pausing of campaigns
- 📝 Detailed logging of all actions
- ⚙️ Easy configuration through YAML file
- 🔍 Real-time status monitoring
- ⏲️ Countdown to next schedule change
- 🌐 UTC timezone support for global campaign management

## Prerequisites

- Python 3.7+
- Facebook Business Account
- Facebook Marketing API access
- Campaign IDs to manage

## Configuration Parameters

The script uses a YAML configuration file (`config.yaml`) that contains all the necessary settings. Here's a detailed breakdown of the configurable parameters:

### Facebook API Settings
- `facebook.app_id`: Your Facebook application ID
- `facebook.app_secret`: Your Facebook application secret key  
- `facebook.access_token`: Access token with ads_management permission

### Timezone
- `timezone`: Timezone for schedule calculations (defaults to 'Asia/Jerusalem')

### Campaign Management
- `campaigns.managed_campaigns`: List of Facebook campaign IDs to manage


### Schedule Configuration
The weekly schedule can be customized for each day with the following parameters:
- `schedule.defaults`: Default schedule settings if day-specific ones aren't set
  - `start_time`: Time to activate campaigns (HH:MM format)
  - `end_time`: Time to pause campaigns (HH:MM format)
  - `enabled`: Whether the schedule is active (optional, defaults to true)

Each day (monday through sunday) can have:
- `start_time`: Campaign activation time
- `end_time`: Campaign deactivation time
- `enabled`: Optional flag to enable/disable the entire day

### Time Format Settings
- `time.format`: Internal time processing format
- `time.display_format`: Time format for log displays
- `time.days_order`: Order of days for schedule processing

### Error Handling
- `errors.retry`:
  - `max_attempts`: Maximum retry attempts for failed operations
  - `delay_seconds`: Delay between retry attempts
  - `exponential_backoff`: Whether to increase delay between retries
- `errors.logging`:
  - `api_errors`: Log level for API errors
  - `schedule_errors`: Log level for schedule parsing errors
  - `status_changes`: Log level for campaign status changes
- `errors.handling`:
  - `continue_on_error`: Whether to continue after non-critical errors
  - `alert_on_consecutive_failures`: Number of failures before alerting

All times must be in 24-hour format (HH:MM) and the schedule supports flexible configurations like:
- Workdays only (Monday-Friday)
- Custom hours per day
- 24/7 operation except specific days
- Different operating hours for weekends

