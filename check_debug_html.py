
import re

file_path = "c:\\juji\\J-Ops\\debug.html"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
        print(f"File size: {len(content)} chars")
        
        # Check for escaped quotes
        pattern_escaped = r'key&quot;:&quot;price&quot;'
        match_escaped = re.search(pattern_escaped, content)
        print(f"Pattern '{pattern_escaped}': {'FOUND' if match_escaped else 'NOT FOUND'}")
        
        # Check for normal quotes
        pattern_normal = r'key":"price"'
        match_normal = re.search(pattern_normal, content)
        print(f"Pattern '{pattern_normal}': {'FOUND' if match_normal else 'NOT FOUND'}")
        
        # Check for mixed or other variations if needed
        # Just printing a snippet around "price" if found
        snippet_match = re.search(r'(.{0,50}price.{0,50})', content)
        if snippet_match:
             print(f"Snippet: {snippet_match.group(1)}")

except Exception as e:
    print(f"Error: {e}")
