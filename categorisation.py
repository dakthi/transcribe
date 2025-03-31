import os
import pandas as pd
from pathlib import Path

# Step 1: User input for the master folder
def select_master_folder() -> str:
    """Get and validate the master folder path."""
    while True:
        print("Drag and drop the master folder here and press Enter:")
        folder = input().strip().replace("'", "").replace('"', "")
        folder_path = Path(os.path.expanduser(folder))
        
        if folder_path.exists() and folder_path.is_dir():
            return str(folder_path)
        print("Invalid folder path. Please try again.")

# Get master folder path
master_folder = select_master_folder()

# Step 2: Locate all CSV transaction files
files = [f for f in os.listdir(master_folder) if f.endswith('.csv')]

if not files:
    print("No CSV transaction files found in the specified folder.")
    exit()

# Updated category mapping
category_mapping = {
    "Salary": ["PAYROLL", "SALARY", "WAGE"],
    "Groceries": ["TESCO", "SAINSBURY", "ASDA", "LIDL"],
    "Dining Out": ["MCDONALDS", "KFC", "STARBUCKS", "BURGER KING"],
    "Entertainment": ["TEMU.COM", "SPOTIFY", "CINEMA", "GAME"],
    "Purchase": ["KOREA FOODS", "UBER", "TRAIN", "BUS"],
    "Sundry": ["LIDL GB", "CO-OP GROUP", "WATER", "COUNCIL TAX", "BT", "VIRGIN"],
    "POS Sale": ["PAYMENTSENSE LIMIT", "EBAY", "ZARA", "H&M"],
    "Business Rates": ["ROYAL BOROUGH", "DENTIST", "OPTICIAN"],
    "Other": []
}

# Function to categorize transactions
def categorize_transaction(description):
    description = str(description).upper()
    for category, keywords in category_mapping.items():
        if any(keyword in description for keyword in keywords):
            return category
    return "Other"

# Step 3: Process each CSV file
for file_name in files:
    file_path = os.path.join(master_folder, file_name)

    # Read the CSV file
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading {file_name}: {e}")
        continue  # Skip this file and proceed with the next one

    # Ensure column names match the expected format
    expected_columns = [
        "Transaction Date", "Transaction Type", "Sort Code", "Account Number",
        "Transaction Description", "Debit Amount", "Credit Amount", "Balance"
    ]
    df.columns = df.columns.str.strip()  # Trim any leading/trailing spaces

    # Verify if all expected columns exist (case-insensitive check)
    lower_columns = {col.lower(): col for col in df.columns}
    if not all(col.lower() in lower_columns for col in expected_columns):
        print(f"Column names do not match the expected format in {file_name}. Skipping file.")
        continue

    # Rename columns to match expected names (handles case and space differences)
    df = df.rename(columns={lower_columns[col.lower()]: col for col in expected_columns})

    # Categorize transactions
    df["Category"] = df["Transaction Description"].apply(categorize_transaction)

    # Step 4: Display categorized data preview
    print(f"\nCategorized Transactions Preview for {file_name}:")
    print(df.head())  # Show first few rows

    # Step 5: Save categorized data back to a new CSV file
    output_file = os.path.join(master_folder, f"categorized_{file_name}")
    df.to_csv(output_file, index=False)

    print(f"\nCategorized transactions saved to: {output_file}")

print("\nProcessing complete for all CSV files!")
