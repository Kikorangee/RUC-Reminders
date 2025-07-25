#!/usr/bin/env python3
"""
Test script for Status Page.py functionality.

This script provides basic unit tests for the RUC Reminders order processing system.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the main module (handle space in filename)
import importlib.util
spec = importlib.util.spec_from_file_location("status_page", "Status Page.py")
status_page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status_page)


class TestWebfleetAPIClient(unittest.TestCase):
    """Test Webfleet API client functionality."""
    
    def setUp(self):
        self.client = status_page.WebfleetAPIClient(
            api_key="test_key",
            account="test_account"
        )
    
    def test_client_initialization(self):
        """Test client initialization."""
        self.assertEqual(self.client.api_key, "test_key")
        self.assertEqual(self.client.account, "test_account")
        self.assertEqual(self.client.base_url, "https://csv.webfleet.com")
    
    @patch('requests.Session.get')
    def test_show_order_attachment_list_success(self, mock_get):
        """Test successful attachment list retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'attachments': [
                {'attachmentid': '123', 'filename': 'doc1.pdf'},
                {'attachmentid': '124', 'filename': 'doc2.pdf'}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test the method
        attachments = self.client.show_order_attachment_list('ORDER123')
        
        # Verify results
        self.assertEqual(len(attachments), 2)
        self.assertEqual(attachments[0]['attachmentid'], '123')
        self.assertEqual(attachments[1]['filename'], 'doc2.pdf')
    
    @patch('requests.Session.get')
    def test_show_order_attachment_list_failure(self, mock_get):
        """Test attachment list retrieval failure."""
        # Mock failed response
        mock_get.side_effect = Exception("API Error")
        
        # Test the method
        attachments = self.client.show_order_attachment_list('ORDER123')
        
        # Should return empty list on failure
        self.assertEqual(attachments, [])
    
    @patch('requests.Session.get')
    def test_download_order_attachment_success(self, mock_get):
        """Test successful attachment download."""
        # Mock successful response with PDF content
        mock_response = Mock()
        mock_response.content = b'%PDF-1.4\ntest pdf content'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test the method
        content = self.client.download_order_attachment('123', 'ORDER123')
        
        # Verify results
        self.assertIsNotNone(content)
        self.assertTrue(content.startswith(b'%PDF'))


class TestPDFAttachmentManager(unittest.TestCase):
    """Test PDF attachment manager functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = status_page.PDFAttachmentManager(temp_dir=self.temp_dir)
    
    def tearDown(self):
        # Cleanup temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_is_pdf_content(self):
        """Test PDF content detection."""
        # Test valid PDF content
        pdf_content = b'%PDF-1.4\ntest content'
        self.assertTrue(self.manager.is_pdf_content(pdf_content))
        
        # Test non-PDF content
        non_pdf_content = b'This is not a PDF'
        self.assertFalse(self.manager.is_pdf_content(non_pdf_content))
    
    def test_save_attachment(self):
        """Test attachment saving."""
        content = b'%PDF-1.4\ntest pdf content'
        filename = 'test_document.pdf'
        order_id = 'ORDER123'
        
        # Save the attachment
        saved_path = self.manager.save_attachment(content, filename, order_id)
        
        # Verify file was saved
        self.assertIsNotNone(saved_path)
        self.assertTrue(saved_path.exists())
        
        # Verify content is correct
        with open(saved_path, 'rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)
    
    def test_generate_safe_filename(self):
        """Test safe filename generation."""
        # Test normal filename
        safe = self.manager._generate_safe_filename('document.pdf')
        self.assertEqual(safe, 'document.pdf')
        
        # Test filename with unsafe characters
        safe = self.manager._generate_safe_filename('doc<>ument?.pdf')
        self.assertTrue(safe.replace('_', '').replace('.', '').replace('doc', '').replace('ument', '').replace('pdf', '') == '')
        
        # Test empty filename
        safe = self.manager._generate_safe_filename('')
        self.assertTrue(safe.startswith('attachment_'))


class TestEmailSender(unittest.TestCase):
    """Test email sender functionality."""
    
    def setUp(self):
        self.sender = status_page.EmailSender(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="test@example.com",
            password="password"
        )
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp_class):
        """Test successful email sending."""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4\ntest content')
            temp_path = Path(temp_file.name)
        
        try:
            # Test email sending
            success = self.sender.send_email(
                to_email="customer@example.com",
                subject="Test Subject",
                body="Test Body",
                pdf_attachments=[temp_path]
            )
            
            # Verify success
            self.assertTrue(success)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@example.com", "password")
            mock_server.send_message.assert_called_once()
            
        finally:
            # Cleanup
            os.unlink(temp_path)


class TestStatusPageProcessor(unittest.TestCase):
    """Test main processor functionality."""
    
    def setUp(self):
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
        
        config = {
            "webfleet": {
                "api_key": "test_key",
                "account": "test_account"
            },
            "email": {
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "password"
            },
            "temp_dir": self.temp_dir
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f)
    
    def tearDown(self):
        # Cleanup temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_processor_initialization(self):
        """Test processor initialization with config file."""
        processor = status_page.StatusPageProcessor(config_path=self.config_path)
        
        # Verify components are initialized
        self.assertIsNotNone(processor.webfleet_client)
        self.assertIsNotNone(processor.pdf_manager)
        self.assertIsNotNone(processor.email_sender)
    
    def test_default_email_body_generation(self):
        """Test default email body generation."""
        processor = status_page.StatusPageProcessor(config_path=self.config_path)
        
        body = processor._generate_default_email_body('ORDER123', 3)
        
        # Verify content
        self.assertIn('ORDER123', body)
        self.assertIn('3 additional', body)
        self.assertIn('Dear Customer', body)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""
    
    def test_complete_order_processing_workflow(self):
        """Test complete order processing workflow."""
        # Create temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
            json.dump({
                "webfleet": {"api_key": "test", "account": "test"},
                "email": {"smtp_server": "test", "smtp_port": 587, "username": "test", "password": "test"}
            }, config_file)
            config_path = config_file.name
        
        try:
            # Create processor
            processor = status_page.StatusPageProcessor(config_path=config_path)
            
            # This test verifies the processor can be created and basic structure is in place
            # More detailed integration testing would require actual API credentials
            self.assertIsNotNone(processor.webfleet_client)
            self.assertIsNotNone(processor.pdf_manager)
            self.assertIsNotNone(processor.email_sender)
            
        finally:
            # Cleanup
            os.unlink(config_path)


def run_tests():
    """Run all tests and return results."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestWebfleetAPIClient,
        TestPDFAttachmentManager,
        TestEmailSender,
        TestStatusPageProcessor,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Running RUC Reminders Status Page Tests...")
    print("=" * 50)
    
    success = run_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("All tests passed! ✅")
    else:
        print("Some tests failed! ❌")
    
    exit(0 if success else 1)