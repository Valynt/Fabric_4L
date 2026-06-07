import re

# Fix benchmark_governance.py
path = 'services/layer5-ground-truth/src/layer5_ground_truth/models/benchmark_governance.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the standalone __table_args__ = {"extend_existing": True} for BenchmarkDataset
# and add it to the tuple instead
old_pattern = '''    __tablename__ = "benchmark_datasets"
    __table_args__ = {"extend_existing": True}

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique benchmark identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Benchmark identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Human-readable benchmark name",
    )
    slug = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe slug for API references",
    )
    benchmark_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of benchmark — see BenchmarkType enum",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the benchmark",
    )

    # -------------------------------------------------------------------------
    # Version tracking
    # -------------------------------------------------------------------------
    current_version = Column(
        String(64),
        nullable=False,
        default="1.0.0",
        comment="Current approved version (semver)",
    )
    latest_version = Column(
        String(64),
        nullable=False,
        default="1.0.0",
        comment="Latest version (including pending)",
    )

    # -------------------------------------------------------------------------
    # Source metadata
    # -------------------------------------------------------------------------
    source_name = Column(
        String(128),
        nullable=False,
        comment="Name of the data source",
    )
    source_url = Column(
        Text,
        nullable=True,
        comment="URL or reference to the source",
    )
    source_type = Column(
        String(32),
        nullable=False,
        comment="Type of source (research, survey, internal, etc.)",
    )
    source_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date the source data was published or collected",
    )
    collection_methodology = Column(
        Text,
        nullable=True,
        comment="Description of data collection methodology",
    )

    # -------------------------------------------------------------------------
    # Confidence and quality
    # -------------------------------------------------------------------------
    confidence_level = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Confidence level in the data (high, medium, low)",
    )
    sample_size = Column(
        Integer,
        nullable=True,
        comment="Sample size of the benchmark data",
    )
    margin_of_error = Column(
        JSON,
        nullable=True,
        comment="Margin of error information",
    )
    data_quality_notes = Column(
        Text,
        nullable=True,
        comment="Notes on data quality and limitations",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this benchmark is active",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the benchmark was deprecated",
    )
    deprecation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for deprecation",
    )

    # -------------------------------------------------------------------------
    # Approval workflow integration
    # -------------------------------------------------------------------------
    approval_request_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Reference to current approval request (if pending)",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_by = Column(
        String(255),
        nullable=True,
        comment="User who created the benchmark",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    versions: Mapped[list["BenchmarkVersion"]] = relationship(
        "BenchmarkVersion",
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="BenchmarkVersion.version",
    )
    scopes: Mapped[list["BenchmarkScope"]] = relationship(
        "BenchmarkScope",
        back_populates="benchmark",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_benchmark_datasets_tenant_type",
            "tenant_id",
            "benchmark_type",
        ),
        Index(
            "ix_benchmark_datasets_tenant_slug",
            "tenant_id",
            "slug",
        ),
    )'''

new_pattern = '''    __tablename__ = "benchmark_datasets"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique benchmark identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Benchmark identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Human-readable benchmark name",
    )
    slug = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe slug for API references",
    )
    benchmark_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of benchmark — see BenchmarkType enum",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the benchmark",
    )

    # -------------------------------------------------------------------------
    # Version tracking
    # -------------------------------------------------------------------------
    current_version = Column(
        String(64),
        nullable=False,
        default="1.0.0",
        comment="Current approved version (semver)",
    )
    latest_version = Column(
        String(64),
        nullable=False,
        default="1.0.0",
        comment="Latest version (including pending)",
    )

    # -------------------------------------------------------------------------
    # Source metadata
    # -------------------------------------------------------------------------
    source_name = Column(
        String(128),
        nullable=False,
        comment="Name of the data source",
    )
    source_url = Column(
        Text,
        nullable=True,
        comment="URL or reference to the source",
    )
    source_type = Column(
        String(32),
        nullable=False,
        comment="Type of source (research, survey, internal, etc.)",
    )
    source_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date the source data was published or collected",
    )
    collection_methodology = Column(
        Text,
        nullable=True,
        comment="Description of data collection methodology",
    )

    # -------------------------------------------------------------------------
    # Confidence and quality
    # -------------------------------------------------------------------------
    confidence_level = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Confidence level in the data (high, medium, low)",
    )
    sample_size = Column(
        Integer,
        nullable=True,
        comment="Sample size of the benchmark data",
    )
    margin_of_error = Column(
        JSON,
        nullable=True,
        comment="Margin of error information",
    )
    data_quality_notes = Column(
        Text,
        nullable=True,
        comment="Notes on data quality and limitations",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this benchmark is active",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the benchmark was deprecated",
    )
    deprecation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for deprecation",
    )

    # -------------------------------------------------------------------------
    # Approval workflow integration
    # -------------------------------------------------------------------------
    approval_request_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Reference to current approval request (if pending)",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_by = Column(
        String(255),
        nullable=True,
        comment="User who created the benchmark",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    versions: Mapped[list["BenchmarkVersion"]] = relationship(
        "BenchmarkVersion",
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="BenchmarkVersion.version",
    )
    scopes: Mapped[list["BenchmarkScope"]] = relationship(
        "BenchmarkScope",
        back_populates="benchmark",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_benchmark_datasets_tenant_type",
            "tenant_id",
            "benchmark_type",
        ),
        Index(
            "ix_benchmark_datasets_tenant_slug",
            "tenant_id",
            "slug",
        ),
        {"extend_existing": True},
    )'''

