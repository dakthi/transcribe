import pandas as pd
import re
from pathlib import Path

def clean_invoice_data(master_folder: str) -> None:
    """
    Clean and organize invoice data from CSV files in master folder.
    """
    try:
        # Clean up the path for macOS drag-and-drop behavior
        master_folder = master_folder.strip('"').strip("'").strip()
        
        # Find CSV files in the master folder
        csv_files = list(Path(master_folder).glob('*.csv'))
        
        if not csv_files:
            print("❌ No CSV files found in the master folder")
            return
            
        # Process each CSV file
        for input_file in csv_files:
            if input_file.name.startswith('cleaned_'):
                continue  # Skip already cleaned files
                
            # Create output filename
            output_file = input_file.parent / f"cleaned_{input_file.name}"
            
            # Read the CSV file
            df = pd.read_csv(input_file)
            
            # Create a new DataFrame with proper columns
            cleaned_df = pd.DataFrame(columns=['No', 'Date', 'Company', 'Amount'])
            
            # Process each row
            for _, row in df.iterrows():
                if pd.notna(row['Description']):  # Check if description exists
                    text = str(row['Description'])
                    
                    # Extract components using regex
                    pattern = r'(\d{2}/\d{2}/\d{2,4}),\s*([^,]+),\s*[£]?(\d+\.?\d*)'
                    match = re.match(pattern, text)
                    
                    if match:
                        date, company, amount = match.groups()
                        cleaned_df.loc[len(cleaned_df)] = {
                            'No': row['No'],
                            'Date': date,
                            'Company': company.strip(),
                            'Amount': amount.strip()
                        }
            
            # Save to new CSV file
            cleaned_df.to_csv(output_file, index=False)
            print(f"✅ Successfully cleaned {input_file.name}")
            print(f"📝 Saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("Drag and drop the master folder into this terminal and press Enter:")
    master_folder = input().strip()
    
    clean_invoice_data(master_folder)
