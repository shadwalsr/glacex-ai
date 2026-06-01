import os
import sys
import yaml
from urllib.parse import urlparse

REQUIRED_KEYS = {"name", "url", "type", "category"}
VALID_TYPES = {"rss", "httpx", "playwright"}
VALID_CATEGORIES = {"newsletter", "arxiv", "company", "product", "investor", "conference", "podcast", "repository"}

def validate_entry(entry, path):
    # Check required keys
    for key in REQUIRED_KEYS:
        if key not in entry or not entry[key]:
            print(f"Error in {path}: Entry '{entry.get('name', 'unknown')}' is missing required key '{key}'")
            return False
            
    # Validate type
    if entry["type"] not in VALID_TYPES:
        print(f"Error in {path}: Invalid type '{entry['type']}' for '{entry['name']}'. Must be one of {VALID_TYPES}")
        return False
        
    # Validate category
    if entry["category"] not in VALID_CATEGORIES:
        print(f"Error in {path}: Invalid category '{entry['category']}' for '{entry['name']}'. Must be one of {VALID_CATEGORIES}")
        return False
        
    # Validate url
    parsed = urlparse(entry["url"])
    if not parsed.scheme or not parsed.netloc:
        print(f"Error in {path}: Invalid URL format '{entry['url']}' for '{entry['name']}'")
        return False
        
    return True

def main():
    root = os.path.join(os.path.dirname(__file__), "..")
    sources_path = os.path.join(root, "config", "sources.yaml")
    backlog_path = os.path.join(root, "sources", "backlog.yaml")
    
    success = True
    
    # 1. Validate config/sources.yaml
    print(f"Validating {sources_path}...")
    if not os.path.exists(sources_path):
        print(f"Error: {sources_path} does not exist!")
        sys.exit(1)
        
    try:
        with open(sources_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        sources = data.get("sources", [])
        if not isinstance(sources, list):
            print("Error: 'sources' root node must be a list")
            success = False
        else:
            for s in sources:
                if not validate_entry(s, "config/sources.yaml"):
                    success = False
    except Exception as e:
        print(f"Error parsing sources.yaml: {e}")
        success = False
        
    # 2. Validate sources/backlog.yaml
    print(f"Validating {backlog_path}...")
    if not os.path.exists(backlog_path):
        print(f"Error: {backlog_path} does not exist!")
        sys.exit(1)
        
    try:
        with open(backlog_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        backlog = data.get("backlog", [])
        if not isinstance(backlog, list):
            print("Error: 'backlog' root node must be a list")
            success = False
        else:
            for entry in backlog:
                if not validate_entry(entry, "sources/backlog.yaml"):
                    success = False
    except Exception as e:
        print(f"Error parsing backlog.yaml: {e}")
        success = False
        
    if success:
        print("YAML schema validation passed successfully!")
        sys.exit(0)
    else:
        print("YAML schema validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
