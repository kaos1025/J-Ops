import os
import sys
import replicate
from dotenv import load_dotenv
from pathlib import Path
import requests

# Force standard encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class FaceSwapper:
    """
    Face Swap Automation Class
    Uses Replicate's lucataco/modelscope-facefusion for face swapping.
    """
    
    # Model ID for lucataco/modelscope-facefusion
    MODEL_ID = "lucataco/modelscope-facefusion:52edbb2b42beb4e19242f0c9ad5717211a96c63ff1f0b0320caa518b2745f4f7"

    def __init__(self):
        """Initialize environment and paths."""
        load_dotenv()
        
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("Error: REPLICATE_API_TOKEN is not set in .env file.")
            
        self.base_dir = Path(__file__).parent
        self.raw_photos_dir = self.base_dir / "raw_photos"
        self.result_photos_dir = self.base_dir / "result_photos"
        self.base_face_path = self.base_dir / "base_face.jpg"
        
        # Ensure directories exist
        self.raw_photos_dir.mkdir(exist_ok=True)
        self.result_photos_dir.mkdir(exist_ok=True)
        
        print(f"[*] Initialized FaceSwapper")
        print(f"    Raw Photos Dir: {self.raw_photos_dir}")
        print(f"    Result Photos Dir: {self.result_photos_dir}")
        print(f"    Base Face: {self.base_face_path}")

    def swap_face(self, target_img_path: Path) -> bool:
        """
        Run the Face Swap API.
        
        Args:
            target_img_path: Path to the photo where face needs to be replaced.
        """
        if not self.base_face_path.exists():
            print(f"[!] Base face image not found at: {self.base_face_path}")
            return False

        try:
            output_filename = f"swapped_{target_img_path.name}"
            output_path = self.result_photos_dir / output_filename
            
            print(f"[*] Processing: {target_img_path.name}")

            with open(target_img_path, "rb") as target_file, open(self.base_face_path, "rb") as source_file:
                # Prepare inputs for Face Swap
                # lucataco/modelscope-facefusion takes 'template_image' (target) and 'user_image' (source)
                inputs = {
                    "template_image": target_file,
                    "user_image": source_file,
                }
                
                output = replicate.run(
                    self.MODEL_ID,
                    input=inputs
                )

            # Output is usually a URL string or object depending on model
            # For this model effectively likely just a URL or FileOutput object
            
            output_url = str(output)

            if output_url and output_url.startswith("http"):
                # Save result
                response = requests.get(output_url)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"[+] Saved to: {output_path}")
                    return True
                else:
                    print(f"[-] Failed to download result from {output_url}")
                    return False
            else:
                print(f"[-] No valid output received. Output: {output}")
                return False

        except Exception as e:
            # Handle API errors (e.g., no face detected) gracefully
            print(f"[!] Error processing {target_img_path.name}: {e}")
            return False

    def run_batch(self):
        """Process all images in raw_photos."""
        photos = list(self.raw_photos_dir.glob("*.[jJ][pP]*[gG]")) + list(self.raw_photos_dir.glob("*.png"))
        
        if not photos:
            print("[!] No photos found in 'raw_photos' directory.")
            return

        if not self.base_face_path.exists():
            print(f"[!] 'base_face.jpg' not found in: {self.base_dir}")
            print("    Please place your desired face image named 'base_face.jpg' in the root folder.")
            return

        success_count = 0
        
        for photo_path in photos:
            if self.swap_face(photo_path):
                success_count += 1
            
        print(f"\n[*] Batch processing complete. {success_count}/{len(photos)} successful.")

def main():
    try:
        app = FaceSwapper()
        app.run_batch()
    except ValueError as ve:
        print(ve)
    except Exception as e:
        print(f"[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