if old_pattern in text:
    text = text.replace(old_pattern, new_pattern, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    print('Fixed benchmark_governance.py')
else:
    print('Pattern not found in benchmark_governance.py')

# Fix policy_governance.py
path2 = 'services/layer5-ground-truth/src/layer5_ground_truth/models/policy_governance.py'
with open(path2, 'r', encoding='utf-8') as f:
    text2 = f.read()

old_policy = '''    __tablename__ = "policy_rules"
    __table_args__ = {"extend_existing": True}

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
    )
    policy_id = Column(
        UUID,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Rule details
    # -------------------------------------------------------------------------
    rule_name = Column(
        String(128),
        nullable=False,
        comment="Human-readable rule name",
    )
    rule_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Order of rule evaluation (lower = earlier)",
    )
    target_field = Column(
        String(128),
        nullable=False,
        comment="Field to evaluate (e.g., 'confidence', 'sample_size')",
    )
    operator = Column(
        String(32),
        nullable=False,
        comment="Comparison operator — see RuleOperator enum",
    )
    expected_value = Column(
        JSON,
        nullable=False,
        comment="Expected value for comparison",
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message when rule fails",
    )

    # -------------------------------------------------------------------------
    # Rule configuration
    # -------------------------------------------------------------------------
    is_blocking = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this rule blocks the operation when it fails",
    )
    severity = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Severity level for this rule",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    description = Column(
        Text,
        nullable=True,
        comment="Description of the rule",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    policy: Mapped["Policy"] = relationship(
        "Policy",
        back_populates="rules",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_policy_rules_tenant_policy",
            "tenant_id",
            "policy_id",
        ),
        Index(
            "ix_policy_rules_policy_order",
            "policy_id",
            "rule_order",
        ),
    )'''

new_policy = '''    __tablename__ = "policy_rules"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
    )
    policy_id = Column(
        UUID,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Rule details
    # -------------------------------------------------------------------------
    rule_name = Column(
        String(128),
        nullable=False,
        comment="Human-readable rule name",
    )
    rule_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Order of rule evaluation (lower = earlier)",
    )
    target_field = Column(
        String(128),
        nullable=False,
        comment="Field to evaluate (e.g., 'confidence', 'sample_size')",
    )
    operator = Column(
        String(32),
        nullable=False,
        comment="Comparison operator — see RuleOperator enum",
    )
    expected_value = Column(
        JSON,
        nullable=False,
        comment="Expected value for comparison",
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message when rule fails",
    )

    # -------------------------------------------------------------------------
    # Rule configuration
    # -------------------------------------------------------------------------
    is_blocking = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this rule blocks the operation when it fails",
    )
    severity = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Severity level for this rule",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    description = Column(
        Text,
        nullable=True,
        comment="Description of the rule",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    policy: Mapped["Policy"] = relationship(
        "Policy",
        back_populates="rules",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_policy_rules_tenant_policy",
            "tenant_id",
            "policy_id",
        ),
        Index(
            "ix_policy_rules_policy_order",
            "policy_id",
            "rule_order",
        ),
        {"extend_existing": True},
    )'''

if old_policy in text2:
    text2 = text2.replace(old_policy, new_policy, 1)
    with open(path2, 'w', encoding='utf-8', newline='') as f:
        f.write(text2)
    print('Fixed policy_governance.py')
else:
    print('Pattern not found in policy_governance.py')
