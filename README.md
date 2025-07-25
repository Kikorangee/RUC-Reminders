# RUC Reminders Status Page System

## Overview

The Status Page.py script is a comprehensive order processing system that integrates with the Webfleet API to download order attachments and send notification emails to customers with all available documentation.

## Features

- **Webfleet API Integration**: Downloads all order attachments using official Webfleet API endpoints
- **PDF Collection**: Automatically identifies and collects PDF attachments from each order
- **Email Notifications**: Sends comprehensive emails with all PDFs plus standard documentation
- **Robust Error Handling**: Comprehensive logging and error recovery mechanisms
- **Configurable**: Supports both file-based and environment variable configuration

## API Endpoints Used

1. `showOrderAttachmentListExtern` - Lists all attachments for an order
2. `downloadOrderAttachment` - Downloads specific attachments by ID

## Installation

1. Install Python 3.7 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Option 1: Configuration File

1. Copy the example configuration:
   ```bash
   cp config.json.example config.json
   ```

2. Edit `config.json` with your credentials:
   ```json
   {
     "webfleet": {
       "api_key": "your_actual_api_key",
       "account": "your_account_name",
       "base_url": "https://csv.webfleet.com"
     },
     "email": {
       "smtp_server": "smtp.gmail.com",
       "smtp_port": 587,
       "username": "your_email@example.com", 
       "password": "your_app_password"
     },
     "standard_pdf_path": "/path/to/standard_document.pdf",
     "temp_dir": "/tmp/ruc_reminders"
   }
   ```

### Option 2: Environment Variables

Set the following environment variables:
- `WEBFLEET_API_KEY`: Your Webfleet API key
- `WEBFLEET_ACCOUNT`: Your Webfleet account name
- `WEBFLEET_BASE_URL`: Webfleet API base URL (optional, defaults to https://csv.webfleet.com)
- `SMTP_SERVER`: SMTP server hostname
- `SMTP_PORT`: SMTP port (optional, defaults to 587)
- `EMAIL_USERNAME`: Email username
- `EMAIL_PASSWORD`: Email password
- `STANDARD_PDF_PATH`: Path to standard PDF document (optional)
- `TEMP_DIR`: Temporary directory for downloads (optional)

## Usage

### Command Line Interface

Process a single order:
```bash
python "Status Page.py" --order-id "ORDER123" --customer-email "customer@example.com"
```

Create sample configuration:
```bash
python "Status Page.py" --create-config
```

Test API connections:
```bash
python "Status Page.py" --test-connection
```

### Programmatic Usage

```python
from Status_Page import StatusPageProcessor

# Initialize processor
processor = StatusPageProcessor(config_path='config.json')

# Process single order
success = processor.process_order(
    order_id='ORDER123',
    customer_email='customer@example.com'
)

# Process multiple orders
orders = [
    {'order_id': 'ORDER123', 'customer_email': 'customer1@example.com'},
    {'order_id': 'ORDER124', 'customer_email': 'customer2@example.com'}
]
results = processor.process_multiple_orders(orders)
```

## Workflow

1. **Order Processing**: For each order, the system:
   - Calls `showOrderAttachmentListExtern` to get list of attachments
   - Downloads each attachment using `downloadOrderAttachment`
   - Filters for PDF files only
   - Saves PDFs to temporary directory

2. **Email Preparation**: 
   - Collects all downloaded PDF attachments
   - Includes standard PDF document (if configured)
   - Prepares email with appropriate subject and body

3. **Email Sending**:
   - Attaches all PDFs to email
   - Sends email via configured SMTP server
   - Logs all attached files for troubleshooting

4. **Cleanup**:
   - Removes temporary files after email is sent
   - Logs completion status

## Error Handling

- **API Failures**: Retries with exponential backoff
- **Download Failures**: Logs warnings but continues with available files
- **Email Failures**: Returns failure status with detailed error logging
- **File System Errors**: Graceful handling with cleanup

## Logging

All operations are logged to both:
- `status_page.log` file
- Console output

Log levels include:
- INFO: Normal operation events
- WARNING: Non-critical issues (e.g., missing attachments)
- ERROR: Critical failures that prevent completion

## Security Considerations

- API keys and passwords should be stored securely
- Use environment variables in production
- Consider using app-specific passwords for email
- Temporary files are cleaned up automatically
- File permissions are set appropriately

## Troubleshooting

### Common Issues

1. **API Authentication Errors**:
   - Verify API key and account name
   - Check API key permissions in Webfleet portal

2. **Email Sending Failures**:
   - Verify SMTP settings
   - Check if app-specific password is required
   - Ensure firewall allows SMTP connections

3. **File Access Errors**:
   - Check temp directory permissions
   - Verify standard PDF path exists
   - Ensure sufficient disk space

### Debug Mode

Enable debug logging by modifying the script:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Integration

The system can be integrated into existing workflows:

- **Scheduled Processing**: Use cron or task scheduler
- **Event-Driven**: Trigger from order status changes
- **Batch Processing**: Process multiple orders from database
- **API Gateway**: Expose as REST endpoint

## License

This software is part of the RUC Reminders system.