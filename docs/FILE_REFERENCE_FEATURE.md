# File Reference Feature (@-tags) - Implementation Guide

## 🎯 Overview

Implemented a comprehensive file reference system that allows users to reference uploaded files in chat using **@-tags** with intelligent autocomplete.

## ✨ Features Implemented

### 1. **Routing System**
- ✅ React Router integration
- ✅ `/chat` - Main chat interface with sidebar
- ✅ `/files` - Dedicated file management page
- ✅ Navigation between pages

### 2. **File Management Page**
- ✅ Full-screen file management interface
- ✅ Drag-and-drop file upload
- ✅ Advanced search and filtering
- ✅ Category filters (excel, csv, json, etc.)
- ✅ Status filters (uploaded, processed, error)
- ✅ File preview and data viewing
- ✅ Download and delete operations
- ✅ Storage statistics dashboard
- ✅ Pagination support

### 3. **@-Tag Autocomplete in Chat**
- ✅ Type `@` to trigger file autocomplete
- ✅ Real-time filtering as you type
- ✅ Keyboard navigation (↑/↓ arrows)
- ✅ Tab or Enter to select file
- ✅ Escape to close autocomplete
- ✅ Visual file preview in dropdown
- ✅ File size display

### 4. **File References in Messages**
- ✅ Track mentioned files in each message
- ✅ Visual file reference badges
- ✅ Quick remove file mentions
- ✅ File context sent to backend
- ✅ File reference component for displaying in messages

### 5. **Enhanced Navigation**
- ✅ Sidebar with navigation links
- ✅ File count badge on Files link
- ✅ Visual indicators for active page
- ✅ Quick file preview in sidebar
- ✅ "Manage files" link from sidebar

## 🚀 How to Use

### **For Users:**

#### **1. Upload Files**
```
Navigate to /files page
OR
Use sidebar file upload zone
```

#### **2. Reference Files in Chat**
```
1. Type @ in the chat input
2. Start typing filename
3. Use ↑/↓ to navigate suggestions
4. Press Tab or Enter to select
5. File reference appears as @filename
6. Send message with file context
```

#### **3. Manage Files**
```
/files page:
- View all uploaded files
- Search by filename
- Filter by category/status
- Download files
- Delete files
- View storage stats
```

### **For Developers:**

#### **File Structure:**
```
frontend/src/
├── App.tsx                          # Router configuration
├── pages/
│   └── FileManagerPage.tsx          # Full file management UI
├── components/
│   ├── shared/
│   │   └── Sidebar.tsx              # Navigation with file preview
│   ├── chat/
│   │   ├── InputBox.tsx             # @-tag autocomplete
│   │   └── ChatContainer.tsx        # Chat logic
│   └── files/
│       └── FileReference.tsx        # File reference display
```

#### **Key Components:**

**1. InputBox with @-tags:**
```typescript
// Track mentioned files
const [mentionedFiles, setMentionedFiles] = useState<FileMention[]>([])

// Detect @ symbol
useEffect(() => {
  const atMatch = textBeforeCursor.match(/@(\w*)$/)
  if (atMatch) {
    setShowAutocomplete(true)
  }
}, [message])

// Send with file context
onSendMessage(message, fileIds)
```

**2. File Reference Component:**
```typescript
<FileReference 
  fileId={fileId}
  showActions={true}
  className="my-2"
/>
```

**3. Routing:**
```typescript
<Routes>
  <Route path="/chat" element={<ChatContainer />} />
  <Route path="/files" element={<FileManagerPage />} />
  <Route path="/" element={<Navigate to="/chat" />} />
</Routes>
```

## 📊 User Experience Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Upload Files                                            │
│  ┌──────────────┐                                          │
│  │ /files page  │ ─→ Drag & drop files                     │
│  │ OR sidebar   │ ─→ Files uploaded & processed            │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Reference in Chat                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ User types:  "Analyze @sal"                          │  │
│  │                                                       │  │
│  │ Autocomplete shows:                                  │  │
│  │  ┌──────────────────────────────────────────┐       │  │
│  │  │ 📊 sales_data.xlsx      (500 KB)         │       │  │
│  │  │ 📊 salary_report.xlsx   (250 KB)         │       │  │
│  │  └──────────────────────────────────────────┘       │  │
│  │                                                       │  │
│  │ User selects → "Analyze @sales_data.xlsx"            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Message Sent with Context                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Message: "Analyze @sales_data.xlsx"                  │  │
│  │ File IDs: ["uuid-123"]                               │  │
│  │                                                       │  │
│  │ Backend receives:                                    │  │
│  │ {                                                    │  │
│  │   message: "Analyze...",                            │  │
│  │   files: ["uuid-123"]                                │  │
│  │ }                                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. AI Processes with File Context                          │
│  - Loads file data from storage                             │
│  - Analyzes content                                         │
│  - Returns insights                                         │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 UI Components

