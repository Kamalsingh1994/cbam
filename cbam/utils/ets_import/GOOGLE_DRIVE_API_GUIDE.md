# 🚀 Google Drive API Setup Guide for ETS Import

## 📋 **Prerequisites**
- Google Cloud Console account
- Python 3.7+ installed
- Basic understanding of APIs

---

## 🔑 **Step 1: Create Google Cloud Project**

### 1.1 Go to Google Cloud Console
- Visit: [https://console.cloud.google.com/](https://console.cloud.google.com/)
- Sign in with your Google account

### 1.2 Create New Project
- Click **"Select a project"** → **"New Project"**
- Enter project name: `ETS Import System` (or your preferred name)
- Click **"Create"**

### 1.3 Enable Google Drive API
- In the left sidebar, click **"APIs & Services"** → **"Library"**
- Search for **"Google Drive API"**
- Click on it and press **"Enable"**

---

## 🔐 **Step 2: Create Service Account**

### 2.1 Create Service Account
- Go to **"APIs & Services"** → **"Credentials"**
- Click **"Create Credentials"** → **"Service Account"**
- Fill in details:
  - **Service account name**: `ets-import-service`
  - **Service account ID**: `ets-import-service@your-project.iam.gserviceaccount.com`
  - **Description**: `Service account for ETS price imports`

### 2.2 Grant Permissions
- Click **"Create and Continue"**
- For **"Grant this service account access to project"**:
  - Select **"Editor"** role
- Click **"Continue"** → **"Done"**

### 2.3 Create and Download Key
- Click on your service account email
- Go to **"Keys"** tab
- Click **"Add Key"** → **"Create new key"**
- Choose **"JSON"** format
- Click **"Create"**
- **IMPORTANT**: The JSON file will download automatically - keep it secure!

---

## 📁 **Step 3: Set Up Google Drive Folders**

### 3.1 Create Main Folder Structure
```
📁 ETS Import System/
├── 📁 ETS Prices 2024/
├── 📁 ETS Prices 2025/
├── 📁 ETS Prices 2026/
└── 📁 Archive/
```

### 3.2 Get Folder IDs
1. **Open Google Drive** in your browser
2. **Navigate to the folder** you want to use
3. **Copy the folder ID** from the URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```
   - The `FOLDER_ID_HERE` part is what you need

### 3.3 Common Folder ID Examples
```python
# Example folder IDs (replace with your actual IDs)
FOLDER_IDS = {
    "main_ets": "1ABC123DEF456GHI789JKL",
    "2024_prices": "2DEF456GHI789JKL012MNO", 
    "2025_prices": "3GHI789JKL012MNO345PQR",
    "2026_prices": "4JKL012MNO345PQR678STU",
    "archive": "5MNO345PQR678STU901VWX"
}
```

---

## ⚙️ **Step 4: Configure Frappe Settings**

### 4.1 Update ETS Import Settings
Go to your **ETS Import Settings** doctype and update:

```json
{
    "google_drive_folder_id": "YOUR_FOLDER_ID_HERE",
    "google_drive_credentials": "YOUR_SERVICE_ACCOUNT_JSON_CONTENT"
}
```

### 4.2 Multiple Folder Configuration
If you want to import from different folders, you can:

**Option A: Single Setting with Multiple Folders**
```python
# In your settings, use a comma-separated list
"google_drive_folder_id": "folder1_id,folder2_id,folder3_id"
```

**Option B: Multiple ETS Import Settings**
- Create separate **ETS Import Settings** records
- Each with different folder IDs
- Different import schedules

---

## 🔧 **Step 5: Test Your Setup**

### 5.1 Test Connection
1. Go to **ETS Import Settings**
2. Click **"Test Google Drive Connection"**
3. Check the response:
   ```json
   {
     "status": "Success",
     "folders": ["ETS Prices 2025", "Archive"],
     "files_count": 3
   }
   ```

### 5.2 Test Import
1. Click **"Import ETS Prices"**
2. Check the progress bar
3. Verify records are created

---

## 📊 **Step 6: Advanced Configuration**

### 6.1 Multiple Service Accounts
For different environments or security levels:

```python
# Development
DEV_CREDENTIALS = {
    "type": "service_account",
    "project_id": "dev-ets-import",
    "private_key_id": "...",
    "private_key": "...",
    "client_email": "dev@dev-ets-import.iam.gserviceaccount.com"
}

# Production  
PROD_CREDENTIALS = {
    "type": "service_account", 
    "project_id": "prod-ets-import",
    "private_key_id": "...",
    "private_key": "...",
    "client_email": "prod@prod-ets-import.iam.gserviceaccount.com"
}
```

### 6.2 Folder Permissions
Ensure your service account has access:

1. **Right-click** on your folder in Google Drive
2. **Share** → **Add people and groups**
3. **Add** your service account email
4. **Set permission** to **"Editor"**

---

## 🚨 **Troubleshooting**

### Common Issues & Solutions

#### Issue 1: "Access Denied"
```bash
# Solution: Check service account permissions
- Verify service account has Editor access to folder
- Check if folder is shared with service account email
- Ensure Google Drive API is enabled
```

#### Issue 2: "Folder Not Found"
```bash
# Solution: Verify folder ID
- Copy folder ID from URL again
- Check if folder was moved or deleted
- Ensure folder is accessible to service account
```

#### Issue 3: "Authentication Failed"
```bash
# Solution: Check credentials
- Verify JSON key file is correct
- Check if service account is active
- Ensure project has billing enabled
```

#### Issue 4: "API Quota Exceeded"
```bash
# Solution: Monitor usage
- Check Google Cloud Console quotas
- Implement rate limiting in your code
- Consider upgrading to paid tier
```

---

## 📈 **Best Practices**

### 1. **Security**
- ✅ Never commit credentials to version control
- ✅ Use environment variables for sensitive data
- ✅ Rotate service account keys regularly
- ✅ Limit service account permissions

### 2. **Organization**
- ✅ Use descriptive folder names
- ✅ Implement consistent naming conventions
- ✅ Archive old data regularly
- ✅ Monitor folder sizes

### 3. **Performance**
- ✅ Use appropriate date filtering
- ✅ Implement incremental imports
- ✅ Monitor API usage
- ✅ Cache frequently accessed data

---

## 🔄 **Updating Folder IDs**

### Method 1: Through Frappe UI
1. Go to **ETS Import Settings**
2. Update **"Google Drive Folder ID"** field
3. Save the record
4. Test the connection

### Method 2: Through Code
```python
# Update folder ID programmatically
settings = frappe.get_doc("ETS Import Settings", "your_settings_name")
settings.google_drive_folder_id = "new_folder_id"
settings.save()

# Test the new configuration
processor = ETSImportProcessor(settings)
result = processor.test_google_drive_connection()
```

### Method 3: Multiple Configurations
```python
# Create multiple import configurations
configs = [
    {"name": "Daily ETS", "folder_id": "daily_folder_id", "frequency": "Daily"},
    {"name": "Weekly ETS", "folder_id": "weekly_folder_id", "frequency": "Weekly"},
    {"name": "Monthly ETS", "folder_id": "monthly_folder_id", "frequency": "Monthly"}
]

for config in configs:
    settings = frappe.get_doc("ETS Import Settings", config["name"])
    settings.google_drive_folder_id = config["folder_id"]
    settings.import_frequency = config["frequency"]
    settings.save()
```

---

## 📞 **Need Help?**

### 1. **Check Logs**
- Look in **Error Log** doctype
- Check Frappe server logs
- Monitor Google Cloud Console

### 2. **Common Resources**
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Frappe Documentation](https://frappeframework.com/docs)

### 3. **Support Channels**
- Google Cloud Support
- Frappe Community Forum
- Your development team

---

## 🎯 **Quick Setup Checklist**

- [ ] Google Cloud Project created
- [ ] Google Drive API enabled
- [ ] Service Account created
- [ ] JSON key downloaded
- [ ] Folder created in Google Drive
- [ ] Folder ID copied
- [ ] Service account added to folder
- [ ] Credentials added to Frappe settings
- [ ] Connection tested
- [ ] Import tested

---

**🎉 You're all set! Your ETS Import system should now work with different Google Drive folders.**

*Last updated: December 2024*
