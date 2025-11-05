import requests
import time
import pandas as pd
import os

# --- IMPORTANT ---
# Please replace the email address below with your own.
# OpenAlex requires a valid email for API access to identify users.
# See: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication#the-polite-pool
USER_EMAIL = "j.muddle@campus.unimib.it"

def reconstruct_abstract(inverted_index):
    """
    Reconstructs the abstract from OpenAlex's inverted index format.
    """
    if not inverted_index:
        return None
    
    word_map = {}
    for word, indices in inverted_index.items():
        for index in indices:
            word_map[index] = word
            
    if not word_map:
        return ""
        
    max_index = max(word_map.keys())
    abstract_words = [word_map.get(i, "") for i in range(max_index + 1)]
            
    return " ".join(abstract_words)

def search_openalex(query):
    """
    Searches OpenAlex for peer-reviewed papers matching the query in title or abstract.
    """
    papers_data = []
    base_url = "https://api.openalex.org/works"
    
    
    print(f"Searching OpenAlex for '{query}'...")
    
    params = {
        'filter': f"publication_year:>2020,abstract.search:\"{query}\"",#has_oa_accepted_or_published_version:true",
        'mailto': USER_EMAIL, # Polite pool email
        'per_page': 100
    }
    
    try:
        with requests.Session() as session:
                print(f"\n[Requesting URL: {session.prepare_request(requests.Request('GET', base_url, params=params)).url}")
                response = session.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get('results', [])
                print(data.get("meta",[]))

                for paper in results:
                    authors = ", ".join([authorship['author']['display_name'] for authorship in paper.get('authorships', [])])
                    
                    paper_dict = {
                        'title': paper.get('title'),
                        'year': paper.get('publication_year'),
                        'authors': authors,
                        'doi': paper.get('doi'),
                        'abstract': reconstruct_abstract(paper.get('abstract_inverted_index')),
                        'venue': paper.get('host_venue', {}).get('display_name') if paper.get('host_venue') else None
                    }
                    papers_data.append(paper_dict)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    print(f"Found {len(papers_data)} results for '{query}'.")
    return pd.DataFrame(papers_data)

if __name__ == "__main__":
    queries = [
        "controlled text generation",
        "constrained text generation",
        "lexical constraints"
    ]

    for query in queries:
        directory = query
        filename = f"{query.replace(' ', '_')}_openalex.csv"
        filepath = os.path.join(directory, filename)

        if not os.path.exists(directory):
            os.makedirs(directory)

        df = search_openalex(query)
        if not df.empty:
            df.to_csv(filepath, index=False)
            print(f"Saved {len(df)} papers to '{filepath}'")
        else:
            print(f"No papers found for '{query}', CSV not created.")
