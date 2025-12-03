# 🎨 GreenTech Painting - QuickBooks API Integration

**Automatically create QuickBooks estimates from your quote data.**

This system connects your quote calculation engine to QuickBooks Online, automatically creating estimates, managing customers, and generating PDFs.

---

## 📖 New User? Start Here!

**See `GETTING_STARTED.md` for complete step-by-step setup guide.**

**Quick version:**
1. Install: `pip3 install -r requirements_txt.txt`
2. Configure: Copy `.env.example` to `.env` and add your credentials
3. OAuth: `python3 initial_oauth_setup.py` (auto-saves tokens!)
4. Create: `python3 create_estimate.py --json samples/quote_sample.json`

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip3 install -r requirements_txt.txt
```

Or run the setup script:
```bash
python3 setup.py
```

### 2. Configure Credentials

Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

Edit `.env` with your credentials from https://developer.intuit.com:
```bash
QBO_CLIENT_ID=your_client_id
QBO_CLIENT_SECRET=your_client_secret
QBO_MODE=sandbox
```

### 3. Set Up OAuth (First Time)

```bash
python3 initial_oauth_setup.py
```

**✅ NO REDIRECT URL CONFIGURATION NEEDED!**
- The script uses Intuit's default redirect URI automatically
- You don't need to add anything to Intuit Developer Portal
- No admin access required

**What happens:**
1. Browser opens to QuickBooks authorization
2. Sign in with Intuit account (use account with "Sandbox US Company 1" for sandbox)
3. Select company and click "Connect"
4. After redirect, **copy the URL from browser address bar** (top of browser)
5. Paste URL in terminal
6. **Done!** Tokens are automatically saved ✅

**If token exchange fails:**
```bash
python3 setup_tokens.py
```
Just paste tokens from OAuth Playground - it saves everything automatically!

### 4. Create Your First Estimate

**Test with mock (no QuickBooks API):**
```bash
python3 create_estimate.py --json samples/quote_sample.json --mock
```

**Create real estimate:**
```bash
python3 create_estimate.py --json samples/quote_sample.json
```

**Interactive mode:**
```bash
python3 create_estimate.py
```

---

## 📖 How to Use

### Create Estimate from JSON File

```bash
python3 create_estimate.py --json your_quote.json
```

### Interactive Mode (Simplified)

```bash
python3 create_estimate.py
```

Just enter:
- Customer name (required)
- Items (one line each: `Description | Qty | Price`)

### Start API Server

```bash
python3 start_server.py
```

Server runs on: `http://localhost:5000`

Send POST requests to: `http://localhost:5000/api/v1/estimate`

---

## 📝 JSON Format

Your quote JSON should look like:

```json
{
  "customer": {
    "display_name": "John Doe",
    "email": "john@example.com",
    "phone": "416-555-0100"
  },
  "quote": {
    "reference": "GT-001",
    "date": "2025-11-17"
  },
  "items": [
    {
      "description": "Interior painting - Living room",
      "qty": 2,
      "unit_price": 150.0
    }
  ],
  "sustainability": {
    "trees": 1,
    "co2_tons": 0.1,
    "water_liters": 10
  },
  "currency": "CAD"
}
```

---

## 🛠️ Common Commands

```bash
# Test connection
python3 quickbooks_client.py

# Test system
python3 test_system.py

# Find estimates
python3 find_estimate.py --list
python3 find_estimate.py --doc-number GT-TEST-001

# View logs
cat logs/quotes_log.csv
```

---

## ❓ Troubleshooting

### "Module not found"
```bash
pip3 install -r requirements_txt.txt
```

### "Token refresh failed" or "invalid_client"
**Simple fix:**
```bash
python3 setup_tokens.py
```
Just paste tokens from OAuth Playground - it saves everything automatically!

### "Cannot connect to QuickBooks"
1. Check `.env` has correct credentials
2. Run: `python3 setup_tokens.py` to update tokens
3. Test: `python3 quickbooks_client.py`

### "We didn't find any companies"
- Use sandbox URL: https://app.sandbox.intuit.com
- Sign in with account that has "Sandbox US Company 1"
- Click "Use a different account" if needed

### Token Expired (After 1 Hour)
```bash
python3 setup_tokens.py
```
Just paste new tokens - it saves automatically!

---

## 🔒 Security

- ✅ **Never commit `.env` file** - Contains secrets
- ✅ **Never share `.token_cache.json`** - Contains tokens
- ✅ **Each user needs their own credentials** from Intuit Developer
- ✅ **Use sandbox mode for testing**

---

## 📁 Project Structure

See `FILE_STRUCTURE_AND_WORKFLOW.md` for complete architecture overview.

**Key Files:**
- `create_estimate.py` - Main tool to create estimates
- `quickbooks_client.py` - QuickBooks API client
- `oauth.py` - Token management
- `mapping.py` - Data transformation
- `api_server.py` - REST API server

---

## 📚 Documentation

- **README.md** (this file) - User guide
- **FILE_STRUCTURE_AND_WORKFLOW.md** - Architecture and structure

---

## ✅ Quick Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed
- [ ] `.env` file configured
- [ ] OAuth setup completed
- [ ] Token cache set
- [ ] Test with mock mode
- [ ] Create real estimate successfully

---

**Ready to get started?** Run `python3 setup.py` now! 🚀
