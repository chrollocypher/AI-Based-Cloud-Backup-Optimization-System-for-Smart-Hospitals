from enum import Enum


class StorageTier(str, Enum):
    """Concrete AWS S3 storage classes."""
    STANDARD = "STANDARD"
    STANDARD_IA = "STANDARD_IA"
    GLACIER_FLEXIBLE = "GLACIER"
    GLACIER_DEEP_ARCHIVE = "DEEP_ARCHIVE"


class TierLabel(str, Enum):
    """Internal high-level business tier classifications."""
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    ARCHIVE = "ARCHIVE"


def map_tier_label_to_aws_class(tier_label: str) -> StorageTier:
    """Explicit deterministic mapping from business tier labels to AWS S3 storage classes."""
    normalized = str(tier_label).strip().upper()
    mapping = {
        TierLabel.HOT.value: StorageTier.STANDARD,
        TierLabel.WARM.value: StorageTier.STANDARD_IA,
        TierLabel.COLD.value: StorageTier.GLACIER_FLEXIBLE,
        TierLabel.ARCHIVE.value: StorageTier.GLACIER_DEEP_ARCHIVE,
        # Direct class mappings
        "STANDARD": StorageTier.STANDARD,
        "STANDARD_IA": StorageTier.STANDARD_IA,
        "GLACIER": StorageTier.GLACIER_FLEXIBLE,
        "GLACIER_FLEXIBLE": StorageTier.GLACIER_FLEXIBLE,
        "DEEP_ARCHIVE": StorageTier.GLACIER_DEEP_ARCHIVE,
    }
    if normalized not in mapping:
        raise ValueError(f"Unknown tier label '{tier_label}'. Allowed: {list(mapping.keys())}")
    return mapping[normalized]


class Criticality(str, Enum):
    """Clinical record criticality levels."""
    CRITICAL = "CRITICAL"  # Weight: 4
    HIGH = "HIGH"          # Weight: 3
    MEDIUM = "MEDIUM"      # Weight: 2
    LOW = "LOW"            # Weight: 1


CRITICALITY_WEIGHTS = {
    Criticality.CRITICAL.value: 4,
    Criticality.HIGH.value: 3,
    Criticality.MEDIUM.value: 2,
    Criticality.LOW.value: 1,
}


class AccessType(str, Enum):
    """EHR access operation types."""
    READ = "READ"
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    RETRIEVE = "RETRIEVE"
    BACKUP = "BACKUP"


class BackupStatus(str, Enum):
    """EHR backup execution lifecycle status."""
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
