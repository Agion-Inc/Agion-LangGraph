# Agent-Chat Testing Guide - File References & @-Tags

## 🚀 Quick Start

### **1. Clean Setup**
```bash
# Kill any running React servers
pkill -f "react-scripts"

# Navigate to Agent-Chat frontend
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat/frontend

# Start the dev server
npm start
```

### **2. Access the Application**
```
URL: http://localhost:3000
- Should redirect to /chat automatically
- Sidebar should show "Chat" and "Files" navigation
```

## 📋 Testing Checklist

### **Phase 1: Routing & Navigation** ✓

1. **Visit http://localhost:3000**
   - Should redirect to `/chat`
   - Sidebar visible on the left
   - Chat interface on the right

2. **Click "Files" in Sidebar**
   - Should navigate to `/files`
   - Full-screen file management interface
   - Upload zone visible

3. **Navigate Back to Chat**
   - Click "Chat" in sidebar
   - Should return to `/chat`
   - Chat interface restored

**Expected Sidebar:**
```
┌─────────────────────────┐
│ [+ New Chat]            │
├─────────────────────────┤
│ 💬 Chat                 │
│ 📁 Files             (2)│  ← Badge shows file count
├─────────────────────────┤
│ 📄 Data Files           │
│ [Upload Zone]           │
│ ├─ file1.xlsx ✓        │
│ └─ file2.csv ✓         │
└─────────────────────────┘
```

### **Phase 2: File Upload** ✓

1. **Go to /files page**
   ```
   http://localhost:3000/files
   ```

2. **Upload Test File**
   - Drag & drop an Excel/CSV file
   - OR click upload zone
   - Watch upload progress
   - File should show "completed" status

3. **Verify File Listed**
   - File appears in the list
   - Shows size, category, status
   - Actions buttons (view, download, delete) visible

**Expected Files Page:**
```
┌─────────────────────────────────────────────┐
│  File Manager          [Show Upload]        │
├─────────────────────────────────────────────┤
│  [Drag & Drop Zone]                         │
├─────────────────────────────────────────────┤
│  🔍 Search  │ 📁 Category ▼ │ ⚡ Status ▼  │
├─────────────────────────────────────────────┤
│  📊 sales_data.xlsx    500KB  ✓ Processed   │
│  [👁 View] [⬇ Download] [🗑 Delete]         │
└─────────────────────────────────────────────┘
```

### **Phase 3: @-Tag Autocomplete** 🎯

1. **Navigate to /chat**

2. **Type @ in Chat Input**
   ```
   Input: "@"
   ```
   - Autocomplete popup should appear
   - Shows all completed files
   - Displays file name and size

3. **Filter Files**
   ```
   Input: "@sal"
   ```
   - Popup filters to show only matching files
   - e.g., "sales_data.xlsx", "salary_report.xlsx"

4. **Navigate with Keyboard**
   - Press ↓ (down arrow) - highlights next file
   - Press ↑ (up arrow) - highlights previous file
   - Press Tab or Enter - selects highlighted file
   - Press Escape - closes popup

5. **Select File**
   - File reference inserted: "@sales_data.xlsx"
   - File badge appears above input
   - Popup closes

**Expected Autocomplete:**
```
┌──────────────────────────────────────┐
│ Reference a file:                    │
├──────────────────────────────────────┤
│ 📊 sales_data.xlsx      @sales_data  │
│    500 KB                            │
├──────────────────────────────────────┤
│ 📝 report.csv           @report      │
│    250 KB                            │
└──────────────────────────────────────┘
```

**Expected File Badge:**
```
┌───────────────────────────────────┐
│ 📄 Referenced files (1):          │
│ ┌─────────────────────────────┐   │
│ │ 📊 sales_data.xlsx       × │   │
│ └─────────────────────────────┘   │
└───────────────────────────────────┘
```

### **Phase 4: Send Message with File Reference**

1. **Complete Message**
   ```
   Input: "Analyze @sales_data.xlsx and show top trends"
   ```

2. **Send Message**
   - Click send button or press Enter
   - Message appears in chat
   - File reference visible in message
   - Backend receives file IDs

3. **Verify File Context**
   - Check browser console (F12)
   - Should see file IDs in request
   - Network tab shows files parameter

## 🐛 Troubleshooting

### **Issue: No Changes Visible**

