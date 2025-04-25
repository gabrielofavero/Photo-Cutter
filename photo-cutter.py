import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import math
import tempfile
from pillow_heif import register_heif_opener

register_heif_opener()

# Global Settings
ANCHOR_OPTIONS = ["center", "start", "end"]
MODE_OPTIONS = ["auto", "landscape", "portrait"]
CROP_ANCHOR = "center"
CROP_FORCE_MODE = "auto"
TARGET_RATIOS = {
    "landscape": (15, 10),
    "portrait": (10, 15),
    "square": (10, 15),
}

selected_files = []
current_index = 0
preview_temp_path = None

# Helper Functions
def get_aspect_ratio(width, height):
    gcd = math.gcd(width, height)
    return f"{width // gcd}x{height // gcd}"

def get_orientation(width, height):
    if width > height:
        return "landscape"
    elif height > width:
        return "portrait"
    else:
        return "square"

def get_crop_coords(start, length, crop_length, anchor):
    if anchor == "start":
        return start, start + crop_length
    elif anchor == "end":
        return start + (length - crop_length), start + length
    else:
        offset = (length - crop_length) // 2
        return start + offset, start + offset + crop_length

def get_target_crop_box(width, height, target_ratio, anchor):
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
    if mode == "landscape":
        return TARGET_RATIOS["landscape"], "landscape"
    elif mode == "portrait":
        return TARGET_RATIOS["portrait"], "portrait"
    else:
        orientation = get_orientation(width, height)
        return TARGET_RATIOS[orientation], orientation

def convert_image_only(file_path, anchor, mode):
    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            target_ratio, _ = determine_target_ratio(width, height, mode)
            crop_box = get_target_crop_box(width, height, target_ratio, anchor)
            return img.crop(crop_box)
    except Exception as e:
        print(f"❌ Error processing {file_path} for preview: {e}")
        return None

def save_image(image, original_path):
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    new_path = os.path.join(os.path.dirname(original_path), f"{base_name}.jpg")
    image.save(new_path, format="JPEG", quality=95)
    if not original_path.lower().endswith('.jpg'):
        os.remove(original_path)
    return new_path

def process_and_save(file_path, anchor, mode):
    image = convert_image_only(file_path, anchor, mode)
    if image:
        log_message(f"✅ Converted '{os.path.basename(file_path)}' successfully.")
        saved_path = save_image(image, file_path)
        log_message(f"💾 Saved to: {saved_path}")
        return saved_path
    else:
        log_message(f"❌ Failed to convert: {file_path}")
        return None

# GUI Functions
def process_files():
    global selected_files, current_index
    file_paths = filedialog.askopenfilenames(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.heic")])
    if not file_paths:
        return
    selected_files = list(file_paths)
    current_index = 0
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.config(state=tk.DISABLED)
    update_preview()

def update_preview():
    global preview_temp_path
    if not selected_files or current_index >= len(selected_files):
        preview_label.config(image='')
        preview_label.image = None
        begin_button.config(state=tk.DISABLED)
        log_message("✅ All files processed.")
        return

    current_path = selected_files[current_index]
    image = convert_image_only(current_path, CROP_ANCHOR, CROP_FORCE_MODE)
    if image:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        preview_temp_path = temp_file.name
        image.thumbnail((300, 300))
        image.save(preview_temp_path, format="JPEG")
        img = Image.open(preview_temp_path)
        img_tk = ImageTk.PhotoImage(img)
        preview_label.config(image=img_tk)
        preview_label.image = img_tk
        begin_button.config(state=tk.NORMAL)
        log_message(f"🔍 Previewing: {os.path.basename(current_path)}")

def begin_process():
    global current_index
    if selected_files and current_index < len(selected_files):
        file_path = selected_files[current_index]
        process_and_save(file_path, CROP_ANCHOR, CROP_FORCE_MODE)
        current_index += 1
        update_preview()

def update_anchor(val):
    global CROP_ANCHOR
    CROP_ANCHOR = val
    update_preview()

def update_mode(val):
    global CROP_FORCE_MODE
    CROP_FORCE_MODE = val
    update_preview()

def log_message(msg):
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, msg + "\n")
    output_text.see(tk.END)
    output_text.config(state=tk.DISABLED)

# GUI Setup
root = tk.Tk()
root.title("🖼️ Image Cropper")
root.resizable(False, False)

frame = ttk.Frame(root, padding=10)
frame.pack(fill=tk.BOTH, expand=False)

ttk.Label(frame, text="Crop Anchor:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
anchor_menu = tk.StringVar(value=CROP_ANCHOR)
ttk.OptionMenu(frame, anchor_menu, CROP_ANCHOR, *ANCHOR_OPTIONS, command=update_anchor).grid(row=0, column=1, padx=5, pady=5)

ttk.Label(frame, text="Crop Mode:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
mode_menu = tk.StringVar(value=CROP_FORCE_MODE)
ttk.OptionMenu(frame, mode_menu, CROP_FORCE_MODE, *MODE_OPTIONS, command=update_mode).grid(row=1, column=1, padx=5, pady=5)

ttk.Button(frame, text="📂 Process File(s)", command=process_files).grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

preview_label = ttk.Label(frame)
preview_label.grid(row=4, column=0, columnspan=2, pady=10)

begin_button = ttk.Button(frame, text="Begin", state=tk.DISABLED, command=begin_process)
begin_button.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")

output_text = tk.Text(frame, height=15, width=80, font=("Consolas", 9), bg="#1e1e1e", fg="#c5c5c5", wrap="word")
output_text.grid(row=6, column=0, columnspan=2, padx=5, pady=10)
output_text.config(state=tk.DISABLED)

root.mainloop()
