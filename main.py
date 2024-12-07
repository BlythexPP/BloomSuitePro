import os
import math
import struct
import tempfile
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class BloomFilter:
    def __init__(self, m=0, k=0, n=0, error_rate=0.0, bit_array=None):
        self.m = m
        self.k = k
        self.n = n
        self.error_rate = error_rate
        self.bit_array = bit_array if bit_array is not None else bytearray(math.ceil(m/8))

    @staticmethod
    def from_file(file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError("Bloom filter file does not exist.")

        with open(file_path, "rb") as f:
            data = f.read()

        if len(data) < 20:
            messagebox.showwarning(
                "File Structure Warning",
                "File is shorter than minimum header length (20 bytes). "
                "Data may be incomplete or corrupted."
            )
            m = k = n = 0
            error_rate = 0.0
            bit_array = bytearray()
            return BloomFilter(m, k, n, error_rate, bit_array)

        m, k, n, error_rate = struct.unpack("<iii d", data[:20])
        bit_array = bytearray(data[20:])
        required_bytes = math.ceil(m / 8)
        actual_bits = len(bit_array) * 8

        if actual_bits < m:
            messagebox.showwarning(
                "Bit Array Warning",
                f"Bit array is too short for declared size. "
                f"Declared {m} bits, got {actual_bits} bits. "
                "The filter may be incomplete or corrupted."
            )
            m = actual_bits
            required_bytes = len(bit_array)
        elif actual_bits > m:
            extra_bits = actual_bits - m
            if extra_bits > 7:
                messagebox.showinfo(
                    "Bit Array Info",
                    f"Bit array is longer than declared size by {extra_bits} bits. "
                    "Truncating extra bits."
                )
            bit_array = bit_array[:required_bytes]

        return BloomFilter(m, k, n, error_rate, bit_array)

    def to_file(self, file_path):
        header = struct.pack("<iii d", self.m, self.k, self.n, self.error_rate)
        with open(file_path, "wb") as f:
            f.write(header)
            f.write(self.bit_array)

    @staticmethod
    def optimal_parameters(num_elements, error_rate):
        if num_elements <= 0:
            raise ValueError("Number of elements must be greater than 0.")
        if not (0 < error_rate < 1):
            raise ValueError("Error rate must be between 0 and 1.")

        m = math.ceil(-num_elements * math.log(error_rate) / (math.log(2)**2))
        k = max(1, round((m / num_elements) * math.log(2)))
        return m, k

    def _hashes(self, item):
        base_hash = hash(item)
        for i in range(self.k):
            yield (base_hash + i * 0x9e3779b97f4a7c16) % self.m

    def add(self, item):
        for h in self._hashes(item):
            byte_idx = h // 8
            bit_idx = h % 8
            self.bit_array[byte_idx] |= (1 << bit_idx)
        self.n += 1

    @classmethod
    def from_text_file(cls, text_file, error_rate):
        if not os.path.exists(text_file):
            raise FileNotFoundError("Text file not found.")

        lines_count = 0
        with open(text_file, "r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                lines_count += 1

        if lines_count == 0:
            raise ValueError("No elements found in text file.")

        m, k = cls.optimal_parameters(lines_count, error_rate)
        bf = cls(m, k, 0, error_rate)

        with open(text_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                element = line.strip()
                if element:
                    bf.add(element)
        return bf


class BFAnalyzerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Professional Bloom Filter Suite")
        self.master.geometry("1000x600")

        style = ttk.Style()
        style.theme_use("clam")

        bg_color = "#f5f5f5"
        self.master.configure(bg=bg_color)
        self.master.option_add("*Font", "Helvetica 11")

        style.configure(".", background=bg_color, foreground="#333333")
        style.configure("TLabel", background=bg_color, foreground="#333333", font=("Helvetica", 11))
        style.configure("TButton", font=("Helvetica", 11), padding=5)
        style.configure("Heading.TLabel", font=("Helvetica", 14, "bold"), foreground="#222222")
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"), foreground="#222222")

        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_analyze = ttk.Frame(self.notebook, style="TFrame")
        self.tab_create = ttk.Frame(self.notebook, style="TFrame")
        self.tab_help = ttk.Frame(self.notebook, style="TFrame")

        self.notebook.add(self.tab_analyze, text="Analyze Bloom Filters")
        self.notebook.add(self.tab_create, text="Create Bloom Filter")
        self.notebook.add(self.tab_help, text="Help")

        self.init_analyze_tab()
        self.init_create_tab()
        self.init_help_tab()

    # Analyze Tab
    def init_analyze_tab(self):
        frame = self.tab_analyze

        ttk.Label(frame, text="Select a .bf file to analyze:", style="Heading.TLabel").pack(pady=10)

        columns = ("filename", "m", "k", "n", "error_rate")
        self.bf_tree = ttk.Treeview(frame, columns=columns, show='headings', height=8)
        self.bf_tree.heading("filename", text="File Name")
        self.bf_tree.heading("m", text="Bits (m)")
        self.bf_tree.heading("k", text="#Hashes (k)")
        self.bf_tree.heading("n", text="#Elements (n)")
        self.bf_tree.heading("error_rate", text="Error Rate")
        self.bf_tree.column("filename", width=200)
        self.bf_tree.column("m", width=100)
        self.bf_tree.column("k", width=100)
        self.bf_tree.column("n", width=100)
        self.bf_tree.column("error_rate", width=100)
        self.bf_tree.pack(pady=10, fill=tk.X, padx=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Analyze Selected", command=self.open_analysis_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_bf_list).pack(side=tk.LEFT, padx=5)

        self.refresh_bf_list()

    def refresh_bf_list(self):
        for item in self.bf_tree.get_children():
            self.bf_tree.delete(item)

        bf_files = [f for f in os.listdir() if f.lower().endswith(".bf")]
        for bf_file in bf_files:
            try:
                bf = BloomFilter.from_file(bf_file)
                m = bf.m
                k = bf.k
                n = bf.n
                error_rate = bf.error_rate
            except Exception:
                m = "?"
                k = "?"
                n = "?"
                error_rate = "?"
            
            self.bf_tree.insert("", tk.END, values=(bf_file, m, k, n, error_rate))

    def open_analysis_window(self):
        selection = self.bf_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a .bf file first.")
            return
        item = self.bf_tree.item(selection[0], 'values')
        selected_file = item[0]

        try:
            bf = BloomFilter.from_file(selected_file)
        except Exception as e:
            messagebox.showerror("Error loading Bloom Filter", str(e))
            return
        
        win = tk.Toplevel(self.master)
        win.title(f"Analyzing: {selected_file}")
        win.geometry("900x500")
        win.configure(bg="#f5f5f5")

        text_area = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=100, height=30, font=("Helvetica", 10))
        text_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        def show_output(text):
            text_area.insert(tk.END, text + "\n\n")
            text_area.see(tk.END)
        
        button_frame = ttk.Frame(win)
        button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        ttk.Label(button_frame, text="Options:", font=("Helvetica", 12, "bold")).pack(pady=5)
        
        def hex_dump():
            data = bf.bit_array
            lines = []
            bytes_per_line = 16
            for i in range(0, len(data), bytes_per_line):
                chunk = data[i:i+bytes_per_line]
                hex_part = ' '.join(f"{b:02x}" for b in chunk)
                ascii_part = ''.join((chr(b) if 32 <= b <= 126 else '.') for b in chunk)
                lines.append(f"{i:08x}  {hex_part:<{bytes_per_line*3}} {ascii_part}")
            show_output("--- Hex Dump of Bit Array ---\n" + "\n".join(lines))
        
        def ascii_preview():
            length = 64
            data = bf.bit_array[:length]
            ascii_str = ''.join((chr(b) if 32 <= b <= 126 else '.') for b in data)
            show_output("--- ASCII Preview ---\n" + ascii_str)
        
        def interpret_le():
            lines = []
            lines.append("--- Header Interpretation (little-endian) ---")
            lines.append(f"Size (bits): {bf.m}")
            lines.append(f"Number of Hash Functions: {bf.k}")
            lines.append(f"Number of Elements: {bf.n}")
            lines.append(f"Error Rate: {bf.error_rate}")
            show_output("\n".join(lines))

        def show_raw_hex():
            show_output("--- Raw Data (Hex) ---\n" + bf.bit_array.hex())

        def show_statistics():
            # Anzahl gesetzter Bits berechnen
            active_bits = 0
            for byte in bf.bit_array:
                active_bits += bin(byte).count("1")
            density = active_bits / bf.m if bf.m > 0 else 0
            lines = []
            lines.append("--- Bloom Filter Statistics ---")
            lines.append(f"Active bits (1s): {active_bits}")
            lines.append(f"Total bits: {bf.m}")
            lines.append(f"Density: {density:.6%}")
            lines.append(f"Number of inserted elements (n): {bf.n}")
            show_output("\n".join(lines))

        ttk.Button(button_frame, text="Show Hex Dump", command=hex_dump).pack(pady=5)
        ttk.Button(button_frame, text="Show ASCII Preview", command=ascii_preview).pack(pady=5)
        ttk.Button(button_frame, text="Interpret Header (LE)", command=interpret_le).pack(pady=5)
        ttk.Button(button_frame, text="Show Raw Data (Hex)", command=show_raw_hex).pack(pady=5)

        # Neuer Button: Show Statistics
        ttk.Button(button_frame, text="Show Statistics", command=show_statistics).pack(pady=5)

        def clear_output():
            text_area.delete('1.0', tk.END)
        ttk.Button(button_frame, text="Clear Output", command=clear_output).pack(pady=5)
        ttk.Button(button_frame, text="Close", command=win.destroy).pack(pady=5)

    # Create Tab
    def init_create_tab(self):
        frame = self.tab_create

        ttk.Label(frame, text="Create a new Bloom Filter from a .txt file", style="Heading.TLabel").pack(pady=10)
        
        list_frame = ttk.Frame(frame)
        list_frame.pack(pady=10, fill=tk.X)
        
        self.txt_list = tk.Listbox(list_frame, height=8, font=("Helvetica", 10))
        self.txt_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.refresh_txt_list()
        
        scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.txt_list.yview)
        self.txt_list.config(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        btn_refresh_txt = ttk.Button(frame, text="Refresh TXT List", command=self.refresh_txt_list)
        btn_refresh_txt.pack(pady=5)

        config_frame = ttk.Labelframe(frame, text="Pre-Processing Options")
        config_frame.pack(pady=10, fill=tk.X, padx=10)

        self.coin_type_var = tk.StringVar(value="BTC")
        ttk.Label(config_frame, text="Select Coin Type:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        coin_choices = ["BTC", "ETH"]
        coin_menu = ttk.OptionMenu(config_frame, self.coin_type_var, *coin_choices)
        coin_menu.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(config_frame, text="Remove Prefixes (comma-separated):").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.prefixes_var = tk.StringVar(value="bc1")
        ttk.Entry(config_frame, textvariable=self.prefixes_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        self.strip_balances_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Strip Balances/Extra Data", variable=self.strip_balances_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        self.remove_empty_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Remove Empty Lines", variable=self.remove_empty_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        param_frame = ttk.Labelframe(frame, text="Bloom Filter Parameters")
        param_frame.pack(pady=10, fill=tk.X, padx=10)
        
        ttk.Label(param_frame, text="Error Rate (0 < p < 1):").grid(row=0, column=0, pady=5, padx=5, sticky=tk.E)
        self.error_rate_var = tk.StringVar(value="0.00000000000001")
        ttk.Entry(param_frame, textvariable=self.error_rate_var, width=30).grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)

        btn_create = ttk.Button(frame, text="Create Bloom Filter", command=self.create_bloom_filter)
        btn_create.pack(pady=10)

    def refresh_txt_list(self):
        self.txt_list.delete(0, tk.END)
        txt_files = [f for f in os.listdir() if f.lower().endswith(".txt")]
        for txt in txt_files:
            self.txt_list.insert(tk.END, txt)
    
    def create_bloom_filter(self):
        selection = self.txt_list.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a .txt file first.")
            return
        selected_txt = self.txt_list.get(selection[0])
        
        try:
            error_rate = float(self.error_rate_var.get().strip())
            if not (0 < error_rate < 1):
                raise ValueError("Error rate must be between 0 and 1.")
        except ValueError as e:
            messagebox.showerror("Invalid input", f"Error rate must be a number between 0 and 1.\n{e}")
            return

        try:
            temp_file = self.preprocess_file(selected_txt)
        except Exception as e:
            messagebox.showerror("Error Preprocessing File", str(e))
            return

        try:
            bf = BloomFilter.from_text_file(temp_file, error_rate)
        except Exception as e:
            messagebox.showerror("Error creating Bloom Filter", str(e))
            return

        base_name = os.path.splitext(selected_txt)[0]
        out_file = base_name + ".bf"
        
        if os.path.exists(out_file):
            if not messagebox.askyesno("File exists", f"{out_file} already exists. Overwrite?"):
                return
        
        bf.to_file(out_file)
        messagebox.showinfo("Success", f"Bloom Filter {out_file} created successfully!")
        self.refresh_bf_list()

    def preprocess_file(self, input_file):
        coin_type = self.coin_type_var.get()
        prefixes = [p.strip() for p in self.prefixes_var.get().split(",") if p.strip()]
        strip_balances = self.strip_balances_var.get()
        remove_empty = self.remove_empty_var.get()

        temp_fd, temp_path = tempfile.mkstemp()
        os.close(temp_fd)
        with open(input_file, "r", encoding="utf-8", errors="ignore") as fin, open(temp_path, "w", encoding="utf-8") as fout:
            for line in fin:
                addr = line.strip()

                if remove_empty and not addr:
                    continue

                # ETH: "0x" am Anfang entfernen
                if coin_type == "ETH" and addr.lower().startswith("0x"):
                    addr = addr[2:].strip()

                # Präfixe entfernen
                if prefixes and any(addr.startswith(pref) for pref in prefixes):
                    continue

                if strip_balances:
                    if '\t' in addr:
                        addr = addr.split('\t', 1)[0].strip()

                if remove_empty and not addr:
                    continue

                if addr:
                    fout.write(addr + "\n")

        return temp_path

    # Help Tab
    def init_help_tab(self):
        frame = self.tab_help
        
        # Hilfetext etwas professioneller und strukturierter gestalten:
        help_text = (
            "=== Professional Bloom Filter Suite - Help & Documentation ===\n\n"
            
            "Welcome to the **Professional Bloom Filter Suite**, your comprehensive tool for creating and analyzing Bloom filters.\n\n"
            
            "=== Key Features ===\n"
            "* **Analyze Bloom Filters**: Load existing `.bf` files, inspect their parameters (size, number of hashes, element count, error rate), view a hex dump of the internal bit array, preview ASCII representation, interpret the header, and examine filter statistics (bit density, number of active bits, etc.).\n\n"
            
            "* **Create Bloom Filters**: Transform raw `.txt` files into efficient Bloom filters by preprocessing addresses or strings. You can:\n"
            "  - Select coin type (BTC or ETH) to apply specific rules.\n"
            "  - Remove custom-defined prefixes (e.g. `bc1` for BTC addresses).\n"
            "  - Strip out balances or extra data associated with each entry.\n"
            "  - Remove empty lines to ensure cleaner input.\n"
            "  - Specify extremely small error rates (e.g. `0.00000000000001`) to achieve a very low probability of false positives.\n\n"
            
            "=== Coin-Specific Rules ===\n"
            "* **BTC**: Define any prefix (like `bc1`, `1`, `3`) to filter out unwanted addresses.\n"
            "* **ETH**: Automatically strip the `0x` prefix from addresses for uniformity.\n\n"
            
            "=== Error Rates ===\n"
            "Bloom filters trade off size and accuracy. A smaller error rate means a larger filter. Thanks to double-precision support, you can set extremely low error rates to meet stringent accuracy requirements.\n\n"
            
            "=== Usage Tips ===\n"
            "* Start by selecting the `.bf` file you want to analyze in the **Analyze** tab. Use the provided options to gain insights.\n"
            "* In the **Create** tab, pick your `.txt` file, configure preprocessing options, and set the error rate. Then, create your new Bloom filter with a single click.\n"
            "* Consult statistics after creation to confirm that the filter meets your criteria.\n\n"
            
            "=== Additional Support ===\n"
            "For more information, best practices, or to learn more about Bloom filters, consider referencing:\n"
            "- [Bloom Filter (Wikipedia)](https://en.wikipedia.org/wiki/Bloom_filter)\n"
            "- Academic papers on probabilistic data structures.\n\n"
            
            "This suite strives to combine user-friendliness with professional-grade features, empowering both novices and experts to harness the power of Bloom filters for efficient data lookups.\n"
        )

        text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=25, font=("Helvetica", 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_area.insert(tk.END, help_text)
        text_area.configure(state='disabled')



if __name__ == "__main__":
    root = tk.Tk()
    app = BFAnalyzerGUI(root)
    root.mainloop()
