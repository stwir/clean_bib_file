import requests
import urllib.parse
from bibtexparser import parse_string, write_string
from bibtexparser.model import Entry, Field
from bibtexparser.library import Library

def fetch_metadata_from_doi(doi):
    headers = {"Accept": "application/vnd.citationstyles.csl+json"}
    try:
        response = requests.get(f"https://doi.org/{doi}", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"DOI lookup failed for {doi}: {e}")
    return None

def find_doi_by_title_author(title, author=None):
    query = f"title:{title}"
    if author:
        query += f" author:{author}"
    url = "https://api.crossref.org/works?query=" + urllib.parse.quote(query)
    try:
        response = requests.get(url, timeout=10)
        items = response.json().get("message", {}).get("items", [])
        if items:
            return items[0].get("DOI")
    except Exception as e:
        print(f"DOI search failed for {title}: {e}")
    return None

def fields_to_dict(entry):
    return {field.key: field.value for field in entry.fields}

def dict_to_fields(d):
    return [Field(key=k, value=v) for k, v in d.items()]

def clean_entry(entry: Entry, metadata) -> Entry:
    new_entry = Entry(entry_type=entry.entry_type, key=entry.key, fields=[])
    fields = {}

    # Author
    authors = metadata.get("author", [])
    if authors:
        fields["author"] = " and ".join(
            [f"{a['family']}, {a['given']}" for a in authors if 'family' in a and 'given' in a]
        )

    # Title
    if "title" in metadata:
        fields["title"] = metadata["title"]

    # Get container title or fallbacks
    container_raw = metadata.get("container-title")

    if isinstance(container_raw, list):
        container_title = container_raw[0]
    elif isinstance(container_raw, str):
        container_title = container_raw
    else:
        container_title = None


    if not container_title:
        if "collection-title" in metadata:
            container_title = metadata["collection-title"][0]
        elif "event" in metadata and isinstance(metadata["event"], dict):
            container_title = metadata["event"].get("name")

    # Determine correct field based on entry type
    if container_title:
        if entry.entry_type == "article":
            fields["journal"] = container_title
        elif entry.entry_type in ["inproceedings", "incollection"]:
            fields["booktitle"] = container_title

    # Year
    if "issued" in metadata and "date-parts" in metadata["issued"]:
        year = metadata["issued"]["date-parts"][0][0]
        if isinstance(year, int):
            fields["year"] = str(year)

    # Volume, Issue, Pages
    if "volume" in metadata:
        fields["volume"] = str(metadata["volume"])
    if "issue" in metadata:
        fields["number"] = str(metadata["issue"])
    if "page" in metadata:
        fields["pages"] = metadata["page"]

    # DOI
    if "DOI" in metadata:
        fields["doi"] = metadata["DOI"]

    new_entry.fields = dict_to_fields(fields)
    return new_entry


def main():
    input_file = "input.bib"
    output_file = "cleaned.bib"

    with open(input_file, "r") as f:
        bib_content = f.read()

    bib_lib = parse_string(bib_content)
    cleaned_entries = []

    for entry in bib_lib.entries:
        original_fields = fields_to_dict(entry)
        doi = original_fields.get("doi")

        if not doi:
            title = original_fields.get("title", "")
            author_field = original_fields.get("author", "")
            author = author_field.split(" and ")[0] if author_field else None
            doi = find_doi_by_title_author(title, author)

        metadata = fetch_metadata_from_doi(doi) if doi else None

        if metadata:
            cleaned = clean_entry(entry, metadata)
            cleaned_entries.append(cleaned)
            print(f"Updated: {entry.key}")
        else:
            cleaned_entries.append(entry)
            print(f"Unchanged (no metadata found): {entry.key}")

    lib = Library()
    lib.__dict__["_blocks"] = cleaned_entries

    output_string = write_string(lib)

    with open(output_file, "w") as f:
        f.write(output_string)

    print(f"Cleaned BibTeX saved to: {output_file}")

if __name__ == "__main__":
    main()
