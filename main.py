import json
import asyncio
from query_generator import QueryGenerator
from search_engine import run_parallel_search

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

    print("\n✅ Aggregated Results:")
    for query_result in results:
        print(f"\n🔎 Query: {query_result['query']}")
        for source_result in query_result["sources"]:
            print(f"  📡 Source: {source_result['source']}")
            for item in source_result["results"]:
                print(f"    • {item['company']} -> {list(item.values())[1]}")

if __name__ == "__main__":
    main()
