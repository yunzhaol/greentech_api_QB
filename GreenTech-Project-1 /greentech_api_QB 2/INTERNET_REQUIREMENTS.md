# 🌐 Internet Connection Requirements

**Does this solution need internet? YES - Absolutely!**

---

## ✅ **YES - Internet Connection is REQUIRED**

Your QuickBooks integration solution **must have internet connection** to work. Here's why:

---

## 🔍 Why Internet is Required

### **1. QuickBooks Online is Cloud-Based**

QuickBooks Online is **not installed on your computer**. It's a **cloud service** hosted on Intuit's servers.

**What this means**:
- All your QuickBooks data is stored on Intuit's servers
- You access it through the internet
- Your Python code must connect to Intuit's servers to create estimates

---

### **2. OAuth Authentication Requires Internet**

**File**: `oauth.py`

**What happens**:
```python
# Token refresh endpoint
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
```

**Internet calls**:
- ✅ **Token refresh**: Connects to `https://oauth.platform.intuit.com`
- ✅ **Initial setup**: Browser opens to QuickBooks login page (internet required)
- ✅ **Token exchange**: Sends HTTP requests to Intuit servers

**Without internet**:
- ❌ Cannot get access tokens
- ❌ Cannot authenticate
- ❌ Cannot connect to QuickBooks

---

### **3. All API Calls Go Over Internet**

**File**: `quickbooks_client.py`

**API Endpoints**:

```python
def get_base_url():
    """Returns the QuickBooks API base URL based on mode"""
    if QBO_MODE == "production":
        return "https://quickbooks.api.intuit.com"  # ← Internet URL
    return "https://sandbox-quickbooks.api.intuit.com"  # ← Internet URL
```

**All operations require internet**:

1. **Get Company Info**:
   ```
   GET https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/companyinfo/1
   ```

2. **Create Customer**:
   ```
   POST https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/customer
   ```

3. **Create Estimate**:
   ```
   POST https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/estimate
   ```

4. **Download PDF**:
   ```
   GET https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/estimate/{id}/pdf
   ```

**Every single operation** sends HTTP requests over the internet to Intuit's servers.

---

## 📊 Internet Usage Breakdown

### **What Requires Internet**

| Operation | Internet Required? | Why |
|-----------|-------------------|-----|
| **OAuth Setup** | ✅ YES | Browser opens QuickBooks login page |
| **Token Refresh** | ✅ YES | Connects to `oauth.platform.intuit.com` |
| **Get Company Info** | ✅ YES | API call to QuickBooks servers |
| **Create Customer** | ✅ YES | API call to QuickBooks servers |
| **Create Estimate** | ✅ YES | API call to QuickBooks servers |
| **Download PDF** | ✅ YES | API call to QuickBooks servers |
| **Find Estimates** | ✅ YES | API call to QuickBooks servers |

### **What Does NOT Require Internet**

| Operation | Internet Required? | Why |
|-----------|-------------------|-----|
| **Data Validation** | ❌ NO | Happens locally in `mapping.py` |
| **JSON File Reading** | ❌ NO | Reads local files |
| **CSV Logging** | ❌ NO | Writes to local `logs/` folder |
| **PDF Saving** | ❌ NO | Saves to local `Quotes/` folder |
| **Server Running** | ❌ NO | Flask server runs locally |
| **Excel/VBA Integration** | ❌ NO | Local communication only |

---

## 🔄 Complete Data Flow (With Internet)

```
Your Computer (Local)
    ↓
┌─────────────────────────────────┐
│ Local Operations (No Internet) │
│ - Read JSON file                │
│ - Validate data                  │
│ - Transform format               │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ INTERNET CONNECTION REQUIRED    │
│ ↓                               │
│ HTTPS Request                   │
│ ↓                               │
│ Intuit OAuth Server             │
│ (Get/Refresh Token)             │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ INTERNET CONNECTION REQUIRED    │
│ ↓                               │
│ HTTPS Request                   │
│ ↓                               │
│ QuickBooks API Server           │
│ (Create Estimate, Get PDF)      │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ Local Operations (No Internet) │
│ - Save PDF to Quotes/ folder    │
│ - Log to CSV                    │
│ - Return result                 │
└─────────────────────────────────┘
```

---

## 🌐 Internet Connection Details

### **Required URLs**

Your system needs to connect to:

