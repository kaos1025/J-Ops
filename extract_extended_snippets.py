
import re

file_path = "c:\\juji\\J-Ops\\debug.html"
output_path = "c:\\juji\\J-Ops\\snippets_extended.txt"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
        # We need to find the START of the tag that contains this string.
        # But finding the tag start is hard on minified HTML.
        # We'll just look around the match.
        
        pattern_string = 'key&quot;:&quot;price&quot;'
        # Find all occurrences
        matches = [m.start() for m in re.finditer(re.escape(pattern_string), content)]
        
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(f"Found {len(matches)} occurrences\n\n")
            for i, start_idx in enumerate(matches[:3]): # Show first 3
                # Print 500 chars before and 200 after
                start_context = max(0, start_idx - 500)
                snippet = content[start_context : start_idx+200]
                out.write(f"Match {i+1} context:\n{snippet}\n\n")
                
    print("Done writing extended snippets.")

except Exception as e:
    print(f"Error: {e}")
