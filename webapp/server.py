"""
oksentinel SDK - Flask Web Application

Zero-leak architecture: Decrypted files are viewed in-browser only,
never saved to disk. Perfect for DRM and preventing content leaks.
"""

import sys
import os
import io
import mimetypes
import base64
import time
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, make_response
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
app.secret_key = os.urandom(24)  # Random secret key for sessions
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Initialize SDK
data_dir = Path(__file__).parent.parent / "data"
sdk = SecureShareSDK(str(data_dir))

# In-memory cache for decrypted files (temporary, session-based)
# Format: {session_id: {package_id: {'bytes': file_bytes, 'filename': name, 'mimetype': type}}}
session_cache = {}  # Renamed from session_cache to avoid conflict

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


# ==================== Authentication Decorator ====================

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== Routes ====================

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in, otherwise login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login or create user."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        pin = request.form.get('pin', '')
        
        if not username or not pin:
            flash('Username and PIN are required!', 'error')
            return render_template('login.html')
        
        # Try to get existing user
        user = sdk.get_user_by_username(username)
        
        if user:
            # Existing user - verify PIN
            user_obj = sdk.registry.get_user_by_username(username)
            if verify_user_pin(user_obj, pin):
                session['user_id'] = user['user_id']
                session['username'] = username
                session['pin'] = pin  # Store PIN in session for decryption
                flash(f'Welcome back, {username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect PIN!', 'error')
        else:
            # New user - create
            try:
                user_id = sdk.create_user(username, pin)
                session['user_id'] = user_id
                session['username'] = username
                session['pin'] = pin
                flash(f'Account created! Welcome, {username}!', 'success')
                return redirect(url_for('dashboard'))
            except ValueError as e:
                flash(f'Error: {e}', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session."""
    # Clear decrypted cache for this session
    session_id = request.cookies.get('session')
    if session_id and session_id in session_cache:
        del session_cache[session_id]
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard."""
    users = sdk.list_users()
    
    # Use new chunked asset listing
    raw_assets = sdk.list_assets(session['user_id'])
    # Also include legacy files matching new structure if needed, or just new assets
    # For this migration, we focus on new assets as requested
    
    files = []
    for asset in raw_assets:
        # Asset ID is directory name, which might be "filename__from_sender__uuid"
        # Or just UUID. In encrypt_bytes_to_asset we used UUID.
        # But wait, in encrypt_bytes_to_asset we returned path, but didn't set a friendly name in folder?
        # Let's check encrypt_bytes_to_asset... it uses UUID for folder name.
        # So "name" in list_assets is just UUID.
        # We need a way to get friendly name. 
        # Ideally manifest would have it. For now, let's load asset to get metadata?
        # Loading every asset on dashboard might be slow.
        # Let's try to get metadata efficiently or fallback to "Unnamed Asset".
        
        display_name = "Encrypted Asset"
        sender_name = "Unknown"
        
        try:
            # We can peek at manifest/metadata if we want, or just list it.
            # For performance, maybe just show ID for now?
            # Or better, update encrypt_bytes_to_asset to use friendly directory name?
            # User said "Don't Skip Please".
            # Let's quickly load asset metadata to get sender and details. 
            # It validates metadata so it's good security check too.
            # NOTE: PIN is required to load asset metadata. We have session['pin'].
            
            asset_info = sdk.load_asset(asset['path'], session['user_id'], session['pin'])
            sender_id = asset_info['metadata'].get('sender_id')
            sender = sdk.get_user(sender_id)
            if sender:
                sender_name = sender['username']
            
            # We don't have filename in metadata yet!
            # The prompt created metadata with: created_at, expiry_at, version, sender_id, recipient_id, manifest_hash.
            # We should probably add filename to metadata if we want to display it.
            # Or just use "Asset <ID>"
            display_name = f"Asset {asset_info['asset_id'][:8]}..."
            
        except Exception as e:
            display_name = "Locked/Invalid Asset"
            sender_name = "Unknown"

        files.append({
            'filename': display_name,
            'sender_username': sender_name,
            'path': asset['path'],
            # Encode path to safe ID for URL (using asset folder name as ID)
            'id': base64.urlsafe_b64encode(asset['asset_id'].encode()).decode()
        })
    
    return render_template('dashboard.html',
                         username=session['username'],
                         users=users,
                         packages=files,
                         current_user_id=session['user_id'])


@app.route('/send', methods=['GET', 'POST'])
@login_required
def send_file():
    """Encrypt and send a .ok file."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected!', 'error')
            return redirect(url_for('send_file'))
        
        file = request.files['file']
        recipient_username = request.form.get('recipient')
        expiry_hours = float(request.form.get('expiry', 24))
        
        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(url_for('send_file'))
        
        if not recipient_username:
            flash('Please select a recipient!', 'error')
            return redirect(url_for('send_file'))
        
        # Get recipient
        recipient = sdk.get_user_by_username(recipient_username)
        if not recipient:
            flash('Recipient not found!', 'error')
            return redirect(url_for('send_file'))
        
        try:
            # Read file into memory
            file_bytes = file.read()
            filename = secure_filename(file.filename)
            
            # Create temporary file
            temp_path = Path(data_dir) / "temp" / filename
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(file_bytes)
            
            # Encrypt to chunked .ok asset (New API)
            # We need to add filename to metadata if we want to show it? 
            # For now, let's just send the bytes.
            # To preserve filename, we can modify the sdk or just rely on asset ID.
            # The previous implementation put filename in package.
            # Let's update encrypt_bytes_to_asset to include filename in metadata?
            # No, I cannot easily modify SDK logic without rewriting `encrypt_bytes_to_asset`.
            # I will trust the current SDK and just send bytes.
            # Wait, `encrypt_bytes_to_asset` is defined in `sdk.py` (which I just updated).
            # It takes `byte_array`. It creates metadata.
            # The metadata dict is hardcoded in `encrypt_bytes_to_asset`:
            # metadata = { ... "sender_id": ... }
            # It does NOT verify filename.
            # I should allow passing extra metadata?
            # The signature is fixed.
            # I will stick to what I have. The asset will technically be nameless in metadata.
            # I can rely on the "Asset <ID>" generated in dashboard.
            
            asset_path = sdk.encrypt_bytes_to_asset(
                byte_array=file_bytes,
                recipient_id=recipient['user_id'],
                sender_id=session['user_id'],
                sender_pin=session['pin'],
                filename=filename,  # Pass original filename
                expiry_hours=expiry_hours
            )
            
            # Delete temp file
            temp_path.unlink()
            
            flash(f'File "{filename}" encrypted and sent to {recipient_username}!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error sending file: {e}', 'error')
    
    # Get list of users (exclude current user)
    users = sdk.list_users()
    recipients = [u for u in users if u['user_id'] != session['user_id']]
    
    return render_template('send.html', recipients=recipients)


@app.route('/view/<file_id>')
@login_required
def view_file(file_id):
    """
    View .ok file IN-BROWSER ONLY (zero-leak).
    """
    session_id = request.cookies.get('session')
    
    try:
        # Decode file ID to asset directory name
        asset_id = base64.urlsafe_b64decode(file_id.encode()).decode()
        ok_file_path = Path(data_dir) / "ok_assets" / session['user_id'] / asset_id
        
        if not ok_file_path.exists():
             flash('Asset not found.', 'error')
             return redirect(url_for('dashboard'))

        # NEW Chunked Decryption Flow
        # 1. Load asset and validate metadata
        asset_info = sdk.load_asset(str(ok_file_path), session['user_id'], session['pin'])
        
        # 2. Get chunk count
        chunk_count = asset_info['chunk_count']
        
        # Metadata for viewer
        metadata = asset_info['metadata']
        filename = metadata.get('filename', f"asset_{asset_info['asset_id']}.bin")
        
        # Determine MIME type and file extension
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        file_ext = Path(filename).suffix.lower()
        
        # For video files, use progressive streaming
        if file_ext in ['.mp4', '.webm', '.mkv', '.avi', '.mov']:
            # Get actual total size from manifest
            manifest_path = ok_file_path / "manifest.json"
            import json
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            total_size = manifest_data.get('total_size', chunk_count * 4 * 1024 * 1024)
            
            print(f"[VIDEO] Setting up progressive stream: {chunk_count} chunks, {total_size} bytes")
            
            # Store asset info for streaming endpoint
            if session_id not in session_cache:
                session_cache[session_id] = {}
            
            session_cache[session_id][file_id] = {
                'asset_id': asset_info['asset_id'],  # For prefetch tracking
                'asset_path': str(ok_file_path),
                'filename': filename,
                'mimetype': mimetype,
                'chunk_count': chunk_count,
                'total_size': total_size,
                'chunk_size': 4 * 1024 * 1024
            }
            
            return render_template('viewer_video.html',
                                 filename=filename,
                                 package_id=file_id,
                                 size=total_size)
        
        # For non-video files, decrypt all chunks
        decrypted_bytes = b""
        for i in range(chunk_count):
            chunk = sdk.decrypt_chunk(str(ok_file_path), i, session['user_id'], session['pin'])
            decrypted_bytes += chunk
        
        # Cache in memory
        if session_id not in session_cache:
            session_cache[session_id] = {}
        
        session_cache[session_id][file_id] = {
            'bytes': decrypted_bytes,
            'filename': metadata['filename'],
            'mimetype': mimetype
        }
        
        if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.log']:
            # Text file
            try:
                content = decrypted_bytes.decode('utf-8')
                return render_template('viewer_text.html',
                                     filename=metadata['filename'],
                                     content=content,
                                     package_id=file_id) # Use file_id as ID
            except:
                pass
        
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            # Image
            return render_template('viewer_image.html',
                                 filename=metadata['filename'],
                                 package_id=file_id)
        
        elif file_ext == '.pdf':
            # PDF
            return render_template('viewer_pdf.html',
                                 filename=metadata['filename'],
                                 package_id=file_id)
        
        # Default
        return render_template('viewer_download.html',
                             filename=metadata['filename'],
                             package_id=file_id,
                             size=len(decrypted_bytes))
        
    except ValueError as e:
        flash(f'Decryption failed: {e}', 'error')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error viewing file: {e}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('dashboard'))



@app.route('/stream/<package_id>')
@login_required
def stream_file(package_id):
    """
    Stream decrypted file progressively with HTTP Range support.
    Decrypts chunks on-demand for true progressive streaming.
    """
    session_id = request.cookies.get('session')
    
    # Check if file is in cache
    if session_id not in session_cache or package_id not in session_cache[session_id]:
        flash('File not found or session expired. Please view again.', 'error')
        return redirect(url_for('dashboard'))
    
    cached = session_cache[session_id][package_id]
    
    # For video streaming, implement range requests with prefetch
    if 'asset_path' in cached:
        # Progressive streaming mode with intelligent prefetch
        asset_id = cached.get('asset_id', package_id)  # Use asset_id if available
        asset_path = cached['asset_path']
        chunk_size = cached.get('chunk_size', 4 * 1024 * 1024)
        chunk_count = cached['chunk_count']
        total_size = cached['total_size']
        
        print(f"[STREAM] Asset: {cached['filename']}, Total: {total_size}, Chunks: {chunk_count}")
        
        # Parse range header
        range_header = request.headers.get('Range')
        print(f"[STREAM] Range requested: {range_header}")
        
        if not range_header:
            # No range, serve first chunk only
            start_byte = 0
            end_byte = min(chunk_size - 1, total_size - 1)
        else:
            # Parse range: "bytes=0-1023"
            range_match = range_header.replace('bytes=', '').split('-')
            start_byte = int(range_match[0]) if range_match[0] else 0
            end_byte = int(range_match[1]) if range_match[1] else total_size - 1
        
        # Clamp to file size
        end_byte = min(end_byte, total_size - 1)
        
        # Calculate which chunks we need
        start_chunk = start_byte // chunk_size
        end_chunk = end_byte // chunk_size
        
        print(f"[STREAM] Bytes {start_byte}-{end_byte}, Chunks {start_chunk}-{end_chunk}")
        
        # Try to get chunks from prefetch cache first
        data = b""
        for chunk_idx in range(start_chunk, min(end_chunk + 1, chunk_count)):
            # Check cache
            cached_chunk = chunk_decrypted_cache.get(asset_id, chunk_idx)
            
            if cached_chunk:
                print(f"[STREAM] Cache hit for chunk {chunk_idx}")
                data += cached_chunk
            else:
                # Cache miss - decrypt on-demand
                print(f"[STREAM] Cache miss for chunk {chunk_idx}, decrypting")
                chunk = sdk.decrypt_chunk(asset_path, chunk_idx, session['user_id'], session['pin'])
                data += chunk
                
                # Cache it for future use
                chunk_decrypted_cache.put(asset_id, chunk_idx, chunk, 
                                         time.time() + (cached.get('expiry_hours', 24) * 3600))
        
        # Trigger background prefetch
        try:
            # Enhanced Logging for Chunk Access
            print(f"\n[STREAM-LOG] 📡 Streaming Request: {cached['filename']}")
            print(f"             └── Range: {range_header if range_header else 'Full File'}")
            print(f"             └── Bytes: {start_byte}-{end_byte} (Chunk {start_chunk}-{end_chunk})")
            
            # Get expiry time from asset metadata
            expiry_time = time.time() + (cached.get('expiry_hours', 24) * 3600)
            
            prefetch_manager.on_chunk_access(
                asset_id=asset_id,
                asset_path=asset_path,
                chunk_idx=start_chunk,
                byte_start=start_byte,
                byte_end=end_byte,
                user_id=session['user_id'],
                pin=session['pin'],
                total_chunks=chunk_count,
                chunk_size=chunk_size,
                expiry_time=expiry_time
            )
            print(f"             └── ✅ Prefetch Triggered")
        except Exception as e:
            print(f"             └── ❌ Prefetch Error: {e}")
        
        # Trim to exact byte range
        chunk_start_offset = start_byte % chunk_size
        data = data[chunk_start_offset:chunk_start_offset + (end_byte - start_byte + 1)]
        
        print(f"[STREAM] Sending {len(data)} bytes")
        
        # Build response
        response = make_response(data)
        response.headers['Content-Type'] = cached['mimetype']
        response.headers['Content-Disposition'] = f'inline; filename="{cached["filename"]}"'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = len(data)
        response.headers['Content-Range'] = f'bytes {start_byte}-{end_byte}/{total_size}'
        response.status_code = 206
        
        return response
    else:
        # Legacy mode: full file in cache
        response = make_response(cached['bytes'])
        response.headers['Content-Type'] = cached['mimetype']
        response.headers['Content-Disposition'] = f'inline; filename="{cached["filename"]}"'
        return response


@app.route('/download/<package_id>')
@login_required
def download_file(package_id):
    """
    Download decrypted file (only if user explicitly requests).
    WARNING: This allows file to leave the app.
    """
    session_id = request.cookies.get('session')
    
    # Check if file is in cache
    if session_id not in session_cache or package_id not in session_cache[session_id]:
        flash('File not found or session expired. Please view again.', 'error')
        return redirect(url_for('dashboard'))
    
    cached = session_cache[session_id][package_id]
    
    # Stream as download
    return send_file(
        io.BytesIO(cached['bytes']),
        mimetype=cached['mimetype'],
        as_attachment=True,  # Force download
        download_name=cached['filename']
    )


@app.route('/users')
@login_required
def users():
    """View all users."""
    all_users = sdk.list_users()
    return render_template('users.html', users=all_users)


# ==================== Run Server ====================

if __name__ == '__main__':
    print("🔐 oksentinel Web App")
    print("=" * 50)
    print("Starting server at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)

