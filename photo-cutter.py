import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import math
import tempfile
from pillow_heif import register_heif_opener

# Register HEIF/HEIC image support
register_heif_opener()

# --- CONFIGURATION ---
ANCHOR_OPTIONS = ["center", "start", "end"]
MODE_OPTIONS = ["auto", "landscape", "portrait"]
TARGET_RATIOS = {
    "landscape": (15, 10),
    "portrait": (10, 15),
    "square": (15, 15),
}

# --- APP STATE ---
app_state = {
    "selected_files": [],
    "current_index": 0,
    "preview_temp_path": None,
    "crop_anchor": "center",
    "crop_mode": "auto"
}

# --- IMAGE UTILS ---

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
        return TARGET_RATIOS[mode], mode
    orientation = get_orientation(width, height)
    return TARGET_RATIOS[orientation], orientation

def convert_image_only(file_path, anchor, mode):
    """Opens and crops image to target ratio (used for preview and processing)."""
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            target_ratio, _ = determine_target_ratio(width, height, mode)
            crop_box = get_target_crop_box(width, height, target_ratio, anchor)
            return img.crop(crop_box)
    except Exception as e:
        log_message(f"❌ Error processing '{file_path}': {e}")
        return None

def save_image(image, original_path):
    """Saves the cropped image as JPEG and deletes original if not JPEG."""
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    output_path = os.path.join(os.path.dirname(original_path), f"{base_name}.jpg")
    image.save(output_path, format="JPEG", quality=95)

    ext = os.path.splitext(original_path)[1].lower()
    if ext != ".jpg":
        os.remove(original_path)
        log_message(f"🗑️ Original '{ext}' file removed after converting to JPEG.")

    return output_path

def process_and_save(file_path, anchor, mode):
    """Processes and saves cropped image."""
    image = convert_image_only(file_path, anchor, mode)
    if image:
        log_message(f"✅ Cropped '{os.path.basename(file_path)}'")
        output_path = save_image(image, file_path)
        log_message(f"💾 Saved to: {output_path}")
        return output_path
    log_message(f"❌ Failed to process: {file_path}")
    messagebox.showinfo("Failed", f"Failed to process: {file_path}")
    return None

def update_target_ratios():
    try:
        w = int(width_var.get())
        h = int(height_var.get())
        if w <= 0 or h <= 0:
            raise ValueError("Width and height must be positive integers")

        big, small = max(w, h), min(w, h)
        TARGET_RATIOS["landscape"] = (big, small)
        TARGET_RATIOS["portrait"] = (small, big)
        TARGET_RATIOS["square"] = (small, big)  # Keeping square same as portrait

        log_message(f"🔧 Updated target ratios to: {big}x{small}")
        update_preview()
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter valid positive integers for width and height.")

# --- GUI FUNCTIONS ---

def log_message(msg):
    """Appends log message to the output box."""
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, msg + "\n")
    output_text.see(tk.END)
    output_text.config(state=tk.DISABLED)

