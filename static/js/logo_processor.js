document.addEventListener('DOMContentLoaded', function() {
    const logoForm = document.getElementById('logo-form');
    const uploadBtn = document.getElementById('upload-btn');
    const previewImage = document.getElementById('preview-image');
    const noPreview = document.getElementById('no-preview');
    const loading = document.getElementById('loading');
    const previewDownloadBtn = document.getElementById('preview-download-btn');
    const downloadContainer = document.getElementById('download-container');
    const errorMessage = document.getElementById('error-message');
    const simpleGuides = document.getElementById('simple-guides');
    
    // Nouveaux éléments pour les contrôles
    const adjustmentControls = document.getElementById('adjustment-controls');
    const horizontalPosition = document.getElementById('horizontal-position');
    const verticalPosition = document.getElementById('vertical-position');
    const scaleFactor = document.getElementById('scale-factor');
    const horizontalValue = document.getElementById('horizontal-value');
    const verticalValue = document.getElementById('vertical-value');
    const scaleValue = document.getElementById('scale-value');
    const processButtonContainer = document.getElementById('process-button-container');
    // Boutons de nudge
    const horizontalDecrease = document.getElementById('horizontal-decrease');
    const horizontalIncrease = document.getElementById('horizontal-increase');
    const verticalDecrease = document.getElementById('vertical-decrease');
    const verticalIncrease = document.getElementById('vertical-increase');
    const scaleDecrease = document.getElementById('scale-decrease');
    const scaleIncrease = document.getElementById('scale-increase');
    
    // Nouveaux éléments pour le choix image/texte
    const typeImage = document.getElementById('type-image');
    const typeText = document.getElementById('type-text');
    const imageSection = document.getElementById('image-section');
    const textSection = document.getElementById('text-section');
    const logoTextInput = document.getElementById('logo-text');
    
    // Nouveaux éléments pour le mode 'card'
    const typeCard = document.getElementById('type-card');
    const cardSection = document.getElementById('card-section');
    const cardLogoInput = document.getElementById('card-logo');
    
    let currentFilename = null; // Stocker le nom du fichier traité
    let currentType = 'image'; // Type actuel (image ou text)
    let lastAction = null; // 'pos' | 'scale' | null
    
    // Gestionnaire pour le champ texte avec mise à jour automatique
    logoTextInput.addEventListener('input', function() {
        if (currentType === 'text') {
            debounceUpdate();
        }
    });
    
    // Gestionnaires pour les sliders avec mise à jour automatique
    let fromSlider = false;
    horizontalPosition.addEventListener('input', function() {
        horizontalValue.textContent = this.value;
        fromSlider = true;
        lastAction = 'pos';
        if (currentFilename) {
            debounceUpdate();
        }
    });
    
    verticalPosition.addEventListener('input', function() {
        verticalValue.textContent = this.value;
        fromSlider = true;
        lastAction = 'pos';
        if (currentFilename) {
            debounceUpdate();
        }
    });
    
    scaleFactor.addEventListener('input', function() {
        scaleValue.textContent = Math.round(this.value * 100);
        fromSlider = true;
        lastAction = 'scale';
        if (currentFilename) {
            debounceUpdate();
        }
    });

    // --- Boutons de nudge ---
    function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
    function nudgeHorizontal(delta) {
        const step = parseInt(horizontalPosition.step) || 10;
        const min = parseInt(horizontalPosition.min);
        const max = parseInt(horizontalPosition.max);
        horizontalPosition.value = clamp(parseInt(horizontalPosition.value) + delta * step, min, max);
        horizontalValue.textContent = horizontalPosition.value;
        fromSlider = true;
        lastAction = 'pos';
        if (currentFilename) debounceUpdate();
    }
    function nudgeVertical(delta) {
        const step = parseInt(verticalPosition.step) || 10;
        const min = parseInt(verticalPosition.min);
        const max = parseInt(verticalPosition.max);
        verticalPosition.value = clamp(parseInt(verticalPosition.value) + delta * step, min, max);
        verticalValue.textContent = verticalPosition.value;
        fromSlider = true;
        lastAction = 'pos';
        if (currentFilename) debounceUpdate();
    }
    function nudgeScale(delta) {
        const step = parseFloat(scaleFactor.step) || 0.05;
        const min = parseFloat(scaleFactor.min);
        const max = parseFloat(scaleFactor.max);
        const next = clamp(parseFloat(scaleFactor.value) + delta * step, min, max);
        scaleFactor.value = next.toFixed(2);
        scaleValue.textContent = Math.round(parseFloat(scaleFactor.value) * 100);
        fromSlider = true;
        lastAction = 'scale';
        if (currentFilename) debounceUpdate();
    }

    if (horizontalDecrease) horizontalDecrease.addEventListener('click', () => nudgeHorizontal(-1));
    if (horizontalIncrease) horizontalIncrease.addEventListener('click', () => nudgeHorizontal(1));
    if (verticalDecrease) verticalDecrease.addEventListener('click', () => nudgeVertical(-1));
    if (verticalIncrease) verticalIncrease.addEventListener('click', () => nudgeVertical(1));
    if (scaleDecrease) scaleDecrease.addEventListener('click', () => nudgeScale(-1));
    if (scaleIncrease) scaleIncrease.addEventListener('click', () => nudgeScale(1));
    
    // Gestionnaire pour les radio buttons
    typeImage.addEventListener('change', function() {
        if (this.checked) {
            resetUI();
            currentType = 'image';
            imageSection.classList.remove('d-none');
            textSection.classList.add('d-none');
            cardSection.classList.add('d-none');
            processButtonContainer.classList.remove('d-none');
            logoTextInput.value = '';
        }
    });
    
    typeText.addEventListener('change', function() {
        if (this.checked) {
            resetUI();
            currentType = 'text';
            textSection.classList.remove('d-none');
            imageSection.classList.add('d-none');
            cardSection.classList.add('d-none');
            processButtonContainer.classList.add('d-none');
            if (logoTextInput.value.trim()) {
                processText(logoTextInput.value.trim());
            }
        }
    });
    
    typeCard.addEventListener('change', function() {
        if (this.checked) {
            resetUI();
            currentType = 'card';
            cardSection.classList.remove('d-none');
            imageSection.classList.add('d-none');
            textSection.classList.add('d-none');
            processButtonContainer.classList.remove('d-none');
        }
    });
    
    // Fonction de debounce pour éviter trop de requêtes
    let updateTimeout;
    function debounceUpdate() {
        clearTimeout(updateTimeout);
        updateTimeout = setTimeout(() => {
            if (currentType === 'text') {
                const text = logoTextInput.value.trim();
                if (text) {
                    showLoading();
                    processText(text);
                }
            } else if (currentType === 'card') {
                const file = cardLogoInput.files[0];
                if (file) {
                    showLoading();
                    processCard(file);
                }
            } else {
                updatePreview();
            }
        }, 300); // Attendre 300ms après le dernier changement
    }
    
    // Gestionnaire pour le formulaire de téléchargement
    logoForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (currentType === 'image') {
            const fileInput = document.getElementById('logo');
            const file = fileInput.files[0];
            
            if (!file) {
                showError('Veuillez sélectionner un fichier');
                return;
            }
            
            // Vérifier le type de fichier
            const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml'];
            if (!allowedTypes.includes(file.type)) {
                showError('Format de fichier non supporté. Veuillez utiliser PNG, JPG, JPEG, GIF ou SVG.');
                return;
            }
            
            showLoading();
            processImage(file);
        } else if (currentType === 'card') {
            const file = cardLogoInput.files[0];
            if (!file) {
                showError('Veuillez sélectionner un logo pour la carte');
                return;
            }
            showLoading();
            processCard(file);
        } else {
            // Type texte
            const text = logoTextInput.value.trim();
            
            if (!text) {
                showError('Veuillez entrer un texte');
                return;
            }
            
            showLoading();
            processText(text);
        }
    });
    
    // Fonction pour traiter l'image
    function processImage(file) {
        const formData = new FormData();
        formData.append('logo', file);
        formData.append('horizontal_offset', horizontalPosition.value);
        formData.append('vertical_offset', verticalPosition.value);
        formData.append('scale_factor', scaleFactor.value);
        formData.append('type', 'image');
        if (fromSlider && lastAction) {
            formData.append('override', lastAction);
            fromSlider = false;
            lastAction = null;
        }
        
        fetch('/process_logo', {
            method: 'POST',
            body: formData
        })
        .then(handleResponse)
        .then(handleSuccess)
        .catch(handleError);
    }
    
    // Fonction pour traiter le texte
    function processText(text) {
        const formData = new FormData();
        formData.append('logo-text', text);
        formData.append('horizontal_offset', horizontalPosition.value);
        formData.append('vertical_offset', verticalPosition.value);
        formData.append('scale_factor', parseFloat(scaleFactor.value));
        formData.append('type', 'text');
        if (fromSlider && lastAction) {
            formData.append('override', lastAction);
            fromSlider = false;
            lastAction = null;
        }
        
        console.log('Sending text with scale_factor:', parseFloat(scaleFactor.value));
        
        fetch('/process_logo', {
            method: 'POST',
            body: formData
        })
        .then(handleResponse)
        .then(handleSuccess)
        .catch(handleError);
    }
    
    // Fonction pour traiter le logo pour la carte
    function processCard(file) {
        const formData = new FormData();
        formData.append('logo', file);
        formData.append('horizontal_offset', horizontalPosition.value);
        formData.append('vertical_offset', verticalPosition.value);
        formData.append('scale_factor', scaleFactor.value);
        if (fromSlider && lastAction) {
            formData.append('override', lastAction);
            fromSlider = false;
            lastAction = null;
        }
        fetch('/process_card', {
            method: 'POST',
            body: formData
        })
        .then(handleResponse)
        .then(handleSuccess)
        .catch(handleError);
    }
    
    // Fonction pour gérer la réponse
    function handleResponse(response) {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Une erreur est survenue lors du traitement');
            });
        }
        return response.json();
    }
    
    // Fonction pour gérer le succès
    function handleSuccess(data) {
        if (data.success) {
            currentFilename = data.filename;
            
            // Afficher les contrôles d'ajustement
            adjustmentControls.classList.remove('d-none');
            
            // Mettre à jour le bouton de téléchargement
            previewDownloadBtn.href = `/processed/${data.filename}?download=true`;
            downloadContainer.classList.remove('d-none');
            
            // Afficher l'image
            const timestamp = new Date().getTime(); // Cache-busting
            previewImage.src = `/processed/${data.filename}?t=${timestamp}`;
            previewImage.classList.remove('d-none');
            previewImage.classList.add('fadeIn');
            
            // Attendre que l'image soit chargée pour ajuster les guides
            previewImage.onload = function() {
                adjustGuidesToImage();
                simpleGuides.classList.remove('d-none');
            };
            
            noPreview.classList.add('d-none');
            loading.classList.add('d-none');
            
            // Hide any previous errors
            errorMessage.classList.add('d-none');
        } else {
            showError(data.error || 'Une erreur est survenue');
        }
    }
    
    // Fonction pour gérer les erreurs
    function handleError(error) {
        showError(error.message || 'Une erreur est survenue lors du traitement');
    }
    
    // Fonction pour mettre à jour la prévisualisation avec les nouveaux paramètres
    function updatePreview() {
        if (currentType === 'image') {
            const fileInput = document.getElementById('logo');
            const file = fileInput.files[0];
            if (!file) return;
            showLoading();
            processImage(file);
        } else if (currentType === 'card') {
            const file = cardLogoInput.files[0];
            if (!file) return;
            showLoading();
            processCard(file);
        } else {
            const text = logoTextInput.value.trim();
            if (!text) return;
            showLoading();
            processText(text);
        }
    }
    
    // Fonction pour afficher les erreurs
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
        loading.classList.add('d-none');
        simpleGuides.classList.add('d-none');
    }
    
    // Fonction pour afficher l'état de chargement
    function showLoading() {
        loading.classList.remove('d-none');
        errorMessage.classList.add('d-none');
        previewImage.classList.add('d-none');
        noPreview.classList.add('d-none');
        downloadContainer.classList.add('d-none');
        simpleGuides.classList.add('d-none');
    }
    
    // Fonction pour ajuster les guides aux dimensions de l'image
    function adjustGuidesToImage() {
        const imgRect = previewImage.getBoundingClientRect();
        const containerRect = document.getElementById('preview-container').getBoundingClientRect();
        
        // Positionner le conteneur des guides exactement sur l'image
        simpleGuides.style.width = imgRect.width + 'px';
        simpleGuides.style.height = imgRect.height + 'px';
        simpleGuides.style.top = '50%';
        simpleGuides.style.left = '50%';
        simpleGuides.style.transform = 'translate(-50%, -50%)';
    }
    
    // --- Fonction pour réinitialiser l'UI ---
    function resetUI() {
        // Réinitialiser le fichier sélectionné et le nom
        currentFilename = null;
        // Masquer preview, guides, download etc.
        previewImage.classList.add('d-none');
        noPreview.classList.remove('d-none');
        loading.classList.add('d-none');
        downloadContainer.classList.add('d-none');
        simpleGuides.classList.add('d-none');
        adjustmentControls.classList.add('d-none');
        // Réinitialiser sliders
        horizontalPosition.value = 0;
        verticalPosition.value = 0;
        scaleFactor.value = 1.0;
        horizontalValue.textContent = '0';
        verticalValue.textContent = '0';
        scaleValue.textContent = '100';
    }
});