**Solution:**
```bash
# Clear browser cache
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Or open DevTools (F12) → Network tab → Disable cache

# Restart dev server
pkill -f "react-scripts"
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat/frontend
npm start
```

### **Issue: @-Tag Popup Not Showing**

**Check:**
1. **Files uploaded and completed?**
   ```javascript
   // In browser console
   window.localStorage.getItem('file-storage')
   ```

2. **InputBox component loaded?**
   ```javascript
   // Check for InputBox in React DevTools
   // Elements tab → Search for "InputBox"
   ```

3. **Console errors?**
   ```
   F12 → Console tab
   Look for errors related to:
   - useFileStore
   - InputBox
   - autocomplete
   ```

**Manual Test:**
```javascript
// In browser console
const { useFileStore } = await import('./hooks/useFiles')
const store = useFileStore.getState()
console.log('Files:', store.files)
console.log('Completed:', store.files.filter(f => f.status === 'completed'))
```

### **Issue: Routing Not Working**

**Check:**
1. **React Router installed?**
   ```bash
   cat package.json | grep react-router-dom
   # Should show: "react-router-dom": "^7.9.3"
   ```

2. **BrowserRouter present?**
   ```javascript
   // In App.tsx, should see:
   <BrowserRouter>
     <Routes>
   ```

3. **Console errors?**
   ```
   F12 → Console
   Look for: "No routes matched location"
   ```

### **Issue: Files Page Not Loading**

**Check:**
```bash
# Verify FileManagerPage exists
ls src/pages/FileManagerPage.tsx

# Check imports in App.tsx
grep "FileManagerPage" src/App.tsx
```

## 🔍 Browser DevTools Inspection

### **1. React DevTools**
```
Install: Chrome/Firefox Extension "React Developer Tools"

Components Tab:
- Search for "InputBox"
- Check state: showAutocomplete, mentionedFiles
- Search for "Sidebar"  
- Check: files array, location
```

### **2. Network Tab**
```
F12 → Network Tab

When sending message:
- Look for POST /api/v1/chat/message
- Check Request Payload
- Should include: { message: "...", files: ["uuid"] }
```

### **3. Console Logs**
```javascript
// Add debug logging
console.log('Files in store:', useFileStore.getState().files)
console.log('Current location:', window.location.pathname)
console.log('Mentioned files:', mentionedFiles)
```

## 📊 Expected Behavior Summary

| Action | Expected Result |
|--------|----------------|
| Visit localhost:3000 | Redirects to /chat |
| Click "Files" in sidebar | Navigate to /files |
| Upload file on /files | File shows "completed" |
| Return to /chat | Chat interface visible |
| Type @ in input | Autocomplete popup appears |
| Type @sal | Filters to matching files |
| Press ↓ key | Highlights next file |
| Press Enter | Inserts @filename |
| File badge appears | Shows referenced file |
| Click X on badge | Removes file reference |
| Send message | Backend receives file IDs |

## 🎯 Success Criteria

✅ **Navigation Works:**
- Can switch between /chat and /files
- Sidebar always visible on /chat
- /files shows full-screen interface

✅ **File Upload Works:**
- Files can be uploaded
- Status changes to "completed"
- Files appear in sidebar preview

✅ **@-Tag Works:**
- Typing @ shows popup
- Popup filters as typing
- Keyboard navigation works
- File selection inserts reference
- File badges display correctly

✅ **Message Sending Works:**
- Messages with @-tags send successfully
- File IDs included in request
- Backend receives file context

## 📞 Getting Help

**If issues persist:**

1. **Capture Console Errors**
   ```
   F12 → Console → Copy all errors
   ```

2. **Check File Structure**
   ```bash
   ls -R src/ | grep -E "(App|InputBox|Sidebar|FileManager)"
   ```

3. **Verify Dependencies**
   ```bash
   npm list react-router-dom
   npm list zustand
   npm list framer-motion
   ```

4. **Share Details**
   - Browser (Chrome/Firefox/Safari)
   - Console errors
   - Network tab requests
   - What you see vs. what you expect

## 🎉 Next Steps After Testing

Once everything works:
1. Test with real files (Excel, CSV)
2. Try multiple file references
3. Test filtering and search
4. Verify download functionality
5. Test file deletion
6. Check storage stats

---

**Remember:** 
- Hard refresh (Cmd+Shift+R) after code changes
- Check browser console for errors
- Use React DevTools for component inspection
- Files must be "completed" status to appear in @-tag
