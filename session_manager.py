#!/usr/bin/env python3
"""
Session Manager Utility
Manages country-specific session folders and provides utilities for session management.
"""

import os
import json
from datetime import datetime
from telegram_otp import session_manager
from config import SESSIONS_DIR

def list_all_sessions():
    """List all sessions organized by country"""
    sessions_by_country = session_manager.list_country_sessions()
    
    if not sessions_by_country:
        print("📁 No sessions found")
        return
    
    print("📊 Session Overview by Country:")
    print("=" * 50)
    
    total_sessions = 0
    for country_code, sessions in sessions_by_country.items():
        print(f"\n🌍 Country: {country_code}")
        print(f"   📱 Sessions: {len(sessions)}")
        
        for session in sessions:
            phone = session['phone_number']
            size = session.get('size', 0)
            modified = session.get('modified', 0)
            
            if modified:
                mod_time = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
            else:
                mod_time = "Unknown"
            
            print(f"   • {phone} ({size} bytes, modified: {mod_time})")
        
        total_sessions += len(sessions)
    
    print(f"\n📈 Total Sessions: {total_sessions}")

def get_country_stats():
    """Get statistics for each country"""
    sessions_by_country = session_manager.list_country_sessions()
    
    if not sessions_by_country:
        print("📁 No sessions found")
        return
    
    print("📊 Country Statistics:")
    print("=" * 50)
    
    for country_code, sessions in sessions_by_country.items():
        total_size = sum(session.get('size', 0) for session in sessions)
        avg_size = total_size / len(sessions) if sessions else 0
        
        print(f"\n🌍 {country_code}:")
        print(f"   📱 Sessions: {len(sessions)}")
        print(f"   💾 Total Size: {total_size:,} bytes")
        print(f"   📊 Average Size: {avg_size:.0f} bytes")

def migrate_legacy_sessions():
    """Migrate legacy sessions from root directory to country folders"""
    if not os.path.exists(SESSIONS_DIR):
        print("📁 Sessions directory does not exist")
        return
    
    migrated = 0
    failed = 0
    
    for item in os.listdir(SESSIONS_DIR):
        if item.endswith('.session'):
            phone_number = item.replace('.session', '')
            legacy_path = os.path.join(SESSIONS_DIR, item)
            
            # Get the proper country-specific path
            session_info = session_manager.get_session_info(phone_number)
            new_path = session_info['session_path']
            
            # Skip if already in correct location
            if os.path.dirname(legacy_path) == os.path.dirname(new_path):
                continue
            
            try:
                # Create country directory if it doesn't exist
                country_dir = os.path.dirname(new_path)
                os.makedirs(country_dir, exist_ok=True)
                
                # Move the file
                os.rename(legacy_path, new_path)
                print(f"✅ Migrated: {phone_number} -> {country_dir}")
                migrated += 1
                
            except Exception as e:
                print(f"❌ Failed to migrate {phone_number}: {e}")
                failed += 1
    
    print(f"\n📊 Migration Complete:")
    print(f"   ✅ Migrated: {migrated}")
    print(f"   ❌ Failed: {failed}")

def cleanup_empty_folders():
    """Remove empty country folders"""
    if not os.path.exists(SESSIONS_DIR):
        return
    
    removed = 0
    
    for item in os.listdir(SESSIONS_DIR):
        item_path = os.path.join(SESSIONS_DIR, item)
        
        if os.path.isdir(item_path):
            # Check if folder is empty
            if not os.listdir(item_path):
                try:
                    os.rmdir(item_path)
                    print(f"🗑️ Removed empty folder: {item}")
                    removed += 1
                except Exception as e:
                    print(f"❌ Failed to remove folder {item}: {e}")
    
    print(f"\n📊 Cleanup Complete: {removed} empty folders removed")

def export_session_info():
    """Export session information to JSON file"""
    sessions_by_country = session_manager.list_country_sessions()
    
    export_data = {
        "export_time": datetime.now().isoformat(),
        "total_sessions": sum(len(sessions) for sessions in sessions_by_country.values()),
        "countries": {}
    }
    
    for country_code, sessions in sessions_by_country.items():
        export_data["countries"][country_code] = {
            "session_count": len(sessions),
            "sessions": []
        }
        
        for session in sessions:
            session_info = {
                "phone_number": session['phone_number'],
                "size": session.get('size', 0),
                "modified": session.get('modified', 0),
                "created": session.get('created', 0),
                "path": session['session_path']
            }
            
            if session.get('modified'):
                session_info['modified_date'] = datetime.fromtimestamp(session['modified']).isoformat()
            if session.get('created'):
                session_info['created_date'] = datetime.fromtimestamp(session['created']).isoformat()
            
            export_data["countries"][country_code]["sessions"].append(session_info)
    
    # Save to file
    filename = f"sessions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"📄 Session information exported to: {filename}")

def main():
    """Main function to handle command line arguments"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python session_manager.py <command>")
        print("\nCommands:")
        print("  list          - List all sessions by country")
        print("  stats         - Show country statistics")
        print("  migrate       - Migrate legacy sessions to country folders")
        print("  cleanup       - Remove empty country folders")
        print("  export        - Export session information to JSON")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_all_sessions()
    elif command == "stats":
        get_country_stats()
    elif command == "migrate":
        migrate_legacy_sessions()
    elif command == "cleanup":
        cleanup_empty_folders()
    elif command == "export":
        export_session_info()
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()