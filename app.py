import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
import tempfile
import uuid
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from logo_processor import process_logo, process_card_logo

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure uploads
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Créer les dossiers s'ils n'existent pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_logo', methods=['POST'])
def process_logo_route():
    try:
        # Récupérer le type (image ou text)
        logo_type = request.form.get('type', 'image')
        override_param = request.form.get('override')
        override_scale = override_param == 'scale'
        override_position = override_param == 'pos'
        
        # Récupérer les paramètres d'ajustement
        horizontal_offset = float(request.form.get('horizontal_offset', 0))
        vertical_offset = float(request.form.get('vertical_offset', 0))
        scale_factor = float(request.form.get('scale_factor', 1.0))
        
        if logo_type == 'image':
            # Traitement d'image
            if 'logo' not in request.files:
                return jsonify({'success': False, 'error': 'Aucun fichier envoyé'}), 400
                
            file = request.files['logo']
            
            if file.filename == '':
                return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400
                
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Format de fichier non supporté'}), 400
                
            # Sauvegarder le fichier
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)
            
            # Générer un nom de fichier unique pour l'image traitée
            output_filename = f"processed_{filename.rsplit('.', 1)[0]}.jpg"
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
            
            # Traiter le logo avec les nouveaux paramètres
            process_logo(
                input_path,
                output_path,
                horizontal_offset=horizontal_offset,
                vertical_offset=vertical_offset,
                scale_factor=scale_factor,
                override_limits={'scale': override_scale, 'position': override_position}
            )
            
            # Supprimer le fichier d'entrée
            os.remove(input_path)
            
        else:
            # Traitement de texte
            text = request.form.get('logo-text', '')
            
            if not text:
                return jsonify({'success': False, 'error': 'Aucun texte fourni'}), 400
                
            # Générer un nom de fichier unique pour le texte traité
            output_filename = f"text_{uuid.uuid4().hex[:8]}.jpg"
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
            
            # Traiter le texte avec les mêmes paramètres
            from logo_processor import process_text_logo
            process_text_logo(
                text,
                output_path,
                horizontal_offset=horizontal_offset,
                vertical_offset=vertical_offset,
                scale_factor=scale_factor,
                override_limits={'scale': override_scale, 'position': override_position}
            )
        
        return jsonify({
            'success': True,
            'filename': output_filename
        })
        
    except Exception as e:
        logging.error(f"Error processing logo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/processed/<filename>')
def processed_file(filename):
    try:
        return send_file(
            os.path.join(app.config['PROCESSED_FOLDER'], filename),
            mimetype='image/png' if filename.lower().endswith('.png') else 'image/jpeg'
        )
    except Exception as e:
        return str(e), 404

@app.route('/process_card', methods=['POST'])
def process_card_route():
    try:
        # Récupérer les paramètres
        horizontal_offset = float(request.form.get('horizontal_offset', 0))
        vertical_offset = float(request.form.get('vertical_offset', 0))
        scale_factor = float(request.form.get('scale_factor', 1.0))
        override_param = request.form.get('override')
        override_scale = override_param == 'scale'
        override_position = override_param == 'pos'
        # Vérifier le fichier
        if 'logo' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier envoyé'}), 400
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400
        # Sauvegarder le fichier
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        # Générer un nom de fichier unique pour la carte générée
        output_filename = f"card_{uuid.uuid4().hex[:8]}.png"
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        # Traiter la carte
        process_card_logo(
            input_path,
            output_path,
            scale_factor=scale_factor,
            horizontal_offset=horizontal_offset,
            vertical_offset=vertical_offset,
            override_limits={'scale': override_scale, 'position': override_position}
        )
        # Supprimer le fichier d'entrée
        os.remove(input_path)
        return jsonify({'success': True, 'filename': output_filename})
    except Exception as e:
        logging.error(f"Error processing card: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True)
