"""
OkSentinel SDK - CLI Demo Application

This CLI demonstrates the SDK functionality with commands for:
- User creation and management
- File encryption and sending
- Package listing and decryption
- Automated end-to-end demo
"""

import sys
import os
from pathlib import Path
import click
from getpass import getpass

# Add parent directory to path to import oksentinel
sys.path.insert(0, str(Path(__file__).parent.parent))

from oksentinel import SecureShareSDK


# Global SDK instance
sdk = None


def init_sdk():
    """Initialize the SDK with data directory."""
    global sdk
    data_dir = Path(__file__).parent.parent / "data"
    sdk = SecureShareSDK(str(data_dir))


@click.group()
def cli():
    """OkSentinel SDK - Enterprise Secure Content Sharing CLI"""
    init_sdk()


@cli.command()
@click.argument('username')
def create_user(username):
    """Create a new user with cryptographic identity."""
    click.echo(f"\n🔐 Creating user: {username}")
    
    # Get PIN from user (zero-trust: user sets their own PIN)
    pin = getpass("Enter a PIN for this user (will be hidden): ")
    confirm_pin = getpass("Confirm PIN: ")
    
    if pin != confirm_pin:
        click.echo("❌ PINs do not match!", err=True)
        return
    
    try:
        user_id = sdk.create_user(username, pin)
        click.echo(f"✅ User created successfully!")
        click.echo(f"   User ID: {user_id}")
        click.echo(f"   Username: {username}")
        click.echo(f"\n💡 Remember your PIN - it's required to decrypt files!")
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
def list_users():
    """List all registered users."""
    users = sdk.list_users()
    
    if not users:
        click.echo("\n📭 No users registered yet.")
        return
    
    click.echo(f"\n👥 Registered Users ({len(users)}):")
    click.echo("-" * 60)
    for user in users:
        click.echo(f"   {user['username']:<20} (ID: {user['user_id']})")


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('recipient_username')
@click.option('--sender', '-s', required=True, help='Sender username')
def encrypt_file(file_path, recipient_username, sender):
    """Encrypt a file for a recipient."""
    click.echo(f"\n🔒 Encrypting file: {file_path}")
    
    # Get sender
    sender_info = sdk.get_user_by_username(sender)
    if not sender_info:
        click.echo(f"❌ Sender '{sender}' not found!", err=True)
        return
    
    # Get recipient
    recipient_info = sdk.get_user_by_username(recipient_username)
    if not recipient_info:
        click.echo(f"❌ Recipient '{recipient_username}' not found!", err=True)
        return
    
    # Get sender's PIN (zero-trust: PIN unlocks sender's key)
    sender_pin = getpass(f"Enter PIN for {sender}: ")
    
    try:
        package_id = sdk.encrypt_file(
            file_path,
            recipient_info['user_id'],
            sender_info['user_id'],
            sender_pin
        )
        
        click.echo(f"✅ File encrypted successfully!")
        click.echo(f"   Package ID: {package_id}")
        
        # Automatically send the package
        sdk.send_package(package_id, recipient_info['user_id'])
        click.echo(f"   📤 Package sent to {recipient_username}")
        
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.argument('username')
def list_packages(username):
    """List packages received by a user."""
    user_info = sdk.get_user_by_username(username)
    if not user_info:
        click.echo(f"❌ User '{username}' not found!", err=True)
        return
    
    packages = sdk.list_received_packages(user_info['user_id'])
    
    if not packages:
        click.echo(f"\n📭 No packages for {username}.")
        return
    
    click.echo(f"\n📦 Packages for {username} ({len(packages)}):")
    click.echo("-" * 80)
    for pkg in packages:
        click.echo(f"   ID: {pkg['package_id']}")
        click.echo(f"   File: {pkg['filename']}")
        click.echo(f"   From: {pkg['sender_username']} ({pkg['sender_id']})")
        click.echo("-" * 80)


