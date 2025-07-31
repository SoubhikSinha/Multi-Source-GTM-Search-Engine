import json
import asyncio
from query_generator import QueryGenerator
from search_engine import run_parallel_search
from result_merger import merge_results

def load_input():
    with open("data/sample_input.json", "r") as f:
        return json.load(f)

def main():
    input_data = load_input()
    research_goal = input_data["research_goal"]

    generator = QueryGenerator()
    queries = generator.generate_queries(research_goal, num_queries=5)

    print("\n🔍 Generated Queries:")
    for q in queries:
        print("-", q)

    print("\n⏳ Running searches across sources...")
    results = asyncio.run(run_parallel_search(queries))

    merged = merge_results(results)

    print("\n✅ Merged Company Insights:")
    for entry in merged:
        print(f"\n🏢 Company: {entry['company']}")
        print(f"🔁 Sources: {entry['evidence_sources']}")
        print(f"🎯 Confidence Score: {entry['confidence_score']}")
        print(f"🔍 Appeared in Queries:")
        for q in entry["appeared_in_queries"]:
            print(f"   • {q}")
        print(f"📎 Findings:")
        for finding in entry["findings"]:
            src = finding["source"]
            snippet = finding["data"]
            print(f"   - [{src}] {snippet}")

if __name__ == "__main__":
    main()
