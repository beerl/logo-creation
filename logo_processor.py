from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont, ImageEnhance
import logging
import os
import io
import textwrap
import io as _io
try:
    import cairosvg
except Exception:
    cairosvg = None

def process_logo(input_path, output_path, top_margin=73, right_margin=73, scale_factor=1.0, invert=False, horizontal_offset=0, vertical_offset=0, override_limits=False):
    """
    Process a logo image selon les spécifications exactes :
    1. Pour les PNG : conversion en noir en préservant la transparence
    2. Pour les autres formats : détourage (suppression du fond blanc) puis conversion en noir
    3. Redimensionnement proportionnel (max 613px de LARGEUR × 283px de HAUTEUR, sans déformation)
    4. Placement sur un canevas blanc (2025px de longueur × 1276px de hauteur)
    5. Positionnement : 73px du haut (ajustable verticalement) et 73px de la droite (ajustable horizontalement)
    6. Sauvegarde en JPG avec une résolution de 1200 DPI pour une qualité optimale
    
    Args:
        input_path: Path to the input image
        output_path: Path to save the processed image
        top_margin: Top margin in pixels (default: 73)
        right_margin: Right margin in pixels (default: 73)
        scale_factor: Scale factor for the logo (default: 1.0)
        invert: Whether to invert the colors (default: False)
        horizontal_offset: Horizontal offset in pixels (default: 0)
        vertical_offset: Vertical offset in pixels (default: 0)
    """
    try:
        # Vérifier si c'est un fichier SVG
        is_svg = input_path.lower().endswith('.svg')
        
        # Charger l'image (conversion SVG -> PNG en mémoire si nécessaire)
        if is_svg:
            if cairosvg is None:
                raise RuntimeError("CairoSVG n'est pas installé. Impossible de traiter les fichiers SVG.")
            png_bytes: bytes = cairosvg.svg2png(url=input_path)
            img = Image.open(_io.BytesIO(png_bytes)).convert('RGBA')
        else:
            # Ouvrir l'image avec PIL en utilisant la plus haute qualité possible
            img = Image.open(input_path)
        
        # Convertir en mode RVB si nécessaire pour une meilleure qualité de traitement
        if img.mode not in ['RGB', 'RGBA']:
            if 'transparency' in img.info:
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        
        # Vérifier si c'est un PNG (ou issu d'un SVG converti)
        is_png = is_svg or (getattr(img, 'format', None) == 'PNG')
        
        if is_png:
            # Pour les PNG, on convertit simplement en noir en préservant la transparence
            if img.mode == 'RGBA':
                # Si l'image a déjà un canal alpha, on le préserve
                r, g, b, alpha = img.split()
                # Créer une image noire ou blanche selon le paramètre invert
                color = (255, 255, 255) if invert else (0, 0, 0)
                color_img = Image.new('RGB', img.size, color)
                processed_img = Image.new('RGBA', img.size)
                processed_img.paste(color_img, (0, 0), mask=alpha)
            else:
                # Si l'image n'a pas de canal alpha, on la convertit simplement en noir ou blanc
                processed_img = ImageOps.grayscale(img)
                if invert:
                    processed_img = ImageOps.invert(processed_img)
                processed_img = processed_img.convert('RGBA')
        else:
            # Pour les autres formats, procéder au détourage
            if img.mode == 'RGBA':
                # Extraire le canal alpha existant
                r, g, b, alpha = img.split()
                
                # Créer une image en noir et blanc pour déterminer les parties à conserver
                gray = ImageOps.grayscale(img)
                
                # Améliorer le contraste pour un meilleur détourage
                contrast_enhancer = ImageEnhance.Contrast(gray)
                gray = contrast_enhancer.enhance(1.2)
                gray = ImageOps.autocontrast(gray, cutoff=2)
                
                # Utiliser un seuil adaptatif pour un meilleur détourage
                binary = gray.point(lambda p: 0 if p < 245 else 255)
                
                # Améliorer le canal alpha en combinant avec notre masque binaire
                # Les zones noires de binary deviennent opaques (255), les zones blanches transparentes (0)
                enhanced_alpha = binary.point(lambda p: 255 if p < 128 else 0)
                
                # Pour les images avec alpha existant, ne pas perdre la transparence existante
                # Conserver la valeur la plus opaque entre les deux
                final_alpha = Image.new('L', img.size)
                alpha_data = list(alpha.getdata())
                enhanced_data = list(enhanced_alpha.getdata())
                final_data = [max(a, e) for a, e in zip(alpha_data, enhanced_data)]
                final_alpha.putdata(final_data)
                
                # Créer une image noire ou blanche selon le paramètre invert
                color = (255, 255, 255) if invert else (0, 0, 0)
                color_img = Image.new('RGB', img.size, color)
                
                # Fusionner les deux images
                # Les zones transparentes resteront transparentes, les zones opaques seront noires ou blanches
                result = Image.new('RGBA', img.size)
                result.paste(color_img, (0, 0), mask=final_alpha)
                
                # Définir l'image traitée
                processed_img = result
                
            else:
                # Convertir l'image en RGB si ce n'est pas déjà fait
                img_rgb = img.convert('RGB')
                
                # Créer une version en niveaux de gris
                gray = ImageOps.grayscale(img_rgb)
                
                # Améliorer le contraste pour un meilleur détourage
                contrast_enhancer = ImageEnhance.Contrast(gray)
                gray = contrast_enhancer.enhance(1.2)
                gray = ImageOps.autocontrast(gray, cutoff=2)
                
                # Utiliser un seuil adaptatif pour un meilleur détourage
                threshold = 245
                binary = gray.point(lambda p: 0 if p < threshold else 255)
                
                # Inverser le masque: les zones sombres (logo) sont opaques (255), 
                # les zones claires (fond) sont transparentes (0)
                alpha_mask = binary.point(lambda p: 255 if p < 128 else 0)
                
                # Créer une version noire ou blanche du logo selon le paramètre invert
                color = (255, 255, 255) if invert else (0, 0, 0)
                color_img = Image.new('RGB', img.size, color)
                
                # Fusionner l'image avec le masque alpha
                processed_img = Image.new('RGBA', img.size)
                processed_img.paste(color_img, (0, 0), mask=alpha_mask)
        
        # Redimensionnement proportionnel
        original_width, original_height = processed_img.size
        max_width, max_height = 613, 283  # valeurs par défaut pour le logging
        # Calcul de la taille de base (fit) qui tient dans 613x283
        base_width_ratio = max_width / original_width
        base_height_ratio = max_height / original_height
        base_ratio = min(base_width_ratio, base_height_ratio)

        if isinstance(override_limits, dict):
            override_scale = override_limits.get('scale', False)
        else:
            override_scale = bool(override_limits)

        if override_scale:
            # Appliquer le facteur par rapport à la taille de base (100% = fit)
            ratio = base_ratio * scale_factor
        else:
            # Respecter les limites 613x283 et appliquer le facteur
            ratio = base_ratio * scale_factor
        
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        logging.debug(f"Original size: {original_width}x{original_height}")
        if override_scale:
            logging.debug("Max size allowed: unlimited (override)")
        else:
            logging.debug(f"Max size allowed: {max_width}x{max_height}")
        logging.debug(f"Final resized size: {new_width}x{new_height}")
        logging.debug(f"Ratio applied: {ratio:.3f}")
        
        # Redimensionner l'image traitée avec LANCZOS pour une meilleure qualité
        # Utiliser un redimensionnement en deux étapes pour une qualité supérieure
        if ratio < 0.5:
            # Si l'image est très réduite, faire un redimensionnement en deux étapes
            intermediate_size = (int(original_width * 0.5), int(original_height * 0.5))
            resized_img = processed_img.resize(intermediate_size, Image.LANCZOS)
            resized_img = resized_img.resize((new_width, new_height), Image.LANCZOS)
        else:
            resized_img = processed_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Améliorer la netteté de l'image de manière plus subtile pour éviter les artefacts
        sharpness = ImageEnhance.Sharpness(resized_img)
        resized_img = sharpness.enhance(1.3)  # Augmenter la netteté de 30%
        
        # Améliorer légèrement le contraste pour une meilleure définition
        contrast = ImageEnhance.Contrast(resized_img)
        resized_img = contrast.enhance(1.1)  # Augmenter le contraste de 10%
        
        # Créer un canevas blanc avec une meilleure qualité et résolution plus élevée
        canvas_width, canvas_height = 2024, 1276
        canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
        
        # Positionner le logo selon les paramètres avec vérification des limites
        paste_x = canvas_width - new_width - right_margin + int(horizontal_offset)
        paste_y = top_margin + int(vertical_offset)
        
        # S'assurer que le logo reste dans les limites du canevas
        if isinstance(override_limits, dict):
            override_position = override_limits.get('position', False)
        else:
            override_position = bool(override_limits)
        if not override_position:
            paste_x = max(0, min(paste_x, canvas_width - new_width))
            paste_y = max(0, min(paste_y, canvas_height - new_height))
        
        logging.debug(f"Placing logo at position ({paste_x}, {paste_y}) with horizontal offset {horizontal_offset} and vertical offset {vertical_offset}")
        
        # Coller l'image traitée sur le canevas en utilisant son propre canal alpha comme masque
        if resized_img.mode == 'RGBA':
            canvas.paste(resized_img, (paste_x, paste_y), mask=resized_img.split()[3])
        else:
            canvas.paste(resized_img, (paste_x, paste_y))
        
        # Définir la résolution à 1200 DPI pour une qualité d'impression supérieure
        canvas.info['dpi'] = (1200, 1200)
        
        # Sauvegarder l'image finale en JPG avec la qualité maximale et 1200 DPI
        canvas.save(output_path, 'JPEG', quality=100, dpi=(1200, 1200), optimize=True, progressive=True)
        
        logging.debug(f"Processed logo saved to {output_path} with 1200 DPI resolution")
        return True
        
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        raise