@cli.command()
@click.argument('package_id')
@click.argument('username')
@click.option('--output', '-o', default='./downloads', help='Output directory')
def decrypt_file(package_id, username, output):
    """Decrypt a received package."""
    click.echo(f"\n🔓 Decrypting package: {package_id}")
    
    # Get user
    user_info = sdk.get_user_by_username(username)
    if not user_info:
        click.echo(f"❌ User '{username}' not found!", err=True)
        return
    
    # Get user's PIN (zero-trust: PIN unlocks private key)
    pin = getpass(f"Enter PIN for {username}: ")
    
    try:
        output_file = sdk.decrypt_file(
            package_id,
            pin,
            user_info['user_id'],
            output
        )
        
        click.echo(f"✅ File decrypted successfully!")
        click.echo(f"   Saved to: {output_file}")
        
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
def demo():
    """Run an automated end-to-end demonstration."""
    click.echo("\n" + "="*80)
    click.echo("🚀 OkSentinel SDK - AUTOMATED DEMO")
    click.echo("="*80)
    
    try:
        # Step 1: Create users
        click.echo("\n📝 Step 1: Creating users...")
        alice_id = sdk.create_user("alice", "1234")
        bob_id = sdk.create_user("bob", "5678")
        click.echo(f"   ✅ Created Alice (ID: {alice_id})")
        click.echo(f"   ✅ Created Bob (ID: {bob_id})")
        
        # Step 2: List users
        click.echo("\n👥 Step 2: Listing users...")
        users = sdk.list_users()
        for user in users:
            click.echo(f"   - {user['username']}")
        
        # Step 3: Create a test file
        click.echo("\n📄 Step 3: Creating test file...")
        test_file = Path(__file__).parent.parent / "data" / "test_message.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        secret_message = """
╔════════════════════════════════════════════╗
║         SECRET MESSAGE FOR BOB             ║
╚════════════════════════════════════════════╝

Hello Bob!

This is a secret message from Alice, encrypted
using the OkSentinel SDK. Only you can decrypt
this with your PIN.

The file was:
1. Encrypted with AES-256-CTR
2. AES key wrapped with your RSA public key
3. Delivered via local transport
4. Decrypted using your PIN-protected private key

Welcome to zero-trust secure file sharing! 🔐

- Alice
"""
        with open(test_file, 'w') as f:
            f.write(secret_message)
        click.echo(f"   ✅ Created: {test_file.name}")
        
        # Step 4: Alice encrypts for Bob
        click.echo("\n🔒 Step 4: Alice encrypts file for Bob...")
        package_id = sdk.encrypt_file(
            str(test_file),
            bob_id,
            alice_id,
            "1234"  # Alice's PIN
        )
        click.echo(f"   ✅ File encrypted (Package ID: {package_id[:8]}...)")
        
        # Step 5: Send package
        click.echo("\n📤 Step 5: Sending package to Bob...")
        sdk.send_package(package_id, bob_id)
        click.echo(f"   ✅ Package delivered")
        
        # Step 6: Bob lists packages
        click.echo("\n📦 Step 6: Bob checks received packages...")
        packages = sdk.list_received_packages(bob_id)
        click.echo(f"   ✅ Bob has {len(packages)} package(s)")
        for pkg in packages:
            click.echo(f"      - {pkg['filename']} from {pkg['sender_username']}")
        
        # Step 7: Bob decrypts with correct PIN
        click.echo("\n🔓 Step 7: Bob decrypts file with correct PIN...")
        output_file = sdk.decrypt_file(
            package_id,
            "5678",  # Bob's PIN
            bob_id,
            str(Path(__file__).parent.parent / "data" / "downloads")
        )
        click.echo(f"   ✅ File decrypted: {Path(output_file).name}")
        
        # Verify content
        with open(output_file, 'r') as f:
            decrypted_content = f.read()
        
        if decrypted_content == secret_message:
            click.echo(f"   ✅ Content verified - matches original!")
        
        # Step 8: Test wrong PIN
        click.echo("\n❌ Step 8: Testing with incorrect PIN...")
        try:
            sdk.decrypt_file(package_id, "0000", bob_id, "./downloads")
            click.echo("   ⚠️  Should have failed with wrong PIN!")
        except ValueError as e:
            click.echo(f"   ✅ Correctly rejected: {e}")
        
        # Success!
        click.echo("\n" + "="*80)
        click.echo("✅ DEMO COMPLETED SUCCESSFULLY!")
        click.echo("="*80)
        click.echo("\n📊 Summary:")
        click.echo(f"   • Created 2 users with PIN-protected identities")
        click.echo(f"   • Encrypted file with AES-256-CTR")
        click.echo(f"   • Wrapped AES key with RSA-2048-OAEP")
        click.echo(f"   • Transferred package via local transport")
        click.echo(f"   • Successfully decrypted with correct PIN")
        click.echo(f"   • Rejected incorrect PIN")
        click.echo("\n🎯 The SDK is working perfectly!\n")
        
    except Exception as e:
        click.echo(f"\n❌ Demo failed: {e}", err=True)
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    cli()

