
import re

file_path = "c:\\juji\\J-Ops\\debug.html"
output_path = "c:\\juji\\J-Ops\\snippets.txt"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
        pattern_string = 'key&quot;:&quot;price&quot;'
        # Find all occurrences
        matches = [m.start() for m in re.finditer(re.escape(pattern_string), content)]
        
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(f"Found {len(matches)} occurrences\n\n")
            for i, start_idx in enumerate(matches[:10]): # Show first 10
                # Print 100 chars after the match
                snippet = content[start_idx:start_idx+150]
                out.write(f"Match {i+1}:\n{snippet}\n\n")
                
    print("Done writing snippets.")

except Exception as e:
    print(f"Error: {e}")
