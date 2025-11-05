import os
import pandas as pd
from functools import reduce

# Get the current working directory
current_directory = os.getcwd()

# List of specific directories to process
subdirectories = [
    "constrained text generation",
    "controlled text generation",
    "lexical constraints"
]

# Loop through each specified subdirectory
for subdir in subdirectories:
    subdir_path = os.path.join(current_directory, subdir)
    
    # Find all CSV files in the subdirectory, excluding 'merged_files.csv'
    csv_files = [
        f for f in os.listdir(subdir_path) 
        if f.endswith('.csv') and f != 'merged_files.csv'
    ]

    # List to hold dataframes
    dfs = []
    
    print(f"Processing CSV files in '{subdir}':")
    for csv_file in csv_files:
        csv_path = os.path.join(subdir_path, csv_file)
        print(f"  - Reading '{csv_file}'")
        df = pd.read_csv(csv_path, na_values=['not available'])
        
        # Standardize column names
        df.columns = [col.lower().strip().replace('"', '') for col in df.columns]

        # Standardize DOI values to be case-insensitive before any processing
        if 'doi' in df.columns:
            df['doi'] = df['doi'].str.lower()
        
        # De-duplicate rows based on 'doi'
        # Group by 'doi' and take the first non-null value for each column
        if 'doi' in df.columns:
            df.dropna(subset=['doi'], inplace=True)
            df = df.groupby('doi', as_index=False).first()
        else:
            print(f"  - Warning: 'doi' column not found in '{csv_file}'. Skipping de-duplication for this file.")

        dfs.append(df)

    if not dfs:
        print(f"No valid dataframes to merge in '{subdir}'.")
        continue

    # Merge all dataframes on the 'doi' column
    merged_df = dfs[0]
    for i in range(1, len(dfs)):
        right_df = dfs[i]
        
        # Find overlapping columns to merge data, excluding the 'doi' key
        overlapping_cols = [col for col in merged_df.columns if col in right_df.columns and col != 'doi']
        
        # Perform the merge with suffixes to handle other overlapping columns temporarily
        merged_df = pd.merge(merged_df, right_df, on='doi', how='outer', suffixes=('_left', '_right'))
        
        # For each overlapping column, combine the data
        for col in overlapping_cols:
            left_col = f'{col}_left'
            right_col = f'{col}_right'
            
            # Fill missing values in the left column with values from the right column
            merged_df[col] = merged_df[left_col].fillna(merged_df[right_col])
            
            # Drop the temporary left and right columns
            merged_df.drop(columns=[left_col, right_col], inplace=True)
        
    # Define the output path for the merged CSV
    output_path = os.path.join(subdir_path, 'merged_files.csv')
    
    # Save the merged dataframe to a new CSV file
    merged_df.to_csv(output_path, index=False, na_rep='not available')
    
    print(f"Successfully merged {len(dfs)} CSV files into '{output_path}'\n")

print("Script finished.")

# --- Final Merge Step ---
print("\nStarting the final merge of all 'merged_files.csv'...")

final_merge_paths = [
    os.path.join(current_directory, subdir, 'merged_files.csv')
    for subdir in subdirectories
]

final_dfs = []
for path in final_merge_paths:
    if os.path.exists(path):
        print(f"  - Reading '{path}'")
        df = pd.read_csv(path, na_values=['not available'])
        # Standardize columns to handle any variations
        df.columns = [col.lower().strip().replace('"', '') for col in df.columns]

        # Standardize DOI values to be case-insensitive before any processing
        if 'doi' in df.columns:
            df['doi'] = df['doi'].str.lower()
            
        final_dfs.append(df)

if len(final_dfs) < 2:
    print("Not enough 'merged_files.csv' to create a final master file. Exiting.")
else:
    # Merge all the 'merged_files.csv' dataframes
    final_merged_df = final_dfs[0]
    for i in range(1, len(final_dfs)):
        right_df = final_dfs[i]
        overlapping_cols = [col for col in final_merged_df.columns if col in right_df.columns and col != 'doi']
        final_merged_df = pd.merge(final_merged_df, right_df, on='doi', how='outer', suffixes=('_left', '_right'))
        for col in overlapping_cols:
            left_col, right_col = f'{col}_left', f'{col}_right'
            final_merged_df[col] = final_merged_df[left_col].fillna(final_merged_df[right_col])
            final_merged_df.drop(columns=[left_col, right_col], inplace=True)

    
    
    if 'publication year' in final_merged_df.columns and 'year' in final_merged_df.columns:
        print("  - Merging 'year' and 'publication year' columns...")
        final_merged_df['year'] = final_merged_df['year'].fillna(final_merged_df['publication year'])
        final_merged_df.drop(columns=['publication year'], inplace=True)
    elif 'publication year' in final_merged_df.columns:
        # If only 'publication year' exists, rename it to 'year'
        final_merged_df.rename(columns={'publication year': 'year'}, inplace=True)

    # Combine document type columns
    type_cols = ['type', 'item type', 'document type']
    present_type_cols = [col for col in type_cols if col in final_merged_df.columns]
    
    if len(present_type_cols) > 1:
        print("  - Merging document type columns...")
        # Use the first column as the base for the new 'type' column
        final_merged_df['type'] = final_merged_df[present_type_cols[0]]
        # Fill in missing values from the other columns
        for col in present_type_cols[1:]:
            final_merged_df['type'] = final_merged_df['type'].fillna(final_merged_df[col])
        # Drop the old, redundant columns
        final_merged_df.drop(columns=[col for col in present_type_cols if col != 'type'], inplace=True)

    # Combine author columns
    author_cols = ['authors', 'author(s)', 'author full names']
    present_author_cols = [col for col in author_cols if col in final_merged_df.columns]
    
    if len(present_author_cols) > 0:
        print("  - Merging author columns...")
        # Create a new unified column to avoid conflicts
        final_merged_df['authors_unified'] = final_merged_df[present_author_cols[0]]
        # Fill in missing values from the other columns
        if len(present_author_cols) > 1:
            for col in present_author_cols[1:]:
                final_merged_df['authors_unified'] = final_merged_df['authors_unified'].fillna(final_merged_df[col])
        # Drop all old author-related columns
        final_merged_df.drop(columns=present_author_cols, inplace=True, errors='ignore')
        # Rename the unified column to 'authors'
        final_merged_df.rename(columns={'authors_unified': 'authors'}, inplace=True)

    # Reorder columns: title, year, then everything else
    print("  - Reordering columns...")
    cols = list(final_merged_df.columns)
    
    # Ensure 'title' and 'year' are present, if not, add them
    if 'title' not in cols: final_merged_df['title'] = 'not available'
    if 'year' not in cols: final_merged_df['year'] = 'not available'
    
    # Remove from list and insert at the front
    if 'title' in cols: cols.remove('title')
    if 'year' in cols: cols.remove('year')
    if 'authors' in cols: cols.remove('authors')
    
    new_order = ['title', 'year', 'authors'] + [c for c in cols if c not in ['title', 'year', 'authors']]
    final_merged_df = final_merged_df[new_order]

    # Filter for the final desired columns before saving
    final_columns_to_keep = ['title', 'year', 'authors', 'doi', 'type', 'venue', 'journal']
    existing_final_columns = [col for col in final_columns_to_keep if col in final_merged_df.columns]
    final_merged_df = final_merged_df[existing_final_columns]

    # Save the final merged dataframe
    final_output_path = os.path.join(current_directory, 'final_master_merge.csv')
    final_merged_df.to_csv(final_output_path, index=False, na_rep='not available')
    
    print(f"\nSuccessfully created the final master file at '{final_output_path}'")