def create_placeholder(mode="auto"):
    """Creates a placeholder image with text and correct aspect ratio."""
    width, height = 450, 300
    if mode == "portrait":
        width, height = 300, 450
    elif mode == "square":
        width = height = 400

    image = Image.new("RGB", (width, height), color="gray")
    draw = ImageDraw.Draw(image)

    text = "Load an image to begin"
    font_size = 24
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    text_width = draw.textlength(text, font=font)
    text_position = ((width - text_width) // 2, height // 2 - font_size // 2)
    draw.text(text_position, text, fill="white", font=font)

    image.thumbnail((300, 300))
    return image

def update_preview():
    """Displays preview of the current image."""
    index = app_state["current_index"]
    files = app_state["selected_files"]

    if not files or index >= len(files):
        placeholder = create_placeholder(app_state["crop_mode"])
        placeholder_tk = ImageTk.PhotoImage(placeholder)
        preview_label.config(image=placeholder_tk)
        preview_label.image = placeholder_tk
        process_button.config(state=tk.DISABLED)
        log_message("✅ All files processed")
        messagebox.showinfo("Success", "All files processed")
        return

    path = files[index]
    anchor = app_state["crop_anchor"]
    mode = app_state["crop_mode"]
    image = convert_image_only(path, anchor, mode)

    if image:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        app_state["preview_temp_path"] = temp_file.name
        image.thumbnail((300, 300))
        image.save(app_state["preview_temp_path"], format="JPEG")

        img = Image.open(app_state["preview_temp_path"])
        img_tk = ImageTk.PhotoImage(img)
        preview_label.config(image=img_tk)
        preview_label.image = img_tk

        process_button.config(state=tk.NORMAL)
        log_message(f"🔍 Previewing: {os.path.basename(path)} | Anchor: {anchor}, Orientation: {mode}")

def begin_process():
    """Processes the current image and loads the next one."""
    index = app_state["current_index"]
    files = app_state["selected_files"]
    if index >= len(files):
        return

    path = files[index]
    anchor = app_state["crop_anchor"]
    mode = app_state["crop_mode"]
    process_and_save(path, anchor, mode)

    app_state["current_index"] += 1
    update_preview()

def update_anchor(val):
    app_state["crop_anchor"] = val
    update_preview()

def update_mode(val):
    app_state["crop_mode"] = val
    update_preview()

def select_files():
    """Opens file dialog and starts previewing selected files."""
    file_paths = filedialog.askopenfilenames(
        filetypes=[("Image Files", "*.jpg *.jpeg *.png *.heic")]
    )
    if not file_paths:
        return
    app_state["selected_files"] = list(file_paths)
    app_state["current_index"] = 0

    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.config(state=tk.DISABLED)

    update_preview()

# --- GUI SETUP ---

root = tk.Tk()
root.title("Photo Cutter")
root.resizable(False, False)

frame = ttk.Frame(root, padding=10)
frame.pack(fill=tk.BOTH, expand=False)

# Proportion settings
proportion_frame = ttk.LabelFrame(frame, text="Image Proportion", padding=(10, 5))
proportion_frame.grid(row=0, column=2, rowspan=2, padx=(10, 0), sticky="nsew")

ttk.Label(proportion_frame, text="Width:").grid(row=0, column=0, padx=5, pady=5)
width_var = tk.StringVar(value="15")
ttk.Entry(proportion_frame, textvariable=width_var, width=5).grid(row=0, column=1, pady=5)

ttk.Label(proportion_frame, text="Height:").grid(row=1, column=0, padx=5, pady=5)
height_var = tk.StringVar(value="10")
ttk.Entry(proportion_frame, textvariable=height_var, width=5).grid(row=1, column=1, pady=5)

ttk.Button(proportion_frame, text="Apply", command=update_target_ratios).grid(row=2, column=0, columnspan=2, pady=10)

# Group crop settings
settings_frame = ttk.LabelFrame(frame, text="Crop Settings", padding=(10, 5))
settings_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")

ttk.Label(settings_frame, text="Anchor:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=5)
anchor_menu = tk.StringVar(value=app_state["crop_anchor"])
ttk.OptionMenu(settings_frame, anchor_menu, app_state["crop_anchor"], *ANCHOR_OPTIONS, command=update_anchor)\
    .grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

ttk.Label(settings_frame, text="Orientation:").grid(row=0, column=2, sticky="w", padx=(10, 5), pady=5)
mode_menu = tk.StringVar(value=app_state["crop_mode"])
ttk.OptionMenu(settings_frame, mode_menu, app_state["crop_mode"], *MODE_OPTIONS, command=update_mode)\
    .grid(row=0, column=3, sticky="ew", pady=5)

settings_frame.columnconfigure(1, weight=1)
settings_frame.columnconfigure(3, weight=1)

# File selection button
ttk.Button(frame, text="📂 Process File(s)", command=select_files)\
    .grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

# Preview
preview_label = ttk.Label(frame)
preview_label.grid(row=2, column=0, columnspan=2, pady=10)

# Process button
process_button = ttk.Button(frame, text="📸 Process Photo", state=tk.DISABLED, command=begin_process)
process_button.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

# Log output
output_text = tk.Text(frame, height=15, width=80, font=("Consolas", 9), bg="#1e1e1e", fg="#c5c5c5", wrap="word")
output_text.grid(row=4, column=0, columnspan=2, padx=5, pady=10)
output_text.config(state=tk.DISABLED)

# Load placeholder at startup
placeholder = create_placeholder(app_state["crop_mode"])
placeholder_tk = ImageTk.PhotoImage(placeholder)
preview_label.config(image=placeholder_tk)
preview_label.image = placeholder_tk

root.mainloop()