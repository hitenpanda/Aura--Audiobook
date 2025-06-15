import tkinter
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import fitz  # PyMuPDF
import pyttsx3
import threading
import os

# --- Core Application Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Aura Audiobooks")
        self.geometry("700x550")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Appearance ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- State Variables ---
        self.pdf_path = ""
        self.is_converting = False

        # --- Load Resources ---
        self.load_icons()
        self.initialize_tts_engine()
        
        # --- UI Widgets ---
        self.create_widgets()

    def load_icons(self):
        """Loads icons from files, handling potential errors."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.book_icon = ctk.CTkImage(Image.open(os.path.join(current_dir, "book.png")), size=(24, 24))
            self.sound_icon = ctk.CTkImage(Image.open(os.path.join(current_dir, "sound.png")), size=(24, 24))
        except Exception:
            self.book_icon = None
            self.sound_icon = None
            print("Warning: Icon files (book.png, sound.png) not found. Continuing without icons.")

    def initialize_tts_engine(self):
        """Initializes the TTS engine and populates voice options robustly."""
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            self.voice_map = {}
            for v in voices:
                lang = f" ({v.languages[0]})" if v.languages else ""
                display_name = f"{v.name}{lang}"
                self.voice_map[display_name] = v.id
            self.voice_names = list(self.voice_map.keys())
            engine.stop()
        except Exception as e:
            self.voice_map = {"Default": "default"}
            self.voice_names = ["Default"]
            self.after(100, lambda: self.handle_error(f"Could not load system voices. Error: {e}"))

    def create_widgets(self):
        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.title_icon_label = ctk.CTkLabel(self.header_frame, text="", image=self.book_icon)
        self.title_icon_label.grid(row=0, column=0, padx=(0, 10))

        self.title_label = ctk.CTkLabel(self.header_frame, text="Aura Audiobooks", font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.grid(row=0, column=1, sticky="w")

        # --- Main Content Frame ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        # --- File Selection ---
        self.select_button = ctk.CTkButton(
            self.main_frame, text="Select PDF to Convert", command=self.select_pdf,
            height=50, font=ctk.CTkFont(size=16, weight="bold"), corner_radius=10
        )
        self.select_button.grid(row=0, column=0, padx=40, pady=(40, 10))

        self.file_label = ctk.CTkLabel(self.main_frame, text="", text_color=self.main_frame.cget("fg_color"))
        self.file_label.grid(row=1, column=0, padx=40, pady=(0, 20))

        # --- Voice Selection ---
        self.voice_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.voice_frame.grid(row=2, column=0, pady=(10,20))
        self.voice_label = ctk.CTkLabel(self.voice_frame, text="Select Voice:", image=self.sound_icon, compound="left", font=ctk.CTkFont(size=14))
        self.voice_label.grid(row=0, column=0, padx=(0,10))
        self.voice_combo = ctk.CTkComboBox(self.voice_frame, values=self.voice_names, width=250)
        if self.voice_names:
            self.voice_combo.set(self.voice_names[0])
        self.voice_combo.grid(row=0, column=1)

        # --- Status & Progress ---
        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready to begin.", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=3, column=0, padx=20, pady=10, sticky="s")

        self.progress_bar = ctk.CTkProgressBar(self.main_frame, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=4, column=0, padx=40, pady=(10, 40), sticky="ew")

    def select_pdf(self):
        """Opens a file dialog to select a PDF and triggers the conversion thread."""
        if self.is_converting: return

        self.pdf_path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if self.pdf_path:
            self.is_converting = True
            display_path = os.path.basename(self.pdf_path)
            self.animate_fade_in(display_path)
            conversion_thread = threading.Thread(target=self.convert_pdf_to_audio, daemon=True)
            conversion_thread.start()

    def convert_pdf_to_audio(self):
        """Extracts text and converts to audio in a background thread."""
        engine = None
        doc = None
        try:
            self.after(0, self.update_ui_for_processing)
            self.after(0, self.update_status, "Opening PDF...")
            
            # Open and validate PDF
            doc = fitz.open(self.pdf_path)
            if doc.page_count == 0:
                raise ValueError("The PDF file appears to be empty")
                
            # Extract text with improved handling
            total_pages = doc.page_count
            full_text = []
            for page_num in range(total_pages):
                self.after(0, self.update_status, f"Reading page {page_num + 1}/{total_pages}")
                page = doc[page_num]
                # Get text with better formatting preservation
                page_text = page.get_text("text").strip()
                if page_text:  # Only add non-empty pages
                    full_text.append(page_text)
                progress = (page_num + 1) / total_pages
                self.after(0, self.progress_bar.set, progress)
            
            # Join text and clean it
            cleaned_text = " ".join(full_text)
            if not cleaned_text.strip():
                raise ValueError("No readable text found in the PDF")
            
            # Initialize TTS engine
            self.after(0, self.update_status, "Initializing audio engine...")
            engine = pyttsx3.init()
            
            # Configure voice
            selected_voice_name = self.voice_combo.get()
            voice_id = self.voice_map.get(selected_voice_name)
            if voice_id and voice_id != "default":
                engine.setProperty('voice', voice_id)
            
            # Set speech properties for better quality
            engine.setProperty('rate', 175)  # Slightly slower than default
            engine.setProperty('volume', 0.9)  # Slightly quieter than maximum
            
            # Save audio file
            self.after(0, self.update_status, "Converting text to speech...")
            output_path = os.path.splitext(self.pdf_path)[0] + ".mp3"
            engine.save_to_file(cleaned_text, output_path)
            engine.runAndWait()
            
            self.after(0, self.finish_conversion, output_path)
        except Exception as e:
            self.after(0, self.handle_error, str(e))
        finally:
            self.is_converting = False

    def update_ui_for_processing(self):
        self.select_button.configure(state="disabled", text="Converting...")
        self.voice_combo.configure(state="disabled")
        self.progress_bar.set(0)

    def finish_conversion(self, audio_path):
        self.progress_bar.set(1)
        short_path = os.path.basename(audio_path)
        self.status_label.configure(text=f"Success! Saved as {short_path}", text_color="#5cb85c")
        self.select_button.configure(state="normal", text="Select Another PDF")
        self.voice_combo.configure(state="normal")

    def handle_error(self, error_message):
        if self.is_converting or "Could not load" in error_message:
            messagebox.showerror("Application Error", f"An error occurred:\n\n{error_message}")
        
        self.status_label.configure(text="An error occurred. Ready to try again.", text_color="#d9534f")
        self.select_button.configure(state="normal", text="Select PDF File")
        self.voice_combo.configure(state="normal")
        self.progress_bar.set(0)
        self.is_converting = False

    def update_status(self, message):
        self.status_label.configure(text=message, text_color="gray80")

    def animate_fade_in(self, text, step=0):
        """Animates the file label by fading it in from the background color."""
        if step == 0:
            self.file_label.configure(text=text)
            
        num_steps = 20
        if step <= num_steps:
            # Calculate opacity for this step (0.0 to 1.0)
            opacity = step / num_steps
            
            # Get the frame's background color from customtkinter's theme
            current_mode = ctk.get_appearance_mode().lower()
            frame_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"][current_mode == "dark"]
            text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"][current_mode == "dark"]
            
            # Use the opacity to blend between frame color and text color
            self.file_label.configure(text_color=text_color)
            
            # Schedule next step
            if step < num_steps:
                self.after(20, self.animate_fade_in, text, step + 1)

if __name__ == "__main__":
    app = App()
    app.mainloop()