def process_text_logo(text, output_path, top_margin=73, right_margin=73, scale_factor=1.0, horizontal_offset=0, vertical_offset=0, override_limits=False):
    """
    Create a text logo with the same constraints as image logos.
    Supports multiline text with automatic line spacing.
    
    Args:
        text: Text to render (can contain newlines)
        output_path: Path to save the processed image
        top_margin: Top margin in pixels (default: 73)
        right_margin: Right margin in pixels (default: 73)
        scale_factor: Scale factor for the text (default: 1.0)
        horizontal_offset: Horizontal offset in pixels (default: 0)
        vertical_offset: Vertical offset in pixels (default: 0)
    """
    try:
        logging.info(f"Processing text with scale_factor: {scale_factor}")
        text = text.replace('\r', '')
        lines = text.split('\n')
        max_width, max_height = 613, 283
        margin = 50
        # Recherche dichotomique de la taille de police maximale
        min_font, max_font = 10, 1000
        best_font_size = min_font
        font_path = None
        try:
            font_path = "fonts/Manrope-Regular.ttf"
            font = ImageFont.truetype(font_path, min_font)
        except:
            try:
                font_path = "arial.ttf"
                font = ImageFont.truetype(font_path, min_font)
            except:
                try:
                    font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                    font = ImageFont.truetype(font_path, min_font)
                except:
                    font_path = None
        if not font_path:
            raise RuntimeError("Aucune police TTF trouvée sur le système. Placez fonts/Manrope-Regular.ttf, arial.ttf ou LiberationSans-Regular.ttf.")
        logging.info(f"Font path used: {font_path}")
        while min_font <= max_font:
            mid_font = (min_font + max_font) // 2
            if font_path:
                font = ImageFont.truetype(font_path, mid_font)
            else:
                font = ImageFont.load_default()
            temp_img = Image.new('RGB', (1, 1), (255, 255, 255))
            draw = ImageDraw.Draw(temp_img)
            line_heights = []
            line_widths = []
            max_line_width = 0
            total_height = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                max_line_width = max(max_line_width, line_width)
                line_heights.append(line_height)
                line_widths.append(line_width)
                total_height += line_height
            line_spacing = int(max(line_heights) * 0.3) if line_heights else 0
            total_height += line_spacing * (len(lines) - 1)
            if max_line_width + 2 * margin <= max_width and total_height + 2 * margin <= max_height:
                best_font_size = mid_font
                min_font = mid_font + 1
            else:
                max_font = mid_font - 1
        # Appliquer le scale_factor
        final_font_size = int(best_font_size * scale_factor)
        if font_path:
            font = ImageFont.truetype(font_path, final_font_size)
        else:
            font = ImageFont.load_default()
        # Recalculer les dimensions finales
        temp_img = Image.new('RGB', (1, 1), (255, 255, 255))
        draw = ImageDraw.Draw(temp_img)
        line_heights = []
        line_widths = []
        max_line_width = 0
        total_height = 0
        line_bboxes = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            max_line_width = max(max_line_width, line_width)
            line_heights.append(line_height)
            line_widths.append(line_width)
            line_bboxes.append(bbox)
            total_height += line_height
        line_spacing = int(max(line_heights) * 0.3) if line_heights else 0
        total_height += line_spacing * (len(lines) - 1)
        # Sécurité: padding supplémentaire pour éviter toute coupure liée aux métriques
        safety_pad = max(4, int(final_font_size * 0.1))
        img_width = max_line_width + (margin * 2) + safety_pad
        img_height = total_height + (margin * 2) + safety_pad
        text_img = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(text_img)
        # Compenser un éventuel bbox top négatif (ascenders)
        min_top = min((b[1] for b in line_bboxes), default=0)
        y = margin - min_top
        for i, line in enumerate(lines):
            bbox = line_bboxes[i]
            x = margin - bbox[0]
            draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
            y += line_heights[i] + line_spacing
        # Contraindre l'image de texte aux limites 613x283 si nécessaire
        if isinstance(override_limits, dict):
            override_scale = override_limits.get('scale', False)
        else:
            override_scale = bool(override_limits)
        if not override_scale:
            max_width, max_height = 613, 283
            if text_img.width > max_width or text_img.height > max_height:
                ratio = min(max_width / text_img.width, max_height / text_img.height)
                new_size = (max(1, int(text_img.width * ratio)), max(1, int(text_img.height * ratio)))
                text_img = text_img.resize(new_size, Image.LANCZOS)
        canvas_width, canvas_height = 2024, 1276
        canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
        paste_x = canvas_width - text_img.width - right_margin + int(horizontal_offset)
        paste_y = top_margin + int(vertical_offset)
        if isinstance(override_limits, dict):
            override_position = override_limits.get('position', False)
        else:
            override_position = bool(override_limits)
        if not override_position:
            paste_x = max(0, min(paste_x, canvas_width - text_img.width))
            paste_y = max(0, min(paste_y, canvas_height - text_img.height))
        canvas.paste(text_img, (paste_x, paste_y), mask=text_img.split()[3])
        canvas.info['dpi'] = (1200, 1200)
        canvas.save(output_path, 'JPEG', quality=100, dpi=(1200, 1200), optimize=True, progressive=True)
        logging.info(f"Processed text logo saved to {output_path} with font size {final_font_size}")
        return True
    except Exception as e:
        logging.error(f"Error processing text: {str(e)}")
        raise

