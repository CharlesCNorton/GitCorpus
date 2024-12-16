GitCorpus is a Python-based GUI application that extracts textual content from GitHub repositories into a single text file. It supports:

- Extracting from a single repository by providing its GitHub URL.
- Extracting from all public repositories of a specified GitHub user.
- Night Mode toggle for a dark interface theme.
- A "True String" mode to produce one continuous line of text with no formatting or whitespace.
- Debug output printed to the console for troubleshooting.

Requirements:
- Python 3
- Requests library (install with: pip install requests)

Usage:
1) Run python GitCorpus.py
2) Select operation (single repository or all user repos).
3) Enter the required input (a GitHub repository URL or a GitHub username).
4) Choose an output file by clicking the "Browse" button.
5) Optionally enable Night Mode or True String mode.
6) Click "Run" to start extraction.

Example:
- Single repository: Enter "https://github.com/python/cpython" and choose an output file (e.g., "cpython_output.txt").
- User repositories: Enter "torvalds" as the username and choose an output file to combine all public repos.

The resulting file contains the textual content of the chosen repositories.
