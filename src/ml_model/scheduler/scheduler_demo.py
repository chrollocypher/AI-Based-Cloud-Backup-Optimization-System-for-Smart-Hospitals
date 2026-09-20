"""
Demonstration of the backup scheduling policy module.
"""
from scheduler import schedule_backups, InvalidInputError

def run_demo():
    print("--- Backup Scheduler Demo ---\n")
    
    # 1. Create sample records with different priorities and sizes
    sample_records = [
        {"record_id": "bck_001", "department": "Cardiology", "criticality": "HIGH", "priority": 3, "data_size_mb": 500.0},
        {"record_id": "bck_002", "department": "General Ward", "criticality": "LOW", "priority": 1, "data_size_mb": 800.0},
        {"record_id": "bck_003", "department": "ICU", "criticality": "CRITICAL", "priority": 4, "data_size_mb": 1200.0},
        {"record_id": "bck_004", "department": "Admin", "criticality": "MEDIUM", "priority": 2, "data_size_mb": 300.0},
        {"record_id": "bck_005", "department": "Emergency", "criticality": "CRITICAL", "priority": 4, "data_size_mb": 900.0},
        {"record_id": "bck_006", "department": "Pharmacy", "criticality": "HIGH", "priority": 3, "data_size_mb": 600.0},
    ]
    
    # 2. Set predicted capacity
    capacity_mb = 2500.0
    
    # 3. Run scheduler
    try:
        result = schedule_backups(sample_records, capacity_mb)
        
        # 4. Print results
        print("Backup Scheduling Result")
        print("------------------------")
        print(f"Predicted Capacity: {capacity_mb} MB\n")
        
        print("Scheduled Records:")
        for rec in result["scheduled_records"]:
            print(f"  - [{rec['priority']}] {rec['criticality']:<8} | Size: {rec['data_size_mb']:>6} MB | ID: {rec['record_id']}")
            
        print("\nDeferred Records:")
        for rec in result["deferred_records"]:
            print(f"  - [{rec['priority']}] {rec['criticality']:<8} | Size: {rec['data_size_mb']:>6} MB | ID: {rec['record_id']}")
            
        print(f"\nTotal Scheduled Volume: {result['scheduled_volume_mb']} MB")
        print(f"Remaining Capacity: {result['remaining_capacity_mb']} MB")
        
    except Exception as e:
        print(f"Error during scheduling: {e}")

    print("\n--- Validation Testing ---\n")
    
    # Test invalid inputs
    print("Testing negative capacity validation...")
    try:
        schedule_backups(sample_records, -100)
    except InvalidInputError as e:
        print(f"Successfully caught invalid capacity: {e}")
        
    print("\nTesting invalid record data_size_mb validation...")
    try:
        invalid_record = {"record_id": "err", "criticality": "LOW", "priority": 1, "data_size_mb": -50}
        schedule_backups([invalid_record], 1000.0)
    except InvalidInputError as e:
        print(f"Successfully caught invalid record size: {e}")

if __name__ == "__main__":
    run_demo()
