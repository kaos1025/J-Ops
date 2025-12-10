import os
import shutil
from pathlib import Path

def refactor_project():
    base_dir = Path(__file__).parent
    
    # 1. Define Directories
    # Structure: src/scraper, src/analyzer, data/raw, data/reports
    target_dirs = {
        "scraper": base_dir / "src" / "scraper",
        "analyzer": base_dir / "src" / "analyzer",
        "raw_data": base_dir / "data" / "raw",
        "reports": base_dir / "data" / "reports",
    }
    
    # 2. Create Directories & __init__.py
    print("[*] Creating directories...")
    for key, path in target_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        print(f"    Created: {path.relative_to(base_dir)}")
        
        # Add __init__.py to src packages
        if "src" in path.parts:
            init_file = path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
    
    # Ensure src/__init__.py exists
    (base_dir / "src" / "__init__.py").touch()

    # 3. Move Files
    print("\n[*] Moving files...")
    
    for file_path in base_dir.glob("*"):
        if not file_path.is_file():
            continue
            
        name = file_path.name
        
        # Skip this script
        if name == "refactor.py":
            continue

        dest = None
        
        # Scrapers
        if name.endswith("_scraper.py") or name == "naver_shopping_scraper.py" or name == "title_fetcher.py":
            dest = target_dirs["scraper"]
            
        # Analyzers
        elif name.endswith("_analyzer.py") or name == "keyword_analyzer.py":
            dest = target_dirs["analyzer"]
            
        # CSV Files
        elif name.endswith(".csv"):
            if "report" in name or "keyword_report" in name or "tag_report" in name:
                dest = target_dirs["reports"]
            else:
                dest = target_dirs["raw_data"]

        # Move if logic matched
        if dest:
            try:
                shutil.move(str(file_path), str(dest / name))
                print(f"    Moved {name} -> {dest.relative_to(base_dir)}")
            except Exception as e:
                print(f"    [!] Error moving {name}: {e}")

    # 4. Update/Create .gitignore
    print("\n[*] Updating .gitignore...")
    gitignore_path = base_dir / ".gitignore"
    
    ignores_to_add = [
        ".env",
        "__pycache__/",
        "data/",
        "*.log",
        ".DS_Store"
    ]
    
    existing_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
    
    with open(gitignore_path, "a", encoding="utf-8") as f:
        # Add a newline if file is not empty and doesn't end with one
        if existing_content and not existing_content.endswith("\n"):
            f.write("\n")
            
        for item in ignores_to_add:
            if item not in existing_content:
                f.write(f"{item}\n")
                print(f"    Added {item}")

    print("\n리팩토링 완료! 파일들이 정리되었습니다.")

if __name__ == "__main__":
    refactor_project()
