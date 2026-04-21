
#imports

from flask import Flask, render_template, request, jsonify, session, send_file
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
import os
import base64
from datetime import datetime
import uuid
import shutil
import subprocess
import platform

#__________________________________________________________
# HUIS App
app  = Flask(__name__)
Scss(app, static_dir='static', asset_dir='static')
app.secret_key = 'your_secret_key_here_change_this'

# Use Downloads folder for storing photos
DOWNLOADS_DIR = os.path.expanduser('~/Downloads')
PHOTOS_DIR = os.path.join(DOWNLOADS_DIR, 'HUIS_Photos')

# Create photos directory in Downloads
if not os.path.exists(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR)
    print(f"Created photos directory: {PHOTOS_DIR}")

# Path to main.exe (now looks in Downloads folder)
MAIN_EXE_PATH = os.path.join(DOWNLOADS_DIR, 'main.exe')

print(f"Looking for main.exe at: {MAIN_EXE_PATH}")
if not os.path.exists(MAIN_EXE_PATH):
    print("WARNING: main.exe not found in Downloads folder!")
    print(f"Expected location: {MAIN_EXE_PATH}")
    print("Place main.exe in your Downloads folder to enable auto-launch.")
else:
    print("✓ main.exe found in Downloads folder")

def launch_main_exe():
    """Launch main.exe with proper working directory"""
    try:
        if os.path.exists(MAIN_EXE_PATH):
            exe_dir = os.path.dirname(MAIN_EXE_PATH)
            print(f"Launching main.exe: {MAIN_EXE_PATH}")
            print(f"Working directory will be: {exe_dir}")

            if platform.system() == 'Windows':
                # Use subprocess.Popen with explicit working directory so the GUI app can open independently
                subprocess.Popen([MAIN_EXE_PATH], cwd=exe_dir, shell=False)
            else:
                # For other systems, try to set working directory and start process
                subprocess.Popen([MAIN_EXE_PATH], cwd=exe_dir, shell=False)

        else:
            print(f"Warning: main.exe not found at {MAIN_EXE_PATH}")
    except Exception as e:
        print(f"Error launching main.exe: {e}")
        import traceback
        traceback.print_exc()

@app.route('/launch_app', methods=['POST'])
def launch_app():
    """Launch main.exe on demand"""
    try:
        print("\n--- Launch app request ---")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Main.exe path: {MAIN_EXE_PATH}")
        print(f"Main.exe exists: {os.path.exists(MAIN_EXE_PATH)}")

        launch_main_exe()
        return jsonify({"status": "success", "message": "Launch requested"})
    except Exception as e:
        error_msg = str(e)
        print(f"Launch failed: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route("/")
def index():
    # Generate a session ID for this user
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template("index.html")

@app.route('/process_image', methods=['POST'])
def process_image():
    # 1. Get the JSON data from the request
    data = request.get_json()

    # 2. Extract the base64 image string
    image_b64 = data.get('image')

    # Get current session ID
    session_id = session.get('session_id', 'default')

    # 3. Decode base64 and save to Downloads folder
    try:
        # Remove data URL prefix if present
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]

        # Decode base64
        image_data = base64.b64decode(image_b64)
        print(f"Image decoded - Size: {len(image_data)} bytes")

        # Create unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"huis_photo_{timestamp}.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)

        # Verify directory exists
        if not os.path.exists(PHOTOS_DIR):
            os.makedirs(PHOTOS_DIR)
            print(f"Created directory: {PHOTOS_DIR}")

        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_data)

        # Verify file was saved
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✓ Image saved successfully!")
            print(f"  Path: {filepath}")
            print(f"  Size: {file_size} bytes")

            # Note: main.exe launch moved to separate route

        else:
            print(f"✗ ERROR: File was not saved to {filepath}")

        # ... Your image processing logic (e.g., run AI model) ...

        # 4. Send a response back with download link
        return jsonify({
            "status": "success",
            "message": "Image processed and saved to Downloads",
            "download_url": f"/download_photo/{filename}",
            "file_path": filepath
        })

    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": error_msg}), 400
    


