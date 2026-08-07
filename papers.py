import requests
import feedparser
import urllib.parse

# ============================================
# SEARCH OPENALEX
# ============================================

def search_openalex(topic, limit=5):

    encoded_topic = urllib.parse.quote(topic)

    url = (
        f"https://api.openalex.org/works"
        f"?search={encoded_topic}"
        f"&per-page={limit}"
    )

    papers = []

    try:

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        data = response.json()

        for paper in data.get("results", []):

            title = paper.get("title", "No Title")

            year = paper.get("publication_year", "Unknown")

            doi = paper.get("doi")

            pdf = None

            location = paper.get("primary_location")

            if location:
                pdf = location.get("pdf_url")

            papers.append({

                "title": title,

                "year": year,

                "pdf": pdf,

                "doi": doi,

                "source": "OpenAlex"

            })

    except Exception as e:

        print("OpenAlex Error:", e)

    return papers


# ============================================
# SEARCH ARXIV
# ============================================

def search_arxiv(topic, limit=5):

    query = urllib.parse.quote(topic)

    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{query}"
        f"&start=0"
        f"&max_results={limit}"
    )

    papers = []

    feed = feedparser.parse(url)

    for entry in feed.entries:

        pdf = entry.id.replace("/abs/", "/pdf/") + ".pdf"

        papers.append({

            "title": entry.title,

            "year": entry.published[:4],

            "pdf": pdf,

            "doi": None,

            "source": "arXiv"

        })

    return papers


# ============================================
# REMOVE DUPLICATES
# ============================================

def remove_duplicates(papers):

    unique = []

    titles = set()

    for paper in papers:

        title = paper["title"].lower().strip()

        if title not in titles:

            titles.add(title)

            unique.append(paper)

    return unique


# ============================================
# DISPLAY PAPERS
# ============================================

def display_papers(papers):

    print("\n")

    print("=" * 100)

    print(f"TOTAL PAPERS FOUND : {len(papers)}")

    print("=" * 100)

    for i, paper in enumerate(papers, start=1):

        print(f"\nPaper {i}")

        print("-" * 80)

        print("Title  :", paper["title"])

        print("Year   :", paper["year"])

        print("Source :", paper["source"])

        print("DOI    :", paper["doi"])

        print("PDF    :", paper["pdf"])


# ============================================
# MAIN
# ============================================

def main():

    topic = input("Enter Research Topic : ")

    print("\nSearching OpenAlex...")

    openalex = search_openalex(topic)

    print("Found", len(openalex), "papers")

    print("\nSearching arXiv...")

    arxiv = search_arxiv(topic)

    print("Found", len(arxiv), "papers")

    all_papers = openalex + arxiv

    all_papers = remove_duplicates(all_papers)

    display_papers(all_papers)


if __name__ == "__main__":

    main()