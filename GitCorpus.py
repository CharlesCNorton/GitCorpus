import sys
import mimetypes
import base64
import requests
from datetime import datetime
from urllib.parse import urlparse
import tkinter as tk
from tkinter import filedialog, messagebox

DEBUG = True  # Set this to False to disable debug output

def debug_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs, file=sys.stderr)

def log_message(text_widget, message):
    text_widget.config(state=tk.NORMAL)
    text_widget.insert(tk.END, message + "\n")
    text_widget.see(tk.END)
    text_widget.config(state=tk.DISABLED)
    text_widget.update_idletasks()

def is_text_file(content_bytes):
    debug_print("Checking if file is text-based, length:", len(content_bytes))
    if b'\x00' in content_bytes:
        debug_print("Binary file detected (null byte present).")
        return False
    return True

def fetch_json(url):
    debug_print("Fetching JSON from URL:", url)
    try:
        resp = requests.get(url)
        debug_print("HTTP status for", url, ":", resp.status_code)
        if resp.status_code == 200:
            debug_print("Successfully fetched JSON:", url)
            return True, resp.json()
        else:
            debug_print("Non-200 status code:", resp.status_code, resp.text)
            return False, f"HTTP {resp.status_code}: {resp.text}"
    except requests.RequestException as e:
        debug_print("Network error while fetching:", url, "Error:", e)
        return False, f"Network error: {e}"

def fetch_repo_file_contents(full_name, path="", text_widget=None):
    debug_print(f"Fetching repo contents: {full_name}, path: {path}")
    if path:
        url = f"https://api.github.com/repos/{full_name}/contents/{path}"
    else:
        url = f"https://api.github.com/repos/{full_name}/contents"
    debug_print("Content URL:", url)

    success, data = fetch_json(url)
    if not success:
        if text_widget:
            log_message(text_widget, f"Error fetching contents of {full_name}/{path}: {data}")
        debug_print(f"Error in fetching contents: {data}")
        return []

    debug_print("Data returned for contents:", data)
    if isinstance(data, dict) and data.get('type') == 'file':
        # Single file scenario
        debug_print("Single file detected:", data['path'])
        content = data.get('content', '')
        encoding = data.get('encoding', 'base64')
        debug_print("Encoding:", encoding)
        if encoding == 'base64':
            try:
                decoded = base64.b64decode(content)
                if is_text_file(decoded):
                    return [(data['path'], decoded.decode('utf-8', errors='replace'))]
                else:
                    debug_print("Skipping binary file:", data['path'])
                    if text_widget:
                        log_message(text_widget, f"Skipping binary file {data['path']}")
                    return []
            except Exception as e:
                debug_print("Error decoding file:", data['path'], e)
                if text_widget:
                    log_message(text_widget, f"Error decoding file {data['path']}: {e}")
                return []
        else:
            debug_print("Unsupported encoding:", encoding)
            if text_widget:
                log_message(text_widget, f"Unsupported encoding {encoding} for file {data['path']}")
            return []
    elif isinstance(data, list):
        # Directory listing scenario
        debug_print("Directory listing detected with", len(data), "items")
        files = []
        for item in data:
            debug_print("Processing item:", item.get('type'), item.get('path'))
            if item['type'] == 'file':
                fpath = item['path']
                f_success, f_data = fetch_json(item['url'])
                if not f_success:
                    debug_print("Error fetching file:", fpath, f_data)
                    if text_widget:
                        log_message(text_widget, f"Error fetching file {fpath}: {f_data}")
                    continue
                if f_data.get('type') == 'file':
                    content = f_data.get('content', '')
                    encoding = f_data.get('encoding', 'base64')
                    debug_print(f"File fetched: {f_data['path']} with encoding {encoding}")
                    if encoding == 'base64':
                        try:
                            decoded = base64.b64decode(content)
                            if is_text_file(decoded):
                                files.append((f_data['path'], decoded.decode('utf-8', errors='replace')))
                            else:
                                debug_print("Skipping binary file:", f_data['path'])
                                if text_widget:
                                    log_message(text_widget, f"Skipping binary file {f_data['path']}")
                        except Exception as e:
                            debug_print("Error decoding file:", f_data['path'], e)
                            if text_widget:
                                log_message(text_widget, f"Error decoding file {f_data['path']}: {e}")
                    else:
                        debug_print("Unsupported encoding:", encoding)
                        if text_widget:
                            log_message(text_widget, f"Unsupported encoding {encoding} for file {f_data['path']}")
                else:
                    debug_print("Item not a file?", f_data)
            elif item['type'] == 'dir':
                # Recurse into directory
                debug_print("Recursing into directory:", item['path'])
                subfiles = fetch_repo_file_contents(full_name, item['path'], text_widget=text_widget)
                files.extend(subfiles)
            else:
                debug_print("Skipping item of type:", item['type'], "at path:", item['path'])
        return files
    else:
        # Unexpected data format
        debug_print("Unexpected data format:", type(data), data)
        if text_widget:
            log_message(text_widget, f"Unexpected data format in repository contents: {data}")
        return []

