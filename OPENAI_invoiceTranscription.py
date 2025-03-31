import base64
import os
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
import csv

# OpenAI client setup with better error handling
try:
    from openai import OpenAI
    client = OpenAI()
except ImportError:
    import openai
    client = openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    openai.api_key = api_key

def encode_image(image_path: str) -> Optional[str]:
    """Encode image to base64 with error handling."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def get_image_paths(folder_path: str, max_images: int = 3) -> List[str]:
    """Get paths of first 3 images in folder, sorted alphabetically."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    image_paths = [
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in image_extensions
    ]
    return sorted(image_paths)[:max_images]

def create_message_content(base64_images: List[str]) -> List[dict]:
    """Create the message content for the API request."""
    prompt_text = {
        "type": "text",
        "text": """transcribe the details of these invoices, each details separated by a coma, details required: date, supplier, amount (just number no currency sign), in the exact order and not anything additional"""
    }
    
    image_contents = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img}"}
        }
        for img in base64_images if img
    ]
    
    return [prompt_text] + image_contents

def get_description(base64_images: List[str]) -> str:
    """Get description from GPT-4 Vision."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": create_message_content(base64_images)
            }],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error getting description: {e}")
        return None

def select_master_folder() -> str:
    """Get and validate master folder path."""
    while True:
        print("Drag and drop the master folder here and press Enter:")
        folder = input().strip().replace("'", "")
        folder_path = Path(os.path.expanduser(folder))
        
        if folder_path.exists() and folder_path.is_dir():
            return str(folder_path)
        print("Invalid folder path. Please try again.")

def process_folders() -> None:
    """Process all images in master folder and save invoice info to CSV."""
    master_folder = select_master_folder()
    
    image_paths = get_image_paths(str(master_folder))
    if not image_paths:
        print("No images found in folder")
        return
        
    print(f"Found {len(image_paths)} images to process")
    
    # CSV template headers (A to H):
    headers = [
        "A",               # Leave blank
        "Sn-",             # Leave blank
        "Type -",          # Leave blank
        "Date Account Referen+t",  # We’ll store date here
        "Nominal A/C Ref =",       # Supplier name here
        "Reference",       # Invoice/reference number
        "Details",         # Description
        "Net Amount -",    # Net amount
        "Tax Amount -",    # VAT/Tax
        "Gross Amount",    # Total/Gross
        "Tax Code ~"       # Leave blank
    ]
    
    csv_path = os.path.join(master_folder, "invoices.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        for index, image_path in enumerate(tqdm(image_paths, desc="Processing images"), 1):
            print(f"\nProcessing image: {Path(image_path).name}")
            
            base64_image = encode_image(image_path)
            if not base64_image:
                print("Failed to encode image")
                continue
                
            description = get_description([base64_image])
            if description:
                print("\nRaw Description:")
                print(description)
                print("-" * 50)
                
                # Parse description assuming: date, supplier, ref, details, net, tax, gross
                try:
                    parts = [part.strip() for part in description.split(",")]
                    while len(parts) < 7:
                        parts.append("")
                    date, supplier, ref, details, net, tax, gross = parts[:7]
                    
                    # Write to CSV in correct column order
                    row = [
                        "", "", "",        # A, Sn-, Type -
                        date,
                        supplier,
                        ref,
                        details,
                        net,
                        tax,
                        gross,
                        ""                 # Tax Code ~
                    ]
                    writer.writerow(row)
                except Exception as e:
                    print(f"Error parsing description: {e}")
                    continue

    print(f"\nInvoices saved to: {csv_path}")

if __name__ == "__main__":
    process_folders()

