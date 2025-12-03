#!/usr/bin/env python3
"""
GreenTech Painting - Simple Estimate Creator
User-friendly script to create estimates interactively or from JSON.
"""
import sys
import json
import pathlib
import argparse
from cli_push_estimate import process_quote

def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 70)
    print("  GreenTech Painting - QuickBooks Estimate Creator")
    print("=" * 70 + "\n")

def create_estimate_interactive():
    """Interactive mode - ask user for quote details (minimal input)"""
    print("📝 Quick Quote Creator")
    print("(Only essential fields required - defaults provided)\n")
    
    # Customer info - only name required
    customer_name = input("Customer Name: ").strip()
    if not customer_name:
        print("❌ Customer name is required")
        return None
    
    # Optional customer details (one line)
    contact = input("Email/Phone (optional, press Enter to skip): ").strip()
    customer_email = contact if "@" in contact else ""
    customer_phone = contact if "@" not in contact and contact else ""
    
    # Quote info - auto-generate reference and use today's date
    from datetime import datetime
    reference = input(f"Quote Reference (default: GT-{datetime.now().strftime('%Y%m%d')}-001): ").strip()
    if not reference:
        # Auto-generate reference
        reference = f"GT-{datetime.now().strftime('%Y%m%d')}-001"
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Items - simplified input
    print("\nEnter line items (one per line, format: 'Description | Qty | Price' or just 'Description')")
    print("Example: 'Interior Painting | 2 | 150' or 'Exterior Painting'")
    print("(Press Enter with empty line to finish):")
    items = []
    item_num = 1
    
    while True:
        line = input(f"Item {item_num}: ").strip()
        if not line:
            break
        
        # Parse: "Description | Qty | Price" or just "Description"
        parts = [p.strip() for p in line.split("|")]
        
        if len(parts) >= 3:
            # Full format: Description | Qty | Price
            description, qty_str, price_str = parts[0], parts[1], parts[2]
            try:
                qty = float(qty_str) if qty_str else 1.0
                unit_price = float(price_str) if price_str else 0.0
            except ValueError:
                qty = 1.0
                unit_price = 0.0
        elif len(parts) == 1:
            # Just description - use defaults
            description = parts[0]
            qty = 1.0
            unit_price = 0.0
        else:
            # Invalid format, skip
            print("  ⚠️  Invalid format, skipping. Use: 'Description | Qty | Price'")
            continue
        
        if description:
            items.append({
                "description": description,
                "qty": qty,
                "unit_price": unit_price
            })
            item_num += 1
    
    if not items:
        print("❌ At least one item is required")
        return None
    
    # Skip sustainability - not essential
    sustainability = {}
    
    # Currency - default to CAD
    currency = "CAD"
    
    # Build JSON
    quote_data = {
        "customer": {
            "display_name": customer_name,
            "email": customer_email,
            "phone": customer_phone
        },
        "quote": {
            "reference": reference,
            "date": date
        },
        "items": items,
        "currency": currency
    }
    
    if sustainability:
        quote_data["sustainability"] = sustainability
    
    return quote_data

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Create QuickBooks estimates easily",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python create_estimate.py

  # From JSON file
  python create_estimate.py --json my_quote.json

  # Mock mode (no QuickBooks API call)
  python create_estimate.py --json my_quote.json --mock
        """
    )
    
    parser.add_argument(
        "--json",
        type=str,
        help="Path to JSON quote file"
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Create mock estimate (no QuickBooks API call)"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode (ask for quote details)"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Determine mode
    if args.json:
        # JSON file mode
        json_path = pathlib.Path(args.json)
        if not json_path.exists():
            print(f"❌ Error: File not found: {json_path}")
            return 1
        
        print(f"📄 Using JSON file: {json_path}")
        print(f"🔧 Mode: {'MOCK' if args.mock else 'QUICKBOOKS API'}\n")
        
        result = process_quote(json_path, use_mock=args.mock)
        
    elif args.interactive or (not args.json and not args.interactive):
        # Interactive mode
        quote_data = create_estimate_interactive()
        
        if not quote_data:
            return 1
        
        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(quote_data, tmp_file, indent=2)
            tmp_path = pathlib.Path(tmp_file.name)
        
        try:
            print(f"\n📄 Quote data saved to: {tmp_path}")
            print(f"🔧 Mode: {'MOCK' if args.mock else 'QUICKBOOKS API'}\n")
            
            result = process_quote(tmp_path, use_mock=args.mock)
            
            # Auto-delete temp file (no prompt)
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise e
    else:
        parser.print_help()
        return 1
    
    # Display result
    print("\n" + "=" * 70)
    if result.get("ok"):
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"Reference: {result.get('reference')}")
        print(f"Customer: {result.get('customer_name')}")
        print(f"Status: {result.get('status')}")
        if result.get('pdf_path'):
            print(f"PDF: {result.get('pdf_path')}")
        if result.get('estimate_id'):
            print(f"QuickBooks Estimate ID: {result.get('estimate_id')}")
        return 0
    else:
        print("❌ FAILED")
        print("=" * 70)
        print(f"Error: {result.get('error', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

