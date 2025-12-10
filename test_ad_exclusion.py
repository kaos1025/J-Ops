from src.extractor.keyword_analyzer import KeywordAnalyzer
import os

# Find the latest results csv
files = [f for f in os.listdir('.') if f.startswith('results_') and f.endswith('.csv')]
files.sort(reverse=True)
latest_csv = files[0]

print(f"Testing with: {latest_csv}")

analyzer = KeywordAnalyzer()
analyzer.analyze_file(latest_csv, "test_report.csv")
