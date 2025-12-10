
import re

file_path = "c:\\juji\\J-Ops\\debug.html"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
        pattern_string = 'key&quot;:&quot;price&quot;'
        # Find all occurrences
        matches = [m.start() for m in re.finditer(re.escape(pattern_string), content)]
        print(f"Found {len(matches)} occurrences")
        
        for i, start_idx in enumerate(matches[:3]): # Show first 3
            # Print 100 chars after the match
            snippet = content[start_idx:start_idx+100]
            print(f"Match {i+1} snippet repr: {repr(snippet)}")
            
except Exception as e:
    print(f"Error: {e}")
