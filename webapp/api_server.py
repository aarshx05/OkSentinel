"""
OkSentinel Mobile API Server
Flask API with CORS support for Flutter mobile app integration
"""

import sys
import os
import io
import mimetypes
import base64
import time
import json
from pathlib import Path
from flask import Flask, request, jsonify, make_response, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from functools import wraps

# Add parent directory to path to import oksentinel
sys.path.insert(0, str(Path(__file__).parent.parent))

from oksentinel import SecureShareSDK
from oksentinel.identity import verify_user_pin

# Import prefetch components
from webapp.chunk_cache import DecryptedChunkCache, EncryptedChunkCache
from webapp.prefetch_manager import PrefetchManager

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Enable CORS for mobile app
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Session-Token"],
        "expose_headers": ["Content-Range", "Accept-Ranges"]
    }
})

# Initialize SDK
data_dir = Path(__file__).parent.parent / "data"
sdk = SecureShareSDK(str(data_dir))

# Session storage (in production, use Redis or similar)
# Format: {session_token: {user_id, username, pin, created_at}}
sessions = {}

# In-memory cache for decrypted files
session_cache = {}

# Prefetch caches and manager
chunk_decrypted_cache = DecryptedChunkCache(max_size=10)
chunk_encrypted_cache = EncryptedChunkCache(max_size=30)
prefetch_manager = PrefetchManager(
    sdk=sdk,
    decrypted_cache=chunk_decrypted_cache,
    encrypted_cache=chunk_encrypted_cache,
    short_range_window=3,
    long_range_window=10,
    worker_threads=2
)

# ==================== Authentication Helpers ====================

def generate_session_token():
    """Generate a random session token."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

def token_required(f):
    """Decorator to require authentication token for API routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Session-Token')
        
        if not token or token not in sessions:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        
        # Add session data to request context
        request.session_data = sessions[token]
        return f(*args, **kwargs)
    return decorated_function

# ==================== API Routes ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': time.time()
    })

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    Login or create user account.
    
    Request: {username, pin}
    Response: {success, token, user_id, username, message}
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    pin = data.get('pin', '')
    
    if not username or not pin:
        return jsonify({'error': 'Username and PIN are required', 'code': 'INVALID_INPUT'}), 400
    
    # Try to get existing user
    user = sdk.get_user_by_username(username)
    
    if user:
        # Existing user - verify PIN
        user_obj = sdk.registry.get_user_by_username(username)
        if verify_user_pin(user_obj, pin):
            # Create session
            token = generate_session_token()
            sessions[token] = {
                'user_id': user['user_id'],
                'username': username,
                'pin': pin,
                'created_at': time.time()
            }
            
            return jsonify({
                'success': True,
                'token': token,
                'user_id': user['user_id'],
                'username': username,
                'message': f'Welcome back, {username}!'
            })
        else:
            return jsonify({'error': 'Incorrect PIN', 'code': 'INVALID_PIN'}), 401
    else:
        # New user - create account
        try:
            user_id = sdk.create_user(username, pin)
            
            # Create session
            token = generate_session_token()
            sessions[token] = {
                'user_id': user_id,
                'username': username,
                'pin': pin,
                'created_at': time.time()
            }
            
            return jsonify({
                'success': True,
                'token': token,
                'user_id': user_id,
                'username': username,
                'message': f'Account created! Welcome, {username}!'
            }), 201
        except ValueError as e:
            return jsonify({'error': str(e), 'code': 'CREATE_FAILED'}), 400

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def api_logout():
    """Logout and invalidate session."""
    token = request.headers.get('X-Session-Token')
    
    # Clear session cache
    if token in session_cache:
        del session_cache[token]
    
    # Remove session
    if token in sessions:
        del sessions[token]
    
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/dashboard', methods=['GET'])
@token_required
def api_dashboard():
    """
    Get dashboard data including received files and stats.
    
    Response: {
        username, 
        user_id,
        files: [{id, filename, sender_username, asset_id, created_at}],
        stats: {total_files, total_users}
    }
    """
    session_data = request.session_data
    
    # Get users list
    users = sdk.list_users()
    
    # Get assets
    raw_assets = sdk.list_assets(session_data['user_id'])
    
    files = []
    for asset in raw_assets:
        display_name = "Encrypted Asset"
        sender_name = "Unknown"
        created_at = None
        
        try:
            asset_info = sdk.load_asset(asset['path'], session_data['user_id'], session_data['pin'])
            sender_id = asset_info['metadata'].get('sender_id')
            sender = sdk.get_user(sender_id)
            if sender:
                sender_name = sender['username']
            
            # Get filename from metadata
            display_name = asset_info['metadata'].get('filename', f"Asset {asset_info['asset_id'][:8]}...")
            created_at = asset_info['metadata'].get('created_at')
            
        except Exception as e:
            display_name = "Locked/Invalid Asset"
            sender_name = "Unknown"
        
        files.append({
            'id': base64.urlsafe_b64encode(asset['asset_id'].encode()).decode(),
            'filename': display_name,
            'sender_username': sender_name,
            'asset_id': asset['asset_id'],
            'created_at': created_at
        })
    
    return jsonify({
        'username': session_data['username'],
        'user_id': session_data['user_id'],
        'files': files,
        'stats': {
            'total_files': len(files),
            'total_users': len(users)
        }
    })

