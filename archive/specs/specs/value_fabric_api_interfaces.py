"""
Value Fabric SaaS Platform - API Interface Specifications
=========================================================

This module defines the REST API endpoints for the Value Fabric platform.

API Categories:
1. Ontology Management - CRUD operations for ontology schema
2. Extraction Jobs - Submit and monitor extraction operations
3. Entity Management - Search, retrieve, and update entities
4. Validation Reporting - Access validation results and metrics
5. Reference Model Integration - Manage industry model mappings
6. Knowledge Graph Export - Export RDF/OWL data
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


# =============================================================================
# COMMON DATA TYPES
# =============================================================================

@dataclass
class APIResponse:
    """Standard API response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: str = ""
    pagination: Optional[Dict[str, Any]] = None


@dataclass
class PaginationParams:
    """Pagination parameters for list endpoints."""
    page: int = 1
    page_size: int = 50
    sort_by: Optional[str] = None
    sort_order: str = "asc"  # asc, desc


@dataclass
class FilterParams:
    """Filter parameters for search endpoints."""
    entity_types: Optional[List[str]] = None
    confidence_min: Optional[float] = None
    confidence_max: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    source_id: Optional[str] = None
    keywords: Optional[List[str]] = None


# =============================================================================
# 1. ONTOLOGY MANAGEMENT API
# =============================================================================

