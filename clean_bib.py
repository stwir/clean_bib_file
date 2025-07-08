import requests
import urllib.parse
from difflib import SequenceMatcher
from bibtexparser import parse_string, write_string
from bibtexparser.model import Entry, Field
from bibtexparser.library import Library

MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

def is_title_match(original, fetched, threshold=0.85):
    if not original or not fetched:
        return False
    ratio = SequenceMatcher(None, original.lower(), fetched.lower()).ratio()
    return ratio >= threshold

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
        for item in items:
            fetched_title = item.get("title", [""])[0]
            if is_title_match(title, fetched_title):
                return item.get("DOI")
    except Exception as e:
        print(f"DOI search failed for {title}: {e}")
    return None

def fields_to_dict(entry):
    return {field.key: field.value for field in entry.fields}

def dict_to_fields(d):
    return [Field(key=k, value=v) for k, v in d.items()]

def clean_entry(entry: Entry, metadata) -> Entry:
    original_fields = fields_to_dict(entry)
    new_entry = Entry(entry_type=entry.entry_type, key=entry.key, fields=[])
    fields = {}

    authors = metadata.get("author", [])
    if authors:
        fields["author"] = " and ".join(
            [f"{a['family']}, {a['given']}" for a in authors if 'family' in a and 'given' in a]
        )

    if "title" in metadata:
        fields["title"] = metadata["title"]

    container = metadata.get("container-title", [])
    container_title = container[0] if isinstance(container, list) and container else None

    if not container_title:
        if "collection-title" in metadata:
            container_title = metadata["collection-title"][0]
        elif "event" in metadata and isinstance(metadata["event"], dict):
            container_title = metadata["event"].get("name")

    if container_title:
        if entry.entry_type == "article":
            fields["journal"] = container_title
        elif entry.entry_type in ["inproceedings", "incollection"]:
            fields["booktitle"] = container_title

    if "publisher" in metadata:
        fields["publisher"] = metadata["publisher"]

    if "issued" in metadata and "date-parts" in metadata["issued"]:
        date_parts = metadata["issued"]["date-parts"][0]
        if len(date_parts) > 0:
            fields["year"] = str(date_parts[0])
        if len(date_parts) > 1:
            month_num = date_parts[1]
            if month_num in MONTHS:
                fields["month"] = MONTHS[month_num]

    if "volume" in metadata:
        fields["volume"] = str(metadata["volume"])
    if "issue" in metadata:
        fields["number"] = str(metadata["issue"])
    if "page" in metadata:
        fields["pages"] = metadata["page"]
    if "DOI" in metadata:
        fields["doi"] = metadata["DOI"]

    # Preserve original fields not overridden
    for key, value in original_fields.items():
        if key not in fields:
            fields[key] = value

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

        metadata = None
        if doi:
            metadata = fetch_metadata_from_doi(doi)
        else:
            title = original_fields.get("title", "")
            author_field = original_fields.get("author", "")
            author = author_field.split(" and ")[0] if author_field else None
            found_doi = find_doi_by_title_author(title, author)
            if found_doi:
                metadata = fetch_metadata_from_doi(found_doi)

        if metadata:
            try:
                cleaned = clean_entry(entry, metadata)
                cleaned_entries.append(cleaned)
                print(f"Updated: {entry.key}")
            except Exception as e:
                print(f"Failed to clean {entry.key}, keeping original. Reason: {e}")
                cleaned_entries.append(entry)
        else:
            cleaned_entries.append(entry)
            print(f"No metadata found: {entry.key}")

    lib = Library()
    lib.__dict__["_blocks"] = cleaned_entries

    output_string = write_string(lib)

    with open(output_file, "w") as f:
        f.write(output_string)

    print(f"Cleaned BibTeX saved to: {output_file}")

if __name__ == "__main__":
    main()
