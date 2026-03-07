# ------------------------------------------------------------
# upin_store.py
# Data / persistence layer for UPIN system
# Owns ALL database access and audit logging
# ------------------------------------------------------------

import sqlite3
import secrets
from typing import Optional, Callable, List, Tuple

from argon2 import PasswordHasher, exceptions


class UpinStore:
    
    def ensure_schema(self) -> None:
    # UPIN table
        self.cur_upin.execute("""
        CREATE TABLE IF NOT EXISTS upin (
            ratepayer_id INTEGER PRIMARY KEY AUTOINCREMENT,

            account_number TEXT NOT NULL,
            is_residential TEXT DEFAULT 'Y',
            normalized_address TEXT,
            heating_fuel_description TEXT,
            primary_land_use_code_description TEXT,
            total_occupancy INTEGER,
            vision_id TEXT,
            lean_eligibility TEXT,          -- LEAN / LMF / n/a / ?

            upin_hash TEXT NOT NULL,        -- Argon2 hash of the UPIN
            status TEXT CHECK(status IN ('active','revoked')) NOT NULL DEFAULT 'active',
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reissue_count INTEGER DEFAULT 0,
            qr_svg TEXT
        );
        """)

        self.cur_upin.execute("""
        CREATE INDEX IF NOT EXISTS idx_upin_account ON upin (account_number);
        """)

        # Audit table
        self.cur_upin.execute("""
        CREATE TABLE IF NOT EXISTS audit_event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            actor TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );
        """)

        self.conn_upin.commit()

    def __init__(self, db_upin: str, db_master: str, alphabet: str):
        self.db_upin = db_upin
        self.db_master = db_master
        self.alphabet = alphabet

        self.conn_upin = sqlite3.connect(self.db_upin)
        self.cur_upin = self.conn_upin.cursor()

        self.conn_master = sqlite3.connect(self.db_master)
        self.cur_master = self.conn_master.cursor()

        self.ph = PasswordHasher()
        self.ensure_schema()


    # ------------------------------------------------------------
    # Audit logging (STORE ONLY)
    # ------------------------------------------------------------
    def log_event(self, event_type: str, actor: str, metadata: str) -> None:
        self.cur_upin.execute(
            """
            INSERT INTO audit_event (event_type, actor, metadata)
            VALUES (?, ?, ?)
            """,
            (event_type, actor, metadata),
        )
        self.conn_upin.commit()

    # ------------------------------------------------------------
    # UPIN generation / validation
    # ------------------------------------------------------------
    def generate_random_upin(self, length: int = 10) -> str:
        return "".join(secrets.choice(self.alphabet) for _ in range(length))

    def validate_upin(
        self, account_number: str, supplied_upin: str, actor: str = "system"
    ) -> bool:
        self.cur_upin.execute(
            """
            SELECT ratepayer_id, upin_hash
            FROM upin
            WHERE account_number = ? AND status = 'active'
            """,
            (account_number,),
        )
        row = self.cur_upin.fetchone()

        if not row:
            self.log_event(
                "validate",
                actor,
                f"account_number={account_number} result=not_found",
            )
            return False

        _, upin_hash = row
        try:
            self.ph.verify(upin_hash, supplied_upin)
            self.log_event(
                "validate",
                actor,
                f"account_number={account_number} result=success",
            )
            return True
        except exceptions.VerifyMismatchError:
            self.log_event(
                "validate",
                actor,
                f"account_number={account_number} result=failure",
            )
            return False

    # ------------------------------------------------------------
    # Prompt wrappers (CLI-facing, but still STORE-owned)
    # ------------------------------------------------------------
    def validate_upin_prompt(self, actor: str = "cli") -> None:
        account_number = input("Enter account_number: ").strip()
        upin = input("Enter your UPIN: ").strip().upper()
        ok = self.validate_upin(account_number, upin, actor=actor)
        print("UPIN valid ✅" if ok else "UPIN not valid ❌")

    # ------------------------------------------------------------
    # Parcel selection
    # ------------------------------------------------------------
    def get_random_parcels(
        self,
        fuel_type: Optional[str] = None,
        limit: int = 1,
        lean_only: bool = False,
    ):
        query = """
            SELECT account_number,
                   is_residential,
                   normalized_address,
                   owner_1_name,
                   heating_fuel_description,
                   primary_land_use_code_description,
                   total_occupancy,
                   vision_id,
                   lean_eligibility
            FROM Assessment_L_Parcels
            WHERE is_residential = 'Y'
        """
        params = []

        if fuel_type:
            query += " AND heating_fuel_description = ?"
            params.append(fuel_type.capitalize())

        if lean_only:
            query += " AND lean_eligibility IN ('LEAN','LMF')"

        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(int(limit))

        self.cur_master.execute(query, tuple(params))
        return self.cur_master.fetchall()

    # ------------------------------------------------------------
    # Issue / Reissue / Revoke
    # it’s cleaner to return the new row id (or upin_hash) 
    # directly so you don’t have to do another query.
    # ------------------------------------------------------------
    
    def issue_upin_from_parcel_row(self, row, actor: str = "system"):
        account_number = row[0]
        upin_plain = self.generate_random_upin()
        upin_hash = self.ph.hash(upin_plain)
        self.cur_upin.execute(
            """
            INSERT INTO upin (
                account_number,
                is_residential,
                normalized_address,
                heating_fuel_description,
                primary_land_use_code_description,
                total_occupancy,
                vision_id,
                lean_eligibility,
                upin_hash,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                row[0],
                row[1],
                row[2],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                upin_hash,
            ),
        )
        self.conn_upin.commit()

        ratepayer_id = int(self.cur_upin.lastrowid)

        self.log_event("issue", actor, f"account_number={account_number} ratepayer_id={ratepayer_id}")
        
        return upin_plain, account_number, ratepayer_id, upin_hash


    # ------------------------------------------------------------
    # Issue Ramdon=me UPIN for residential Parcel
    # ------------------------------------------------------------
    def issue_random_upin_prompt(
        self,
        qr_renderer: Optional[Callable] = None,
        actor: str = "cli",
    ) -> None:
        rows = self.get_random_parcels(limit=1)
        if not rows:
            print("No eligible parcels found.")
            return

        row = rows[0]  # <-- FIX: define row
        upin_plain, acct, ratepayer_id, upin_hash = self.issue_upin_from_parcel_row(row, actor=actor)

        if qr_renderer:
            # Regen QR for this account (or you can update by ratepayer_id if you prefer)
            self.regenerate_qr_for_account(acct, qr_renderer=qr_renderer, actor=actor)

        print(f"Issued UPIN {upin_plain} for account {acct}")


    def issue_random_upins_by_fuel_prompt(
        self,
        qr_renderer: Optional[Callable] = None,
        actor: str = "cli",
        limit: int = 30,
    ) -> None:
        fuel = input("Enter heating fuel (Gas | Electric | Oil): ").strip()
        rows = self.get_random_parcels(fuel_type=fuel, limit=limit)

        if not rows:
            print("No eligible parcels found.")
            return

        for row in rows:
            upin_plain, acct, _ , _ = self.issue_upin_from_parcel_row(row, actor=actor)
            if qr_renderer:
                self.regenerate_qr_for_account(acct, qr_renderer, actor)

        print(f"Issued {len(rows)} UPINs for fuel={fuel}")

    def reissue_upin_prompt(
        self,
        qr_renderer: Optional[Callable] = None,
        actor: str = "cli",
    ) -> None:
        acct = input("Enter account_number for reissue: ").strip()

        self.cur_upin.execute(
            """
            SELECT ratepayer_id,
                   heating_fuel_description,
                   vision_id,
                   lean_eligibility,
                   upin_hash
            FROM upin
            WHERE account_number = ? AND status = 'active'
            """,
            (acct,),
        )
        row = self.cur_upin.fetchone()

        if not row:
            print("No active UPIN found.")
            return

        ratepayer_id, fuel, vision_id, lean, upin_hash = row
        qr_svg = (
            qr_renderer(upin_hash, fuel, vision_id, lean)
            if qr_renderer
            else None
        )

        self.cur_upin.execute(
            """
            UPDATE upin
            SET reissue_count = reissue_count + 1,
                qr_svg = ?
            WHERE ratepayer_id = ?
            """,
            (qr_svg, ratepayer_id),
        )
        self.conn_upin.commit()

        self.log_event("reissue", actor, f"account_number={acct}")
        print("UPIN reissued (same UPIN, QR regenerated).")

    def regenerate_qr_for_account(
        self,
        account_number: str,
        qr_renderer: Callable,
        actor: str = "system",
    ) -> bool:
        self.cur_upin.execute(
            """
            SELECT ratepayer_id,
                   heating_fuel_description,
                   vision_id,
                   upin_hash,
                   lean_eligibility
            FROM upin
            WHERE account_number = ? AND status = 'active'
            """,
            (account_number,),
        )
        row = self.cur_upin.fetchone()

        if not row:
            return False

        ratepayer_id, fuel, vision_id, upin_hash, lean = row
        qr_svg = qr_renderer(upin_hash, fuel, vision_id, lean)

        self.cur_upin.execute(
            "UPDATE upin SET qr_svg = ? WHERE ratepayer_id = ?",
            (qr_svg, ratepayer_id),
        )
        self.conn_upin.commit()

        self.log_event("qr_regen", actor, f"account_number={account_number}")
        return True

    # ------------------------------------------------------------
    # History
    # ------------------------------------------------------------
    def get_upin_history(self, account_number: str):
        self.cur_upin.execute(
            """
            SELECT timestamp, event_type, actor, metadata
            FROM audit_event
            WHERE metadata LIKE ?
            ORDER BY timestamp ASC
            """,
            (f"%account_number={account_number}%",),
        )
        return self.cur_upin.fetchall()
    
    # ------------------------------------------------------------
    # Add QR codes to all UPIns in the database
    # ------------------------------------------------------------
        
    def add_qr_codes_to_all(
        self,
        qr_renderer,
        actor: str = "system",
        status: str = "active",
    ) -> int:
        """
        Generate (or regenerate) QR codes for all UPIN rows with given status
        and store the resulting SVG in upin.qr_svg.

        Returns the number of rows updated.
        """
        self.cur_upin.execute(
            """
            SELECT ratepayer_id,
                   account_number,
                   heating_fuel_description,
                   vision_id,
                   upin_hash,
                   lean_eligibility
            FROM upin
            WHERE status = ?
            """,
            (status,),
        )
        rows = self.cur_upin.fetchall()
        if not rows:
            self.log_event("qr_regen_all", actor, f"status={status} count=0")
            return 0

        updated = 0
        for ratepayer_id, account_number, fuel, vision_id, upin_hash, lean in rows:
            qr_svg = qr_renderer(upin_hash, fuel, vision_id, lean)
            self.cur_upin.execute(
                "UPDATE upin SET qr_svg = ? WHERE ratepayer_id = ?",
                (qr_svg, ratepayer_id),
            )
            updated += 1

        self.conn_upin.commit()
        self.log_event("qr_regen_all", actor, f"status={status} count={updated}")
        return updated
    
    # ------------------------------------------------------------
    # Export QRs to SVG
    # ------------------------------------------------------------  
        
    def export_qr_svgs(
    self,
    out_dir: str = "qr_exports",
    filename_mode: str = "vision_account",
    only_with_qr: bool = True,
    actor: str = "system",
    ) -> int:
        """
        Export stored QR SVGs to individual .svg files.

        filename_mode:
          - "vision_account"  -> qr_<vision_id>_<account_number>.svg
          - "ratepayer_id"    -> qr_<ratepayer_id>.svg
          - "account"         -> qr_<account_number>.svg

        only_with_qr:
          - if True, export only rows where qr_svg IS NOT NULL

        Returns number of files written.
        """
        import os

        os.makedirs(out_dir, exist_ok=True)

        where = "WHERE qr_svg IS NOT NULL" if only_with_qr else ""
        self.cur_upin.execute(
            f"""
            SELECT ratepayer_id, account_number, vision_id, qr_svg
            FROM upin
            {where}
            """
        )
        rows = self.cur_upin.fetchall()
        if not rows:
            self.log_event("export_qr", actor, f"out_dir={out_dir} count=0")
            return 0

        n = 0
        for ratepayer_id, account_number, vision_id, svg_text in rows:
            if not svg_text:
                continue

            safe_acct = str(account_number).replace("/", "_")
            safe_vision = str(vision_id).replace("/", "_")

            if filename_mode == "ratepayer_id":
                fname = f"qr_{ratepayer_id}.svg"
            elif filename_mode == "account":
                fname = f"qr_{safe_acct}.svg"
            else:  # default "vision_account"
                fname = f"qr_{safe_vision}_{safe_acct}.svg"

            path = os.path.join(out_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg_text)

            n += 1

        self.log_event("export_qr", actor, f"out_dir={out_dir} count={n}")
        return n
        
    # ------------------------------------------------------------
    # Revoke and reissue UPIN mgmt helpers
    # ------------------------------------------------------------  

    def revoke_upin(self, account_number: str, actor: str = "system") -> int:
        """
        Revoke (disable) any active UPIN rows for this account_number.
        Returns number of rows revoked.
        """
        acct = (account_number or "").strip()

        self.cur_upin.execute(
            "SELECT COUNT(*) FROM upin WHERE account_number = ? AND status = 'active'",
            (acct,),
        )
        (n_active,) = self.cur_upin.fetchone()

        if n_active == 0:
            self.log_event("revoke", actor, f"account_number={acct} result=no_active")
            return 0

        self.cur_upin.execute(
            """
            UPDATE upin
            SET status = 'revoked'
            WHERE account_number = ? AND status = 'active'
            """,
            (acct,),
        )
        self.conn_upin.commit()

        self.log_event("revoke", actor, f"account_number={acct} result=revoked count={n_active}")
        return int(n_active)


    def _get_master_parcel_row_by_account(self, account_number: str):
        """
        Fetch parcel metadata from master DB for a specific account_number.
        Row layout matches issue_upin_from_parcel_row(...):
          (account_number, is_residential, normalized_address, owner_1_name,
           heating_fuel_description, primary_land_use_code_description,
           total_occupancy, vision_id, lean_eligibility)
        """
        acct = (account_number or "").strip()
        self.cur_master.execute(
            """
            SELECT account_number,
                   is_residential,
                   normalized_address,
                   owner_1_name,
                   heating_fuel_description,
                   primary_land_use_code_description,
                   total_occupancy,
                   vision_id,
                   lean_eligibility
            FROM Assessment_L_Parcels
            WHERE account_number = ?
            LIMIT 1
            """,
            (acct,),
        )
        return self.cur_master.fetchone()


    def revoke_and_issue_new_upin(self, account_number: str, actor: str = "system"):
        """
        ALWAYS issue a new random UPIN for this account_number.

        - Revokes any active UPIN(s) if present
        - Issues a new UPIN from master DB metadata
        - Returns the new UPIN plaintext (or None if master record missing)
        """
        acct = (account_number or "").strip()

        # Revoke if present (do not require it)
        revoked_count = self.revoke_upin(acct, actor=actor)

        master_row = self._get_master_parcel_row_by_account(acct)
        if not master_row:
            self.log_event("revoke_and_issue", actor, f"account_number={acct} result=master_not_found")
            return None

        # NOTE: now returns 4 values
        upin_plain, acct2, ratepayer_id, upin_hash = self.issue_upin_from_parcel_row(master_row, actor=actor)

        self.log_event(
            "revoke_and_issue",
            actor,
            f"account_number={acct2} result=success revoked_count={revoked_count} ratepayer_id={ratepayer_id}",
        )
        return upin_plain


    def revoke_upin_prompt(self, actor: str = "cli") -> None:
        acct = input("Enter account_number to revoke UPIN: ").strip()
        n = self.revoke_upin(acct, actor=actor)
        if n == 0:
            print("No active UPIN found to revoke.")
        else:
            print(f"Revoked {n} active UPIN record(s) for account {acct}.")
    
    #-----------------------------------------------------------------
    # Issue Randome LEAN/VMF UPINs by fuel type : Helper Function
    #-----------------------------------------------------------------
    
    def issue_random_lean_upins_by_fuel(
    self,
    fuel_type: str,
    lean_code: str,
    qr_renderer: Optional[Callable] = None,
    actor: str = "system",
    limit: int = 20,
    ) -> int:
        clean_fuel = (fuel_type or "").strip().upper()
        clean_lean = (lean_code or "").strip().upper()

        if clean_lean not in ("LEAN", "LMF"):
            raise ValueError("lean_code must be LEAN or LMF")

        q = """
            SELECT account_number,
                   is_residential,
                   normalized_address,
                   owner_1_name,
                   heating_fuel_description,
                   primary_land_use_code_description,
                   total_occupancy,
                   vision_id,
                   lean_eligibility
            FROM Assessment_L_Parcels
            WHERE is_residential = 'Y'
              AND UPPER(TRIM(heating_fuel_description)) = ?
              AND UPPER(TRIM(lean_eligibility))        = ?
        """

        if clean_lean == "LEAN":
            q += " AND total_occupancy BETWEEN 2 AND 4"
        else:
            q += " AND total_occupancy > 4"

        q += " ORDER BY RANDOM() LIMIT ?"

        self.cur_master.execute(q, (clean_fuel, clean_lean, int(limit)))
        rows = self.cur_master.fetchall()

        if not rows:
            self.log_event(
                "issue_lean_fuel",
                actor,
                f"fuel={clean_fuel} lean={clean_lean} result=none_found limit={limit}",
            )
            return 0

        issued = 0
        for row in rows:
            upin_plain, acct, ratepayer_id, upin_hash = self.issue_upin_from_parcel_row(row, actor=actor)

            if qr_renderer:
                fuel_row = row[4]
                vision_id = row[7]
                lean_row = row[8]

                qr_svg = qr_renderer(upin_hash, fuel_row, vision_id, lean_row)

                self.cur_upin.execute(
                    "UPDATE upin SET qr_svg = ? WHERE ratepayer_id = ?",
                    (qr_svg, ratepayer_id),
                )

            issued += 1

        self.conn_upin.commit()
        self.log_event(
            "issue_lean_fuel",
            actor,
            f"fuel={clean_fuel} lean={clean_lean} result=success count={issued}",
        )
        return issued


    def revoke_and_issue_new_upin_prompt(self, actor: str = "cli") -> None:
        try:
            account_number = input("Enter account_number to revoke and reissue UPIN: ").strip()
            new_upin = self.revoke_and_issue_new_upin(account_number, actor=actor)
            if new_upin:
                print(f"New UPIN issued for account {account_number}: {new_upin}")
            else:
                print("Could not issue: master record missing for that account_number.")
        except Exception as e:
            print(f"Error in revoke and issue new UPIN: {e}")

        
    def _get_upin_hash_by_ratepayer_id(self, ratepayer_id: int) -> str:
        self.cur_upin.execute("SELECT upin_hash FROM upin WHERE ratepayer_id=?", (ratepayer_id,))
        row = self.cur_upin.fetchone()
        if not row:
            raise RuntimeError(f"No upin row for ratepayer_id={ratepayer_id}")
        return row[0]

    #-----------------------------------------------------------------
    # Support fuction for test driver based on MENU 
    #-----------------------------------------------------------------
    
    def issue_random_lean_upins_by_fuel_prompt(self, qr_renderer=None, actor: str = "cli") -> None:
        """
        Prompt for fuel + LEAN/LMF, then issue 20 UPINs by fuel.
        """
        fuel_type = input("Enter heating fuel (Gas | Electric | Oil): ").strip()
        lean_choice = input("Enter eligibility type (LEAN | LMF): ").strip().upper()

        if lean_choice not in ("LEAN", "LMF"):
            print("Invalid eligibility type. Please enter LEAN or LMF.")
            return

        n = self.issue_random_lean_upins_by_fuel(
            fuel_type=fuel_type,
            lean_code=lean_choice,
            qr_renderer=qr_renderer,
            actor=actor,
            limit=20,
        )

        if n == 0:
            print(f"No parcels found for fuel={fuel_type} with lean_eligibility={lean_choice}.")
        else:
            print(f"Issued {n} UPINs for fuel={fuel_type}, lean_eligibility={lean_choice}.")

    #-----------------------------------------------------------------
    #  We use this because issue_upin_from_parcel_row(...) 
    #  returns plaintext UPIN, buT QR content is based on 
    #  the stored hash string, consistent with current design.
    #-----------------------------------------------------------------
    
    def _get_active_upin_hash_for_account(self, account_number: str) -> str:
        """
        Return the upin_hash for the newest active UPIN row for an account_number.
        Raises if not found.
        """
        acct = (account_number or "").strip()
        self.cur_upin.execute(
            """
            SELECT upin_hash
            FROM upin
            WHERE account_number=? AND status='active'
            ORDER BY issued_at DESC
            LIMIT 1
            """,
            (acct,),
        )
        row = self.cur_upin.fetchone()
        if not row:
            raise RuntimeError(f"No active UPIN hash found for account_number={acct}")
        return row[0]
        
    #-------------------------------------------------------------------------
    #  Core helper: fetch 1 random parcel by eligibility (+ optional fuel)
    #------------------------------------------------------------------------
    
    def get_one_random_lean_parcel(self, lean_code: str, fuel_type: str = ""):
        """
        Return 1 random parcel row matching LEAN/LMF + optional fuel filter.
        Row layout matches issue_upin_from_parcel_row.
        """
        clean_lean = (lean_code or "").strip().upper()
        clean_fuel = (fuel_type or "").strip().upper()

        if clean_lean not in ("LEAN", "LMF"):
            raise ValueError("lean_code must be LEAN or LMF")

        q = """
            SELECT account_number,
                   is_residential,
                   normalized_address,
                   owner_1_name,
                   heating_fuel_description,
                   primary_land_use_code_description,
                   total_occupancy,
                   vision_id,
                   lean_eligibility
            FROM Assessment_L_Parcels
            WHERE is_residential = 'Y'
              AND UPPER(TRIM(lean_eligibility)) = ?
        """

        # occupancy rules
        if clean_lean == "LEAN":
            q += " AND total_occupancy BETWEEN 2 AND 4"
        else:
            q += " AND total_occupancy > 4"

        # optional fuel filter
        params = [clean_lean]
        if clean_fuel:
            q += " AND UPPER(TRIM(heating_fuel_description)) = ?"
            params.append(clean_fuel)

        q += " ORDER BY RANDOM() LIMIT 1"

        self.cur_master.execute(q, tuple(params))
        return self.cur_master.fetchone()
        
    #-------------------------------------------------------------------------
    #  Prompt method: Option 9 (single-record version of Option 10)
    #------------------------------------------------------------------------
        
    def issue_random_lean_upin_prompt(
        self,
        qr_renderer=None,
        actor: str = "cli",
    ) -> None:
        """
        Option 9: Single-record version of Option 10.

        Prompts user for:
          - eligibility type (LEAN | LMF)
          - optional fuel (Gas | Electric | Oil) or blank for any

        Issues exactly ONE UPIN from the matching pool.
        """
        try:
            lean_choice = input("Enter eligibility type (LEAN | LMF): ").strip().upper()
            if lean_choice not in ("LEAN", "LMF"):
                print("Invalid eligibility type. Please enter LEAN or LMF.")
                return

            fuel_type = input("Optional fuel filter (Gas | Electric | Oil) or press Enter for any: ").strip()
            # Normalize fuel to upper for query; allow blank
            fuel_clean = fuel_type.strip().upper()

            row = self.get_one_random_lean_parcel(lean_choice, fuel_clean)
            if not row:
                if fuel_clean:
                    print(f"No parcels found for lean_eligibility={lean_choice} with fuel={fuel_clean}.")
                else:
                    print(f"No parcels found for lean_eligibility={lean_choice}.")
                self.log_event(
                    "issue_one_lean",
                    actor,
                    f"lean={lean_choice} fuel={fuel_clean or 'ANY'} result=none_found",
                )
                return

            # Issue UPIN (your method returns 4 values now)
            upin_plain, acct, ratepayer_id, upin_hash = self.issue_upin_from_parcel_row(row, actor=actor)

            # Generate QR for the exact inserted row without any lookups
            if qr_renderer:
                fuel_row = row[4]
                vision_id = row[7]
                lean_row = row[8]
                qr_svg = qr_renderer(upin_hash, fuel_row, vision_id, lean_row)
                self.cur_upin.execute(
                    "UPDATE upin SET qr_svg = ? WHERE ratepayer_id = ?",
                    (qr_svg, ratepayer_id),
                )
                self.conn_upin.commit()

            print(f"Issued {lean_choice}-eligible UPIN {upin_plain} for account {acct}")
            self.log_event(
                "issue_one_lean",
                actor,
                f"lean={lean_choice} fuel={fuel_clean or 'ANY'} result=success account_number={acct} ratepayer_id={ratepayer_id}",
            )

        except Exception as e:
            print(f"Error issuing single LEAN/LMF UPIN: {e}")
            self.log_event("issue_one_lean", actor, f"result=error error={e}")


