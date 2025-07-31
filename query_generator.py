import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

class QueryGenerator:
    def __init__(self):
        pass

    def generate_queries(self, research_goal: str, num_queries: int = 10):
        prompt = f"""
        You are an expert GTM research assistant.

        Your task is to break down the following research goal into a set of {num_queries} useful and diverse search queries across multiple data sources.

        Research Goal: "{research_goal}"

        Please return the queries as a Python list of strings.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            output = response.choices[0].message.content.strip()
            queries = eval(output)
            return queries

        except Exception as e:
            print("[ERROR] Failed to generate queries:", e)
            return []
