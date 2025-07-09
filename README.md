# BibTeX Cleaner and Metadata Enhancer

This script cleans up `.bib` files and enriches them with metadata from Crossref. It keeps the original citation keys intact, fixes formatting (like proper page ranges), and fills in missing or inconsistent fields like author names, journal/booktitle, publisher, month, etc.

* Use with care if your input file has poor or ambiguous titles — it’s designed to be conservative and only updates when it’s confident.

## What is this thing doing?

- Keeps your original citation keys
- Fetches metadata using the DOI, or falls back to a title + author search if the DOI is missing
- Ensures fields are only replaced if they’re missing or significantly different
- Verifies that the fetched title is a good match before making any changes (to avoid corrupting the entry)
- Distinguishes between entry types (`article`, `inproceedings`, `book`, `book-chapter`, etc.)
- Outputs a cleaned BibTeX file with `_cleaned.bib` suffix

## Dependencies

- Python 3.7+
- `bibtexparser==1.4.3`
- `requests`

Install with:

```bash
pip install bibtexparser==1.4.3 requests
````

## Usage

```bash
python clean_bib.py myfile.bib
```

If you don’t pass a file, it defaults to `input.bib` and writes to `cleaned.bib`.

## Example

Before:

```bibtex
@article{doe2020,
  author = {Doe, John},
  title = {Some Title},
  year = {2020}
}
```

After:

```bibtex
@article{doe2020,
  author = {Doe, John},
  title = {The Actual Title from Crossref},
  journal = {Some Journal},
  year = {2020},
  volume = {12},
  number = {3},
  pages = {123--134},
  doi = {10.1234/example}
}
```

## Notes

* If no metadata is found or the title match is poor, the entry is left untouched.
* Subtitle-aware matching is included, so `title + subtitle` is used when comparing.
* Crossref often returns multiple results (e.g. book and chapter); the code handles that.


