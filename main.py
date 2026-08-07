from summarize import summarize_papers
from architecture import generate_architecture

import requests
import feedparser
import urllib.parse


# ==========================================================
# Decode OpenAlex Abstract
# ==========================================================

def decode_abstract(index):

    if index is None:
        return "No Abstract Available"

    words = []

    for word, positions in index.items():
        for pos in positions:
            words.append((pos, word))

    words.sort()

    return " ".join(word for pos, word in words)


# ==========================================================
# Search OpenAlex
# ==========================================================

def search_openalex(topic, limit=5):

    encoded = urllib.parse.quote(topic)

    url = (
        f"https://api.openalex.org/works"
        f"?search={encoded}"
        f"&per-page={limit}"
    )

    papers = []

    try:

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        data = response.json()

        for paper in data.get("results", []):

            abstract = decode_abstract(
                paper.get("abstract_inverted_index")
            )

            papers.append({

                "title": paper.get("title", "No Title"),

                "abstract": abstract,

                "year": paper.get("publication_year", "Unknown"),

                "source": "OpenAlex"

            })

    except Exception as e:

        print("OpenAlex Error:", e)

    return papers


# ==========================================================
# Search arXiv
# ==========================================================

def search_arxiv(topic, limit=5):

    encoded = urllib.parse.quote(topic)

    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{encoded}"
        f"&start=0"
        f"&max_results={limit}"
    )

    papers = []

    try:

        feed = feedparser.parse(url)

        for entry in feed.entries:

            papers.append({

                "title": entry.title,

                "abstract": entry.summary,

                "year": entry.published[:4],

                "source": "arXiv"

            })

    except Exception as e:

        print("arXiv Error:", e)

    return papers


# ==========================================================
# MAIN
# ==========================================================

def main():

    print("=" * 70)
    print("          AI Research Paper Analyzer")
    print("=" * 70)

    topic = input("\nEnter Research Topic : ")

    # ---------------- OpenAlex ----------------

    print("\nSearching OpenAlex...")

    openalex = search_openalex(topic)

    print(f"✓ Found {len(openalex)} papers")

    # ---------------- arXiv ----------------

    print("\nSearching arXiv...")

    arxiv = search_arxiv(topic)

    print(f"✓ Found {len(arxiv)} papers")

    # ---------------- Combine ----------------

    papers = openalex + arxiv

    if len(papers) == 0:

        print("\n❌ No papers found.")
        return

    print(f"\n✅ Total Papers Collected : {len(papers)}")

    # ---------------- Summaries ----------------

    print("\n" + "=" * 70)
    print("Generating AI Paper Summaries...")
    print("=" * 70)

    summary = summarize_papers(papers)

    print(summary)

    # ---------------- Architecture ----------------

    print("\n" + "=" * 70)
    print("Generating Generalized Architecture...")
    print("=" * 70)

    architecture = generate_architecture(papers)

    print(architecture)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()