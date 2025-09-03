# Copyright (c) 2025, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
import io
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from cryptography.fernet import Fernet
import base64


class GoogleDriveService:
    def __init__(self, settings):
        """Initialize Google Drive service with settings"""
        self.settings = settings
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate using service account credentials"""
        try:
            # Get the raw private key
            raw_key = self.settings.google_private_key
            if not raw_key:
                raise Exception("Private key is empty")
            
            # Decrypt the private key
            private_key = self._decrypt_private_key(raw_key)
            if not private_key:
                raise Exception("Failed to decrypt private key")
            
            # Format the private key
            formatted_key = self._format_private_key(private_key)
            if not formatted_key:
                raise Exception("Failed to format private key")
            
            # Validate the formatted key
            if not formatted_key.startswith("-----BEGIN"):
                raise Exception("Private key is not in valid PEM format")
            
            # Create service account info
            service_account_info = {
                "type": "service_account",
                "private_key": formatted_key,
                "client_email": self.settings.google_service_account_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            # Validate required fields
            if not self.settings.google_service_account_email:
                raise Exception("Service account email is empty")
            
            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(service_account_info)
            
            # Build Google Drive service
            service = build('drive', 'v3', credentials=credentials)
            
            # Test the service by making a simple call
            try:
                # Try to get drive info to verify the service works
                about = service.about().get(fields="user").execute()
                frappe.logger().info(f"Google Drive service authenticated successfully for user: {about.get('user', {}).get('emailAddress', 'Unknown')}")
            except Exception as service_test_error:
                frappe.logger().error(f"Service test failed: {str(service_test_error)}")
                raise Exception(f"Google Drive service test failed: {str(service_test_error)}")
            return service
            
        except Exception as e:
            frappe.log_error(f"Google Drive authentication failed: {str(e)}")
            raise Exception(f"Google Drive authentication failed: {str(e)}")
    
    def _decrypt_private_key(self, encrypted_key):
        """Decrypt the private key using Frappe's encryption"""
        try:
            if not encrypted_key:
                raise Exception("Private key is empty")
            
            # For Long Text fields, we need to handle encryption manually
            # Check if the key is encrypted (starts with gAAAAA)
            if encrypted_key.startswith("gAAAAA"):
                # This is an encrypted key, decrypt it
                try:
                    from cryptography.fernet import Fernet
                    import base64
                    
                    # Get Frappe's encryption key
                    encryption_key = frappe.local.conf.encryption_key
                    if not encryption_key:
                        raise Exception("Frappe encryption key not configured")
                    
                    # Ensure key is 32 bytes for Fernet
                    key = base64.urlsafe_b64encode(encryption_key.encode()[:32].ljust(32, b'0'))
                    f = Fernet(key)
                    
                    # Decrypt the key
                    decrypted_key = f.decrypt(encrypted_key.encode()).decode()
                    return decrypted_key
                    
                except Exception as decrypt_error:
                    frappe.log_error(f"Failed to decrypt private key: {str(decrypt_error)}")
                    # If decryption fails, return the original (maybe it's not encrypted)
                    return encrypted_key
            else:
                # Key is not encrypted, return as-is
                return encrypted_key
            
        except Exception as e:
            frappe.log_error(f"Failed to decrypt private key: {str(e)}")
            raise Exception(f"Failed to decrypt private key: {str(e)}")
    
    def _format_private_key(self, private_key):
        """Format the private key for Google service account authentication"""
        try:
            # Remove any extra whitespace and newlines
            private_key = private_key.strip()
            
            # Check if it's already in the correct format
            if private_key.startswith("-----BEGIN RSA PRIVATE KEY-----"):
                return private_key
            elif private_key.startswith("-----BEGIN PRIVATE KEY-----"):
                return private_key
            
            # If the key doesn't start with any of the expected headers,
            # it might be the raw key content that needs to be wrapped
            # Remove any existing headers if they exist
            if "-----BEGIN" in private_key:
                # Extract the key content between headers
                start_idx = private_key.find("-----BEGIN")
                end_idx = private_key.find("-----END")
                if start_idx != -1 and end_idx != -1:
                    # Find the actual key content
                    key_start = private_key.find("\n", start_idx) + 1
                    key_end = private_key.rfind("\n", 0, end_idx)
                    if key_start > 0 and key_end > key_start:
                        private_key = private_key[key_start:key_end].strip()
            
            # Clean the key content (remove any remaining headers, footers, or extra text)
            lines = private_key.split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("-----") and not line.startswith("#"):
                    clean_lines.append(line)
            
            if not clean_lines:
                raise Exception("No valid key content found after cleaning")
            
            # Join the clean lines
            clean_key = ''.join(clean_lines)
            
            # Format as RSA PRIVATE KEY
            formatted_lines = []
            formatted_lines.append("-----BEGIN RSA PRIVATE KEY-----")
            
            # Split the key into 64-character chunks as per PEM format
            for i in range(0, len(clean_key), 64):
                formatted_lines.append(clean_key[i:i+64])
            
            formatted_lines.append("-----END RSA PRIVATE KEY-----")
            formatted_key = "\n".join(formatted_lines)
            
            return formatted_key
            
        except Exception as e:
            frappe.log_error(f"Failed to format private key: {str(e)}")
            # Don't return the original key if formatting fails - it won't work
            raise Exception(f"Failed to format private key: {str(e)}")
    
    def list_files_in_folder(self, folder_id, file_pattern=None):
        """List files in Google Drive folder matching the pattern"""
        try:
            # Build query for files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            
            if file_pattern:
                # Convert file pattern to Google Drive query
                # Handle wildcards and common patterns
                pattern = self._convert_pattern_to_query(file_pattern)
                query += f" and name contains '{pattern}'"
            
            # Execute query
            results = self.service.files().list(
                q=query,
                orderBy="modifiedTime desc",
                fields="files(id,name,modifiedTime,size,md5Checksum)"
            ).execute()
            
            files = results.get('files', [])
            
            # Filter by file pattern more precisely
            if file_pattern:
                files = self._filter_files_by_pattern(files, file_pattern)
            
            return files
            
        except Exception as e:
            frappe.log_error(f"Failed to list files in Google Drive folder: {str(e)}")
            raise Exception(f"Failed to list files in Google Drive folder: {str(e)}")
    
    def _convert_pattern_to_query(self, pattern):
        """Convert file pattern to Google Drive query"""
        # Remove wildcards for basic search
        basic_pattern = pattern.replace("*", "").replace("?", "")
        return basic_pattern
    
    def _filter_files_by_pattern(self, files, pattern):
        """Filter files by pattern using regex"""
        try:
            # Convert pattern to regex
            regex_pattern = pattern.replace("*", ".*").replace("?", ".")
            regex = re.compile(regex_pattern, re.IGNORECASE)
            
            filtered_files = []
            for file in files:
                if regex.match(file['name']):
                    filtered_files.append(file)
            
            return filtered_files
            
        except Exception as e:
            frappe.log_error(f"Failed to filter files by pattern: {str(e)}")
            return files  # Return all files if filtering fails
    
    def download_file(self, file_id, filename):
        """Download file from Google Drive"""
        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            
            # Check if it's a Google Docs/Sheets file
            mime_type = file_metadata.get('mimeType', '')
            
            if mime_type in ['application/vnd.google-apps.spreadsheet', 'application/vnd.google-apps.document']:
                # Export Google Sheets to Excel format
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
            else:
                # Download regular file content
                request = self.service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
            
            # Download file content
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            return file_content
            
        except Exception as e:
            error_msg = f"Download failed for {filename}: {str(e)}"
            frappe.log_error(error_msg)
            raise Exception(error_msg)
    
    def get_file_info(self, file_id):
        """Get detailed information about a file"""
        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields="id,name,modifiedTime,size,md5Checksum,parents"
            ).execute()
            
            return file_info
            
        except Exception as e:
            frappe.log_error(f"Failed to get file info for {file_id}: {str(e)}")
            raise Exception(f"Failed to get file info: {str(e)}")
    
    def create_folder(self, folder_name, parent_folder_id=None):
        """Create a new folder in Google Drive"""
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id,name,parents'
            ).execute()
            
            return folder
            
        except Exception as e:
            frappe.log_error(f"Failed to create folder {folder_name}: {str(e)}")
            raise Exception(f"Failed to create folder: {str(e)}")
    
    def delete_file(self, file_id):
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
            
        except Exception as e:
            frappe.log_error(f"Failed to delete file {file_id}: {str(e)}")
            raise Exception(f"Failed to delete file: {str(e)}")
    
    def move_file(self, file_id, new_parent_folder_id):
        """Move a file to a different folder"""
        try:
            # Get the file's current parents
            file = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move the file to the new parent
            file = self.service.files().update(
                fileId=file_id,
                addParents=new_parent_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return file
            
        except Exception as e:
            frappe.log_error(f"Failed to move file {file_id}: {str(e)}")
            raise Exception(f"Failed to move file: {str(e)}")
    
    def search_files(self, query, max_results=100):
        """Search for files in Google Drive"""
        try:
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id,name,modifiedTime,size,md5Checksum,parents,mimeType)"
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            frappe.log_error(f"Failed to search files with query '{query}': {str(e)}")
            raise Exception(f"Failed to search files: {str(e)}")
    
    def get_drive_info(self):
        """Get information about the Google Drive account"""
        try:
            about = self.service.about().get(fields="user,storageQuota").execute()
            return about
            
        except Exception as e:
            frappe.log_error(f"Failed to get drive info: {str(e)}")
            raise Exception(f"Failed to get drive info: {str(e)}")
    
    def test_connection(self):
        """Test the connection to Google Drive"""
        try:
            # Try to get drive info as a connection test
            drive_info = self.get_drive_info()
            return {
                "status": "Success",
                "message": "Connection successful",
                "user_email": drive_info.get("user", {}).get("emailAddress", "Unknown"),
                "storage_quota": drive_info.get("storageQuota", {})
            }
            
        except Exception as e:
            return {
                "status": "Error",
                "message": f"Connection failed: {str(e)}"
            }
