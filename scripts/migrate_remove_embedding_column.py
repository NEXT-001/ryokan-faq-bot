"""
PostgreSQL Schema Migration: Remove embedding column from faq_data table
scripts/migrate_remove_embedding_column.py

This script removes the embedding column from faq_data table since we now use
the separate faq_embeddings table for embedding storage.
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


def remove_embedding_column():
    """Remove embedding column from faq_data table if it exists"""
    try:
        print(f"[MIGRATION] Checking database type: {DB_TYPE}")
        
        # Check if embedding column exists
        if not check_column_exists('faq_data', 'embedding'):
            print("✅ Embedding column does not exist in faq_data table")
            return True
        
        print("🔧 Removing embedding column from faq_data table...")
        
        with get_cursor() as cursor:
            if DB_TYPE == "postgresql":
                alter_query = "ALTER TABLE faq_data DROP COLUMN IF EXISTS embedding"
            else:
                # SQLite doesn't support DROP COLUMN directly, need to recreate table
                # First, get current table schema without embedding column
                cursor.execute("PRAGMA table_info(faq_data)")
                columns = cursor.fetchall()
                
                # Filter out embedding column and recreate column definitions
                new_columns = []
                for col in columns:
                    if col[1] != 'embedding':  # col[1] is column name
                        col_def = f"{col[1]} {col[2]}"  # name + type
                        if col[3]:  # NOT NULL
                            col_def += " NOT NULL"
                        if col[4] is not None:  # DEFAULT value
                            col_def += f" DEFAULT {col[4]}"
                        if col[5]:  # PRIMARY KEY
                            col_def += " PRIMARY KEY"
                        new_columns.append(col_def)
                
                # Create new table without embedding column
                new_table_sql = f"CREATE TABLE faq_data_new ({', '.join(new_columns)})"
                cursor.execute(new_table_sql)
                
                # Copy data (excluding embedding column)
                copy_columns = [col[1] for col in columns if col[1] != 'embedding']
                copy_sql = f"""
                    INSERT INTO faq_data_new ({', '.join(copy_columns)})
                    SELECT {', '.join(copy_columns)} FROM faq_data
                """
                cursor.execute(copy_sql)
                
                # Drop old table and rename new one
                cursor.execute("DROP TABLE faq_data")
                cursor.execute("ALTER TABLE faq_data_new RENAME TO faq_data")
            
            if DB_TYPE == "postgresql":
                cursor.execute(alter_query)
            
        print("✅ Successfully removed embedding column from faq_data table")
        return True
        
    except Exception as e:
        print(f"❌ Error removing embedding column: {e}")
        return False


def main():
    """Main migration function"""
    print("🚀 Starting embedding column removal migration...")
    
    try:
        success = remove_embedding_column()
        
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