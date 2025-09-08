# Google Drive Setup Guide

This guide will help you set up Google Drive upload functionality for the Multitrack Audio Recorder.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project name for later use

## Step 2: Enable Google Drive API

1. In the Google Cloud Console, navigate to "APIs & Services" > "Library"
2. Search for "Google Drive API"
3. Click on "Google Drive API" and then click "Enable"

## Step 3: Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in the required fields (App name, User support email, Developer contact)
   - Add your email to test users
4. For Application type, choose "Desktop application"
5. Give it a name (e.g., "Multitrack Recorder")
6. Click "Create"

## Step 4: Download Credentials

1. After creating the OAuth client, click the download button (⬇️)
2. Save the downloaded file as `credentials.json` in the same directory as the application
3. **Important**: Keep this file secure and never share it publicly

## Step 5: Get Your Google Drive Folder ID

1. Open [Google Drive](https://drive.google.com) in your browser
2. Navigate to the folder where you want to store your recordings
3. Copy the folder ID from the URL:
   - The URL will look like: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Copy the `FOLDER_ID_HERE` part (it's a long string of letters, numbers, and underscores)
   - **Important**: Make sure you're in the actual folder, not just viewing it in a list

### Alternative Method to Get Folder ID:
1. Right-click on the folder in Google Drive
2. Select "Get link" or "Share"
3. Copy the link and extract the folder ID from the URL

### Common Issues:
- **Wrong ID**: Make sure you're copying the folder ID, not a file ID
- **Access Denied**: Ensure you have write access to the folder
- **Folder Not Found**: The folder must exist and be accessible to your Google account

## Step 6: Configure the Application

1. Run the Multitrack Audio Recorder
2. In the "Google Drive Upload" section:
   - Check "Enable Google Drive Upload"
   - Click "Authenticate Google Drive"
   - A browser window will open asking you to sign in to Google
   - Grant the necessary permissions (including access to shared drives if applicable)
   - You should see "Authenticated" in green
3. Paste your folder ID in the "Folder ID" field
4. Click "Validate" to verify the folder ID is correct
   - You should see "Valid folder: [Folder Name]" in green
   - If you see an error, double-check your folder ID

### Note about Shared Drives (Google Team Drives)
- The application supports both personal Google Drive folders and Google Shared Drives
- If you're using a Shared Drive, make sure you have the necessary permissions
- You may need to delete `token.pickle` and re-authenticate if you encounter permission issues

## Step 7: Test the Setup

1. Select your audio devices and start recording
2. Stop the recording
3. Check your Google Drive folder - the .wav files should appear there automatically

## Troubleshooting

### "credentials.json not found" Error
- Make sure you downloaded the OAuth2 credentials file
- Rename it to exactly `credentials.json`
- Place it in the same directory as the application

### "Authentication failed" Error
- Check that the Google Drive API is enabled in your project
- Make sure you're using the correct credentials file
- Try deleting `token.pickle` and re-authenticating

### "No Google Drive folder ID set" Error
- Make sure you've entered the correct folder ID
- The folder ID is the long string in the Google Drive URL
- Make sure you have write access to the folder
- Use the "Validate" button to check if your folder ID is correct

### "File not found" Error (404)
- The folder ID is incorrect or the folder doesn't exist
- Use the "Validate" button to verify your folder ID
- Make sure you're copying the folder ID, not a file ID
- Ensure the folder exists and you have access to it
- If using a Shared Drive, make sure you have the necessary permissions

### "Didn't opt-in to Shared Drives" Error
- This occurs when trying to access Google Shared Drives (Team Drives)
- Delete the `token.pickle` file and re-authenticate
- The application now supports Shared Drives with the updated scopes

### Files not uploading
- Check that you're authenticated (should show "Authenticated" in green)
- Verify the folder ID is correct
- Check the console output for error messages
- Make sure you have internet connectivity

## Security Notes

- Never share your `credentials.json` file
- The `token.pickle` file contains your access tokens - keep it secure
- Only grant access to trusted applications
- You can revoke access at any time in your Google Account settings

## Support

If you encounter issues:
1. Check the console output for error messages
2. Verify all steps in this guide were followed correctly
3. Try re-authenticating by deleting `token.pickle` and running the authentication again