def process_card_logo(logo_path, output_path, card_template_path='static/card_template.png', top_margin=35, right_margin=35, max_width=210, max_height=100, scale_factor=1.0, horizontal_offset=0, vertical_offset=0, override_limits=False):
    """
    Place un logo détouré/redimensionné sur une carte bancaire.
    - logo_path: chemin du logo utilisateur
    - output_path: chemin de sauvegarde
    - card_template_path: chemin de l'image de carte
    - top_margin, right_margin: marges en px
    - max_width, max_height: taille max du logo
    - scale_factor: multiplicateur de taille
    """
    try:
        # Charger la carte
        card = Image.open(card_template_path).convert('RGBA')
        # Charger et traiter le logo (détourage, noir, etc.)
        processed_logo = None
        is_svg = logo_path.lower().endswith('.svg')
        if is_svg:
            if cairosvg is None:
                raise RuntimeError("CairoSVG n'est pas installé. Impossible de traiter les fichiers SVG.")
            png_bytes: bytes = cairosvg.svg2png(url=logo_path)
            img = Image.open(_io.BytesIO(png_bytes)).convert('RGBA')
        else:
            img = Image.open(logo_path)
        if img.mode not in ['RGB', 'RGBA']:
            img = img.convert('RGBA')
        # Détourage simplifié (fond blanc -> transparent)
        if img.mode == 'RGBA':
            # Pour les PNG (ou images déjà avec transparence), on garde l'alpha et on colore en BLANC
            r, g, b, alpha = img.split()
            color_img = Image.new('RGB', img.size, (255, 255, 255))  # blanc
            result = Image.new('RGBA', img.size)
            result.paste(color_img, (0, 0), mask=alpha)
            processed_logo = result
        else:
            # Pour les autres formats : détourage et recolorisation en BLANC
            img_rgb = img.convert('RGB')
            gray = ImageOps.grayscale(img_rgb)
            binary = gray.point(lambda p: 0 if p < 245 else 255)
            alpha_mask = binary.point(lambda p: 255 if p < 128 else 0)
            color_img = Image.new('RGB', img.size, (255, 255, 255))
            processed_logo = Image.new('RGBA', img.size)
            processed_logo.paste(color_img, (0, 0), mask=alpha_mask)
        # Redimensionnement proportionnel
        original_width, original_height = processed_logo.size
        if isinstance(override_limits, dict):
            override_scale = override_limits.get('scale', False)
        else:
            override_scale = bool(override_limits)
        if override_scale:
            ratio = scale_factor
        else:
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            ratio = min(width_ratio, height_ratio) * scale_factor
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        resized_logo = processed_logo.resize((new_width, new_height), Image.LANCZOS)
        # Position sur la carte
        paste_x = card.width - new_width - right_margin + int(horizontal_offset)
        paste_y = top_margin + int(vertical_offset)
        # S'assurer que le logo reste dans les limites du canevas
        if isinstance(override_limits, dict):
            override_position = override_limits.get('position', False)
        else:
            override_position = bool(override_limits)
        if not override_position:
            paste_x = max(0, min(paste_x, card.width - new_width))
            paste_y = max(0, min(paste_y, card.height - new_height))
        # Coller le logo
        card.paste(resized_logo, (paste_x, paste_y), mask=resized_logo.split()[3])
        # Sauvegarder en PNG pour conserver la transparence des coins
        card.save(output_path, 'PNG')
        return True
    except Exception as e:
        logging.error(f"Error processing card logo: {str(e)}")
        raise
