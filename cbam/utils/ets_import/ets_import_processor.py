# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
from .google_drive_service import GoogleDriveService

class ETSImportProcessor:
    def __init__(self, settings):
        """Initialize ETS import processor with settings"""
        self.settings = settings
        self.drive_service = GoogleDriveService(settings)
        self.processed_files = self._get_processed_files()
        self.current_import_log = None
        self.pending_excel_data = None
        # Remove last_processed_df since we're not using date filtering anymore
    
    def _get_processed_files(self):
        """Get list of already processed files to avoid duplicates"""
        try:
            processed_files = frappe.get_all(
                "ETS Import Log",
                filters={"status": "Success"},
                fields=["google_drive_file_id", "source_file"]
            )
            return {log["google_drive_file_id"]: log["source_file"] for log in processed_files}
        except Exception as e:
            frappe.log_error(f"Failed to get processed files: {str(e)}")
            return {}
    
    def import_ets_prices(self):
        """Main ETS price import function"""
        try:
            frappe.publish_progress(0, title="Starting ETS price import...")
            
            # Find latest Excel file in Google Drive folder
            files = self.drive_service.list_files_in_folder(
                self.settings.google_drive_folder_id, 
                self.settings.file_pattern
            )
            
            if not files:
                raise Exception("No Excel files found in Google Drive folder")
            
            # Get the most recent file
            latest_file = files[0]
            
            # Note: We no longer skip files that were processed before
            # This allows incremental imports from the same file
            # Individual records are still checked for duplicates during processing
            
            try:
                # Download file from Google Drive
                excel_file = self.drive_service.download_file(latest_file['id'], latest_file['name'])
                
                # Process Excel data
                df = self._read_excel_file(excel_file, latest_file['name'])
                
                # Validate data structure
                self._validate_excel_structure(df)
                
                # Process and import all data from Excel file (no date filtering)
                frappe.log_error("process_ets_start", "Starting to process ETS data")
                imported_count, successful_rows = self._process_ets_data(df, latest_file['name'])
                frappe.log_error("process_ets_complete", f"ETS data processing complete. Imported: {imported_count}")
                
                # Store only the Excel data rows that were successfully used to create ETS records
                # Note: This will be called later when we have current_import_log set
                frappe.log_error("store_excel_start", "Starting to store successful Excel data rows")
                # Store the data for later use instead of calling the method now
                self.pending_excel_data = {
                    'df': df,
                    'filename': latest_file['name'],
                    'successful_rows': successful_rows
                }
                frappe.log_error("store_excel_complete", f"Excel data prepared for later storage. {len(successful_rows)} rows ready")
                
                # Mark file as processed
                self._mark_file_as_processed(latest_file['id'], latest_file['name'])
                
                return {
                    "status": "Success",
                    "file": latest_file['name'],
                    "file_id": latest_file['id'],
                    "records": imported_count
                }
                
            except Exception as process_error:
                frappe.log_error(f"Process error: {str(process_error)}")
                raise process_error
            
        except Exception as e:
            error_msg = f"ETS import failed: {str(e)}"
            frappe.log_error(error_msg)
            raise Exception(error_msg)
    
    # Date filtering method removed - now processing all records from Excel file

    
    def _read_excel_file(self, excel_file, filename):
        """Read Excel file and return DataFrame"""
        try:
            # Try to read the Excel file
            df = pd.read_excel(excel_file, sheet_name=0)  # Read first sheet
            
            return df
            
        except Exception as e:
            raise Exception(f"Failed to read Excel file {filename}: {str(e)}")
    
    def _validate_excel_structure(self, df):
        """Validate Excel file structure for ETS prices with flexible column matching"""
        try:
            # Get column mappings from settings
            mapped_columns = self._get_column_mappings()
            
            # Check if we have any mapped columns
            if not mapped_columns:
                raise Exception("No column mappings found. Please configure column mappings in the child table.")
            
            # Clean column names (remove trailing spaces and normalize)
            df.columns = df.columns.str.strip()
            
            # Check if mapped columns exist in Excel (with flexible matching)
            missing_columns = []
            column_mapping = {}  # Map configured names to actual Excel names
            
            for mapped_col in mapped_columns:
                mapped_col_clean = mapped_col.strip()
                
                # Try exact match first
                if mapped_col_clean in df.columns:
                    column_mapping[mapped_col] = mapped_col_clean
                    continue
                
                # Try case-insensitive match
                excel_cols_lower = [col.lower() for col in df.columns]
                if mapped_col_clean.lower() in excel_cols_lower:
                    actual_col = df.columns[excel_cols_lower.index(mapped_col_clean.lower())]
                    column_mapping[mapped_col] = actual_col
                    continue
                
                # Try partial match (handle trailing spaces, etc.)
                for excel_col in df.columns:
                    if excel_col.strip() == mapped_col_clean:
                        column_mapping[mapped_col] = excel_col
                        break
                else:
                    missing_columns.append(mapped_col)
            
            if missing_columns:
                # Show available columns for debugging
                available_cols = list(df.columns)
                raise Exception(f"Missing mapped columns in Excel: {missing_columns}. Available columns: {available_cols}")
            
            # Store the column mapping for use in processing
            self.column_mapping = column_mapping
            
            # Log column mapping for debugging (concise)
            frappe.log_error("mapped_columns_count", len(column_mapping))
            frappe.log_error("excel_columns", list(df.columns))
            
            # Debug: Show each mapping individually to avoid truncation
            for mapped_col, actual_col in column_mapping.items():
                frappe.log_error(f"map_{mapped_col.strip()}", actual_col)
            
            # Find the price column (required for ETS import)
            price_column = None
            
            # First try to find by data_type if available
            if hasattr(self.settings, 'excel_column_mapping'):
                for mapping in self.settings.excel_column_mapping:
                    if hasattr(mapping, 'data_type') and mapping.data_type == 'Price':
                        mapped_col = mapping.column_name
                        actual_col = column_mapping.get(mapped_col)
                        if actual_col:
                            price_column = actual_col
                            break
            
            # If no price column found by data_type, try by column name
            if not price_column:
                for mapped_col in mapped_columns:
                    actual_col = column_mapping.get(mapped_col)
                    if actual_col and actual_col.lower() in ['price', 'closing', 'cost', 'rate', 'value', 'amount']:
                        price_column = actual_col
                        break
            
            if not price_column:
                raise Exception("No price column found in mappings. Please map a column containing price data.")
            
            # Validate price column data type
            try:
                df[price_column] = pd.to_numeric(df[price_column], errors='coerce')
                # Remove rows with invalid prices
                df = df.dropna(subset=[price_column])
            except Exception as e:
                raise Exception(f"Price column '{price_column}' must be numeric: {str(e)}")
            
            # Check for empty data
            if df.empty:
                raise Exception("Excel file contains no valid data after validation")
            
            return True
            
        except Exception as e:
            raise Exception(f"Excel structure validation failed: {str(e)}")
    
    def _get_column_mappings(self):
        """Get column mappings from settings"""
        try:
            if not hasattr(self.settings, 'excel_column_mapping'):
                return []
            
            if not self.settings.excel_column_mapping:
                return []
            
            # Return the actual column names from child table
            column_names = []
            for mapping in self.settings.excel_column_mapping:
                if mapping.column_name:
                    column_names.append(mapping.column_name)
            
            return column_names
            
        except Exception as e:
            return []
    

    
    def _process_ets_data(self, df, filename):
        """Process and import ETS price data"""
        try:
            imported_count = 0
            mapped_columns = self._get_column_mappings()
            
            # Check if we have any mapped columns
            if not mapped_columns:
                raise Exception("No column mappings found. Please configure column mappings in the child table.")
            
            # Find the price column (required for ETS import) using actual Excel column name
            price_column = None
            for col_name in mapped_columns:
                if col_name.lower() in ['price', 'cost', 'rate', 'value', 'amount', 'closing']:
                    # Find the actual Excel column name
                    for excel_col in df.columns:
                        if excel_col.strip() == col_name.strip():
                            price_column = excel_col
                            break
                    if price_column:
                        break
            
            if not price_column:
                raise Exception("No price column found in mappings. Please map a column containing price data.")
            
            frappe.log_error("price_column", price_column)
            frappe.log_error("total_rows", len(df))
            frappe.log_error("mapped_columns", str(mapped_columns))
            frappe.log_error("excel_columns", str(list(df.columns)))
            
            # Initialize list to store successful rows
            successful_rows = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    frappe.log_error(f"row_{index}_start", "Processing row")
                    
                    # Get price value (required) using actual Excel column name
                    price_value = row[price_column]
                    frappe.log_error(f"row_{index}_price", str(price_value))
                    
                    # Skip if price is invalid
                    if pd.isna(price_value) or price_value <= 0:
                        frappe.log_error(f"row_{index}_skipped", "Invalid price")
                        continue
                    
                    # Extract date value if available using actual Excel column names
                    date_value = None
                    for col_name in mapped_columns:
                        if col_name.lower() in ['date', 'time', 'period', 'year', 'month', 'day'] or 'date' in col_name.lower():
                            # Find the actual Excel column name
                            actual_col = None
                            for excel_col in df.columns:
                                if excel_col.strip() == col_name.strip():
                                    actual_col = excel_col
                                    break
                            
                            if actual_col and pd.notna(row[actual_col]):
                                date_value = row[actual_col]
                                break
                    
                    # Use today's date if no date found
                    if not date_value or pd.isna(date_value):
                        date_value = frappe.utils.today()
                    
                    # Convert date format if it's a string in DD.MM.YYYY format
                    if isinstance(date_value, str) and '.' in str(date_value):
                        try:
                            # Parse German date format DD.MM.YYYY
                            from datetime import datetime
                            parsed_date = datetime.strptime(str(date_value), '%d.%m.%Y')
                            date_value = parsed_date
                            frappe.log_error("date_converted", f"Converted {str(date_value)} to {parsed_date}")
                        except Exception as e:
                            frappe.log_error("date_conversion_error", f"Failed to convert date {str(date_value)}: {str(e)}")
                            # Keep original value if conversion fails
                            pass
                    
                    # Extract all mapped column values for ETS record
                    volume_value = None
                    high_value = None
                    low_value = None
                    ets_price_type_value = None
                    price_year_value = None
                    
                    for col_name in mapped_columns:
                        if col_name != price_column:
                            # Find the actual Excel column name
                            actual_col = None
                            for excel_col in df.columns:
                                if excel_col.strip() == col_name.strip():
                                    actual_col = excel_col
                                    break
                            
                            if actual_col and pd.notna(row[actual_col]):
                                col_value = row[actual_col]
                                
                                # Map to specific fields based on column names
                                if 'volume' in col_name.lower():
                                    volume_value = col_value
                                elif 'high' in col_name.lower():
                                    high_value = col_value
                                elif 'low' in col_name.lower():
                                    low_value = col_value
                                elif 'type' in col_name.lower():
                                    ets_price_type_value = col_value
                                elif 'year' in col_name.lower():
                                    price_year_value = col_value
                    
                    # Create source description from all mapped columns
                    source_parts = []
                    for col_name in mapped_columns:
                        if col_name != price_column:
                            # Find the actual Excel column name
                            actual_col = None
                            for excel_col in df.columns:
                                if excel_col.strip() == col_name.strip():
                                    actual_col = excel_col
                                    break
                            
                            if actual_col and pd.notna(row[actual_col]):
                                source_parts.append(f"{col_name}: {row[actual_col]}")
                    
                    source_value = " | ".join(source_parts) if source_parts else f"Imported from {filename}"
                    
                    # Check if record already exists before creating
                    existing_record = self._check_existing_record(
                        date_value, price_value, source_value,
                        volume_value, high_value, low_value, 
                        ets_price_type_value, price_year_value
                    )
                    
                    if existing_record:
                        frappe.log_error(f"row_{index}_duplicate", f"Record already exists: {existing_record}")
                        continue
                    
                    # Create ETS record with all extracted values
                    frappe.log_error(f"row_{index}_creating", "Creating ETS record")
                    frappe.log_error(f"row_{index}_values", f"Date: {date_value}, Price: {price_value}, Volume: {volume_value}, High: {high_value}, Low: {low_value}, Type: {ets_price_type_value}, Year: {price_year_value}")
                    
                    self._create_ets_record(date_value, price_value, None, source_value, filename, 
                                         volume_value, high_value, low_value, ets_price_type_value, price_year_value)
                    imported_count += 1
                    
                    # Add this row to successful rows for logging
                    successful_rows.append({
                        'index': index,
                        'row_data': row.to_dict(),
                        'processed_values': {
                            'date': date_value,
                            'price': price_value,
                            'volume': volume_value,
                            'high': high_value,
                            'low': low_value,
                            'type': ets_price_type_value,
                            'year': price_year_value
                        }
                    })
                    
                    frappe.log_error(f"row_{index}_success", "Record created successfully")
                    
                except Exception as e:
                    frappe.log_error(f"row_{index}_error", str(e))
                    frappe.log_error(f"row_{index}_error_traceback", str(e))
                    continue
            
            return imported_count, successful_rows
            
        except Exception as e:
            raise Exception(f"Failed to process ETS data: {str(e)}")
    

    
    def _check_existing_record(self, date_value, price_value, source_value, volume_value=None, high_value=None, low_value=None, ets_price_type_value=None, price_year_value=None):
        """Check if ETS price record already exists with more comprehensive duplicate detection"""
        try:
            frappe.log_error("duplicate_check_start", f"Price: {price_value}, Date: {date_value}, Volume: {volume_value}, Type: {ets_price_type_value}")
            
            # Build filter conditions for duplicate detection
            # Use more fields to make duplicate detection more accurate
            filters = {}
            
            # Always check by price (this is the main identifier)
            filters["price"] = float(price_value)
            
            # Add date filter if date value exists and is valid
            if date_value and pd.notna(date_value):
                try:
                    if hasattr(date_value, 'strftime'):
                        date_str = date_value.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_value)
                    filters["price_date"] = date_str
                    frappe.log_error("duplicate_check_date", date_str)
                except Exception as e:
                    frappe.log_error("duplicate_check_date_error", str(e))
                    # If date conversion fails, skip date filter
                    pass
            
            # Add volume filter if available (helps distinguish between different market conditions)
            if volume_value and pd.notna(volume_value):
                filters["volume"] = float(volume_value)
                frappe.log_error("duplicate_check_volume", str(volume_value))
            
            # Add ETS price type filter if available (different types can have same price)
            if ets_price_type_value and pd.notna(ets_price_type_value):
                filters["ets_price_type"] = str(ets_price_type_value)
                frappe.log_error("duplicate_check_type", str(ets_price_type_value))
            
            # Add price year filter if available (different years can have same price)
            if price_year_value and pd.notna(price_year_value):
                filters["price_year"] = int(price_year_value)
                frappe.log_error("duplicate_check_year", str(price_year_value))
            
            frappe.log_error("duplicate_check_filters", str(filters))
            
            # Check if record exists with these filters
            existing = frappe.db.exists("ETS Carbon Price", filters)
            frappe.log_error("duplicate_check_result", existing or "No duplicate found")
            
            return existing
            
        except Exception as e:
            frappe.log_error(f"Failed to check existing record: {str(e)}")
            return None
    
    def _create_ets_record(self, date_value, price_value, currency_value, source_value, filename, 
                          volume_value=None, high_value=None, low_value=None, ets_price_type_value=None, price_year_value=None):
        """Create new ETS Carbon Price record"""
        try:
            frappe.log_error("create_record_start", f"Creating ETS record with price: {price_value}")
            
            # Create new record
            ets_doc_data = {
                "doctype": "ETS Carbon Price",
                "price": float(price_value),
                "import_source": f"Google Drive: {filename}"
            }
            
            frappe.log_error("create_record_basic", str(ets_doc_data))
            
            # Add date if available
            if date_value and pd.notna(date_value):
                try:
                    if hasattr(date_value, 'strftime'):
                        date_str = date_value.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_value)
                    ets_doc_data["price_date"] = date_str
                    frappe.log_error("create_record_date", date_str)
                except Exception as e:
                    frappe.log_error("create_record_date_error", str(e))
                    pass
            
            # Skip carbon_price_source - it will be set to default value
            
            # Add volume if available
            if volume_value and pd.notna(volume_value):
                ets_doc_data["volume"] = float(volume_value)
                frappe.log_error("create_record_volume", str(volume_value))
            
            # Add high if available
            if high_value and pd.notna(high_value):
                ets_doc_data["high"] = float(high_value)
                frappe.log_error("create_record_high", str(high_value))
            
            # Add low if available
            if low_value and pd.notna(low_value):
                ets_doc_data["low"] = float(low_value)
                frappe.log_error("create_record_low", str(low_value))
            
            # Add ETS price type if available
            if ets_price_type_value and pd.notna(ets_price_type_value):
                ets_doc_data["ets_price_type"] = str(ets_price_type_value)
                frappe.log_error("create_record_type", str(ets_price_type_value))
            
            # Add price year if available (required for Future types)
            if price_year_value and pd.notna(price_year_value):
                ets_doc_data["price_year"] = int(price_year_value)
                frappe.log_error("create_record_year", str(price_year_value))
            
            frappe.log_error("create_record_final_data", str(ets_doc_data))
            
            ets_doc = frappe.get_doc(ets_doc_data)
            frappe.log_error("create_record_doc_created", "Document object created")
            
            ets_doc.insert(ignore_permissions=True)
            frappe.log_error("create_record_inserted", "Record inserted successfully")
            
        except Exception as e:
            frappe.log_error("create_record_error", str(e))
            frappe.log_error("create_record_error_traceback", str(e))
            raise e
    
    def _update_ets_record(self, existing_id, price_value, currency_value, source_value, filename):
        """Update existing ETS Carbon Price record"""
        try:
            ets_doc = frappe.get_doc("ETS Carbon Price", existing_id)
            ets_doc.price = float(price_value)
            
            # Only update currency if it was mapped and has a value
            if currency_value:
                ets_doc.currency = str(currency_value)
            
            # Only update source if it was mapped and has a value
            if source_value:
                ets_doc.source = str(source_value)
            
            ets_doc.import_source = f"Google Drive: {filename}"
            
            ets_doc.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Failed to update ETS record: {str(e)}")
            raise e
    
    def _is_file_already_processed(self, file_id):
        """Check if file was already processed"""
        return file_id in self.processed_files
    
    def _mark_file_as_processed(self, file_id, filename):
        """Mark file as processed"""
        self.processed_files[file_id] = filename
    
    def _create_file_detail_record(self, file_info, status):
        """Create a file detail record in the child table"""
        try:
            # Check if we have a current import log
            if not self.current_import_log:
                frappe.log_error("no_import_log", "No import log available yet, creating temporary file detail")
                # Create a temporary file detail structure that will be used later
                file_detail = {
                    "doctype": "ETS Import File Details",
                    "file_name": file_info['name'],
                    "file_id": file_info['id'],
                    "mime_type": file_info.get('mimeType', ''),
                    "file_size": file_info.get('size', ''),
                    "last_modified": file_info.get('modifiedTime', ''),
                    "processing_status": status,
                    "records_imported": 0,
                    "processing_time": 0
                }
                return file_detail
            
            # Get the current import log
            import_log = frappe.get_doc("ETS Import Log", self.current_import_log)
            
            # Create file detail
            file_detail = {
                "doctype": "ETS Import File Details",
                "file_name": file_info['name'],
                "file_id": file_info['id'],
                "mime_type": file_info.get('mimeType', ''),
                "file_size": file_info.get('size', ''),
                "last_modified": file_info.get('modifiedTime', ''),
                "processing_status": status,
                "records_imported": 0,
                "processing_time": 0
            }
            
            import_log.append("ets_import_file_details", file_detail)
            import_log.save(ignore_permissions=True)
            
            return file_detail
            
        except Exception as e:
            frappe.log_error(f"Failed to create file detail record: {str(e)}")
            return None
    
    def _update_file_detail_status(self, file_detail, status, error_message=None):
        """Update the status of a file detail record"""
        try:
            if not file_detail:
                return
            
            # Check if we have a current import log
            if not self.current_import_log:
                frappe.log_error("no_import_log_update", "No import log available yet, cannot update file detail status")
                return
                
            # Find and update the file detail record
            import_log = frappe.get_doc("ETS Import Log", self.current_import_log)
            
            for detail in import_log.ets_import_file_details:
                if detail.file_id == file_detail['file_id']:
                    detail.processing_status = status
                    if error_message:
                        detail.error_message = error_message
                    detail.processing_time = frappe.utils.time_diff(
                        frappe.utils.now(), 
                        import_log.import_date
                    ).total_seconds()
                    break
            
            import_log.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Failed to update file detail status: {str(e)}")
    
    def _store_excel_data_rows(self, df, filename, successful_rows=None):
        """Store Excel data rows as individual child table records"""
        # If no successful_rows provided, store all rows (for backward compatibility)
        if successful_rows is None:
            successful_rows = [{'index': i, 'row_data': row.to_dict()} for i, row in df.iterrows()]
        try:
            frappe.log_error("store_method_start", f"Starting _store_excel_data_rows for {filename}")
            frappe.log_error("store_method_df_shape", f"DataFrame shape: {df.shape}")
            frappe.log_error("store_method_current_log", self.current_import_log)
            
            # Check if we have a current import log
            if not self.current_import_log:
                frappe.log_error("no_import_log_store", "No import log available yet, cannot store Excel data rows")
                return
            
            import_log = frappe.get_doc("ETS Import Log", self.current_import_log)
            
            # Clear existing child table records
            import_log.ets_import_file_details = []
            
            # Get mapped columns
            mapped_columns = self._get_column_mappings()
            frappe.log_error("store_method_mapped_columns", str(mapped_columns))
            
            # Find price column (required)
            price_column = None
            
            # First try to find by data_type if available
            if hasattr(self.settings, 'excel_column_mapping'):
                for mapping in self.settings.excel_column_mapping:
                    if hasattr(mapping, 'data_type') and mapping.data_type == 'Price':
                        price_column = mapping.column_name
                        break
            
            # If no price column found by data_type, try by column name
            if not price_column:
                for col_name in mapped_columns:
                    if col_name.lower() in ['price', 'cost', 'rate', 'value', 'amount', 'closing']:
                        price_column = col_name
                        break
            
            if not price_column:
                raise Exception("No price column found in mappings")
            
            # Create individual child table records for each successful row
            for row_info in successful_rows:
                index = row_info['index']
                row = pd.Series(row_info['row_data'])
                # Skip empty rows (only Price is required)
                if pd.isna(row[price_column]):
                    continue
                
                # Create child table record with dynamic data
                child_record = {
                    "doctype": "ETS Import File Details",
                    "row_index": index + 1,
                    "price": float(row[price_column]),
                    "processing_status": "Pending"
                }
                
                # Map each column to the correct child table field
                for col_name in mapped_columns:
                    if col_name != price_column:
                        # Find the actual Excel column name
                        actual_col = None
                        for excel_col in df.columns:
                            if excel_col.strip() == col_name.strip():
                                actual_col = excel_col
                                break
                        
                        if actual_col and pd.notna(row[actual_col]):
                            col_value = row[actual_col]
                            
                            # Map to specific child table fields based on column names
                            if 'date' in col_name.lower():
                                # Convert date format from DD.MM.YYYY to YYYY-MM-DD
                                try:
                                    if isinstance(col_value, str) and '.' in col_value:
                                        # Parse DD.MM.YYYY format
                                        day, month, year = col_value.split('.')
                                        formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                        child_record["price_date"] = formatted_date
                                    else:
                                        child_record["price_date"] = col_value
                                except:
                                    # If date conversion fails, skip the date field
                                    pass
                            elif 'year' in col_name.lower():
                                child_record["price_year"] = col_value
                            elif 'type' in col_name.lower():
                                child_record["ets_price_type"] = col_value
                            elif 'volume' in col_name.lower():
                                child_record["volume"] = col_value
                            elif 'high' in col_name.lower():
                                child_record["high"] = col_value
                            elif 'low' in col_name.lower():
                                child_record["low"] = col_value
                
                import_log.append("ets_import_file_details", child_record)
            
            # Save the import log with all child records
            frappe.log_error("store_method_before_save", f"About to save {len(import_log.ets_import_file_details)} child records")
            import_log.save(ignore_permissions=True)
            frappe.log_error("store_method_after_save", "Import log saved successfully")
            
            frappe.log_error("store_method_complete", f"Stored {len(import_log.ets_import_file_details)} Excel rows for file {filename}")
            
        except Exception as e:
            frappe.log_error("store_method_error", f"Failed to store Excel data rows: {str(e)}")
            frappe.log_error("store_method_error_traceback", str(e))
            raise e
    
    def _debug_column_mapping(self, df, mapped_columns):
        """Debug column mapping issues"""
        try:
            debug_info = {
                "mapped_columns": mapped_columns,
                "excel_columns": list(df.columns),
                "excel_columns_stripped": [col.strip() for col in df.columns],
                "mapped_columns_stripped": [col.strip() for col in mapped_columns]
            }
            
            frappe.log_error(f"Column mapping debug info: {debug_info}")
            return debug_info
            
        except Exception as e:
            frappe.log_error(f"Failed to debug column mapping: {str(e)}")
            return {"error": str(e)}
    