#_____________________________________________________________________________________
# Route to download the captured photo
@app.route('/download_photo/<filename>')
def download_photo(filename):
    """Download the captured photo"""
    try:
        filepath = os.path.join(PHOTOS_DIR, filename)

        print(f"Download request - Filename: {filename}")
        print(f"Looking for file at: {filepath}")
        print(f"File exists: {os.path.exists(filepath)}")

        if not os.path.exists(filepath):
            error_msg = f"Photo not found at {filepath}"
            print(f"ERROR: {error_msg}")
            return jsonify({"status": "error", "message": error_msg}), 404

        print(f"Sending file: {filepath}")
        return send_file(filepath, mimetype='image/jpeg', as_attachment=True, download_name=filename)

    except Exception as e:
        error_msg = f"Download error: {str(e)}"
        print(f"ERROR: {error_msg}")
        return jsonify({"status": "error", "message": error_msg}), 400


#_____________________________________________________________________________________
# Cleanup route to delete the temporary photo after download or when no longer needed
@app.route('/test_launch')
def test_launch():
    """Test page to try different launch methods"""
    return '''
    <html>
    <head><title>Test Launch Methods</title></head>
    <body>
        <h1>Test Different Launch Methods</h1>
        <button onclick="testMethod('subprocess_cwd')">Test subprocess with cwd</button>
        <button onclick="testMethod('os_startfile')">Test os.startfile</button>
        <button onclick="testMethod('subprocess_simple')">Test subprocess simple</button>
        <br><br>
        <div id="results"></div>

        <script>
        async function testMethod(method) {
            const results = document.getElementById('results');
            results.innerHTML = 'Testing ' + method + '...';

            try {
                const response = await fetch('/test_launch_method', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({method: method})
                });
                const result = await response.json();
                results.innerHTML = '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
            } catch (error) {
                results.innerHTML = 'Error: ' + error.message;
            }
        }
        </script>
    </body>
    </html>
    '''

@app.route('/test_launch_method', methods=['POST'])
def test_launch_method():
    """Test different launch methods"""
    data = request.get_json()
    method = data.get('method', 'subprocess_cwd')

    results = {
        'method': method,
        'main_exe_path': MAIN_EXE_PATH,
        'exists': os.path.exists(MAIN_EXE_PATH),
        'current_cwd': os.getcwd(),
        'exe_dir': os.path.dirname(MAIN_EXE_PATH) if os.path.exists(MAIN_EXE_PATH) else None
    }

    try:
        if not os.path.exists(MAIN_EXE_PATH):
            results['error'] = 'main.exe not found'
            return jsonify(results)

        if method == 'subprocess_cwd':
            exe_dir = os.path.dirname(MAIN_EXE_PATH)
            process = subprocess.run([MAIN_EXE_PATH], cwd=exe_dir, capture_output=True, text=True, timeout=5)
            results['returncode'] = process.returncode
            results['stdout'] = process.stdout
            results['stderr'] = process.stderr

        elif method == 'os_startfile':
            os.startfile(MAIN_EXE_PATH)
            results['message'] = 'os.startfile called (no return value)'

        elif method == 'subprocess_simple':
            process = subprocess.run([MAIN_EXE_PATH], capture_output=True, text=True, timeout=5)
            results['returncode'] = process.returncode
            results['stdout'] = process.stdout
            results['stderr'] = process.stderr

        results['success'] = True

    except subprocess.TimeoutExpired:
        results['error'] = 'Process timed out'
    except Exception as e:
        results['error'] = str(e)

    return jsonify(results)

if __name__ == "__main__":
    print("=" * 60)
    print("HUIS Visual Analysis App Starting")
    print(f"Photos directory: {PHOTOS_DIR}")
    print(f"Main.exe path: {MAIN_EXE_PATH}")
    print(f"Main.exe exists: {os.path.exists(MAIN_EXE_PATH)}")
    print("=" * 60 + "\n")

    app.run(debug=True)