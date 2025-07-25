#!/usr/bin/env python3
"""
Status Page.py - RUC Reminders Order Processing System

This script integrates with the Webfleet API to download order attachments
and send comprehensive emails to customers with all available documentation.

Features:
- Download all order attachments via Webfleet API
- Collect PDF attachments for email distribution
- Send emails with all PDFs plus standard PDF
- Robust error handling and logging
- Order processing workflow integration

Author: RUC Reminders System
Version: 1.0.0
"""

import os
import sys
import logging
import json
import requests
import smtplib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import tempfile
import hashlib


class WebfleetAPIClient:
    """Client for interacting with Webfleet API for order attachments."""
    
    def __init__(self, api_key: str, account: str, base_url: str = "https://csv.webfleet.com"):
        """
        Initialize Webfleet API client.
        
        Args:
            api_key: Webfleet API key
            account: Webfleet account identifier
            base_url: Base URL for Webfleet API
        """
        self.api_key = api_key
        self.account = account
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        """
        Make authenticated request to Webfleet API.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: On API request failure
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Add authentication parameters
        auth_params = {
            'apikey': self.api_key,
            'account': self.account,
            **params
        }
        
        try:
            response = self.session.get(url, params=auth_params, timeout=30)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Webfleet API request failed: {e}")
            raise
    
    def show_order_attachment_list(self, order_id: str) -> List[Dict]:
        """
        List all attachments for a specific order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            List of attachment metadata dictionaries
        """
        self.logger.info(f"Fetching attachment list for order: {order_id}")
        
        try:
            response = self._make_request('showOrderAttachmentListExtern', {
                'orderid': order_id
            })
            
            # Parse response (assuming JSON format)
            data = response.json()
            attachments = data.get('attachments', [])
            
            self.logger.info(f"Found {len(attachments)} attachments for order {order_id}")
            return attachments
            
        except Exception as e:
            self.logger.error(f"Failed to list attachments for order {order_id}: {e}")
            return []
    
    def download_order_attachment(self, attachment_id: str, order_id: str) -> Optional[bytes]:
        """
        Download a specific attachment by ID.
        
        Args:
            attachment_id: Attachment identifier
            order_id: Order identifier for logging
            
        Returns:
            Attachment content as bytes, or None if download failed
        """
        self.logger.info(f"Downloading attachment {attachment_id} for order {order_id}")
        
        try:
            response = self._make_request('downloadOrderAttachment', {
                'attachmentid': attachment_id
            })
            
            content = response.content
            self.logger.info(f"Successfully downloaded attachment {attachment_id} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to download attachment {attachment_id}: {e}")
            return None


class PDFAttachmentManager:
    """Manages PDF attachment collection and processing."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize PDF attachment manager.
        
        Args:
            temp_dir: Directory for temporary files, uses system temp if None
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self.temp_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.pdf_files = []
        
    def is_pdf_content(self, content: bytes) -> bool:
        """
        Check if content is a PDF file.
        
        Args:
            content: File content bytes
            
        Returns:
            True if content appears to be PDF
        """
        return content.startswith(b'%PDF')
    
    def save_attachment(self, content: bytes, filename: str, order_id: str) -> Optional[Path]:
        """
        Save attachment content to temporary file.
        
        Args:
            content: File content
            filename: Original filename
            order_id: Order ID for file organization
            
        Returns:
            Path to saved file, or None if save failed
        """
        try:
            # Create order-specific subdirectory
            order_dir = self.temp_dir / f"order_{order_id}"
            order_dir.mkdir(exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(filename)
            file_path = order_dir / safe_filename
            
            # Write content to file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            self.logger.info(f"Saved attachment to: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save attachment {filename}: {e}")
            return None
    
    def _generate_safe_filename(self, filename: str) -> str:
        """Generate safe filename for filesystem."""
        # Remove or replace unsafe characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        safe_name = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Ensure it's not empty and has reasonable length
        if not safe_name or safe_name.startswith('.'):
            safe_name = f"attachment_{hashlib.md5(filename.encode()).hexdigest()[:8]}"
        
        return safe_name[:100]  # Limit length
    
    def collect_order_pdfs(self, webfleet_client: WebfleetAPIClient, order_id: str) -> List[Path]:
        """
        Collect all PDF attachments for an order.
        
        Args:
            webfleet_client: Configured Webfleet API client
            order_id: Order identifier
            
        Returns:
            List of paths to downloaded PDF files
        """
        pdf_paths = []
        
        try:
            # Get list of attachments
            attachments = webfleet_client.show_order_attachment_list(order_id)
            
            for attachment in attachments:
                attachment_id = attachment.get('attachmentid') or attachment.get('id')
                filename = attachment.get('filename', f"attachment_{attachment_id}")
                
                if not attachment_id:
                    self.logger.warning(f"Attachment missing ID: {attachment}")
                    continue
                
                # Download attachment
                content = webfleet_client.download_order_attachment(attachment_id, order_id)
                if not content:
                    self.logger.warning(f"Failed to download attachment {attachment_id}")
                    continue
                
                # Check if it's a PDF
                if self.is_pdf_content(content):
                    # Save PDF file
                    pdf_path = self.save_attachment(content, filename, order_id)
                    if pdf_path:
                        pdf_paths.append(pdf_path)
                        self.logger.info(f"Collected PDF: {filename}")
                else:
                    self.logger.info(f"Skipping non-PDF attachment: {filename}")
            
            self.logger.info(f"Collected {len(pdf_paths)} PDF attachments for order {order_id}")
            return pdf_paths
            
        except Exception as e:
            self.logger.error(f"Failed to collect PDFs for order {order_id}: {e}")
            return []
    
    def cleanup_temp_files(self, order_id: str = None):
        """
        Clean up temporary files.
        
        Args:
            order_id: If specified, only clean files for this order
        """
        try:
            if order_id:
                order_dir = self.temp_dir / f"order_{order_id}"
                if order_dir.exists():
                    for file_path in order_dir.iterdir():
                        file_path.unlink()
                    order_dir.rmdir()
                    self.logger.info(f"Cleaned up temp files for order {order_id}")
            else:
                # Clean all temp files (use with caution)
                for item in self.temp_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir() and item.name.startswith('order_'):
                        for file_path in item.iterdir():
                            file_path.unlink()
                        item.rmdir()
                self.logger.info("Cleaned up all temp files")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


class EmailSender:
    """Handles email sending with PDF attachments."""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """
        Initialize email sender.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)
    
    def send_email(self, to_email: str, subject: str, body: str, 
                   pdf_attachments: List[Path], standard_pdf_path: Optional[Path] = None,
                   from_email: str = None) -> bool:
        """
        Send email with PDF attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            pdf_attachments: List of PDF file paths to attach
            standard_pdf_path: Path to standard PDF (always attached)
            from_email: Sender email (uses username if None)
            
        Returns:
            True if email sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email or self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Track attached files for logging
            attached_files = []
            
            # Attach standard PDF if provided
            if standard_pdf_path and standard_pdf_path.exists():
                if self._attach_pdf(msg, standard_pdf_path, "Standard_Document.pdf"):
                    attached_files.append("Standard_Document.pdf")
            
            # Attach order PDFs
            for pdf_path in pdf_attachments:
                if pdf_path.exists():
                    filename = pdf_path.name
                    if self._attach_pdf(msg, pdf_path, filename):
                        attached_files.append(filename)
                else:
                    self.logger.warning(f"PDF attachment not found: {pdf_path}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent to {to_email} with {len(attached_files)} attachments: {attached_files}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _attach_pdf(self, msg: MIMEMultipart, pdf_path: Path, filename: str) -> bool:
        """
        Attach PDF file to email message.
        
        Args:
            msg: Email message object
            pdf_path: Path to PDF file
            filename: Filename for attachment
            
        Returns:
            True if attachment succeeded
        """
        try:
            with open(pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'pdf')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            msg.attach(part)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to attach PDF {pdf_path}: {e}")
            return False


class StatusPageProcessor:
    """Main processor for order status and email notifications."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize status page processor.
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.webfleet_client = WebfleetAPIClient(
            api_key=self.config['webfleet']['api_key'],
            account=self.config['webfleet']['account'],
            base_url=self.config['webfleet'].get('base_url', 'https://csv.webfleet.com')
        )
        
        self.pdf_manager = PDFAttachmentManager(
            temp_dir=self.config.get('temp_dir')
        )
        
        self.email_sender = EmailSender(
            smtp_server=self.config['email']['smtp_server'],
            smtp_port=self.config['email']['smtp_port'],
            username=self.config['email']['username'],
            password=self.config['email']['password']
        )
        
        self.standard_pdf_path = Path(self.config.get('standard_pdf_path', '')) if self.config.get('standard_pdf_path') else None
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('status_page.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def _load_config(self, config_path: str = None) -> Dict:
        """
        Load configuration from file or environment.
        
        Args:
            config_path: Path to JSON config file
            
        Returns:
            Configuration dictionary
        """
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load config file {config_path}: {e}")
        
        # Fallback to environment variables
        return {
            'webfleet': {
                'api_key': os.getenv('WEBFLEET_API_KEY', ''),
                'account': os.getenv('WEBFLEET_ACCOUNT', ''),
                'base_url': os.getenv('WEBFLEET_BASE_URL', 'https://csv.webfleet.com')
            },
            'email': {
                'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'username': os.getenv('EMAIL_USERNAME', ''),
                'password': os.getenv('EMAIL_PASSWORD', '')
            },
            'standard_pdf_path': os.getenv('STANDARD_PDF_PATH', ''),
            'temp_dir': os.getenv('TEMP_DIR', '/tmp/ruc_reminders')
        }
    
    def process_order(self, order_id: str, customer_email: str, 
                     subject: str = None, body: str = None) -> bool:
        """
        Process an order: download attachments and send notification email.
        
        Args:
            order_id: Order identifier
            customer_email: Customer email address
            subject: Email subject (uses default if None)
            body: Email body (uses default if None)
            
        Returns:
            True if processing succeeded
        """
        self.logger.info(f"Processing order {order_id} for customer {customer_email}")
        
        try:
            # Collect PDF attachments
            pdf_attachments = self.pdf_manager.collect_order_pdfs(
                self.webfleet_client, order_id
            )
            
            # Prepare email content
            email_subject = subject or f"Order {order_id} - Documentation Package"
            email_body = body or self._generate_default_email_body(order_id, len(pdf_attachments))
            
            # Send email with attachments
            success = self.email_sender.send_email(
                to_email=customer_email,
                subject=email_subject,
                body=email_body,
                pdf_attachments=pdf_attachments,
                standard_pdf_path=self.standard_pdf_path
            )
            
            if success:
                self.logger.info(f"Successfully processed order {order_id}")
            else:
                self.logger.error(f"Failed to send email for order {order_id}")
            
            # Cleanup temporary files
            self.pdf_manager.cleanup_temp_files(order_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing order {order_id}: {e}")
            return False
    
    def _generate_default_email_body(self, order_id: str, attachment_count: int) -> str:
        """Generate default email body content."""
        return f"""Dear Customer,

Please find attached the documentation package for your order {order_id}.

This package includes:
- Standard documentation (always included)
- {attachment_count} additional proof of delivery and order-related documents

Thank you for your business.

Best regards,
RUC Reminders Team

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def process_multiple_orders(self, orders: List[Dict]) -> Dict[str, bool]:
        """
        Process multiple orders.
        
        Args:
            orders: List of order dictionaries with 'order_id' and 'customer_email'
            
        Returns:
            Dictionary mapping order_id to success status
        """
        results = {}
        
        for order in orders:
            order_id = order.get('order_id')
            customer_email = order.get('customer_email')
            
            if not order_id or not customer_email:
                self.logger.warning(f"Invalid order data: {order}")
                results[order_id or 'unknown'] = False
                continue
            
            success = self.process_order(
                order_id=order_id,
                customer_email=customer_email,
                subject=order.get('subject'),
                body=order.get('body')
            )
            
            results[order_id] = success
        
        return results


def create_sample_config(config_path: str = 'config.json'):
    """Create a sample configuration file."""
    sample_config = {
        "webfleet": {
            "api_key": "your_webfleet_api_key_here",
            "account": "your_webfleet_account_here",
            "base_url": "https://csv.webfleet.com"
        },
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "your_email@example.com",
            "password": "your_email_password_here"
        },
        "standard_pdf_path": "/path/to/your/standard_document.pdf",
        "temp_dir": "/tmp/ruc_reminders"
    }
    
    with open(config_path, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"Sample configuration created at: {config_path}")
    print("Please update the configuration with your actual credentials and paths.")


def main():
    """Main entry point for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='RUC Reminders Status Page Processor')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--order-id', help='Single order ID to process')
    parser.add_argument('--customer-email', help='Customer email for single order')
    parser.add_argument('--create-config', action='store_true', help='Create sample configuration file')
    parser.add_argument('--test-connection', action='store_true', help='Test API connections')
    
    args = parser.parse_args()
    
    if args.create_config:
        create_sample_config()
        return
    
    try:
        processor = StatusPageProcessor(config_path=args.config)
        
        if args.test_connection:
            # Test Webfleet connection
            try:
                # Try to list attachments for a dummy order (this will fail but test connection)
                processor.webfleet_client.show_order_attachment_list('test')
                print("Webfleet API connection: OK")
            except Exception as e:
                print(f"Webfleet API connection: FAILED - {e}")
            return
        
        if args.order_id and args.customer_email:
            # Process single order
            success = processor.process_order(args.order_id, args.customer_email)
            if success:
                print(f"Successfully processed order {args.order_id}")
            else:
                print(f"Failed to process order {args.order_id}")
                sys.exit(1)
        else:
            print("Please provide --order-id and --customer-email, or use --create-config")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()