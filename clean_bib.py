import requests
import urllib.parse
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import sys
import os
from difflib import SequenceMatcher

def is_similar(a, b, threshold=0.7):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold

def smart_update(field, old_val, new_val, threshold=0.7):
    if not new_val:
        return old_val
    if not old_val:
        return new_val
    if old_val.lower() == new_val.lower():
        return old_val
    if is_similar(old_val, new_val, threshold):
        return new_val
    return old_val

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
        best_match = None
        highest_similarity = 0

        for item in items:
            candidate_title = item.get("title", "")
            if isinstance(candidate_title, list):
                candidate_title = candidate_title[0] if candidate_title else ""

            # Also combine subtitle for better match
            subtitle = item.get("subtitle", "")
            if isinstance(subtitle, list):
                subtitle = subtitle[0] if subtitle else ""
            full_title = f"{candidate_title}: {subtitle}" if subtitle else candidate_title

            similarity = SequenceMatcher(None, title.lower(), full_title.lower()).ratio()
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = item

        if best_match and highest_similarity > 0.7:  # Adjustable threshold
            return best_match.get("DOI")
        


    except Exception as e:
        print(f"DOI search failed for {title}: {e}")
    return None

def clean_entry(entry, metadata):
    cleaned = {}
    cleaned["ENTRYTYPE"] = entry.get("ENTRYTYPE", "misc")
    cleaned["ID"] = entry.get("ID")

    # Author
    old_author = entry.get("author", "")
    if "author" in metadata:
        authors = metadata["author"]
        if isinstance(authors, list):
            new_author = " and ".join(
                [f"{a['family']}, {a['given']}" for a in authors if "family" in a and "given" in a]
            )
            cleaned["author"] = smart_update("author", old_author, new_author)
        else:
            cleaned["author"] = old_author
    else:
        cleaned["author"] = old_author

    # Title
    old_title = entry.get("title", "")
    title = metadata.get("title", "")
    if isinstance(title, list):
        title = title[0] if title else ""
    if not is_similar(old_title, title):
        return entry  # Reject update if title doesn't match

    cleaned["title"] = old_title if not title else title

    # Container title
    container = metadata.get("container-title", [])
    if not container and "collection-title" in metadata:
        container = metadata["collection-title"]
    if not container and "event" in metadata and isinstance(metadata["event"], dict):
        name = metadata["event"].get("name")
        if name:
            container = [name]
    container_title = container[0] if container else None

    if cleaned["ENTRYTYPE"] == "article":
        cleaned["journal"] = smart_update("journal", entry.get("journal", ""), container_title)
    elif cleaned["ENTRYTYPE"] in ["inproceedings", "incollection"]:
        cleaned["booktitle"] = smart_update("booktitle", entry.get("booktitle", ""), container_title)

    # Publisher
    cleaned["publisher"] = smart_update("publisher", entry.get("publisher", ""), metadata.get("publisher"))

    # Year
    year = None
    if "issued" in metadata and "date-parts" in metadata["issued"]:
        year = str(metadata["issued"]["date-parts"][0][0])
    cleaned["year"] = smart_update("year", entry.get("year", ""), year)

    # Month
    month = None
    if "issued" in metadata and "date-parts" in metadata["issued"]:
        date_parts = metadata["issued"]["date-parts"][0]
        if len(date_parts) > 1:
            month_num = date_parts[1]
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            if 1 <= month_num <= 12:
                month = months[month_num - 1]
    cleaned["month"] = smart_update("month", entry.get("month", ""), month)

    # Volume, Issue, Pages, DOI
    for field in ["volume", "issue", "page", "DOI"]:
        new_val = str(metadata.get(field)) if metadata.get(field) else None
        if field == "page" and new_val:
            new_val = new_val.replace("-", "--")
        field_key = "number" if field == "issue" else field.lower()
        cleaned[field_key] = smart_update(field_key, entry.get(field_key, ""), new_val)

    return cleaned

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "input.bib"
    output_file = os.path.splitext(input_file)[0] + "_cleaned.bib"

    with open(input_file) as bibtex_file:
        db = bibtexparser.load(bibtex_file)

    cleaned_entries = []

    for entry in db.entries:
        doi = entry.get("doi")
        if not doi:
            title = entry.get("title", "")
            author_field = entry.get("author", "")
            author = author_field.split(" and ")[0] if author_field else None
            doi = find_doi_by_title_author(title, author)

        metadata = fetch_metadata_from_doi(doi) if doi else None

        if metadata:
            title_original = entry.get("title", "")
            title_main = metadata.get("title", "")
            subtitle = metadata.get("subtitle", "")
            if isinstance(title_main, list):
                title_main = title_main[0] if title_main else ""
            if isinstance(subtitle, list):
                subtitle = subtitle[0] if subtitle else ""
            title_fetched = f"{title_main}: {subtitle}" if subtitle else title_main

            if is_similar(title_original, title_fetched):
                cleaned = clean_entry(entry, metadata)
                cleaned_entries.append(cleaned)
                print(f"Updated: {entry['ID']}")
            else:
                print(f"Skipped (title mismatch): {entry['ID']}")
                cleaned_entries.append(entry)
        else:
            print(f"Unchanged (no metadata found): {entry['ID']}")
            cleaned_entries.append(entry)

    db_cleaned = BibDatabase()
    db_cleaned.entries = cleaned_entries
    writer = BibTexWriter()
    writer.order_entries_by = None

    with open(output_file, "w") as bibfile:
        bibfile.write(writer.write(db_cleaned))

    print(f"Cleaned BibTeX saved to: {output_file}")

if __name__ == "__main__":
    main()