def extract_repo_text(owner, repo, text_widget=None, format_output=True):
    """
    Extracts all text files from a single repository (owner/repo).
    If format_output is False, no headers/formatting are added.
    """
    full_name = f"{owner}/{repo}"
    debug_print(f"Extracting repo text for {full_name}")
    if text_widget:
        log_message(text_widget, f"Fetching contents of repository: {full_name}")
    files = fetch_repo_file_contents(full_name, text_widget=text_widget)
    if not files:
        debug_print("No files found or repository empty:", full_name)
        if text_widget:
            log_message(text_widget, f"No files found or repository empty: {full_name}")
        return ""

    combined = []
    if format_output:
        combined.append(f"========== REPOSITORY: {full_name} ==========\n\n")
    for fpath, content in files:
        if format_output:
            combined.append(f"--- FILE: {fpath} ---\n")
        combined.append(content)
        if format_output:
            combined.append("\n\n")
    return "".join(combined)

def extract_user_repos_text(username, text_widget=None, format_output=True):
    """
    Extracts text from all public repositories of a given user.
    If format_output is False, no headers/formatting are added.
    """
    debug_print(f"Extracting all repos for user: {username}")
    if text_widget:
        log_message(text_widget, f"Fetching repository list for user: {username}")
    url = f"https://api.github.com/users/{username}/repos?per_page=100"
    all_repos = []
    while url:
        debug_print("Fetching repo list page:", url)
        success, data = fetch_json(url)
        if not success:
            debug_print("Error fetching repos:", data)
            if text_widget:
                log_message(text_widget, f"Error fetching repos for user {username}: {data}")
            return ""
        all_repos.extend(data)
        try:
            r = requests.get(url)
            links = r.links
        except Exception as e:
            debug_print("Error checking pagination:", e)
            links = {}
        if 'next' in links:
            url = links['next']['url']
            debug_print("Next page of repos:", url)
        else:
            url = None

    if not all_repos:
        debug_print("No public repositories found for user:", username)
        if text_widget:
            log_message(text_widget, f"No public repositories found for user {username}.")
        return ""

    combined = []
    if format_output:
        combined.append(f"========== ALL REPOS FOR USER: {username} ==========\n")
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        combined.append(f"Generated on: {now}\nNumber of repositories: {len(all_repos)}\n\n")

    for idx, repo_data in enumerate(all_repos, start=1):
        repo_name = repo_data.get('name')
        if not repo_name:
            debug_print("Repository data lacks 'name' field:", repo_data)
            continue
        if text_widget:
            log_message(text_widget, f"Processing repository {idx}/{len(all_repos)}: {username}/{repo_name}")
        debug_print(f"Extracting text for repo {username}/{repo_name}")
        repo_text = extract_repo_text(username, repo_name, text_widget=text_widget, format_output=format_output)
        if repo_text.strip():
            combined.append(repo_text)
        else:
            if text_widget:
                log_message(text_widget, f"Skipping empty or non-textual repository: {repo_name}")
            debug_print(f"No textual content found in repo {repo_name}, skipping.")

    return "".join(combined)

