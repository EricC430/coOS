import os
import shutil
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# --- Config ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "coos.db"
LOG_DIR = PROJECT_ROOT / "logs"
ENV_PATH = PROJECT_ROOT / ".env"

def fresh_start():
    print("🚀 coOS Fresh Start - Data Cleanup Tool")
    print("---------------------------------------")
    
    # Load .env
    load_dotenv(ENV_PATH)
    
    # Try to extract current user ID from DB before deleting it
    db_user_id = None
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT id FROM users LIMIT 1")
            row = cur.fetchone()
            if row:
                db_user_id = row[0]
            conn.close()
        except Exception:
            pass
    
    # Use ENV if DB failed or doesn't exist
    current_user_id = db_user_id or os.getenv("CURRENT_USER_ID")
    
    # 1. Close backend warning
    print("⚠️  請確保已停止 pnpm dev:backend 與桌面端程式。")
    
    # 2. Supabase Cleanup (Do this BEFORE deleting local DB to ensure we have the ID)
    supabase_db_url = os.getenv("SUPABASE_DB_URL")
    
    if supabase_db_url:
        print(f"🌐 偵測到 Supabase 連線。")
        if current_user_id:
            print(f"🗑️  正在清理使用者 {current_user_id} 的雲端資料...")
            try:
                import psycopg2
                conn = psycopg2.connect(supabase_db_url)
                cur = conn.cursor()
                
                # Tables linked via role_id
                cur.execute("SELECT id FROM roles WHERE user_id = %s", (current_user_id,))
                role_ids = [row[0] for row in cur.fetchall()]
                
                if role_ids:
                    role_linked_tables = [
                        "xp_ledger", "role_projects", "role_settings", 
                        "daily_reflection_segments", "daily_reflections", 
                        "goals", "promises", "ai_experts"
                    ]
                    for table in role_linked_tables:
                        query = f"DELETE FROM {table} WHERE role_id IN %s"
                        cur.execute(query, (tuple(role_ids),))
                        print(f"   - 已清理 {table} ({cur.rowcount} 筆)")

                # User direct records
                cur.execute("DELETE FROM daily_reflections WHERE user_id = %s", (current_user_id,))
                cur.execute("DELETE FROM roles WHERE user_id = %s", (current_user_id,))
                cur.execute("DELETE FROM user_badges WHERE user_id = %s", (current_user_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (current_user_id,))
                
                conn.commit()
                cur.close()
                conn.close()
                print("✅ 雲端資料清理完成。")
            except Exception as e:
                print(f"❌ 雲端資料清理失敗: {e}")
        else:
            print("ℹ️  找不到有效的 User ID，略過雲端清理。")
    
    # 3. Delete SQLite DB
    if DB_PATH.exists():
        print(f"🗑️  正在刪除本地資料庫: {DB_PATH}")
        try:
            os.remove(DB_PATH)
            print("✅ 本地資料庫已刪除。")
        except Exception as e:
            print(f"❌ 無法刪除本地資料庫: {e} (可能程式仍在執行中)")
        
    # 4. Clear logs

    print("---------------------------------------")
    print("✨ 清理完成！現在您可以重新啟動系統，體驗全新的使用者流程：")
    print("1. pnpm dev:backend")
    print("2. pnpm --filter @coos/desktop tauri dev")

if __name__ == "__main__":
    fresh_start()
