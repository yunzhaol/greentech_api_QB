#!/usr/bin/env python3
"""
QuickBooks Estimate Finder
Search for estimates by Doc Number or list all estimates
"""
import sys
import argparse
from quickbooks_client import _make_request, QuickBooksAPIError

def list_all_estimates(limit=50):
    """List all estimates"""
    try:
        query = f"SELECT * FROM Estimate MAXRESULTS {limit}"
        response = _make_request('GET', f'query?query={query}')
        
        estimates = response.get('QueryResponse', {}).get('Estimate', [])
        
        if not estimates:
            print("No estimates found.")
            return
        
        print(f"\n{'=' * 70}")
        print(f"Found {len(estimates)} estimate(s)")
        print(f"{'=' * 70}\n")
        
        for est in estimates:
            doc_num = est.get('DocNumber', 'N/A')
            customer = est.get('CustomerRef', {}).get('name', 'N/A')
            total = est.get('TotalAmt', 0)
            status = est.get('TxnStatus', 'N/A')
            est_id = est.get('Id', 'N/A')
            date = est.get('TxnDate', 'N/A')
            
            print(f"Doc Number: {doc_num}")
            print(f"  Customer: {customer}")
            print(f"  Date: {date}")
            print(f"  Total: ${total}")
            print(f"  Status: {status}")
            print(f"  ID: {est_id}")
            print()
        
    except QuickBooksAPIError as e:
        print(f"❌ QuickBooks API Error: {e.message}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

def find_estimate_by_doc_number(doc_number):
    """Find estimate by Doc Number"""
    try:
        # Escape single quotes in doc_number
        safe_doc_number = doc_number.replace("'", "''")
        query = f"SELECT * FROM Estimate WHERE DocNumber = '{safe_doc_number}'"
        
        response = _make_request('GET', f'query?query={query}')
        
        estimates = response.get('QueryResponse', {}).get('Estimate', [])
        
        if not estimates:
            print(f"\n❌ No estimate found with Doc Number: {doc_number}")
            print("\n💡 Try listing all estimates:")
            print("   python3 find_estimate.py --list")
            return 1
        
        est = estimates[0]
        
        print(f"\n{'=' * 70}")
        print(f"✅ Found Estimate: {doc_number}")
        print(f"{'=' * 70}\n")
        
        print(f"Doc Number: {est.get('DocNumber')}")
        print(f"Customer: {est.get('CustomerRef', {}).get('name', 'N/A')}")
        print(f"Date: {est.get('TxnDate', 'N/A')}")
        print(f"Total: ${est.get('TotalAmt', 0)}")
        print(f"Status: {est.get('TxnStatus', 'N/A')}")
        print(f"QuickBooks ID: {est.get('Id')}")
        print(f"Sync Token: {est.get('SyncToken', 'N/A')}")
        
        # Show line items
        lines = est.get('Line', [])
        if lines:
            print(f"\nLine Items ({len(lines)}):")
            for i, line in enumerate(lines, 1):
                desc = line.get('Description', 'N/A')
                qty = line.get('Amount', 0)
                print(f"  {i}. {desc}: ${qty}")
        
        print()
        
    except QuickBooksAPIError as e:
        print(f"❌ QuickBooks API Error: {e.message}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Find estimates in QuickBooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all estimates
  python3 find_estimate.py --list

  # Find by Doc Number
  python3 find_estimate.py --doc-number GT-TEST-001

  # List with custom limit
  python3 find_estimate.py --list --limit 100
        """
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all estimates'
    )
    
    parser.add_argument(
        '--doc-number',
        type=str,
        help='Find estimate by Doc Number (e.g., GT-TEST-001)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Limit number of results when listing (default: 50)'
    )
    
    args = parser.parse_args()
    
    if args.list:
        return list_all_estimates(limit=args.limit)
    elif args.doc_number:
        return find_estimate_by_doc_number(args.doc_number)
    else:
        parser.print_help()
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