def parse_repo_url(repo_url):
    debug_print("Parsing repo URL:", repo_url)
    parsed = urlparse(repo_url)
    debug_print("Parsed URL:", parsed)
    parts = parsed.path.strip('/').split('/')
    if len(parts) == 2:
        debug_print("Parsed owner and repo:", parts)
        return parts[0], parts[1]
    debug_print("Failed to parse URL into owner/repo.")
    return None, None

def run_extraction(mode, input_value, output_path, text_widget, true_string_option):
    debug_print(f"run_extraction called with mode={mode}, input_value={input_value}, output_path={output_path}, true_string_option={true_string_option}")
    if not output_path:
        debug_print("No output file selected.")
        messagebox.showerror("Error", "No output file selected.")
        return

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    # If true_string_option is on, we do no formatting
    format_output = not true_string_option

    if mode == 'single':
        owner, repo = parse_repo_url(input_value)
        if not owner or not repo:
            debug_print("Invalid repository URL:", input_value)
            messagebox.showerror("Error", "Invalid repository URL. Please enter a URL like https://github.com/user/repo.")
            return
        if text_widget:
            log_message(text_widget, f"Starting extraction for single repo: {owner}/{repo}")
        debug_print(f"Extracting single repo: {owner}/{repo}")
        if format_output:
            combined = f"GitCorpus Output (Single Repository)\nGenerated on: {now}\nSource: {input_value}\n\n"
        else:
            combined = ""
        combined += extract_repo_text(owner, repo, text_widget=text_widget, format_output=format_output)
    else:
        # mode == 'user'
        username = input_value.strip()
        if not username:
            debug_print("Invalid username input.")
            messagebox.showerror("Error", "Invalid username. Please enter a GitHub username.")
            return
        debug_print(f"Extracting all repos for user: {username}")
        if text_widget:
            log_message(text_widget, f"Starting extraction for user: {username}")
        if format_output:
            combined = f"GitCorpus Output (All Repositories for User: {username})\nGenerated on: {now}\n\n"
        else:
            combined = ""
        combined += extract_user_repos_text(username, text_widget=text_widget, format_output=format_output)

    if true_string_option:
        # Remove all whitespace to produce a continuous line of text
        debug_print("Removing all whitespace for true_string_option.")
        combined = "".join(combined.split())

    if combined.strip():
        debug_print("Writing output to file:", output_path)
        try:
            with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(combined)
            messagebox.showinfo("Success", f"Extraction complete. Output saved to {output_path}")
            if text_widget:
                log_message(text_widget, f"Output successfully saved to {output_path}")
        except Exception as e:
            debug_print("Failed to save output file:", e)
            messagebox.showerror("Error", f"Failed to save output file: {e}")
    else:
        debug_print("No textual content found to save.")
        messagebox.showinfo("Info", "No textual content found to save.")
        if text_widget:
            log_message(text_widget, "No textual content to save.")

def browse_output_file(entry):
    debug_print("Opening file dialog for output selection.")
    filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
    if filepath:
        entry.delete(0, tk.END)
        entry.insert(0, filepath)

