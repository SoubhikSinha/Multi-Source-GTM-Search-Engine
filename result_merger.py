from collections import defaultdict

def merge_results(all_query_results: list) -> list:
    merged = defaultdict(lambda: {
        "evidence_sources": set(),
        "queries": set(),
        "findings": []
    })

    for query_result in all_query_results:
        query = query_result["query"]
        for source in query_result["sources"]:
            source_name = source["source"]
            for item in source["results"]:
                company = item.get("company")
                if not company:
                    continue
                entry = merged[company]
                entry["evidence_sources"].add(source_name)
                entry["queries"].add(query)
                entry["findings"].append({
                    "source": source_name,
                    "query": query,
                    "data": item
                })

    final_output = []
    for company, data in merged.items():
        final_output.append({
            "company": company,
            "evidence_sources": list(data["evidence_sources"]),
            "appeared_in_queries": list(data["queries"]),
            "findings": data["findings"],
            "confidence_score": round(min(1.0, 0.3 + 0.2 * len(data["evidence_sources"])), 2)
        })

    return final_output
