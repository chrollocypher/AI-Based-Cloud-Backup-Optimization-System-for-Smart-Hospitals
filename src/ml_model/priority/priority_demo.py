"""
Demonstration of the priority policy module.
"""
from priority_policy import (
    assign_priority, 
    sort_records_by_priority, 
    validate_criticality,
    InvalidCriticalityError
)

def run_demo():
    print("--- Priority Policy Demo ---\n")
    
    # 1. Create sample records
    sample_records = [
        {"id": "bck_001", "department": "Cardiology", "criticality": "HIGH"},
        {"id": "bck_002", "department": "General Ward", "criticality": "LOW"},
        {"id": "bck_003", "department": "ICU", "criticality": "CRITICAL"},
        {"id": "bck_004", "department": "Admin", "criticality": "MEDIUM"},
    ]
    
    print("Original Records:")
    for rec in sample_records:
        print(rec)
    print("\n")
    
    # 2. Sort records by priority descending
    sorted_records = sort_records_by_priority(sample_records)
    
    # 3. Print resulting order clearly
    print("Backup Priority Order")
    print("---------------------")
    for i, record in enumerate(sorted_records, 1):
        print(f"{i}. {record['criticality']:<8} | Priority: {record['priority']} (ID: {record['id']})")
        
    print("\n--- Validation Testing ---\n")
    
    # 4. Test invalid criticality rejection
    invalid_criticality = "UNKNOWN_LEVEL"
    print(f"Testing invalid criticality: '{invalid_criticality}'")
    try:
        validate_criticality(invalid_criticality)
    except InvalidCriticalityError as e:
        print(f"Successfully caught invalid criticality: {e}")

if __name__ == "__main__":
    run_demo()