def toggle_night_mode(root, text_widget, night_mode):
    debug_print("Toggling night mode:", night_mode)
    # Define known color schemes
    day_bg = "#f0f0f0"
    day_fg = "black"
    night_bg = "black"
    night_fg = "white"

    if night_mode:
        bg = night_bg
        fg = night_fg
    else:
        bg = day_bg
        fg = day_fg

    # Set root colors
    root.configure(bg=bg)

    # Traverse all widgets and set their colors
    stack = [root]
    while stack:
        parent = stack.pop()
        children = parent.winfo_children()
        for c in children:
            try:
                c.configure(bg=bg, fg=fg)
            except:
                pass
            stack.append(c)

    # Set text_widget colors
    try:
        text_widget.configure(bg=bg, fg=fg)
    except:
        pass

def main():
    debug_print("Starting GitCorpus GUI application.")
    root = tk.Tk()
    root.title("GitCorpus")

    mode_var = tk.StringVar(value="single")
    night_mode_var = tk.BooleanVar(value=False)
    true_string_var = tk.BooleanVar(value=False)

    title_label = tk.Label(root, text="GitCorpus - Extract GitHub Repositories to Text", font=("Helvetica", 14, "bold"))
    title_label.grid(column=0, row=0, columnspan=3, pady=10, padx=10, sticky="w")

    op_label = tk.Label(root, text="Choose Operation:", font=("Helvetica", 10, "bold"))
    op_label.grid(column=0, row=1, sticky="w", padx=10)

    single_radio = tk.Radiobutton(root, text="Single Repository", variable=mode_var, value="single")
    single_radio.grid(column=0, row=2, sticky="w", padx=30)

    user_radio = tk.Radiobutton(root, text="All Repos of a User", variable=mode_var, value="user")
    user_radio.grid(column=0, row=3, sticky="w", padx=30)

    input_label = tk.Label(root, text="Input (Repository URL or GitHub Username):", font=("Helvetica", 10, "bold"))
    input_label.grid(column=0, row=4, sticky="w", pady=(10,0), padx=10)
    input_entry = tk.Entry(root, width=50)
    input_entry.grid(column=0, row=5, columnspan=2, sticky="we", pady=5, padx=10)

    output_label = tk.Label(root, text="Select Output File:", font=("Helvetica", 10, "bold"))
    output_label.grid(column=0, row=6, sticky="w", pady=(10,0), padx=10)
    output_entry = tk.Entry(root, width=50)
    output_entry.grid(column=0, row=7, sticky="we", pady=5, padx=10)
    browse_button = tk.Button(root, text="Browse", command=lambda: browse_output_file(output_entry))
    browse_button.grid(column=1, row=7, sticky="w")

    def on_night_mode_toggle():
        toggle_night_mode(root, text_widget, night_mode_var.get())

    night_mode_check = tk.Checkbutton(root, text="Night Mode", variable=night_mode_var,
                                      command=on_night_mode_toggle)
    night_mode_check.grid(column=0, row=8, sticky="w", pady=(10,0), padx=10)

    true_string_check = tk.Checkbutton(root, text="True String (No Formatting, No Whitespace)", variable=true_string_var)
    true_string_check.grid(column=0, row=9, sticky="w", pady=(10,0), padx=10)

    run_button = tk.Button(root, text="Run")
    run_button.grid(column=0, row=10, pady=(10,0), padx=10, sticky="w")

    text_widget = tk.Text(root, width=80, height=10, state=tk.DISABLED)
    text_widget.grid(column=0, row=11, columnspan=3, pady=10, padx=10)

    def run_clicked():
        input_value = input_entry.get().strip()
        output_path = output_entry.get().strip()
        mode = mode_var.get()
        ts = true_string_var.get()

        debug_print(f"Run clicked with mode={mode}, input_value='{input_value}', output_path='{output_path}', true_string={ts}")
        run_extraction(mode, input_value, output_path, text_widget, ts)

    run_button.configure(command=run_clicked)

    # Allow expansion
    root.columnconfigure(0, weight=1)
    root.rowconfigure(11, weight=1)

    # Set initial day mode colors
    toggle_night_mode(root, text_widget, False)

    root.mainloop()

if __name__ == "__main__":
    main()
