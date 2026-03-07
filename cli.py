import os
from qr_render import generate_qr_svg
from upin_store import UpinStore


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
DB_UPIN = "upinmgmt.sqlite"
DB_MASTER = "lawrence_master.sqlite"
# Alphabet chosen to avoid confusing characters (no 0/O, 1/I, etc.)
UPIN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

store = UpinStore(DB_UPIN, DB_MASTER, UPIN_ALPHABET)

# -------------------------------------------------------------------
# Wrappers for Menu support
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# QR export / regeneration
# -------------------------------------------------------------------

def add_qr_codes_to_all() -> None:
    n = store.add_qr_codes_to_all(qr_renderer=generate_qr_svg, actor="cli")
    print(f"Generated and stored QR codes for {n} UPIN entries.")

    
    
def regenerate_branded_qr_for_account_prompt() -> None:
    try:
        account_number = input("Enter account_number: ").strip()
        ok = store.regenerate_qr_for_account(
            account_number,
            qr_renderer=generate_qr_svg,
            actor="cli",
        )
        if ok:
            print("Regenerated branded QR for that account.")
        else:
            print("No active UPIN found for that account (nothing regenerated).")
    except Exception as e:
        print(f"Error regenerating branded QR: {e}")

        
        
def export_qr_svgs() -> None:
    n = store.export_qr_svgs(out_dir="qr_exports", filename_mode="vision_account", actor="cli")
    print(f"Exported {n} QR SVG files.")


        
def issue_random_lean_upin_prompt() -> None:
    """Issue one random UPIN from LEAN-eligible parcels."""
    try:
        rows = get_random_parcels(limit=1, lean_only=True)
        if not rows:
            print("No LEAN-eligible parcels found.")
            return
        upin_plain, account_number, _, _ = issue_upin_from_row(rows[0])
        print(f"Random LEAN-eligible UPIN issued: {upin_plain} for account {account_number}")
    except Exception as e:
        print(f"Error issuing LEAN-eligible random UPIN: {e}")


        
def show_upin_history_prompt() -> None:
    account_number = input("Enter account_number: ").strip()
    rows = store.get_upin_history(account_number)

    if not rows:
        print("No audit history found for that account_number.")
        return

    print("\n==================== UPIN HISTORY ====================")
    for ts, event_type, actor, meta in rows:
        print(f"[{ts}] {event_type.upper()} by {actor}")
        print(f"    {meta}")
    print("======================================================\n")


# -------------------------------------------------------------------
# Menu wiring
# -------------------------------------------------------------------
MENU_OPTIONS = {
    "2": lambda: store.validate_upin_prompt(actor="cli"),
    "3": lambda: store.reissue_upin_prompt(qr_renderer=generate_qr_svg, actor="cli"),
    "4": lambda: store.issue_random_upin_prompt(qr_renderer=generate_qr_svg, actor="cli"),
    "6": lambda: store.issue_random_upins_by_fuel_prompt(qr_renderer=generate_qr_svg, actor="cli", limit=30),
    "7": export_qr_svgs,
    "8": add_qr_codes_to_all,
    "9": lambda: store.issue_random_lean_upin_prompt(qr_renderer=generate_qr_svg, actor="cli"),
    "10": lambda: store.issue_random_lean_upins_by_fuel_prompt(qr_renderer=generate_qr_svg, actor="cli"),
    "11": regenerate_branded_qr_for_account_prompt,
    "12": show_upin_history_prompt,
    "13": lambda: store.revoke_upin_prompt(actor="cli"),
    "14": lambda: store.revoke_and_issue_new_upin_prompt(actor="cli"),
}



def main_menu() -> None:
    while True:
        print("\nUPIN Management Prototype Menu:")
#        print("1. Generate new UPIN (manual input)")
        print("2. Validate existing UPIN")
        print("3. Lost UPIN (Reissue same UPIN, regenerate QR)")
        print("4. Generate UPIN from random residential parcel")
        print("5. Quit")
        print("6. Generate 30 random UPINs by heating fuel (Gas | Electric | Oil)")
        print("7. Export stored QR codes to .svg files")
        print("8. Generate and store QR codes for all UPIN entries")
        print("9. Generate UPIN from random LEAN-eligible parcel")
        print("10. Generate 20 UPINs for LEAN (2–4 units) or LMF (>4 units) by heating fuel")
        print("11. Generate branded QR for one account_number")
        print("12. Show UPIN audit history for an account")
        print("13. Revoke UPIN (disable current UPIN)")
        print("14. Revoke current UPIN and issue a NEW one (fresh registration)")
        choice = input("Enter choice (1–14 or Esc): ").strip()
        if choice in ("5", "esc", "ESC"):
            print("Exiting prototype. Goodbye!")
            break
        elif choice in MENU_OPTIONS:
            try:
                MENU_OPTIONS[choice]()
            except Exception as e:
                print(f"Unexpected error: {e}")
        else:
            print("Invalid choice. Returning to menu.")
if __name__ == "__main__":
    main_menu()