### **1. Autocomplete Dropdown**
```
┌──────────────────────────────────────────┐
│ Reference a file:                        │
├──────────────────────────────────────────┤
│ 📊 sales_data.xlsx      @sales_data.xlsx │
│    500 KB                                │
├──────────────────────────────────────────┤
│ 📝 report.csv           @report.csv      │
│    250 KB                                │
└──────────────────────────────────────────┘
```

### **2. File Reference Badge**
```
┌───────────────────────────────┐
│ 📊 sales_data.xlsx            │
│    500 KB • completed      ⬇  │
└───────────────────────────────┘
```

### **3. Mentioned Files Preview**
```
┌───────────────────────────────────────┐
│ 📄 Referenced files (2):              │
│ ┌─────────────────┐ ┌──────────────┐ │
│ │ 📊 data.xlsx  × │ │ 📝 report  × │ │
│ └─────────────────┘ └──────────────┘ │
└───────────────────────────────────────┘
```

## 🔧 Backend Integration

### **API Updates Needed:**

**1. Chat Endpoint - Accept File References:**
```python
@router.post("/chat/message")
async def send_message(
    message: str,
    files: Optional[List[str]] = None  # File IDs
):
    # Load file data
    file_data = []
    if files:
        for file_id in files:
            file_info = await get_file(file_id)
            file_data.append(file_info)
    
    # Process with file context
    response = await agent.process(message, context=file_data)
    return response
```

**2. File Context in Agent:**
```python
class AgentOrchestrator:
    async def process(self, message: str, context: List[FileInfo]):
        # Include file data in prompt
        prompt = f"""
        User Message: {message}
        
        Available Files:
        {format_file_context(context)}
        
        Process the user's request using the file data.
        """
        
        return await self.invoke(prompt)
```

## 📋 Testing Checklist

### **Frontend:**
- [x] Router navigation works (/chat, /files)
- [x] @ trigger shows autocomplete
- [x] Autocomplete filters as typing
- [x] Keyboard navigation works
- [x] File selection inserts reference
- [x] Multiple files can be referenced
- [x] File badges display correctly
- [x] Remove file mentions works
- [x] File references sent to backend

### **Backend:**
- [ ] Chat endpoint accepts file parameter
- [ ] File data loaded from storage
- [ ] File context passed to agents
- [ ] Agents process file-aware requests
- [ ] Response includes file insights

### **Integration:**
- [ ] Upload → Reference → Chat flow works
- [ ] File data accessible in agent responses
- [ ] Error handling for missing files
- [ ] Performance with large files

## 🎯 Next Steps

### **Immediate:**
1. Update backend chat API to accept file IDs
2. Implement file context loading in orchestrator
3. Test end-to-end flow
4. Add file reference display in message bubbles

### **Enhancement:**
1. **File Preview** - Show file data preview in chat
2. **Smart Suggestions** - AI suggests relevant files
3. **File Versioning** - Track file changes over time
4. **Collaborative Annotations** - Users can annotate files
5. **File Collections** - Group related files

### **Advanced:**
1. **Real-time Collaboration** - Multiple users referencing same files
2. **File Analysis Cache** - Cache processed file insights
3. **Visual Data Explorer** - Interactive data visualization
4. **Export Chat with Files** - Export conversation with file context

## 💡 Tips & Best Practices

### **For Users:**
1. **Use descriptive filenames** - Easier to find with @-tags
2. **Reference specific sheets** - Use @filename[Sheet1] (future feature)
3. **Combine multiple files** - Reference multiple files in one message
4. **Check file status** - Only "completed" files can be referenced

### **For Developers:**
1. **Validate file access** - Ensure user has permission
2. **Handle missing files** - Graceful error messages
3. **Optimize file loading** - Cache frequently accessed files
4. **Monitor performance** - Large files may slow processing
5. **Security** - Validate file IDs to prevent unauthorized access

## 🐛 Troubleshooting

### **@-tag not showing:**
- Check if files are uploaded and processed
- Verify file status is "completed"
- Ensure cursor is after @ symbol

### **File not found error:**
- File may have been deleted
- Check file ID is valid
- Verify file permissions

### **Autocomplete not filtering:**
- Check search logic in InputBox
- Verify file names match query
- Clear and retry typing

## 📞 Support

- **Documentation:** `/docs`
- **API Reference:** `http://localhost:8000/docs`
- **Issues:** GitHub Issues
- **Chat:** Type `/help` in chat interface

---

**Status:** ✅ **FRONTEND COMPLETE** | ⏳ **BACKEND INTEGRATION NEEDED**

**Version:** 2.0.0  
**Date:** January 28, 2025  
**Feature:** File Reference System with @-tags
