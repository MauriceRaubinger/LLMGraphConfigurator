import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
import json
import os
import datetime
from tkinter.scrolledtext import ScrolledText


class LLMTSupDocumentationCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("LLMTSup - Documentation Creator")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f8ff")  # Light blue background

        # Set application icon (if available)
        try:
            self.root.iconbitmap("icon.ico")  # Place an icon file named icon.ico in the same directory
        except:
            pass

        # Custom style
        self.style = ttk.Style()
        self.style.configure("Blue.TFrame", background="#1e88e5")
        self.style.configure("White.TFrame", background="#ffffff")
        self.style.configure("Blue.TButton", background="#1976d2", foreground="white",
                             font=("Arial", 10, "bold"), borderwidth=1)
        self.style.map("Blue.TButton",
                       background=[("active", "#0d47a1")])
        self.style.configure("Title.TLabel", background="#1e88e5", foreground="white",
                             font=("Arial", 16, "bold"))
        self.style.configure("Category.TLabel", background="#e3f2fd", foreground="#0d47a1",
                             font=("Arial", 10, "bold"), padding=5)

        # Header
        self.header = ttk.Frame(root, style="Blue.TFrame", height=80)
        self.header.pack(fill="x", padx=0, pady=0)

        title_label = ttk.Label(self.header, text="LLMTSup Documentation Creator",
                                style="Title.TLabel")
        title_label.pack(pady=20)

        # Main content
        self.main_frame = ttk.Frame(root, style="White.TFrame")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Create panes
        self.paned_window = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL,
                                           sashwidth=4, sashrelief=tk.RAISED, bg="#bbdefb")
        self.paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        # Left panel - Categories
        self.left_panel = ttk.Frame(self.paned_window, width=250, style="White.TFrame")
        self.paned_window.add(self.left_panel)

        # Category controls
        cat_header = ttk.Frame(self.left_panel, style="Blue.TFrame")
        cat_header.pack(fill="x", pady=(0, 10))

        ttk.Label(cat_header, text="DOCUMENTATION CATEGORIES",
                  style="Title.TLabel", font=("Arial", 11)).pack(pady=8)

        button_frame = ttk.Frame(self.left_panel, style="White.TFrame")
        button_frame.pack(fill="x", padx=10, pady=(5, 10))

        ttk.Button(button_frame, text="+ Add Category", command=self.add_category,
                   style="Blue.TButton").pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(button_frame, text="− Remove", command=self.remove_category,
                   style="Blue.TButton").pack(side="left", fill="x", expand=True, padx=2)

        self.category_listbox = tk.Listbox(self.left_panel, selectmode=tk.SINGLE,
                                           bg="white", fg="#0d47a1", font=("Arial", 10),
                                           relief="flat", highlightthickness=0)
        self.category_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.category_listbox.bind('<<ListboxSelect>>', self.select_category)

        # Right panel - Editor
        self.right_panel = ttk.Frame(self.paned_window, style="White.TFrame")
        self.paned_window.add(self.right_panel, stretch="always")

        self.editor_header = ttk.Frame(self.right_panel, style="Blue.TFrame")
        self.editor_header.pack(fill="x", pady=(0, 10))

        self.editor_label = ttk.Label(self.editor_header, text="SELECT A CATEGORY TO EDIT",
                                      style="Title.TLabel", font=("Arial", 11))
        self.editor_label.pack(pady=8)

        # Editor with scrollbar
        self.editor_frame = ttk.Frame(self.right_panel, style="White.TFrame")
        self.editor_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.text_editor = ScrolledText(self.editor_frame, wrap="word", undo=True,
                                        bg="white", fg="#0d47a1", font=("Arial", 11),
                                        padx=10, pady=10, relief="flat", highlightthickness=0)
        self.text_editor.pack(fill="both", expand=True)
        self.text_editor.config(insertbackground="#1976d2")  # Blue cursor
        self.text_editor.bind("<KeyRelease>", self.save_content)

        # Status bar
        self.status_frame = ttk.Frame(root, style="Blue.TFrame", height=30)
        self.status_frame.pack(fill="x", padx=0, pady=0)

        self.status_var = tk.StringVar()
        self.status_var.set("LLMTSup Documentation Creator - Ready")
        self.status_bar = ttk.Label(self.status_frame, textvariable=self.status_var,
                                    style="Category.TLabel", anchor="w")
        self.status_bar.pack(fill="x", padx=10)

        # Create menu
        self.create_menu()

        # Initialize data
        self.categories = {}
        self.current_category = None
        self.filename = "llmtsup_docs.json"  # Default file name

        # Try to load default file on startup
        self.load_from_file(self.filename)

        # Set initial paned window position
        self.paned_window.sash_place(0, 250, 0)

    def create_menu(self):
        self.menu_bar = tk.Menu(self.root, bg="#e3f2fd", fg="#0d47a1", activebackground="#bbdefb")

        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#e3f2fd", fg="#0d47a1",
                                 activebackground="#bbdefb")
        self.file_menu.add_command(label="New", command=self.new_file)
        self.file_menu.add_command(label="Save", command=self.save_to_file)
        self.file_menu.add_command(label="Save As...", command=self.save_as)
        self.file_menu.add_command(label="Open...", command=self.load_from_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export to Markdown...", command=self.export_markdown)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_app)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        # Edit menu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#e3f2fd", fg="#0d47a1",
                                 activebackground="#bbdefb")
        self.edit_menu.add_command(label="Add Category", command=self.add_category)
        self.edit_menu.add_command(label="Remove Category", command=self.remove_category)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Clear All", command=self.clear_all)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)

        # View menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#e3f2fd", fg="#0d47a1",
                                 activebackground="#bbdefb")
        self.view_menu.add_command(label="Toggle Fullscreen", command=self.toggle_fullscreen)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)

        # Help menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0, bg="#e3f2fd", fg="#0d47a1",
                                 activebackground="#bbdefb")
        self.help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        self.root.config(menu=self.menu_bar)

    def update_status(self, message):
        self.status_var.set(message)

    def add_category(self):
        name = simpledialog.askstring("New Category", "Enter category name:")
        if name and name.strip():
            if name in self.categories:
                messagebox.showerror("Error", "Category already exists!")
                return
            self.categories[name] = ""
            self.category_listbox.insert(tk.END, name)
            self.category_listbox.selection_clear(0, tk.END)
            self.category_listbox.selection_set(tk.END)
            self.select_category()
            self.save_to_file()
            self.update_status(f"Added category: {name}")

    def remove_category(self):
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "No category selected")
            return
        index = selection[0]
        name = self.category_listbox.get(index)

        if messagebox.askyesno("Confirm", f"Delete '{name}' and its contents?"):
            del self.categories[name]
            self.category_listbox.delete(index)
            self.current_category = None
            self.editor_label.config(text="SELECT A CATEGORY TO EDIT")
            self.text_editor.delete(1.0, tk.END)
            self.save_to_file()
            self.update_status(f"Removed category: {name}")

    def select_category(self, event=None):
        selection = self.category_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        name = self.category_listbox.get(index)

        if self.current_category:
            self.save_content()

        self.current_category = name
        self.editor_label.config(text=f"EDITING: {name}")
        self.text_editor.delete(1.0, tk.END)
        self.text_editor.insert(tk.END, self.categories[name])
        self.update_status(f"Editing category: {name}")

    def save_content(self, event=None):
        if self.current_category:
            content = self.text_editor.get(1.0, tk.END)
            self.categories[self.current_category] = content.strip()
            self.save_to_file()

    def save_to_file(self, filename=None):
        filename = filename or self.filename
        try:
            with open(filename, 'w') as f:
                json.dump(self.categories, f, indent=4)
            self.update_status(f"Saved: {filename} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{str(e)}")

    def save_as(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="llmtsup_docs.json"
        )
        if filename:
            self.filename = filename
            self.save_to_file()

    def load_from_file(self, filename=None):
        if not filename:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if not filename:
                return

        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.categories = json.load(f)
                self.filename = filename

                # Update UI
                self.category_listbox.delete(0, tk.END)
                for category in self.categories:
                    self.category_listbox.insert(tk.END, category)

                self.current_category = None
                self.editor_label.config(text="SELECT A CATEGORY TO EDIT")
                self.text_editor.delete(1.0, tk.END)

                self.update_status(f"Loaded: {filename} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
                self.root.title(f"LLMTSup - {os.path.basename(filename)}")
            else:
                self.update_status(f"New file: {filename}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load file:\n{str(e)}")

    def new_file(self):
        if messagebox.askyesno("New File", "Create a new documentation file? Current data will be lost."):
            self.categories = {}
            self.category_listbox.delete(0, tk.END)
            self.current_category = None
            self.editor_label.config(text="SELECT A CATEGORY TO EDIT")
            self.text_editor.delete(1.0, tk.END)
            self.filename = "llmtsup_docs.json"
            self.update_status("Created new documentation file")

    def clear_all(self):
        if messagebox.askyesno("Clear All", "Remove all categories and content?"):
            self.categories = {}
            self.category_listbox.delete(0, tk.END)
            self.current_category = None
            self.editor_label.config(text="SELECT A CATEGORY TO EDIT")
            self.text_editor.delete(1.0, tk.END)
            self.save_to_file()
            self.update_status("Cleared all categories and content")

    def export_markdown(self):
        if not self.categories:
            messagebox.showinfo("Export", "No content to export")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
            initialfile="llmtsup_docs.md"
        )
        if not filename:
            return

        try:
            with open(filename, 'w') as f:
                f.write("# LLMTSup Documentation\n\n")
                f.write(f"*Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")

                for category, content in self.categories.items():
                    f.write(f"## {category}\n\n")
                    f.write(content + "\n\n")

            self.update_status(f"Exported Markdown: {filename}")
            messagebox.showinfo("Export Successful", "Documentation exported to Markdown format")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export file:\n{str(e)}")

    def toggle_fullscreen(self):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def show_about(self):
        about_text = """LLMTSup Documentation Creator

Version 1.0
Developed for LLMTSup

A simple and intuitive tool for creating and managing documentation with categories. Features include:
- Create and manage documentation categories
- Rich text editing with auto-save
- JSON file saving and loading
- Export to Markdown format
- Blue and white theme

© 2023 LLMTSup - All Rights Reserved"""
        messagebox.showinfo("About LLMTSup Documentation Creator", about_text)

    def exit_app(self):
        self.save_to_file()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LLMTSupDocumentationCreator(root)
    root.mainloop()