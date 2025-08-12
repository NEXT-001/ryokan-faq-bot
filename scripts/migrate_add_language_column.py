"""
PostgreSQL Schema Migration: Add language column to faq_data table
scripts/migrate_add_language_column.py

This script adds the missing language column to existing faq_data tables
that don't have it.
"""
import sys
import os

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_cursor, DB_TYPE


def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        with get_cursor() as cursor:
            if DB_TYPE == "postgresql":
                query = """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                """
                cursor.execute(query, (table_name, column_name))
                result = cursor.fetchone()
                return result is not None
            else:
                query = f"PRAGMA table_info({table_name})"
                cursor.execute(query)
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]  # column_name is at index 1
                return column_name in column_names
                
    except Exception as e:
        print(f"Error checking column existence: {e}")
        return False


def add_language_column():
    """Add language column to faq_data table if it doesn't exist"""
    try:
        print(f"[MIGRATION] Checking database type: {DB_TYPE}")
        
        # Check if language column already exists
        if check_column_exists('faq_data', 'language'):
            print("✅ Language column already exists in faq_data table")
            return True
        
        print("🔧 Adding language column to faq_data table...")
        
        with get_cursor() as cursor:
            if DB_TYPE == "postgresql":
                alter_query = "ALTER TABLE faq_data ADD COLUMN language TEXT DEFAULT 'ja'"
            else:
                alter_query = "ALTER TABLE faq_data ADD COLUMN language TEXT DEFAULT 'ja'"
            
            cursor.execute(alter_query)
            
        print("✅ Successfully added language column to faq_data table")
        return True
        
    except Exception as e:
        print(f"❌ Error adding language column: {e}")
        return False


def main():
    """Main migration function"""
    print("🚀 Starting language column migration...")
    
    try:
        success = add_language_column()
        
        if success:
            print("🎉 Migration completed successfully!")
        else:
            print("❌ Migration failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)