@app.route('/api/users', methods=['GET'])
@token_required
def api_users():
    """
    Get list of all users (for recipient selection).
    
    Response: {users: [{user_id, username}]}
    """
    session_data = request.session_data
    users = sdk.list_users()
    
    # Exclude current user
    recipients = [
        {'user_id': u['user_id'], 'username': u['username']} 
        for u in users if u['user_id'] != session_data['user_id']
    ]
    
    return jsonify({'users': recipients})

@app.route('/api/send', methods=['POST'])
@token_required
def api_send_file():
    """
    Encrypt and send a file to a recipient.
    
    Multipart form data:
    - file: file upload
    - recipient_id: recipient user ID
    - expiry_hours: expiration time (default 24)
    
    Response: {success, message, asset_id}
    """
    session_data = request.session_data
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided', 'code': 'NO_FILE'}), 400
    
    file = request.files['file']
    recipient_id = request.form.get('recipient_id')
    expiry_hours = float(request.form.get('expiry_hours', 24))
    
    if file.filename == '':
        return jsonify({'error': 'No file selected', 'code': 'EMPTY_FILE'}), 400
    
    if not recipient_id:
        return jsonify({'error': 'Recipient required', 'code': 'NO_RECIPIENT'}), 400
    
    # Verify recipient exists
    recipient = sdk.get_user(recipient_id)
    if not recipient:
        return jsonify({'error': 'Recipient not found', 'code': 'INVALID_RECIPIENT'}), 404
    
    try:
        # Read file
        file_bytes = file.read()
        filename = secure_filename(file.filename)
        
        # Encrypt to asset
        asset_path = sdk.encrypt_bytes_to_asset(
            byte_array=file_bytes,
            recipient_id=recipient_id,
            sender_id=session_data['user_id'],
            sender_pin=session_data['pin'],
            filename=filename,
            expiry_hours=expiry_hours
        )
        
        # Extract asset ID from path
        asset_id = Path(asset_path).name
        
        return jsonify({
            'success': True,
            'message': f'File "{filename}" sent to {recipient["username"]}',
            'asset_id': asset_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Encryption failed: {str(e)}', 'code': 'ENCRYPT_FAILED'}), 500

@app.route('/api/file/<file_id>/info', methods=['GET'])
@token_required
def api_file_info(file_id):
    """
    Get file metadata without downloading.
    
    Response: {filename, mimetype, size, chunk_count, sender, created_at}
    """
    session_data = request.session_data
    
    try:
        # Decode file ID
        asset_id = base64.urlsafe_b64decode(file_id.encode()).decode()
        asset_path = Path(data_dir) / "ok_assets" / session_data['user_id'] / asset_id
        
        if not asset_path.exists():
            return jsonify({'error': 'File not found', 'code': 'NOT_FOUND'}), 404
        
        # Load asset metadata
        asset_info = sdk.load_asset(str(asset_path), session_data['user_id'], session_data['pin'])
        
        metadata = asset_info['metadata']
        filename = metadata.get('filename', f"asset_{asset_info['asset_id']}.bin")
        
        # Get sender info
        sender_id = metadata.get('sender_id')
        sender = sdk.get_user(sender_id)
        sender_name = sender['username'] if sender else 'Unknown'
        
        # Get size from manifest
        manifest_path = asset_path / "manifest.json"
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        total_size = manifest_data.get('total_size', 0)
        
        # Determine MIME type
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        return jsonify({
            'filename': filename,
            'mimetype': mimetype,
            'size': total_size,
            'chunk_count': asset_info['chunk_count'],
            'sender': sender_name,
            'created_at': metadata.get('created_at'),
            'expiry_at': metadata.get('expiry_at')
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to load file info: {str(e)}', 'code': 'LOAD_FAILED'}), 500

@app.route('/api/stream/<file_id>', methods=['GET'])
@token_required
def api_stream_file(file_id):
    """
    Stream file with progressive chunk decryption and HTTP Range support.
    Supports video streaming with intelligent prefetch.
    """
    session_data = request.session_data
    token = request.headers.get('X-Session-Token')
    
    try:
        # Decode file ID
        asset_id = base64.urlsafe_b64decode(file_id.encode()).decode()
        asset_path = Path(data_dir) / "ok_assets" / session_data['user_id'] / asset_id
        
        if not asset_path.exists():
            return jsonify({'error': 'File not found', 'code': 'NOT_FOUND'}), 404
        
        # Load asset if not in cache
        if token not in session_cache or file_id not in session_cache[token]:
            asset_info = sdk.load_asset(str(asset_path), session_data['user_id'], session_data['pin'])
            
            metadata = asset_info['metadata']
            filename = metadata.get('filename', f"asset_{asset_id}.bin")
            
            # Get size from manifest
            manifest_path = asset_path / "manifest.json"
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            total_size = manifest_data.get('total_size', 0)
            
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            
            # Cache asset info
            if token not in session_cache:
                session_cache[token] = {}
            
            session_cache[token][file_id] = {
                'asset_id': asset_id,
                'asset_path': str(asset_path),
                'filename': filename,
                'mimetype': mimetype,
                'chunk_count': asset_info['chunk_count'],
                'total_size': total_size,
                'chunk_size': 4 * 1024 * 1024,
                'expiry_hours': 24
            }
        
        cached = session_cache[token][file_id]
        
        # Handle range requests for progressive streaming
        chunk_size = cached['chunk_size']
        chunk_count = cached['chunk_count']
        total_size = cached['total_size']
        
        # Parse range header
        range_header = request.headers.get('Range')
        
        if not range_header:
            start_byte = 0
            end_byte = min(chunk_size - 1, total_size - 1)
        else:
            range_match = range_header.replace('bytes=', '').split('-')
            start_byte = int(range_match[0]) if range_match[0] else 0
            end_byte = int(range_match[1]) if range_match[1] else total_size - 1
        
        end_byte = min(end_byte, total_size - 1)
        
        # Calculate chunks needed
        start_chunk = start_byte // chunk_size
        end_chunk = end_byte // chunk_size
        
        # Decrypt chunks
        data = b""
        for chunk_idx in range(start_chunk, min(end_chunk + 1, chunk_count)):
            # Try cache first
            cached_chunk = chunk_decrypted_cache.get(asset_id, chunk_idx)
            
            if cached_chunk:
                data += cached_chunk
            else:
                # Decrypt on-demand
                chunk = sdk.decrypt_chunk(cached['asset_path'], chunk_idx, 
                                        session_data['user_id'], session_data['pin'])
                data += chunk
                
                # Cache it
                chunk_decrypted_cache.put(asset_id, chunk_idx, chunk,
                                        time.time() + (cached['expiry_hours'] * 3600))
        
        # Trigger prefetch
        try:
            expiry_time = time.time() + (cached['expiry_hours'] * 3600)
            prefetch_manager.on_chunk_access(
                asset_id=asset_id,
                asset_path=cached['asset_path'],
                chunk_idx=start_chunk,
                byte_start=start_byte,
                byte_end=end_byte,
                user_id=session_data['user_id'],
                pin=session_data['pin'],
                total_chunks=chunk_count,
                chunk_size=chunk_size,
                expiry_time=expiry_time
            )
        except Exception as e:
            print(f"Prefetch error: {e}")
        
        # Trim to exact byte range
        chunk_start_offset = start_byte % chunk_size
        data = data[chunk_start_offset:chunk_start_offset + (end_byte - start_byte + 1)]
        
        # Build response
        response = make_response(data)
        response.headers['Content-Type'] = cached['mimetype']
        response.headers['Content-Disposition'] = f'inline; filename="{cached["filename"]}"'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = len(data)
        response.headers['Content-Range'] = f'bytes {start_byte}-{end_byte}/{total_size}'
        response.status_code = 206 if range_header else 200
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Stream failed: {str(e)}', 'code': 'STREAM_FAILED'}), 500

# ==================== Run Server ====================

if __name__ == '__main__':
    print("🔐 OkSentinel Mobile API Server")
    print("=" * 50)
    print("Starting server at: http://0.0.0.0:5000")
    print("API endpoints available at: /api/*")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
