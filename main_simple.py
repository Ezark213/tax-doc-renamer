#!/usr/bin/env python3
"""
Tax Document Renamer System v5.3.5 - Simple Version
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.unified_classifier import classify_document_unified_v5
    from core.rename_engine import generate_deterministic_filename_v5
    from helpers.yymm_policy import resolve_yymm_policy
except ImportError as e:
    print(f"Import error: {e}")
    print("Running in basic mode without advanced features")
    
    def classify_document_unified_v5(text, filename, **kwargs):
        return type('Result', (), {'document_type': 'unknown', 'confidence': 0.5})()
    
    def generate_deterministic_filename_v5(**kwargs):
        return "renamed_document.pdf"
    
    def resolve_yymm_policy(**kwargs):
        return "2508"

class SimpleTaxDocumentRenamer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tax Document Renamer v5.3.5")
        self.root.geometry("800x600")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Tax Document Renamer System v5.3.5", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # File selection
        ttk.Label(main_frame, text="Select Files:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.file_list = tk.Listbox(file_frame, height=8)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear List", command=self.clear_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Process Files", command=self.process_files).pack(side=tk.LEFT, padx=5)
        
        # Output folder
        ttk.Label(main_frame, text="Output Folder:").grid(row=4, column=0, sticky=tk.W, pady=(20,5))
        
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.output_folder_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop"))
        ttk.Entry(folder_frame, textvariable=self.output_folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="Browse", command=self.browse_output_folder).pack(side=tk.RIGHT, padx=(5,0))
        
        # Log area
        ttk.Label(main_frame, text="Processing Log:").grid(row=6, column=0, sticky=tk.W, pady=(20,5))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = tk.Text(log_frame, height=12)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF or CSV files",
            filetypes=[("Supported files", "*.pdf *.csv"), ("PDF files", "*.pdf"), ("CSV files", "*.csv")]
        )
        
        for file in files:
            self.file_list.insert(tk.END, file)
            
        self.log(f"Added {len(files)} files")
        
    def clear_files(self):
        self.file_list.delete(0, tk.END)
        self.log("File list cleared")
        
    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
            
    def process_files(self):
        files = list(self.file_list.get(0, tk.END))
        output_folder = self.output_folder_var.get()
        
        if not files:
            messagebox.showwarning("No Files", "Please add files to process")
            return
            
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output folder: {e}")
                return
                
        self.log("Processing started...")
        processed = 0
        
        for file_path in files:
            try:
                if not os.path.exists(file_path):
                    self.log(f"File not found: {file_path}")
                    continue
                    
                filename = os.path.basename(file_path)
                self.log(f"Processing: {filename}")
                
                # Simple rename logic
                base_name, ext = os.path.splitext(filename)
                new_filename = f"processed_{base_name}_{processed:03d}{ext}"
                new_path = os.path.join(output_folder, new_filename)
                
                # Copy file
                import shutil
                shutil.copy2(file_path, new_path)
                
                self.log(f"Renamed: {filename} -> {new_filename}")
                processed += 1
                
            except Exception as e:
                self.log(f"Error processing {filename}: {e}")
                
        self.log(f"Processing completed. {processed} files processed.")
        messagebox.showinfo("Complete", f"Processing completed. {processed} files processed.")
        
    def run(self):
        self.log("Tax Document Renamer System v5.3.5 started")
        self.log("Ready to process files...")
        self.root.mainloop()

if __name__ == "__main__":
    app = SimpleTaxDocumentRenamer()
    app.run()