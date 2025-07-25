#!/usr/bin/env python3
"""
Demo script for Status Page.py functionality.

This script demonstrates the RUC Reminders order processing system
with mock data and simulated API responses.
"""

import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("status_page", "Status Page.py")
status_page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status_page)


def create_demo_pdf(filename: str) -> Path:
    """Create a demo PDF file for testing."""
    content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
({filename}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000100 00000 n 
0000000178 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
223
%%EOF"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
    temp_file.write(content)
    temp_file.close()
    
    return Path(temp_file.name)


def demo_webfleet_api():
    """Demonstrate Webfleet API client functionality."""
    print("🔌 Demo: Webfleet API Client")
    print("-" * 40)
    
    # Create client
    client = status_page.WebfleetAPIClient(
        api_key="demo_api_key",
        account="demo_account"
    )
    
    print(f"✅ Client initialized with account: {client.account}")
    
    # Mock API responses
    with patch.object(client, '_make_request') as mock_request:
        # Mock attachment list response
        mock_response_list = Mock()
        mock_response_list.json.return_value = {
            'attachments': [
                {'attachmentid': 'ATT001', 'filename': 'proof_of_delivery.pdf'},
                {'attachmentid': 'ATT002', 'filename': 'delivery_receipt.pdf'},
                {'attachmentid': 'ATT003', 'filename': 'customer_signature.pdf'}
            ]
        }
        
        # Mock download responses
        demo_pdf_content = b'%PDF-1.4\nDemo PDF content for proof of delivery'
        mock_response_download = Mock()
        mock_response_download.content = demo_pdf_content
        
        # Set up mock to return different responses based on endpoint
        def mock_request_side_effect(endpoint, params):
            if endpoint == 'showOrderAttachmentListExtern':
                return mock_response_list
            elif endpoint == 'downloadOrderAttachment':
                return mock_response_download
        
        mock_request.side_effect = mock_request_side_effect
        
        # Test listing attachments
        attachments = client.show_order_attachment_list('ORDER123')
        print(f"📎 Found {len(attachments)} attachments for ORDER123:")
        for att in attachments:
            print(f"   - {att['filename']} (ID: {att['attachmentid']})")
        
        # Test downloading attachment
        content = client.download_order_attachment('ATT001', 'ORDER123')
        print(f"⬇️  Downloaded attachment: {len(content)} bytes")


def demo_pdf_manager():
    """Demonstrate PDF attachment manager functionality."""
    print("\n📄 Demo: PDF Attachment Manager")
    print("-" * 40)
    
    # Create manager with temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = status_page.PDFAttachmentManager(temp_dir=temp_dir)
        print(f"📁 Temp directory: {temp_dir}")
        
        # Test PDF content detection
        pdf_content = b'%PDF-1.4\nTest PDF content'
        non_pdf_content = b'This is not a PDF file'
        
        print(f"🔍 PDF detection - PDF content: {manager.is_pdf_content(pdf_content)}")
        print(f"🔍 PDF detection - Non-PDF content: {manager.is_pdf_content(non_pdf_content)}")
        
        # Test file saving
        saved_path = manager.save_attachment(pdf_content, 'test_document.pdf', 'ORDER123')
        print(f"💾 Saved attachment to: {saved_path}")
        
        # Test safe filename generation
        unsafe_filename = 'doc<>ument?.pdf'
        safe_filename = manager._generate_safe_filename(unsafe_filename)
        print(f"🔒 Safe filename: '{unsafe_filename}' → '{safe_filename}'")


def demo_email_sender():
    """Demonstrate email sender functionality."""
    print("\n📧 Demo: Email Sender")
    print("-" * 40)
    
    # Create sender
    sender = status_page.EmailSender(
        smtp_server="smtp.demo.com",
        smtp_port=587,
        username="demo@example.com",
        password="demo_password"
    )
    
    print(f"📮 Email sender configured for: {sender.username}")
    
    # Create demo PDF files
    pdf1 = create_demo_pdf("Proof of Delivery")
    pdf2 = create_demo_pdf("Customer Receipt")
    
    try:
        # Mock SMTP to avoid actually sending emails
        with patch('smtplib.SMTP') as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_class.return_value.__enter__.return_value = mock_server
            
            # Test email sending
            success = sender.send_email(
                to_email="customer@example.com",
                subject="Order ORDER123 - Documentation Package",
                body="Dear Customer,\n\nPlease find attached your order documentation.\n\nBest regards,\nRUC Team",
                pdf_attachments=[pdf1, pdf2]
            )
            
            print(f"📤 Email sending result: {'Success' if success else 'Failed'}")
            print(f"🔗 Mock SMTP calls:")
            print(f"   - starttls(): {mock_server.starttls.called}")
            print(f"   - login(): {mock_server.login.called}")
            print(f"   - send_message(): {mock_server.send_message.called}")
    
    finally:
        # Cleanup demo files
        os.unlink(pdf1)
        os.unlink(pdf2)


def demo_complete_workflow():
    """Demonstrate complete order processing workflow."""
    print("\n🔄 Demo: Complete Workflow")
    print("-" * 40)
    
    # Create demo config
    config = {
        "webfleet": {
            "api_key": "demo_api_key",
            "account": "demo_account"
        },
        "email": {
            "smtp_server": "smtp.demo.com",
            "smtp_port": 587,
            "username": "demo@example.com",
            "password": "demo_password"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
        json.dump(config, config_file)
        config_path = config_file.name
    
    try:
        # Create processor
        processor = status_page.StatusPageProcessor(config_path=config_path)
        print("⚙️  Status Page Processor initialized")
        
        # Create demo standard PDF
        standard_pdf = create_demo_pdf("Standard Company Document")
        processor.standard_pdf_path = standard_pdf
        
        print(f"📋 Standard PDF: {standard_pdf}")
        
        # Mock the entire workflow
        with patch.object(processor.webfleet_client, 'show_order_attachment_list') as mock_list, \
             patch.object(processor.webfleet_client, 'download_order_attachment') as mock_download, \
             patch.object(processor.email_sender, 'send_email') as mock_send:
            
            # Setup mocks
            mock_list.return_value = [
                {'attachmentid': 'ATT001', 'filename': 'delivery_proof.pdf'},
                {'attachmentid': 'ATT002', 'filename': 'customer_signature.pdf'}
            ]
            
            mock_download.return_value = b'%PDF-1.4\nDemo PDF content'
            mock_send.return_value = True
            
            # Process order
            success = processor.process_order(
                order_id='ORDER123',
                customer_email='customer@example.com'
            )
            
            print(f"🎯 Order processing result: {'Success' if success else 'Failed'}")
            
            # Verify workflow steps
            print("📊 Workflow verification:")
            print(f"   - Listed attachments: {mock_list.called}")
            print(f"   - Downloaded attachments: {mock_download.call_count} times")
            print(f"   - Sent email: {mock_send.called}")
            
            if mock_send.called:
                call_args = mock_send.call_args
                print(f"   - Email recipient: {call_args[1]['to_email']}")
                print(f"   - Attachments count: {len(call_args[1]['pdf_attachments'])}")
        
        # Clean up
        os.unlink(standard_pdf)
    
    finally:
        os.unlink(config_path)


def demo_multiple_orders():
    """Demonstrate processing multiple orders."""
    print("\n🔢 Demo: Multiple Orders Processing")
    print("-" * 40)
    
    # Create demo config
    config = {
        "webfleet": {"api_key": "demo", "account": "demo"},
        "email": {"smtp_server": "demo", "smtp_port": 587, "username": "demo", "password": "demo"}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
        json.dump(config, config_file)
        config_path = config_file.name
    
    try:
        processor = status_page.StatusPageProcessor(config_path=config_path)
        
        # Mock the process_order method to simulate different outcomes
        with patch.object(processor, 'process_order') as mock_process:
            # Simulate different success/failure scenarios
            def mock_process_side_effect(order_id, customer_email, **kwargs):
                if order_id == 'ORDER123':
                    return True  # Success
                elif order_id == 'ORDER124':
                    return True  # Success
                elif order_id == 'ORDER125':
                    return False  # Failure
                return True
            
            mock_process.side_effect = mock_process_side_effect
            
            # Test multiple orders
            orders = [
                {'order_id': 'ORDER123', 'customer_email': 'customer1@example.com'},
                {'order_id': 'ORDER124', 'customer_email': 'customer2@example.com'},
                {'order_id': 'ORDER125', 'customer_email': 'customer3@example.com'}
            ]
            
            results = processor.process_multiple_orders(orders)
            
            print("📋 Batch processing results:")
            for order_id, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"   - {order_id}: {status}")
            
            success_count = sum(results.values())
            total_count = len(results)
            print(f"📊 Summary: {success_count}/{total_count} orders processed successfully")
    
    finally:
        os.unlink(config_path)


def main():
    """Run all demonstrations."""
    print("🚀 RUC Reminders Status Page System Demo")
    print("=" * 60)
    print("This demo shows the functionality of the order processing system")
    print("with mock data and simulated API responses.\n")
    
    try:
        demo_webfleet_api()
        demo_pdf_manager()
        demo_email_sender()
        demo_complete_workflow()
        demo_multiple_orders()
        
        print("\n" + "=" * 60)
        print("🎉 Demo completed successfully!")
        print("📝 Next steps:")
        print("   1. Configure actual API credentials in config.json")
        print("   2. Set up SMTP email settings")
        print("   3. Test with real Webfleet orders")
        print("   4. Integrate into your order processing workflow")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()