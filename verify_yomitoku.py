try:
    from yomitoku.document_analyzer import DocumentAnalyzer
    print("Success: yomitoku imported")
except ImportError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")