1. **OAuth Server**:
   - `https://oauth.platform.intuit.com`
   - Port: 443 (HTTPS)

2. **Sandbox API** (for testing):
   - `https://sandbox-quickbooks.api.intuit.com`
   - Port: 443 (HTTPS)

3. **Production API** (for live use):
   - `https://quickbooks.api.intuit.com`
   - Port: 443 (HTTPS)

### **Network Requirements**

- ✅ **Outbound HTTPS** (port 443) must be allowed
- ✅ **DNS resolution** must work (to resolve domain names)
- ✅ **Firewall** must allow HTTPS connections
- ✅ **Proxy settings** (if behind corporate firewall)

---

## 🏢 Corporate Network Considerations

### **If You're Behind a Corporate Firewall**

**Potential Issues**:
- ❌ Firewall blocks outbound HTTPS
- ❌ Proxy requires authentication
- ❌ Corporate proxy intercepts SSL certificates

**Solutions**:
1. **Whitelist Intuit domains**:
   - `*.intuit.com`
   - `*.platform.intuit.com`

2. **Configure proxy** (if needed):
   ```python
   # In quickbooks_client.py or oauth.py
   import os
   proxies = {
       'https': os.getenv('HTTPS_PROXY', '')
   }
   requests.post(url, proxies=proxies, ...)
   ```

3. **Test connectivity**:
   ```bash
   curl https://sandbox-quickbooks.api.intuit.com
   ```

---

## 📱 Offline Mode?

### **Can It Work Offline?**

**Short Answer**: ❌ **NO**

**Why**:
- QuickBooks Online data is in the cloud
- All operations require API calls
- No local QuickBooks database

### **What CAN Work Offline**

**Mock Mode** (`--mock` flag):
```bash
python3 create_estimate.py --json quote.json --mock
```

**What Mock Mode Does**:
- ✅ Validates data locally
- ✅ Creates a fake PDF file
- ✅ Logs to CSV
- ❌ **Does NOT** connect to QuickBooks
- ❌ **Does NOT** create real estimates

**Use Case**: Testing your integration without internet, but **not for real work**.

---

## 🔍 How to Check Internet Connectivity

### **Test 1: Basic Internet**
```bash
ping google.com
```

### **Test 2: QuickBooks API**
```bash
curl https://sandbox-quickbooks.api.intuit.com
```

### **Test 3: OAuth Server**
```bash
curl https://oauth.platform.intuit.com
```

### **Test 4: From Python**
```python
import requests
try:
    response = requests.get("https://sandbox-quickbooks.api.intuit.com", timeout=5)
    print("✅ Internet connection OK")
except:
    print("❌ Cannot reach QuickBooks API")
```

---

## 🎯 Summary

### **Internet Required For**:

✅ **OAuth Authentication** - Get/refresh tokens  
✅ **All QuickBooks API Calls** - Create estimates, customers, etc.  
✅ **PDF Downloads** - Get estimate PDFs from QuickBooks  
✅ **Initial Setup** - OAuth authorization flow  

### **Internet NOT Required For**:

❌ **Data Validation** - Happens locally  
❌ **File Operations** - Reading JSON, writing CSV/PDF  
❌ **Server Running** - Flask runs locally  
❌ **Mock Mode** - Testing without QuickBooks  

### **Bottom Line**:

**YES - You MUST have internet connection for this solution to work with QuickBooks Online.**

The only exception is **mock mode**, which creates fake PDFs for testing but doesn't actually connect to QuickBooks.

---

## 🛠️ Troubleshooting No Internet

### **Error Messages You Might See**:

1. **"Network error: Connection timeout"**
   - ❌ No internet or firewall blocking

2. **"Failed to refresh token"**
   - ❌ Cannot reach OAuth server

3. **"QuickBooks API Error: Connection refused"**
   - ❌ Cannot reach QuickBooks API

### **Solutions**:

1. **Check internet connection**:
   ```bash
   ping google.com
   ```

2. **Check firewall settings**:
   - Allow outbound HTTPS (port 443)
   - Whitelist `*.intuit.com`

3. **Test API connectivity**:
   ```bash
   curl https://sandbox-quickbooks.api.intuit.com
   ```

4. **Use mock mode for testing** (if internet unavailable):
   ```bash
   python3 create_estimate.py --json quote.json --mock
   ```

---

**In summary: Internet connection is absolutely essential for this QuickBooks integration to work!** 🌐✅

