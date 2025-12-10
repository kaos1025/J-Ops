import os
import sys
import replicate
from dotenv import load_dotenv
from pathlib import Path
import time

# Force standard encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class IdmVtonVMD:
    """
    IDM-VTON Virtual Model Dressing Class
    Uses Replicate's IDM-VTON model for accurate garment fitting.
    """
    
    # Constants
    MODEL_ID = "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"
    DEFAULT_MODEL_URL = "https://replicate.delivery/pbxt/Jt7G4y3x2x4zX9x8/model_01.jpg" # Example fallback or use a known public one
    
    # Valid categories for IDM-VTON
    CATEGORIES = ["upper_body", "lower_body", "dresses"]

    def __init__(self):
        """Initialize environment and paths."""
        load_dotenv()
        
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("Error: REPLICATE_API_TOKEN is not set in .env file.")
            
        self.base_dir = Path(__file__).parent
        self.clothes_dir = self.base_dir / "raw_clothes"
        self.model_dir = self.base_dir / "base_model"
        self.output_dir = self.base_dir / "fitted_images"
        
        # Ensure directories exist
        self.clothes_dir.mkdir(exist_ok=True)
        self.model_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Define base model path
        self.base_model_path = self.model_dir / "model_01.jpg"
        
        print(f"[*] Initialized IdmVtonVMD")
        print(f"    Clothes Dir: {self.clothes_dir}")
        print(f"    Base Model: {self.base_model_path}")
        print(f"    Output Dir: {self.output_dir}")

    def classify_category(self, filename: str) -> str:
        """
        Auto-classify garment category based on keywords in filename.
        Defaults to 'upper_body'.
        """
        lower = filename.lower()
        if any(x in lower for x in ['pant', 'jean', 'skirt', 'short', 'trousers']):
            return "lower_body"
        elif any(x in lower for x in ['dress', 'gown', 'robe']):
            return "dresses"
        else:
            return "upper_body"

    def get_garment_description(self, filename: str) -> str:
        """
        Generate a simple description from the filename.
        """
        # Remove extension and replace underscore/hyphen with space
        name = Path(filename).stem
        cleaned = name.replace("_", " ").replace("-", " ")
        return f"A high quality photo of {cleaned}"

    def generate_tryon(self, garment_path: Path, human_img_input: object, category: str, description: str) -> bool:
        """
        Run the virtual try-on API.
        
        Args:
            garment_path: Path to garment image
            human_img_input: File handle or URL for the human model
            category: 'upper_body', 'lower_body', or 'dresses'
            description: Text description of the garment
        """
        try:
            output_filename = f"fitted_{garment_path.name}"
            output_path = self.output_dir / output_filename
            
            print(f"[*] Processing: {garment_path.name} ({category})")
            print(f"    Desc: {description}")

            with open(garment_path, "rb") as garm_file:
                # Prepare inputs for IDM-VTON
                inputs = {
                    "garm_img": garm_file,
                    "human_img": human_img_input,
                    "garment_des": description,
                    "category": category,
                    "crop": False, # Basic crop usually false for high qual full image
                    "seed": 42,
                    "steps": 30
                }
                
                output_url = replicate.run(
                   self.MODEL_ID,
                   input=inputs
                )

            if output_url:
                # Save result
                import requests
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
                print("[-] No output received from Replicate API.")
                return False

        except Exception as e:
            print(f"[!] Error processing {garment_path.name}: {e}")
            return False

    def run_batch(self):
        """Process all images in raw_clothes."""
        clothes = list(self.clothes_dir.glob("*.[jJ][pP]*[gG]")) + list(self.clothes_dir.glob("*.png"))
        
        if not clothes:
            print("[!] No clothes found in 'raw_clothes' directory.")
            return

        # Prepare Human Image
        # If local file exists, use it. Otherwise, use DEFAULT_MODEL_URL if we can (API supports URL?)
        # Replicate python client methods usually take file handles or URLs.
        # Ideally, we should use a valid file handle if local, or a URL string.
        
        human_img_handle = None
        human_img_url = None
        
        if self.base_model_path.exists():
            print(f"[*] Using local base model: {self.base_model_path.name}")
            # We open it for each request or read bytes? File handle needs to be fresh usually.
            # We will handle opening inside the loop or pass path? 
            # Replicate `input` argument expects an open file handle.
            # We'll handle it inside the loop to be safe with file pointers.
        else:
            print(f"[*] Local base model not found. Using default demo URL.")
            human_img_url = self.DEFAULT_MODEL_URL

        success_count = 0
        
        for garm_path in clothes:
            category = self.classify_category(garm_path.name)
            desc = self.get_garment_description(garm_path.name)
            
            # Open human image handle if local
            if human_img_url:
                human_input = human_img_url
                if self.generate_tryon(garm_path, human_input, category, desc):
                    success_count += 1
            else:
                # Use local file
                try:
                    with open(self.base_model_path, "rb") as h_file:
                        if self.generate_tryon(garm_path, h_file, category, desc):
                            success_count += 1
                except Exception as e:
                    print(f"[!] Error reading base model: {e}")

        print(f"\n[*] Batch processing complete. {success_count}/{len(clothes)} successful.")

def main():
    try:
        app = IdmVtonVMD()
        app.run_batch()
    except ValueError as ve:
        print(ve)
    except Exception as e:
        print(f"[!] Critical Error: {e}")

if __name__ == "__main__":
    main()
