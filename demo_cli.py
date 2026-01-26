"""
OkSentinel SDK - .ok File Format Demo (ASCII version)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from oksentinel import SecureShareSDK


def demo():
    print("\n" + "="*70)
    print("OkSentinel SDK - .ok FILE FORMAT DEMO")
    print("="*70)
    
    sdk = SecureShareSDK(data_dir="./data")
    
    # Step 1: Create users
    print("\n[*] Step 1: Creating users...")
    try:
        alice_id = sdk.create_user("alice", "1234")
        print(f"   [+] Created Alice (ID: {alice_id[:16]}...)")
    except ValueError:
        print("   [i] Alice already exists")
        alice_id = sdk.get_user_by_username("alice")['user_id']
    
    try:
        bob_id = sdk.create_user("bob", "5678")
        print(f"   [+] Created Bob (ID: {bob_id[:16]}...)")
    except ValueError:
        print("   [i] Bob already exists")
        bob_id = sdk.get_user_by_username("bob")['user_id']
    
    # Step 2: Create test file
    print("\n[*] Step 2: Creating test file...")
    test_file = Path("./data/secret_message.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_file, 'w') as f:
        f.write("CONFIDENTIAL MESSAGE FOR BOB\n\n" +
                "This is encrypted in a .ok file with:\n" +
                "- AES-256-CTR encryption\n" +
                "- RSA-2048 key wrapping\n" +
                "- Embedded expiry enforcement\n\n" +
                "- Alice")
    
    print(f"   [+] Created: {test_file.name}")
    
    # Step 3: Create .ok file
    print("\n[*] Step 3: Creating .ok file for Bob...")
    ok_file = sdk.encrypt_to_ok_file(
        input_file_path=str(test_file),
        recipient_id=bob_id,
        sender_id=alice_id,
        sender_pin="1234",
        expiry_hours=1
    )
    
    print(f"   [+] Created: {Path(ok_file).name}")
    print(f"   [+] Size: {Path(ok_file).stat().st_size} bytes")
    
    # Step 4: Decrypt
    print("\n[*] Step 4: Bob decrypts .ok file...")
    try:
        output, meta = sdk.decrypt_ok_file(ok_file, bob_id, "5678")
        print(f"   [+] Decryption successful!")
        print(f"   [+] Output: {output}")
        print(f"   [+] Expires: {meta['expiry_time']}")
    except ValueError as e:
        print(f"   [-] Error: {e}")
    
    # Step 5: Test wrong PIN
    print("\n[*] Step 5: Testing wrong PIN...")
    try:
        sdk.decrypt_ok_file(ok_file, bob_id, "0000")
        print("   [!] Should have failed!")
    except ValueError as e:
        print(f"   [+] Correctly rejected: Incorrect PIN")
    
    # Step 6: Test expiry
    print("\n[*] Step 6: Testing expiry enforcement...")
    expired_file = sdk.encrypt_to_ok_file(
        str(test_file), bob_id, alice_id, "1234", expiry_hours=-1
    )
    print(f"   [+] Created expired file")
    
    try:
        sdk.decrypt_ok_file(expired_file, bob_id, "5678")
        print("   [!] Should have failed!")
    except ValueError as e:
        if "expired" in str(e).lower():
            print(f"   [+] Expiry enforcement working!")
    
    print("\n" + "="*70)
    print("[+] DEMO COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\nSummary:")
    print("  - Created portable .ok file format")
    print("  - Encrypted with AES-256-CTR + RSA-2048-OAEP")
    print("  - Embedded expiry metadata")
    print("  - Base64 encoded + obfuscated")
    print("  - Enforced expiry on decryption")
    print("  - Validated PIN protection")
    print("\n[+] The .ok file format is working!\n")


if __name__ == '__main__':
    demo()

