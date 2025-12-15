import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import math
import io
from pillow_heif import register_heif_opener

# Register HEIF/HEIC image support
register_heif_opener()

# --- CONFIGURATION ---
ANCHOR_OPTIONS = ["center", "start", "end"]
MODE_OPTIONS = ["auto", "landscape", "portrait"]

# Initialize session state
if "target_ratios" not in st.session_state:
    st.session_state.target_ratios = {
        "landscape": (15, 10),
        "portrait": (10, 15),
        "square": (15, 15),
    }

if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

if "log_messages" not in st.session_state:
    st.session_state.log_messages = []

# --- HELPER FUNCTIONS ---

def log_message(msg):
    """Appends log message to session state."""
    st.session_state.log_messages.append(msg)

def get_aspect_ratio(width, height):
    """Returns aspect ratio as a simplified string like '3x2'."""
    gcd = math.gcd(width, height)
    return f"{width // gcd}x{height // gcd}"

def get_orientation(width, height):
    """Returns orientation: 'landscape', 'portrait', or 'square'."""
    if width > height:
        return "landscape"
    elif height > width:
        return "portrait"
    return "square"

def get_crop_coords(start, length, crop_length, anchor):
    """Calculates cropping start and end points based on anchor."""
    if anchor == "start":
        return start, start + crop_length
    elif anchor == "end":
        return start + (length - crop_length), start + length
    else:  # center
        offset = (length - crop_length) // 2
        return start + offset, start + offset + crop_length

def get_target_crop_box(width, height, target_ratio, anchor):
    """Returns crop box (x0, y0, x1, y1) to achieve the target aspect ratio."""
    target_w, target_h = target_ratio
    current_ratio = width / height
    target_ratio_float = target_w / target_h

    if current_ratio > target_ratio_float:
        new_width = int(height * target_ratio_float)
        x0, x1 = get_crop_coords(0, width, new_width, anchor)
        return (x0, 0, x1, height)
    else:
        new_height = int(width / target_ratio_float)
        y0, y1 = get_crop_coords(0, height, new_height, anchor)
        return (0, y0, width, y1)

def determine_target_ratio(width, height, mode):
    """Determines target crop ratio based on mode or image orientation."""
    if mode in ["landscape", "portrait"]:
        return st.session_state.target_ratios[mode], mode
    orientation = get_orientation(width, height)
    return st.session_state.target_ratios[orientation], orientation

def convert_image_only(image_file, anchor, mode):
    """Opens and crops image to target ratio (used for preview and processing)."""
    try:
        img = Image.open(image_file)
        img = img.convert("RGB")
        width, height = img.size
        target_ratio, _ = determine_target_ratio(width, height, mode)
        crop_box = get_target_crop_box(width, height, target_ratio, anchor)
        return img.crop(crop_box)
    except Exception as e:
        log_message(f"❌ Error processing image: {e}")
        return None

def image_to_bytes(image, format="JPEG"):
    """Converts PIL Image to bytes."""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format=format, quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr

# --- STREAMLIT UI ---

def main():
    st.set_page_config(
        page_title="Photo Cutter",
        page_icon="📸",
        layout="wide"
    )
    
    st.title("📸 Photo Cutter")
    st.markdown("Upload and crop images to custom aspect ratios")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Image Proportion Settings
        st.subheader("Image Proportion")
        col1, col2 = st.columns(2)
        with col1:
            width_ratio = st.number_input("Width", min_value=1, max_value=100, value=15, step=1)
        with col2:
            height_ratio = st.number_input("Height", min_value=1, max_value=100, value=10, step=1)
        
        if st.button("Apply Ratios", type="primary"):
            big, small = max(width_ratio, height_ratio), min(width_ratio, height_ratio)
            st.session_state.target_ratios["landscape"] = (big, small)
            st.session_state.target_ratios["portrait"] = (small, big)
            st.session_state.target_ratios["square"] = (small, big)
            log_message(f"🔧 Updated target ratios to: {big}x{small}")
            st.success(f"Ratios updated to {big}x{small}")
        
        st.divider()
        
        # Crop Settings
        st.subheader("Crop Settings")
        anchor = st.selectbox(
            "Anchor Position",
            ANCHOR_OPTIONS,
            index=ANCHOR_OPTIONS.index("center"),
            help="Where to anchor the crop"
        )
        
        mode = st.selectbox(
            "Orientation Mode",
            MODE_OPTIONS,
            index=MODE_OPTIONS.index("auto"),
            help="Auto detects orientation from image"
        )
        
        st.divider()
        
        # Display current ratios
        st.subheader("Current Ratios")
        st.text(f"Landscape: {st.session_state.target_ratios['landscape'][0]}x{st.session_state.target_ratios['landscape'][1]}")
        st.text(f"Portrait: {st.session_state.target_ratios['portrait'][0]}x{st.session_state.target_ratios['portrait'][1]}")
    
    # Main content area
    uploaded_files = st.file_uploader(
        "Upload Image(s)",
        type=["jpg", "jpeg", "png", "heic"],
        accept_multiple_files=True,
        help="Select one or more images to process"
    )
    
    if uploaded_files:
        # Create tabs for each uploaded image
        if len(uploaded_files) == 1:
            # Single image - no tabs needed
            process_single_image(uploaded_files[0], anchor, mode)
        else:
            # Multiple images - use tabs
            tabs = st.tabs([f"📷 {file.name}" for file in uploaded_files])
            for tab, uploaded_file in zip(tabs, uploaded_files):
                with tab:
                    process_single_image(uploaded_file, anchor, mode)
    
    # Log section at the bottom
    if st.session_state.log_messages:
        with st.expander("📋 Processing Log", expanded=False):
            for msg in st.session_state.log_messages:
                st.text(msg)

def process_single_image(uploaded_file, anchor, mode):
    """Process and display a single image."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original")
        original_img = Image.open(uploaded_file)
        st.image(original_img, use_container_width=True)
        
        # Display image info
        width, height = original_img.size
        orientation = get_orientation(width, height)
        st.caption(f"Size: {width}x{height} | Ratio: {get_aspect_ratio(width, height)} | {orientation.title()}")
    
    with col2:
        st.subheader("Preview (Cropped)")
        
        # Reset file pointer
        uploaded_file.seek(0)
        cropped_img = convert_image_only(uploaded_file, anchor, mode)
        
        if cropped_img:
            st.image(cropped_img, use_container_width=True)
            
            # Display cropped image info
            crop_width, crop_height = cropped_img.size
            st.caption(f"Size: {crop_width}x{crop_height} | Ratio: {get_aspect_ratio(crop_width, crop_height)}")
            
            # Download button
            img_bytes = image_to_bytes(cropped_img)
            base_name = os.path.splitext(uploaded_file.name)[0]
            
            st.download_button(
                label="💾 Download Cropped Image",
                data=img_bytes,
                file_name=f"{base_name}_cropped.jpg",
                mime="image/jpeg",
                type="primary"
            )
            
            log_message(f"✅ Processed: {uploaded_file.name} | Anchor: {anchor} | Mode: {mode}")
        else:
            st.error("Failed to process image")
            log_message(f"❌ Failed to process: {uploaded_file.name}")

if __name__ == "__main__":
    main()