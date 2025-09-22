#!/usr/bin/env python3
"""
Database Manager - Single Source of Truth for Survey DAG Database

Eliminates confusion over working files by establishing:
- ONE working database: surveys_db/current_database.pkl
- Snapshot system for backups
- Clear load/save/snapshot operations

Usage:
    from database_manager import DatabaseManager
    
    db = DatabaseManager()
    graph = db.load_graph()
    # ... modify graph ...
    db.save_graph(graph)
    db.create_snapshot("phase3_complete")
"""

import pickle
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import networkx as nx


class DatabaseManager:
    """Manages single source of truth for survey DAG database."""
    
    def __init__(self, project_root: Path = None):
        """Initialize database manager."""
        if project_root is None:
            # Go up from core/ to project root
            project_root = Path(__file__).parent.parent
        
        self.project_root = project_root
        self.db_dir = project_root / "surveys_db"
        self.snapshots_dir = self.db_dir / "snapshots"
        self.exports_dir = self.db_dir / "exports"
        
        # SINGLE source of truth
        self.current_db_path = self.db_dir / "current_database.pkl"
        
        # Ensure directories exist
        self.db_dir.mkdir(exist_ok=True)
        self.snapshots_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        
        print(f"Database Manager initialized")
        print(f"Working database: {self.current_db_path}")
        print(f"Snapshots: {self.snapshots_dir}")
        print(f"Exports: {self.exports_dir}")
    
    def load_graph(self) -> nx.DiGraph:
        """Load the current working database."""
        if not self.current_db_path.exists():
            raise FileNotFoundError(
                f"No current database found at {self.current_db_path}. "
                f"Run setup_current_database() first."
            )
        
        with open(self.current_db_path, 'rb') as f:
            data = pickle.load(f)
        
        # Handle different data types
        if hasattr(data, 'number_of_nodes'):  # Already a NetworkX graph
            graph = data
        elif hasattr(data, 'graph'):  # SchemaCompliantExtractor object
            graph = data.graph
        else:
            raise TypeError(f"Unknown database format: {type(data)}")
        
        print(f"✓ Loaded current database: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return graph
    
    def save_graph(self, graph: nx.DiGraph) -> None:
        """Save graph as the current working database."""
        # For now, save just the graph. Later we can enhance to save full extractor
        with open(self.current_db_path, 'wb') as f:
            pickle.dump(graph, f)
        
        print(f"✓ Saved current database: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    
    def create_snapshot(self, snapshot_name: str) -> Path:
        """Create a named snapshot of current database."""
        if not self.current_db_path.exists():
            raise FileNotFoundError("No current database to snapshot")
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"{snapshot_name}_{timestamp}.pkl"
        snapshot_path = self.snapshots_dir / snapshot_filename
        
        shutil.copy(self.current_db_path, snapshot_path)
        print(f"✓ Created snapshot: {snapshot_path}")
        return snapshot_path
    
    def restore_from_snapshot(self, snapshot_name: str) -> None:
        """Restore current database from a snapshot."""
        # Find most recent snapshot with this name
        matching_snapshots = list(self.snapshots_dir.glob(f"{snapshot_name}_*.pkl"))
        if not matching_snapshots:
            raise FileNotFoundError(f"No snapshots found matching '{snapshot_name}'")
        
        # Get most recent
        latest_snapshot = max(matching_snapshots, key=lambda p: p.stat().st_mtime)
        
        # Create backup of current before restore
        if self.current_db_path.exists():
            backup_name = f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.create_snapshot(backup_name)
        
        # Restore
        shutil.copy(latest_snapshot, self.current_db_path)
        print(f"✓ Restored from snapshot: {latest_snapshot}")
    
    def list_snapshots(self) -> Dict[str, Any]:
        """List all available snapshots."""
        snapshots = []
        for snapshot_path in self.snapshots_dir.glob("*.pkl"):
            stat = snapshot_path.stat()
            snapshots.append({
                'name': snapshot_path.name,
                'size_mb': stat.st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(snapshot_path)
            })
        
        # Sort by creation time (newest first)
        snapshots.sort(key=lambda x: x['created'], reverse=True)
        
        return {
            'count': len(snapshots),
            'snapshots': snapshots
        }
    
    def setup_current_database(self, force: bool = False) -> None:
        """Setup current database from best available source."""
        if self.current_db_path.exists() and not force:
            print(f"✓ Current database already exists: {self.current_db_path}")
            return
        
        # Look for best source in priority order
        source_candidates = [
            self.db_dir / "phase3_output" / "phase3_fully_fixed_database.pkl",
            self.db_dir / "phase3_output" / "phase3_fixed_database.pkl", 
            self.db_dir / "phase3_output" / "phase3_working_database.pkl",
            self.db_dir / "htops_graph_database.pkl",
            self.db_dir / "htops_consolidated_database.pkl"
        ]
        
        source_path = None
        for candidate in source_candidates:
            if candidate.exists():
                source_path = candidate
                break
        
        if source_path is None:
            raise FileNotFoundError(
                f"No source database found. Checked:\n" + 
                "\n".join(f"  {p}" for p in source_candidates)
            )
        
        # Copy to current database
        shutil.copy(source_path, self.current_db_path)
        print(f"✓ Setup current database from: {source_path}")
        
        # Create snapshot of this initial state
        self.create_snapshot("initial_setup")
    
    def cleanup_old_databases(self, archive: bool = True) -> None:
        """Clean up old scattered database files."""
        old_files = [
            self.db_dir / "phase3_output" / "phase3_database.pkl",
            self.db_dir / "phase3_output" / "phase3_working_database.pkl",
            self.db_dir / "phase3_output" / "phase3_fixed_database.pkl",
            self.db_dir / "htops_graph_database.pkl",
            self.db_dir / "htops_consolidated_database.pkl"
        ]
        
        cleaned = []
        for old_file in old_files:
            if old_file.exists():
                if archive:
                    # Move to snapshots with descriptive name
                    archive_name = f"legacy_{old_file.stem}_{datetime.now().strftime('%Y%m%d')}.pkl"
                    archive_path = self.snapshots_dir / archive_name
                    shutil.move(old_file, archive_path)
                    cleaned.append(f"Archived: {old_file} -> {archive_path}")
                else:
                    old_file.unlink()
                    cleaned.append(f"Deleted: {old_file}")
        
        if cleaned:
            print("Database cleanup completed:")
            for action in cleaned:
                print(f"  {action}")
        else:
            print("No old database files found to clean up")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current database manager status."""
        status = {
            'current_database': {
                'exists': self.current_db_path.exists(),
                'path': str(self.current_db_path)
            },
            'snapshots': self.list_snapshots(),
            'directories': {
                'db_dir': str(self.db_dir),
                'snapshots_dir': str(self.snapshots_dir),
                'exports_dir': str(self.exports_dir)
            }
        }
        
        if status['current_database']['exists']:
            stat = self.current_db_path.stat()
            status['current_database'].update({
                'size_mb': stat.st_size / (1024 * 1024),
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return status
    
    def print_status(self) -> None:
        """Print formatted status information."""
        status = self.get_status()
        
        print("\nDatabase Manager Status")
        print("=" * 30)
        
        # Current database
        current = status['current_database']
        if current['exists']:
            print(f"✓ Current Database: {current['path']}")
            print(f"  Size: {current['size_mb']:.2f} MB")
            print(f"  Modified: {current['last_modified']}")
        else:
            print(f"✗ No current database at: {current['path']}")
        
        # Snapshots
        snapshots = status['snapshots']
        print(f"\nSnapshots: {snapshots['count']} available")
        if snapshots['count'] > 0:
            for snapshot in snapshots['snapshots'][:3]:  # Show latest 3
                print(f"  {snapshot['name']} ({snapshot['size_mb']:.1f} MB, {snapshot['created'][:16]})")
            if snapshots['count'] > 3:
                print(f"  ... and {snapshots['count'] - 3} more")


def main():
    """Command line interface for database management."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python database_manager.py <command>")
        print("Commands:")
        print("  setup     - Setup current database from best available source")
        print("  status    - Show database manager status")
        print("  snapshot <name> - Create named snapshot")
        print("  restore <name>  - Restore from snapshot")
        print("  cleanup   - Clean up old database files")
        print("  list      - List all snapshots")
        return
    
    db = DatabaseManager()
    command = sys.argv[1].lower()
    
    if command == "setup":
        force = "--force" in sys.argv
        db.setup_current_database(force=force)
    
    elif command == "status":
        db.print_status()
    
    elif command == "snapshot":
        if len(sys.argv) < 3:
            print("Usage: python database_manager.py snapshot <name>")
            return
        snapshot_name = sys.argv[2]
        db.create_snapshot(snapshot_name)
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python database_manager.py restore <name>")
            return
        snapshot_name = sys.argv[2]
        db.restore_from_snapshot(snapshot_name)
    
    elif command == "cleanup":
        archive = "--no-archive" not in sys.argv
        db.cleanup_old_databases(archive=archive)
    
    elif command == "list":
        snapshots = db.list_snapshots()
        print(f"\nAvailable Snapshots ({snapshots['count']})")
        print("-" * 50)
        for snapshot in snapshots['snapshots']:
            print(f"{snapshot['name']:<40} {snapshot['size_mb']:>6.1f} MB  {snapshot['created'][:16]}")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
