# 🚀 Getting Started - Step by Step

## For New Users

Follow these steps to set up and use the system.

---

## Step 1: Get the Project

**Option A: Git**
```bash
git clone <repository-url>
cd greentech_api_QB\ 2
```

**Option B: Download Zip**
- Download and extract the project
- Open terminal in the project folder

---

## Step 2: Install Dependencies

```bash
pip3 install -r requirements_txt.txt
```

Or use the setup script:
```bash
python3 setup.py
```

---

## Step 3: Get QuickBooks Credentials

1. **Go to:** https://developer.intuit.com
2. **Sign in** (or create free account)
3. **Create an app:**
   - Click "Create an app"
   - Select "QuickBooks Online"
   - Fill in app details
4. **Get credentials:**
   - Go to "Keys & OAuth" section
   - Copy **Client ID** and **Client Secret**

---

## Step 4: Configure Credentials

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file:**
   ```bash
   nano .env
   # or use any text editor
   ```

3. **Add your credentials:**
   ```bash
   QBO_CLIENT_ID=your_client_id_here
   QBO_CLIENT_SECRET=your_client_secret_here
   QBO_MODE=sandbox
   ```

---

## Step 5: Set Up OAuth (One Time)

```bash
python3 initial_oauth_setup.py
```

### ✅ IMPORTANT: No Redirect URL Configuration Needed!

**You DON'T need to:**
- ❌ Add redirect URL to Intuit app
- ❌ Configure anything in Developer Portal
- ❌ Have admin access

**The script uses Intuit's default redirect URI automatically!**

### What Happens:

1. **Browser opens** to QuickBooks authorization
2. **Sign in** with your Intuit account
   - Use account with "Sandbox US Company 1" for sandbox
3. **Select company** and click "Connect"
4. **After redirect**, look at your **browser's address bar** (top of browser)
5. **Copy the ENTIRE URL** from the address bar
6. **Paste it in the terminal** when asked
7. **Done!** Tokens are automatically saved ✅

**💡 Don't worry about what the redirect page says - just copy the URL!**

### If You See "We didn't find any companies":
- Click "Use a different account"
- Sign in with account that has "Sandbox US Company 1"
- Or create sandbox company at: https://app.sandbox.intuit.com

### If Token Exchange Fails:
```bash
python3 setup_tokens.py
```
- Get tokens from: https://developer.intuit.com/v2/OAuth2Playground
- Paste tokens when prompted
- Everything saves automatically ✅

---

## Step 6: Test the System

```bash
# Test connection
python3 quickbooks_client.py

# Test with mock (no QuickBooks API)
python3 create_estimate.py --json samples/quote_sample.json --mock

# Create real estimate
python3 create_estimate.py --json samples/quote_sample.json
```

---

## Step 7: Create Your First Estimate

### Option 1: From JSON File

Create a JSON file with your quote data:
```json
{
  "customer": {
    "display_name": "John Doe",
    "email": "john@example.com"
  },
  "quote": {
    "reference": "GT-001",
    "date": "2025-11-28"
  },
  "items": [
    {
      "description": "Interior painting",
      "qty": 2,
      "unit_price": 150.0
    }
  ],
  "currency": "CAD"
}
```

Then run:
```bash
python3 create_estimate.py --json your_quote.json
```

### Option 2: Interactive Mode

```bash
python3 create_estimate.py
```

Just enter:
- Customer name
- Items (one line each: `Description | Qty | Price`)

**Done!** PDF saved in `Quotes/` folder.

---

## ✅ That's It!

You're ready to create estimates. The system will:
- ✅ Create customers automatically
- ✅ Create estimates in QuickBooks
- ✅ Download PDFs automatically
- ✅ Log everything to CSV

---

## 🔄 When Token Expires (After 1 Hour)

```bash
python3 setup_tokens.py
```

Get new tokens from OAuth Playground and paste them.

---

## 📚 Need Help?

- **README.md** - Full user guide
- **FILE_STRUCTURE_AND_WORKFLOW.md** - Architecture details
- **Test system:** `python3 test_system.py`

---

## ⚡ Quick Reference

| Task | Command |
|------|---------|
| **Setup** | `python3 setup.py` |
| **OAuth** | `python3 initial_oauth_setup.py` |
| **Set tokens** | `python3 setup_tokens.py` |
| **Create estimate** | `python3 create_estimate.py` |
| **From JSON** | `python3 create_estimate.py --json file.json` |
| **Test** | `python3 quickbooks_client.py` |
| **Find estimates** | `python3 find_estimate.py --list` |

---

**Ready? Start with Step 1!** 🎉

