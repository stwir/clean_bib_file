# BibTeX Cleaner with DOI Metadata Lookup

This script updates and cleans `.bib` files by fetching authoritative metadata from the CrossRef API using existing DOIs or by searching based on title and author.

It standardizes fields such as:

- `author` (converted to "Last, First" format)
- `title`
- `journal`
- `year`, `volume`, `issue`, `pages`
- `doi`

## Features

- Preserves original citation keys
- Works with `bibtexparser==2.0.0b7`
- Replaces missing or inconsistent metadata via DOI or title lookup
- Outputs a clean, ready-to-use `.bib` file

## Requirements

```bash
pip install bibtexparser==2.0.0b7 requests
````

## Usage

1. Place your original `.bib` file in the same directory as the script and name it `input.bib`
2. Run the script:

```bash
python clean_bib.py
```

3. A cleaned file named `cleaned.bib` will be created in the same directory.

## Notes

* If a DOI is missing, the script will attempt to find one using the title and first listed author via the CrossRef API.
* Original entries are preserved if no metadata is found.
* All citation keys remain unchanged.