class OntologyManagementAPI:
    """
    API endpoints for managing the Value Fabric ontology schema.
    
    Base Path: /api/v1/ontology
    """
    
    # -------------------------------------------------------------------------
    # GET /api/v1/ontology/classes
    # -------------------------------------------------------------------------
    LIST_CLASSES = {
        "method": "GET",
        "path": "/api/v1/ontology/classes",
        "description": "List all ontology classes",
        "parameters": {
            "query": {
                "includeAbstract": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include abstract classes"
                },
                "includeDeprecated": {
                    "type": "boolean", 
                    "default": False,
                    "description": "Include deprecated classes"
                }
            }
        },
        "responses": {
            "200": {
                "description": "List of ontology classes",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entityType": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "parentClasses": {"type": "array", "items": {"type": "string"}},
                            "propertyCount": {"type": "integer"},
                            "isAbstract": {"type": "boolean"}
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/ontology/classes/{entityType}
    # -------------------------------------------------------------------------
    GET_CLASS = {
        "method": "GET",
        "path": "/api/v1/ontology/classes/{entityType}",
        "description": "Get detailed definition of an ontology class",
        "parameters": {
            "path": {
                "entityType": {
                    "type": "string",
                    "required": True,
                    "description": "Entity type identifier",
                    "enum": ["Capability", "UseCase", "Persona", "ValueDriver", 
                            "Product", "Feature", "Process", "Activity"]
                }
            }
        },
        "responses": {
            "200": {
                "description": "Class definition",
                "schema": {
                    "type": "object",
                    "properties": {
                        "entityType": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "parentClasses": {"type": "array", "items": {"type": "string"}},
                        "properties": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "required": {"type": "boolean"},
                                    "cardinalityMin": {"type": "integer"},
                                    "cardinalityMax": {"type": "integer"},
                                    "description": {"type": "string"},
                                    "examples": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "allowedRelationships": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "404": {"description": "Class not found"}
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/ontology/relationships
    # -------------------------------------------------------------------------
    LIST_RELATIONSHIPS = {
        "method": "GET",
        "path": "/api/v1/ontology/relationships",
        "description": "List all relationship types with constraints",
        "parameters": {
            "query": {
                "domainType": {
                    "type": "string",
                    "description": "Filter by domain entity type"
                },
                "rangeType": {
                    "type": "string",
                    "description": "Filter by range entity type"
                }
            }
        },
        "responses": {
            "200": {
                "description": "List of relationship types",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "relationshipType": {"type": "string"},
                            "domain": {"type": "array", "items": {"type": "string"}},
                            "range": {"type": "array", "items": {"type": "string"}},
                            "cardinalityMin": {"type": "integer"},
                            "cardinalityMax": {"type": "integer"},
                            "inverseProperty": {"type": "string"},
                            "transitive": {"type": "boolean"},
                            "symmetric": {"type": "boolean"}
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # POST /api/v1/ontology/classes
    # -------------------------------------------------------------------------
    CREATE_CLASS = {
        "method": "POST",
        "path": "/api/v1/ontology/classes",
        "description": "Create a new ontology class (admin only)",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["entityType", "name", "description"],
                        "properties": {
                            "entityType": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "parentClasses": {"type": "array", "items": {"type": "string"}},
                            "properties": {"type": "object"},
                            "allowedRelationships": {"type": "array", "items": {"type": "string"}},
                            "isAbstract": {"type": "boolean"}
                        }
                    }
                }
            }
        },
        "responses": {
            "201": {"description": "Class created successfully"},
            "400": {"description": "Invalid class definition"},
            "403": {"description": "Admin access required"}
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/ontology/export
    # -------------------------------------------------------------------------
    EXPORT_ONTOLOGY = {
        "method": "GET",
        "path": "/api/v1/ontology/export",
        "description": "Export ontology schema in various formats",
        "parameters": {
            "query": {
                "format": {
                    "type": "string",
                    "default": "json",
                    "enum": ["json", "owl", "turtle", "jsonld"],
                    "description": "Export format"
                },
                "includeInstances": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include instance data"
                }
            }
        },
        "responses": {
            "200": {
                "description": "Ontology export",
                "content": {
                    "application/json": {"schema": {"type": "object"}},
                    "text/turtle": {"schema": {"type": "string"}},
                    "application/ld+json": {"schema": {"type": "object"}},
                    "application/rdf+xml": {"schema": {"type": "string"}}
                }
            }
        }
    }


# =============================================================================
# 2. EXTRACTION JOB API
# =============================================================================

class ExtractionJobAPI:
    """
    API endpoints for submitting and monitoring extraction jobs.
    
    Base Path: /api/v1/extraction
    """
    
    # -------------------------------------------------------------------------
    # POST /api/v1/extraction/jobs
    # -------------------------------------------------------------------------
    SUBMIT_JOB = {
        "method": "POST",
        "path": "/api/v1/extraction/jobs",
        "description": "Submit a new extraction job",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["sourceId"],
                        "properties": {
                            "sourceId": {
                                "type": "string",
                                "description": "Identifier of pre-ingested source document"
                            },
                            "targetEntityTypes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Entity types to extract (default: all)"
                            },
                            "configuration": {
                                "type": "object",
                                "properties": {
                                    "similarityThreshold": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                        "default": 0.85
                                    },
                                    "confidenceThreshold": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                        "default": 0.5
                                    },
                                    "enableCoreferenceResolution": {
                                        "type": "boolean",
                                        "default": True
                                    },
                                    "enableEntailmentValidation": {
                                        "type": "boolean",
                                        "default": True
                                    },
                                    "modelVersion": {
                                        "type": "string",
                                        "default": "gpt-4"
                                    }
                                }
                            },
                            "callbackUrl": {
                                "type": "string",
                                "format": "uri",
                                "description": "Webhook URL for job completion notification"
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "202": {
                "description": "Job accepted for processing",
                "schema": {
                    "type": "object",
                    "properties": {
                        "jobId": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "queued"]},
                        "estimatedCompletion": {"type": "string", "format": "date-time"},
                        "pollUrl": {"type": "string", "format": "uri"}
                    }
                }
            },
            "400": {"description": "Invalid request"},
            "404": {"description": "Source not found"}
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/extraction/jobs/{jobId}
    # -------------------------------------------------------------------------
    GET_JOB_STATUS = {
        "method": "GET",
        "path": "/api/v1/extraction/jobs/{jobId}",
        "description": "Get extraction job status and results",
        "parameters": {
            "path": {
                "jobId": {
                    "type": "string",
                    "required": True,
                    "description": "Job identifier"
                }
            }
        },
        "responses": {
            "200": {
                "description": "Job status and results",
                "schema": {
                    "type": "object",
                    "properties": {
                        "jobId": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "processing", "completed", "failed", "cancelled"]
                        },
                        "sourceId": {"type": "string"},
                        "submittedAt": {"type": "string", "format": "date-time"},
                        "startedAt": {"type": "string", "format": "date-time"},
                        "completedAt": {"type": "string", "format": "date-time"},
                        "progress": {
                            "type": "object",
                            "properties": {
                                "stage": {"type": "string"},
                                "percentComplete": {"type": "integer"},
                                "entitiesExtracted": {"type": "integer"},
                                "relationshipsExtracted": {"type": "integer"}
                            }
                        },
                        "result": {
                            "type": "object",
                            "properties": {
                                "extractionId": {"type": "string"},
                                "entities": {"type": "array"},
                                "relationships": {"type": "array"},
                                "validationErrors": {"type": "array", "items": {"type": "string"}},
                                "processingTimeMs": {"type": "integer"}
                            }
                        },
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                                "details": {"type": "object"}
                            }
                        }
                    }
                }
            },
            "404": {"description": "Job not found"}
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/extraction/jobs
    # -------------------------------------------------------------------------
    LIST_JOBS = {
        "method": "GET",
        "path": "/api/v1/extraction/jobs",
        "description": "List extraction jobs with filtering",
        "parameters": {
            "query": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "processing", "completed", "failed", "cancelled"]
                },
                "sourceId": {"type": "string"},
                "fromDate": {"type": "string", "format": "date-time"},
                "toDate": {"type": "string", "format": "date-time"},
                "page": {"type": "integer", "default": 1},
                "pageSize": {"type": "integer", "default": 50}
            }
        },
        "responses": {
            "200": {
                "description": "List of extraction jobs",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "total": {"type": "integer"},
                        "page": {"type": "integer"},
                        "pageSize": {"type": "integer"},
                        "totalPages": {"type": "integer"}
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # DELETE /api/v1/extraction/jobs/{jobId}
    # -------------------------------------------------------------------------
    CANCEL_JOB = {
        "method": "DELETE",
        "path": "/api/v1/extraction/jobs/{jobId}",
        "description": "Cancel a pending or running extraction job",
        "parameters": {
            "path": {
                "jobId": {
                    "type": "string",
                    "required": True
                }
            }
        },
        "responses": {
            "204": {"description": "Job cancelled"},
            "404": {"description": "Job not found"},
            "409": {"description": "Job cannot be cancelled (already completed or failed)"}
        }
    }


# =============================================================================
# 3. ENTITY MANAGEMENT API
# =============================================================================

class EntityManagementAPI:
    """
    API endpoints for searching, retrieving, and managing entities.
    
    Base Path: /api/v1/entities
    """
    
    # -------------------------------------------------------------------------
    # GET /api/v1/entities
    # -------------------------------------------------------------------------
    SEARCH_ENTITIES = {
        "method": "GET",
        "path": "/api/v1/entities",
        "description": "Search entities with filtering and pagination",
        "parameters": {
            "query": {
                "q": {
                    "type": "string",
                    "description": "Full-text search query"
                },
                "entityTypes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by entity types"
                },
                "confidenceMin": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "confidenceMax": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "sourceId": {
                    "type": "string",
                    "description": "Filter by extraction source"
                },
                "hasRelationships": {
                    "type": "boolean",
                    "description": "Filter entities by relationship presence"
                },
                "page": {"type": "integer", "default": 1},
                "pageSize": {"type": "integer", "default": 50},
                "sortBy": {
                    "type": "string",
                    "enum": ["name", "confidence", "createdAt", "relevance"],
                    "default": "relevance"
                },
                "sortOrder": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "default": "desc"
                }
            }
        },
        "responses": {
            "200": {
                "description": "Search results",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entityId": {"type": "string"},
                                    "entityType": {"type": "string"},
                                    "canonicalName": {"type": "string"},
                                    "description": {"type": "string"},
                                    "confidenceScore": {"type": "number"},
                                    "alternativeNames": {"type": "array", "items": {"type": "string"}},
                                    "relationshipCount": {"type": "integer"},
                                    "sourceId": {"type": "string"},
                                    "extractedAt": {"type": "string", "format": "date-time"}
                                }
                            }
                        },
                        "total": {"type": "integer"},
                        "facets": {
                            "type": "object",
                            "properties": {
                                "entityTypes": {"type": "object"},
                                "confidenceRanges": {"type": "object"},
                                "sources": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # POST /api/v1/entities/search
    # -------------------------------------------------------------------------
    ADVANCED_SEARCH = {
        "method": "POST",
        "path": "/api/v1/entities/search",
        "description": "Advanced entity search with semantic similarity",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "semanticSearch": {"type": "boolean", "default": True},
                            "similarityThreshold": {"type": "number", "default": 0.75},
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "entityTypes": {"type": "array", "items": {"type": "string"}},
                                    "confidenceRange": {
                                        "type": "object",
                                        "properties": {
                                            "min": {"type": "number"},
                                            "max": {"type": "number"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "Search results with similarity scores",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entity": {"type": "object"},
                                    "matchScore": {"type": "number"},
                                    "matchType": {"type": "string", "enum": ["exact", "semantic", "fuzzy"]}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/entities/{entityId}
    # -------------------------------------------------------------------------
    GET_ENTITY = {
        "method": "GET",
        "path": "/api/v1/entities/{entityId}",
        "description": "Get detailed entity information",
        "parameters": {
            "path": {
                "entityId": {
                    "type": "string",
                    "required": True
                }
            },
            "query": {
                "includeRelationships": {
                    "type": "boolean",
                    "default": True
                },
                "relationshipDepth": {
                    "type": "integer",
                    "default": 1,
                    "maximum": 3
                },
                "includeProvenance": {
                    "type": "boolean",
                    "default": True
                }
            }
        },
        "responses": {
            "200": {
                "description": "Entity details",
                "schema": {
                    "type": "object",
                    "properties": {
                        "entityId": {"type": "string"},
                        "entityType": {"type": "string"},
                        "canonicalName": {"type": "string"},
                        "properties": {"type": "object"},
                        "alternativeNames": {"type": "array", "items": {"type": "string"}},
                        "confidenceScore": {"type": "number"},
                        "relationships": {
                            "type": "object",
                            "properties": {
                                "outgoing": {"type": "array"},
                                "incoming": {"type": "array"}
                            }
                        },
                        "provenance": {
                            "type": "object",
                            "properties": {
                                "sourceId": {"type": "string"},
                                "extractionId": {"type": "string"},
                                "extractedAt": {"type": "string", "format": "date-time"},
                                "modelVersion": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "404": {"description": "Entity not found"}
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/entities/{entityId}/relationships
    # -------------------------------------------------------------------------
    GET_ENTITY_RELATIONSHIPS = {
        "method": "GET",
        "path": "/api/v1/entities/{entityId}/relationships",
        "description": "Get relationships for an entity",
        "parameters": {
            "path": {
                "entityId": {"type": "string", "required": True}
            },
            "query": {
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both"
                },
                "relationshipTypes": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "minConfidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                }
            }
        },
        "responses": {
            "200": {
                "description": "Entity relationships",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "relationshipId": {"type": "string"},
                            "relationshipType": {"type": "string"},
                            "direction": {"type": "string"},
                            "relatedEntity": {"type": "object"},
                            "confidenceScore": {"type": "number"},
                            "evidenceText": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # PATCH /api/v1/entities/{entityId}
    # -------------------------------------------------------------------------
    UPDATE_ENTITY = {
        "method": "PATCH",
        "path": "/api/v1/entities/{entityId}",
        "description": "Update entity properties (manual curation)",
        "parameters": {
            "path": {
                "entityId": {"type": "string", "required": True}
            }
        },
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "canonicalName": {"type": "string"},
                            "properties": {"type": "object"},
                            "alternativeNames": {"type": "array", "items": {"type": "string"}},
                            "curationNotes": {"type": "string"}
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {"description": "Entity updated"},
            "404": {"description": "Entity not found"},
            "403": {"description": "Curation privileges required"}
        }
    }
    
    # -------------------------------------------------------------------------
    # POST /api/v1/entities/merge
    # -------------------------------------------------------------------------
    MERGE_ENTITIES = {
        "method": "POST",
        "path": "/api/v1/entities/merge",
        "description": "Merge duplicate entities (manual coreference resolution)",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["sourceEntityIds", "targetEntityId"],
                        "properties": {
                            "sourceEntityIds": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Entities to merge (will be deprecated)"
                            },
                            "targetEntityId": {
                                "type": "string",
                                "description": "Entity to merge into (or 'new' to create)"
                            },
                            "canonicalName": {
                                "type": "string",
                                "description": "Name for merged entity (if creating new)"
                            },
                            "curationNotes": {"type": "string"}
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {"description": "Entities merged successfully"},
            "400": {"description": "Invalid merge request"}
        }
    }


# =============================================================================
# 4. VALIDATION REPORTING API
# =============================================================================

class ValidationReportingAPI:
    """
    API endpoints for accessing validation results and quality metrics.
    
    Base Path: /api/v1/validation
    """
    
    # -------------------------------------------------------------------------
    # GET /api/v1/validation/reports
    # -------------------------------------------------------------------------
    LIST_VALIDATION_REPORTS = {
        "method": "GET",
        "path": "/api/v1/validation/reports",
        "description": "List validation reports",
        "parameters": {
            "query": {
                "extractionId": {"type": "string"},
                "sourceId": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["ERROR", "WARNING", "INFO"]
                },
                "fromDate": {"type": "string", "format": "date-time"},
                "toDate": {"type": "string", "format": "date-time"}
            }
        },
        "responses": {
            "200": {
                "description": "List of validation reports",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "reportId": {"type": "string"},
                            "extractionId": {"type": "string"},
                            "generatedAt": {"type": "string", "format": "date-time"},
                            "summary": {
                                "type": "object",
                                "properties": {
                                    "totalChecks": {"type": "integer"},
                                    "passed": {"type": "integer"},
                                    "failed": {"type": "integer"},
                                    "errors": {"type": "integer"},
                                    "warnings": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/validation/reports/{reportId}
    # -------------------------------------------------------------------------
    GET_VALIDATION_REPORT = {
        "method": "GET",
        "path": "/api/v1/validation/reports/{reportId}",
        "description": "Get detailed validation report",
        "parameters": {
            "path": {
                "reportId": {"type": "string", "required": True}
            }
        },
        "responses": {
            "200": {
                "description": "Validation report details",
                "schema": {
                    "type": "object",
                    "properties": {
                        "reportId": {"type": "string"},
                        "extractionId": {"type": "string"},
                        "generatedAt": {"type": "string", "format": "date-time"},
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ruleId": {"type": "string"},
                                    "ruleType": {"type": "string"},
                                    "passed": {"type": "boolean"},
                                    "severity": {"type": "string"},
                                    "message": {"type": "string"},
                                    "affectedEntities": {"type": "array", "items": {"type": "string"}},
                                    "affectedRelationships": {"type": "array", "items": {"type": "string"}},
                                    "suggestion": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/validation/quality-metrics
    # -------------------------------------------------------------------------
    GET_QUALITY_METRICS = {
        "method": "GET",
        "path": "/api/v1/validation/quality-metrics",
        "description": "Get overall quality metrics for the knowledge graph",
        "parameters": {
            "query": {
                "timeRange": {
                    "type": "string",
                    "enum": ["24h", "7d", "30d", "90d", "all"],
                    "default": "30d"
                }
            }
        },
        "responses": {
            "200": {
                "description": "Quality metrics",
                "schema": {
                    "type": "object",
                    "properties": {
                        "overallScore": {"type": "number"},
                        "metrics": {
                            "type": "object",
                            "properties": {
                                "completeness": {"type": "number"},
                                "consistency": {"type": "number"},
                                "accuracy": {"type": "number"},
                                "coverage": {"type": "number"}
                            }
                        },
                        "entityTypeBreakdown": {"type": "object"},
                        "trend": {"type": "array"}
                    }
                }
            }
        }
    }


# =============================================================================
# 5. REFERENCE MODEL INTEGRATION API
# =============================================================================

class ReferenceModelAPI:
    """
    API endpoints for managing industry reference model mappings.
    
    Base Path: /api/v1/reference-models
    """
    
    # -------------------------------------------------------------------------
    # GET /api/v1/reference-models
    # -------------------------------------------------------------------------
    LIST_MODELS = {
        "method": "GET",
        "path": "/api/v1/reference-models",
        "description": "List available reference models",
        "responses": {
            "200": {
                "description": "List of reference models",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "modelType": {"type": "string"},
                            "name": {"type": "string"},
                            "version": {"type": "string"},
                            "description": {"type": "string"},
                            "conceptCount": {"type": "integer"},
                            "mappingCount": {"type": "integer"},
                            "coverage": {"type": "number"}
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/reference-models/{modelType}/concepts
    # -------------------------------------------------------------------------
    LIST_CONCEPTS = {
        "method": "GET",
        "path": "/api/v1/reference-models/{modelType}/concepts",
        "description": "List concepts from a reference model",
        "parameters": {
            "path": {
                "modelType": {
                    "type": "string",
                    "required": True,
                    "enum": ["apqc", "bian", "fibo"]
                }
            },
            "query": {
                "search": {"type": "string"},
                "hierarchyLevel": {"type": "integer"},
                "parentId": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "pageSize": {"type": "integer", "default": 50}
            }
        },
        "responses": {
            "200": {
                "description": "List of reference model concepts",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "conceptId": {"type": "string"},
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "hierarchyLevel": {"type": "integer"},
                                    "parentId": {"type": "string"},
                                    "mappedEntityCount": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/reference-models/{modelType}/mappings
    # -------------------------------------------------------------------------
    LIST_MAPPINGS = {
        "method": "GET",
        "path": "/api/v1/reference-models/{modelType}/mappings",
        "description": "List mappings between Value Fabric and reference model",
        "parameters": {
            "path": {
                "modelType": {"type": "string", "required": True}
            },
            "query": {
                "status": {
                    "type": "string",
                    "enum": ["auto_mapped", "manually_mapped", "proposed", "rejected"]
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low", "uncertain"]
                },
                "entityType": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "pageSize": {"type": "integer", "default": 50}
            }
        },
        "responses": {
            "200": {
                "description": "List of mappings",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total": {"type": "integer"},
                                "byStatus": {"type": "object"},
                                "byConfidence": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # POST /api/v1/reference-models/{modelType}/mappings
    # -------------------------------------------------------------------------
    CREATE_MAPPING = {
        "method": "POST",
        "path": "/api/v1/reference-models/{modelType}/mappings",
        "description": "Create manual mapping",
        "parameters": {
            "path": {
                "modelType": {"type": "string", "required": True}
            }
        },
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["vfEntityId", "referenceConceptId"],
                        "properties": {
                            "vfEntityId": {"type": "string"},
                            "referenceConceptId": {"type": "string"},
                            "mappingType": {
                                "type": "string",
                                "enum": ["exact", "narrow", "broad", "related"],
                                "default": "exact"
                            },
                            "notes": {"type": "string"}
                        }
                    }
                }
            }
        },
        "responses": {
            "201": {"description": "Mapping created"},
            "400": {"description": "Invalid mapping"},
            "404": {"description": "Entity or concept not found"}
        }
    }
    
    # -------------------------------------------------------------------------
    # POST /api/v1/reference-models/{modelType}/generate-mappings
    # -------------------------------------------------------------------------
    GENERATE_MAPPINGS = {
        "method": "POST",
        "path": "/api/v1/reference-models/{modelType}/generate-mappings",
        "description": "Generate automated mapping suggestions",
        "parameters": {
            "path": {
                "modelType": {"type": "string", "required": True}
            }
        },
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "entityTypes": {"type": "array", "items": {"type": "string"}},
                            "similarityThreshold": {"type": "number", "default": 0.75},
                            "autoApproveHighConfidence": {"type": "boolean", "default": False}
                        }
                    }
                }
            }
        },
        "responses": {
            "202": {
                "description": "Mapping generation job started",
                "schema": {
                    "type": "object",
                    "properties": {
                        "jobId": {"type": "string"},
                        "status": {"type": "string"}
                    }
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/reference-models/{modelType}/crosswalk-report
    # -------------------------------------------------------------------------
    GET_CROSSWALK_REPORT = {
        "method": "GET",
        "path": "/api/v1/reference-models/{modelType}/crosswalk-report",
        "description": "Get crosswalk coverage report",
        "parameters": {
            "path": {
                "modelType": {"type": "string", "required": True}
            },
            "query": {
                "format": {
                    "type": "string",
                    "enum": ["json", "csv", "xlsx"],
                    "default": "json"
                }
            }
        },
        "responses": {
            "200": {
                "description": "Crosswalk report",
                "content": {
                    "application/json": {"schema": {"type": "object"}},
                    "text/csv": {"schema": {"type": "string"}},
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                }
            }
        }
    }


# =============================================================================
# 6. KNOWLEDGE GRAPH EXPORT API
# =============================================================================

class KnowledgeGraphExportAPI:
    """
    API endpoints for exporting knowledge graph data.
    
    Base Path: /api/v1/export
    """
    
    # -------------------------------------------------------------------------
    # POST /api/v1/export/rdf
    # -------------------------------------------------------------------------
    EXPORT_RDF = {
        "method": "POST",
        "path": "/api/v1/export/rdf",
        "description": "Export knowledge graph as RDF",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["turtle", "ntriples", "jsonld", "rdfxml"],
                                "default": "turtle"
                            },
                            "entityTypes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by entity types"
                            },
                            "sourceIds": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "includeSchema": {
                                "type": "boolean",
                                "default": True
                            },
                            "graphOrganization": {
                                "type": "string",
                                "enum": ["single", "by_source", "by_type"],
                                "default": "single"
                            },
                            "confidenceMin": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "RDF export",
                "content": {
                    "text/turtle": {"schema": {"type": "string"}},
                    "application/n-triples": {"schema": {"type": "string"}},
                    "application/ld+json": {"schema": {"type": "object"}},
                    "application/rdf+xml": {"schema": {"type": "string"}}
                }
            }
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/export/sparql
    # -------------------------------------------------------------------------
    SPARQL_ENDPOINT = {
        "method": "GET",
        "path": "/api/v1/export/sparql",
        "description": "SPARQL query endpoint (read-only)",
        "parameters": {
            "query": {
                "query": {
                    "type": "string",
                    "required": True,
                    "description": "SPARQL SELECT/CONSTRUCT/ASK query"
                }
            }
        },
        "responses": {
            "200": {
                "description": "Query results",
                "content": {
                    "application/sparql-results+json": {"schema": {"type": "object"}},
                    "application/sparql-results+xml": {"schema": {"type": "string"}},
                    "text/csv": {"schema": {"type": "string"}}
                }
            },
            "400": {"description": "Invalid SPARQL query"}
        }
    }
    
    # -------------------------------------------------------------------------
    # POST /api/v1/export/sparql
    # -------------------------------------------------------------------------
    SPARQL_QUERY_POST = {
        "method": "POST",
        "path": "/api/v1/export/sparql",
        "description": "SPARQL query endpoint (POST for complex queries)",
        "requestBody": {
            "required": True,
            "content": {
                "application/sparql-query": {
                    "schema": {"type": "string"}
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {"description": "Query results"}
        }
    }
    
    # -------------------------------------------------------------------------
    # GET /api/v1/export/network
    # -------------------------------------------------------------------------
    EXPORT_NETWORK = {
        "method": "GET",
        "path": "/api/v1/export/network",
        "description": "Export as network graph format (for visualization)",
        "parameters": {
            "query": {
                "format": {
                    "type": "string",
                    "enum": ["cytoscape", "d3", "graphml", "gexf"],
                    "default": "cytoscape"
                },
                "centerEntityId": {
                    "type": "string",
                    "description": "Center node for neighborhood export"
                },
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "maximum": 5
                },
                "entityTypes": {"type": "array", "items": {"type": "string"}},
                "relationshipTypes": {"type": "array", "items": {"type": "string"}}
            }
        },
        "responses": {
            "200": {
                "description": "Network export",
                "content": {
                    "application/json": {"schema": {"type": "object"}}
                }
            }
        }
    }


# =============================================================================
# API ROUTE REGISTRY
# =============================================================================

API_ROUTES = {
    # Ontology Management
    "list_classes": OntologyManagementAPI.LIST_CLASSES,
    "get_class": OntologyManagementAPI.GET_CLASS,
    "list_relationships": OntologyManagementAPI.LIST_RELATIONSHIPS,
    "create_class": OntologyManagementAPI.CREATE_CLASS,
    "export_ontology": OntologyManagementAPI.EXPORT_ONTOLOGY,
    
    # Extraction Jobs
    "submit_job": ExtractionJobAPI.SUBMIT_JOB,
    "get_job_status": ExtractionJobAPI.GET_JOB_STATUS,
    "list_jobs": ExtractionJobAPI.LIST_JOBS,
    "cancel_job": ExtractionJobAPI.CANCEL_JOB,
    
    # Entity Management
    "search_entities": EntityManagementAPI.SEARCH_ENTITIES,
    "advanced_search": EntityManagementAPI.ADVANCED_SEARCH,
    "get_entity": EntityManagementAPI.GET_ENTITY,
    "get_entity_relationships": EntityManagementAPI.GET_ENTITY_RELATIONSHIPS,
    "update_entity": EntityManagementAPI.UPDATE_ENTITY,
    "merge_entities": EntityManagementAPI.MERGE_ENTITIES,
    
    # Validation Reporting
    "list_validation_reports": ValidationReportingAPI.LIST_VALIDATION_REPORTS,
    "get_validation_report": ValidationReportingAPI.GET_VALIDATION_REPORT,
    "get_quality_metrics": ValidationReportingAPI.GET_QUALITY_METRICS,
    
    # Reference Model Integration
    "list_models": ReferenceModelAPI.LIST_MODELS,
    "list_concepts": ReferenceModelAPI.LIST_CONCEPTS,
    "list_mappings": ReferenceModelAPI.LIST_MAPPINGS,
    "create_mapping": ReferenceModelAPI.CREATE_MAPPING,
    "generate_mappings": ReferenceModelAPI.GENERATE_MAPPINGS,
    "get_crosswalk_report": ReferenceModelAPI.GET_CROSSWALK_REPORT,
    
    # Knowledge Graph Export
    "export_rdf": KnowledgeGraphExportAPI.EXPORT_RDF,
    "sparql_endpoint": KnowledgeGraphExportAPI.SPARQL_ENDPOINT,
    "sparql_query_post": KnowledgeGraphExportAPI.SPARQL_QUERY_POST,
    "export_network": KnowledgeGraphExportAPI.EXPORT_NETWORK,
}
